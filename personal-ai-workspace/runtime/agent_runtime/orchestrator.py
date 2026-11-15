"""Task state machine: intake -> execute -> optional QA -> report (workflows/task-execution.md)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Callable

from . import prompts, tools
from .config import AgentSpec, Workspace
from .model import ModelClient, ModelError, ModelTurn
from .policy import Policy
from .store import TaskStore

STATUS_RE = re.compile(r"^\s*STATUS:\s*(completed|partial|blocked)\s*$", re.IGNORECASE | re.MULTILINE)
OUTCOME_RE = re.compile(r"^\s*OUTCOME:\s*(PASS WITH NOTES|PASS|FAIL|BLOCKED)\s*$", re.IGNORECASE | re.MULTILINE)

Progress = Callable[[str], None]


@dataclass
class AgentRun:
    agent_id: str
    text: str = ""
    status: str = "partial"
    turns: int = 0
    tool_calls: int = 0
    tool_errors: int = 0
    usage: dict = field(default_factory=lambda: {"input_tokens": 0, "output_tokens": 0,
                                                 "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0})
    notes: list[str] = field(default_factory=list)


@dataclass
class TaskResult:
    task_id: str
    status: str
    plan: dict
    executor: AgentRun | None
    review: AgentRun | None
    review_outcome: str | None
    report_path: str


class Orchestrator:
    def __init__(self, ws: Workspace, store: TaskStore, model: ModelClient, policy: Policy,
                 progress: Progress = lambda _: None, today: date | None = None):
        self.ws, self.store, self.model, self.policy = ws, store, model, policy
        self.progress = progress
        self.today = today or date.today()
        self.project = policy.project  # set by `run --project <id>` (DEC-005)

    # ------------------------------------------------------------------
    def executors(self) -> list[str]:
        return [a.id for a in self.ws.active_agents() if a.id != "orchestrator"]

    def run(self, request: str) -> TaskResult:
        task_id = self.store.create(request, today=self.today,
                                    project=self.project.id if self.project else "global")
        self.store.log(task_id, "request", {"text": request})
        self.progress(f"[{task_id}] Đã tạo task, đang phân loại yêu cầu...")
        try:
            plan = self._classify(task_id, request)
        except ModelError as exc:
            return self._finish_blocked(task_id, {"title": "(intake failed)", "objective": request}, str(exc))

        if self.project is not None:
            plan["project"] = self.project.id
        self.store.update(task_id, title=plan["title"], project=plan.get("project") or "global",
                          primary_agent=plan["primary_agent"])
        self._write_brief(task_id, request, plan)
        if plan.get("clarification_needed", "").strip():
            question = plan["clarification_needed"].strip()
            self.progress(f"[{task_id}] Cần làm rõ: {question}")
            return self._finish_blocked(task_id, plan, f"Clarification needed: {question}")

        executor = self.ws.agent(plan["primary_agent"])
        self.store.update(task_id, status="in_progress")
        self.progress(f"[{task_id}] Giao cho {executor.id}: {plan['title']}")
        exec_run = self._run_agent(task_id, executor, "execute", self._execute_prompt(task_id, plan))

        review_run, outcome = None, None
        qa = self.ws.agents.get("qa_auditor")
        if plan.get("needs_qa") and qa and qa.active and executor.id != qa.id and exec_run.status != "blocked":
            self.store.update(task_id, status="review")
            self.progress(f"[{task_id}] QA & Auditor đang rà soát...")
            review_run = self._run_agent(task_id, qa, "review", self._review_prompt(task_id, plan, exec_run))
            m = OUTCOME_RE.findall(review_run.text)
            outcome = m[-1].upper() if m else "BLOCKED"

        status = exec_run.status
        if outcome == "FAIL" and status == "completed":
            status = "partial"
        report = self._write_report(task_id, request, plan, exec_run, review_run, outcome, status)
        self.store.update(task_id, status=status)
        self.store.log(task_id, "finished", {"status": status, "qa_outcome": outcome})
        self.progress(f"[{task_id}] Hoàn tất với trạng thái: {status}")
        return TaskResult(task_id, status, plan, exec_run, review_run, outcome, report)

    # ------------------------------------------------------------------
    def _classify(self, task_id: str, request: str) -> dict:
        orch = self.ws.agent("orchestrator")
        executors = self.executors()
        project_line = f"Project: {self.project.id}\n" if self.project else ""
        user = (f"Today: {self.today.isoformat()}\nTask ID: {task_id}\n{project_line}"
                f"Executors: {', '.join(executors)}\n\n"
                f"Commander's request:\n{request}")
        turn = self.model.complete(
            purpose="classify", profile=self.ws.profile_for(orch.id),
            system=prompts.system_blocks(self.ws, orch, "classify", self.project),
            messages=[{"role": "user", "content": user}], tools=[],
            output_schema=prompts.classify_schema(executors),
        )
        self._log_turn(task_id, orch.id, turn)
        if turn.stop_reason == "refusal":
            raise ModelError(f"The model declined the request (category: {turn.refusal_category}).")
        try:
            plan = json.loads(turn.text)
        except json.JSONDecodeError as exc:
            raise ModelError(f"Intake returned invalid JSON: {exc}") from exc
        if plan.get("primary_agent") not in executors:
            raise ModelError(f"Intake chose an unknown or inactive agent: {plan.get('primary_agent')!r}")
        self.store.log(task_id, "plan", plan, agent=orch.id)
        return plan

    def _run_agent(self, task_id: str, agent: AgentSpec, mode: str, user_prompt: str) -> AgentRun:
        run = AgentRun(agent.id)
        specs = tools.tools_for(agent)
        missing = tools.unimplemented_registry_tools(agent)
        if missing:
            run.notes.append(f"Registry tools not available in runtime v0.1: {', '.join(missing)}")
        ctx = tools.ToolContext(self.ws, self.policy, agent, task_id, self.store)
        system = prompts.system_blocks(self.ws, agent, mode, self.project)
        api_tools = [s.to_api() for s in specs]
        messages: list = [{"role": "user", "content": user_prompt}]
        profile = self.ws.profile_for(agent.id)

        for _ in range(self.ws.max_tool_turns):
            try:
                turn = self.model.complete(purpose=mode, profile=profile, system=system,
                                           messages=messages, tools=api_tools)
            except ModelError as exc:
                run.status, run.text = "blocked", f"Model call failed: {exc}"
                run.notes.append(str(exc))
                self.store.log(task_id, "model_error", {"error": str(exc)}, agent=agent.id)
                return run
            run.turns += 1
            for k, v in turn.usage.items():
                run.usage[k] = run.usage.get(k, 0) + (v or 0)
            self._log_turn(task_id, agent.id, turn)
            messages.append({"role": "assistant", "content": turn.content})

            if turn.stop_reason == "tool_use":
                results = []
                for call in turn.tool_calls:
                    self.progress(f"[{task_id}]   {agent.id} -> {call.name}({_short(call.input)})")
                    content, is_error = tools.execute(ctx, call.name, call.input)
                    run.tool_calls += 1
                    run.tool_errors += int(is_error)
                    results.append({"type": "tool_result", "tool_use_id": call.id,
                                    "content": content, "is_error": is_error})
                messages.append({"role": "user", "content": results})  # all results in one message
                continue
            if turn.stop_reason == "pause_turn":
                continue

            run.text = turn.text
            if turn.stop_reason == "refusal":
                run.status = "blocked"
                run.notes.append(f"Model declined (category: {turn.refusal_category}).")
            elif turn.stop_reason == "max_tokens":
                run.status = "partial"
                run.notes.append("Response hit max_tokens and may be cut off.")
            else:
                m = STATUS_RE.findall(turn.text)
                run.status = m[-1].lower() if m else "partial"
                if not m:
                    run.notes.append("Agent did not end with a STATUS line; recorded as partial.")
            return run

        run.status = "partial"
        run.notes.append(f"Stopped after {self.ws.max_tool_turns} model turns (max_tool_turns).")
        return run

    # ------------------------------------------------------------------
    def _execute_prompt(self, task_id: str, plan: dict) -> str:
        criteria = "\n".join(f"- {c}" for c in plan.get("acceptance_criteria", []))
        return (f"Task ID: {task_id}\nDate: {self.today.isoformat()}\nProject: {plan.get('project', 'global')}\n"
                f"Task folder: tasks/{task_id}/ (TASK.md there holds the brief)\n"
                + ("Project repository: use 'project:' paths (root: 'project:')\n" if self.project else "")
                + "\n"
                f"Objective:\n{plan['objective']}\n\nAcceptance criteria:\n{criteria}")

    def _review_prompt(self, task_id: str, plan: dict, exec_run: AgentRun) -> str:
        return (self._execute_prompt(task_id, plan)
                + f"\n\nThe primary agent ({exec_run.agent_id}) returned status '{exec_run.status}' "
                  f"and this report:\n\n<agent_report>\n{exec_run.text}\n</agent_report>\n\n"
                  f"Review it against the acceptance criteria. Your reply is saved into "
                  f"tasks/{task_id}/REPORT.md by the runtime.")

    def _log_turn(self, task_id: str, agent_id: str, turn: ModelTurn) -> None:
        self.store.log(task_id, "model_turn",
                       {"model": turn.model, "stop_reason": turn.stop_reason, "usage": turn.usage,
                        "tool_calls": [c.name for c in turn.tool_calls]}, agent=agent_id)

    def _task_dir(self, task_id: str):
        path = self.ws.tasks_dir / task_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _write_brief(self, task_id: str, request: str, plan: dict) -> None:
        criteria = "\n".join(f"- [ ] {c}" for c in plan.get("acceptance_criteria", []))
        text = (f"# Task — {plan['title']}\n\n- **Task ID:** {task_id}\n- **Project:** {plan.get('project', 'global')}\n"
                f"- **Primary agent:** {plan['primary_agent']}\n- **Created:** {self.today.isoformat()}\n"
                f"- **QA required:** {'yes' if plan.get('needs_qa') else 'no'}\n\n"
                f"## Request\n{request}\n\n## Objective\n{plan['objective']}\n\n## Acceptance criteria\n{criteria}\n")
        (self._task_dir(task_id) / "TASK.md").write_text(text, encoding="utf-8")

    def _finish_blocked(self, task_id: str, plan: dict, reason: str) -> TaskResult:
        self.progress(f"[{task_id}] Bị chặn: {reason}")
        run = AgentRun("orchestrator", text=reason, status="blocked", notes=[reason])
        report = self._write_report(task_id, plan.get("objective", ""), plan, run, None, None, "blocked")
        self.store.update(task_id, status="blocked")
        self.store.log(task_id, "finished", {"status": "blocked", "reason": reason})
        return TaskResult(task_id, "blocked", plan, run, None, None, report)

    def _write_report(self, task_id, request, plan, exec_run, review_run, outcome, status) -> str:
        runs = [r for r in (exec_run, review_run) if r]
        usage = {k: sum(r.usage.get(k, 0) for r in runs) for k in
                 ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")}
        notes = [n for r in runs for n in r.notes]
        lines = [
            "# Agent Execution Report", "",
            f"- **Task ID:** {task_id}",
            f"- **Agent:** {exec_run.agent_id if exec_run else '-'}"
            + (f" (QA: {review_run.agent_id})" if review_run else ""),
            f"- **Status:** {status}",
            f"- **QA outcome:** {outcome or 'not run'}",
            f"- **Date:** {self.today.isoformat()}", "",
            f"## Objective\n{plan.get('objective', request)}", "",
            "## Primary agent report", "", (exec_run.text or "(no report)") if exec_run else "(not run)", "",
        ]
        if review_run:
            lines += ["## QA review", "", review_run.text or "(no review)", ""]
        lines += [
            "## Runtime evidence (written by the runtime, not by an agent)", "",
            f"- Model turns: {sum(r.turns for r in runs)}; tool calls: {sum(r.tool_calls for r in runs)} "
            f"({sum(r.tool_errors for r in runs)} refused or failed)",
            f"- Tokens: input {usage['input_tokens']}, output {usage['output_tokens']}, "
            f"cache read {usage['cache_read_input_tokens']}, cache write {usage['cache_creation_input_tokens']}",
            f"- Full audit log: `python -m agent_runtime show {task_id}`",
        ]
        if notes:
            lines += ["", "## Runtime notes", *[f"- {n}" for n in notes]]
        path = self._task_dir(task_id) / "REPORT.md"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path.relative_to(self.ws.root).as_posix()


def _short(args: dict) -> str:
    text = ", ".join(f"{k}={v!r}" if k != "content" else f"content=<{len(v)} chars>" for k, v in args.items())
    return text if len(text) <= 80 else text[:77] + "..."
