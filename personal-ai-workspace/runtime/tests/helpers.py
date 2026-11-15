"""Shared fixtures: a disposable copy of the real workspace and a scripted model."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from agent_runtime.model import ModelTurn, ToolCall

WORKSPACE = Path(__file__).resolve().parents[2]          # personal-ai-workspace/
REPO = WORKSPACE.parent                                  # repository root (holds ../skills)
COPY_DIRS = ("config", "agents", "skills", "templates", "workflows", "docs")
COPY_FILES = ("AGENTS.md", "PROJECT_CONTEXT.md", "DECISIONS.md", "README.md")


class TempWorkspace:
    """Copies the canonical workspace into a temp dir so tests never touch real task records."""

    def __enter__(self) -> Path:
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        shutil.copytree(REPO / "skills", base / "skills")
        root = base / "personal-ai-workspace"
        root.mkdir()
        for d in COPY_DIRS:
            shutil.copytree(WORKSPACE / d, root / d)
        for f in COPY_FILES:
            shutil.copy2(WORKSPACE / f, root / f)
        (root / "tasks").mkdir()
        shutil.copy2(WORKSPACE / "tasks" / "INDEX.md", root / "tasks" / "INDEX.md")
        (root / ".env").write_text("SECRET=1\n", encoding="utf-8")
        (root / "notes.md").write_text("hello\n", encoding="utf-8")
        return root

    def __exit__(self, *exc) -> None:
        self._tmp.cleanup()


def text_turn(text: str) -> ModelTurn:
    return ModelTurn("end_turn", [{"type": "text", "text": text}], text, model="scripted")


def tool_turn(*calls: tuple[str, dict]) -> ModelTurn:
    tcs = [ToolCall(f"call_{i}", name, args) for i, (name, args) in enumerate(calls)]
    content = [{"type": "tool_use", "id": c.id, "name": c.name, "input": c.input} for c in tcs]
    return ModelTurn("tool_use", content, tool_calls=tcs, model="scripted")


class ScriptedModel:
    """Returns pre-baked turns per purpose ('classify', 'execute', 'review') in order."""

    def __init__(self, script: dict[str, list[ModelTurn]]):
        self.script = {k: list(v) for k, v in script.items()}
        self.calls: list[dict] = []

    def complete(self, *, purpose, profile, system, messages, tools, output_schema=None) -> ModelTurn:
        self.calls.append({"purpose": purpose, "messages": list(messages), "tools": tools,
                           "system": system, "output_schema": output_schema})
        return self.script[purpose].pop(0)
