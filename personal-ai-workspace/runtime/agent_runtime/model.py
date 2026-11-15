"""Model adapters: the real Claude client and an offline scripted model for --dry-run and tests."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Protocol

from .config import ModelProfile

FALLBACK_BETA = "server-side-fallback-2026-07-01"


class ModelError(Exception):
    """A model call failed in a way the task cannot recover from."""


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict


@dataclass
class ModelTurn:
    stop_reason: str
    content: list                     # assistant content to append back unchanged
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    model: str = ""
    refusal_category: str | None = None


class ModelClient(Protocol):
    def complete(self, *, purpose: str, profile: ModelProfile, system: list[dict], messages: list,
                 tools: list[dict], output_schema: dict | None = None) -> ModelTurn: ...


# ---------------------------------------------------------------------------
class AnthropicModel:
    """Calls Claude through the official SDK. Credentials come from the environment (DEC-004)."""

    def __init__(self, refusal_fallback: str | None = "default"):
        import anthropic  # imported lazily so --dry-run works without credentials

        self._anthropic = anthropic
        self.client = anthropic.Anthropic()
        self.refusal_fallback = refusal_fallback

    def complete(self, *, purpose, profile, system, messages, tools, output_schema=None) -> ModelTurn:
        output_config: dict = {"effort": profile.effort}
        if output_schema is not None:
            output_config["format"] = {"type": "json_schema", "schema": output_schema}
        kwargs: dict = {
            "model": profile.model,
            "max_tokens": profile.max_tokens,
            "system": system,
            "messages": messages,
            "output_config": output_config,
            "cache_control": {"type": "ephemeral"},
        }
        if tools:
            kwargs["tools"] = tools
        a = self._anthropic
        try:
            if self.refusal_fallback:
                response = self.client.beta.messages.create(
                    betas=[FALLBACK_BETA], fallbacks=self.refusal_fallback, **kwargs
                )
            else:
                response = self.client.messages.create(**kwargs)
        except a.AuthenticationError as exc:
            raise ModelError("Authentication failed: set ANTHROPIC_API_KEY or run `ant auth login`.") from exc
        except a.PermissionDeniedError as exc:
            raise ModelError(f"Permission denied by the API: {exc.message}") from exc
        except a.NotFoundError as exc:
            raise ModelError(f"Model or endpoint not found ({profile.model}): {exc.message}") from exc
        except a.BadRequestError as exc:
            raise ModelError(f"Bad request: {exc.message}") from exc
        except a.RateLimitError as exc:
            raise ModelError("Rate limited after retries; try again later.") from exc
        except a.APIStatusError as exc:
            raise ModelError(f"API error {exc.status_code}: {exc.message}") from exc
        except a.APIConnectionError as exc:
            raise ModelError("Network error: could not reach the Anthropic API.") from exc

        text_parts, calls = [], []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                calls.append(ToolCall(block.id, block.name, dict(block.input)))
        usage = response.usage
        category = None
        if response.stop_reason == "refusal" and getattr(response, "stop_details", None):
            category = response.stop_details.category
        return ModelTurn(
            stop_reason=response.stop_reason,
            content=list(response.content),
            text="\n".join(text_parts),
            tool_calls=calls,
            usage={
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
                "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
            },
            model=response.model,
            refusal_category=category,
        )


# ---------------------------------------------------------------------------
KEYWORD_ROUTES = (
    ("engineering", r"\b(code|bug|test|refactor|implement|api|python|script|lỗi|lập trình|viết code)\b"),
    ("research", r"\b(research|compare|sources?|market|tìm hiểu|nghiên cứu|so sánh)\b"),
    ("qa_auditor", r"\b(review|audit|kiểm tra|rà soát)\b"),
)


class DryRunModel:
    """Deterministic offline stand-in for Claude. Exercises the full loop without network or cost."""

    model_name = "dry-run"

    def __init__(self, executors: list[str]):
        self.executors = executors

    def _route(self, request: str) -> str:
        for agent, pattern in KEYWORD_ROUTES:
            if agent in self.executors and re.search(pattern, request, re.IGNORECASE):
                return agent
        return "knowledge_manager" if "knowledge_manager" in self.executors else self.executors[0]

    @staticmethod
    def _last_user_text(messages: list) -> str:
        for msg in reversed(messages):
            if msg["role"] == "user" and isinstance(msg["content"], str):
                return msg["content"]
        return ""

    def complete(self, *, purpose, profile, system, messages, tools, output_schema=None) -> ModelTurn:
        usage = {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
        if purpose == "classify":
            request = self._last_user_text(messages).split("Commander's request:", 1)[-1].strip()
            plan = {
                "title": request.strip().splitlines()[0][:80] or "Untitled task",
                "project": "global",
                "primary_agent": self._route(request),
                "objective": request.strip(),
                "acceptance_criteria": ["A report is produced", "No files outside the task folder are changed"],
                "needs_qa": True,
                "clarification_needed": "",
            }
            text = json.dumps(plan, ensure_ascii=False)
            return ModelTurn("end_turn", [{"type": "text", "text": text}], text, usage=usage, model=self.model_name)

        tool_names = {t["name"] for t in tools}
        already_called = any(
            isinstance(m["content"], list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in m["content"])
            for m in messages if m["role"] == "user"
        )
        if not already_called and "list_dir" in tool_names:
            in_project = "Project repository:" in self._last_user_text(messages[:1])
            call = ToolCall("dryrun_1", "list_dir", {"path": "project:" if in_project else "."})
            content = [{"type": "tool_use", "id": call.id, "name": call.name, "input": call.input}]
            return ModelTurn("tool_use", content, tool_calls=[call], usage=usage, model=self.model_name)

        if purpose == "review":
            text = ("## QA review (dry run)\n\nDry-run mode: no real review was performed.\n\n"
                    "OUTCOME: PASS WITH NOTES")
        else:
            text = ("## Report (dry run)\n\nDry-run mode: the runtime loop, tools, policy checks and persistence ran, "
                    "but no model was called, so no real work was done.\n\nSTATUS: partial")
        return ModelTurn("end_turn", [{"type": "text", "text": text}], text, usage=usage, model=self.model_name)
