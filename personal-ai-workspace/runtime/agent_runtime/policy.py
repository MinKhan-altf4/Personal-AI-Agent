"""Permission enforcement: the runtime counterpart of config/permissions.yaml (DEC-002, DEC-004, DEC-005)."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable

from .config import AgentSpec, ProjectSpec, Workspace

# Paths no agent may read or write, whatever its level (permissions.yaml global_denials).
SECRET_PATTERNS = (".env", ".env.*", "*.pem", "*.key", "*.pfx", "*.p12", "secrets", "secrets/*")
# Workspace internals that agents must not touch directly.
PROTECTED_PREFIXES = ("runtime/data", "runtime/.venv", ".git")
# Paths in a project repository start with this prefix, e.g. "project:KnightServer/Program.cs".
PROJECT_PREFIX = "project:"


class PolicyError(Exception):
    """Raised when an action is outside the agent's granted permissions."""


Approver = Callable[[str], bool]


def deny_all(_: str) -> bool:
    return False


def approve_all(_: str) -> bool:
    return True


def is_project_path(relative: str) -> bool:
    return relative.strip().startswith(PROJECT_PREFIX)


@dataclass
class Policy:
    ws: Workspace
    approver: Approver = deny_all
    project: ProjectSpec | None = None

    # --- tool level ------------------------------------------------------
    def check_tool(self, agent: AgentSpec, tool: str) -> None:
        if not agent.active:
            raise PolicyError(f"Agent '{agent.id}' is not active")
        if tool not in agent.tools:
            raise PolicyError(f"Agent '{agent.id}' is not registered for tool '{tool}'")
        min_level = self.ws.tool_min_levels.get(tool)
        if min_level is None:
            raise PolicyError(f"Tool '{tool}' is not in the permissions catalog (default deny)")
        if agent.permission_level < min_level:
            raise PolicyError(
                f"Agent '{agent.id}' (level {agent.permission_level}) cannot use '{tool}' (min level {min_level})"
            )

    # --- paths -----------------------------------------------------------
    def _area(self, relative: str) -> tuple[Path, str, tuple[str, ...], tuple[str, ...]]:
        """Return (root, path-inside-root, protected prefixes, excluded names) for a tool path."""
        text = relative.strip()
        if is_project_path(text):
            if self.project is None:
                raise PolicyError("This task has no project; 'project:' paths need `run --project <id>`")
            return self.project.source_path, text[len(PROJECT_PREFIX):], (".git",), self.project.exclude
        return self.ws.root, text, PROTECTED_PREFIXES, ()

    def resolve(self, relative: str) -> Path:
        """Resolve a tool path; reject anything outside its root, secret, protected, or excluded."""
        root, inner, protected, excluded = self._area(relative)
        inner = inner.replace("\\", "/").strip()
        if inner in {"", "."}:
            return root
        candidate = (root / inner).resolve()
        try:
            rel = candidate.relative_to(root)
        except ValueError as exc:
            raise PolicyError(f"Path '{relative}' is outside the allowed folder") from exc
        posix = PurePosixPath(rel.as_posix())
        for part in posix.parts:
            if any(fnmatch.fnmatch(part, pat) for pat in SECRET_PATTERNS):
                raise PolicyError(f"Access to secret path '{relative}' is denied")
            if any(fnmatch.fnmatch(part, pat) for pat in excluded):
                raise PolicyError(f"Path '{relative}' is excluded for this project")
        if any(posix.as_posix() == p or posix.as_posix().startswith(p + "/") for p in protected):
            raise PolicyError(f"Path '{relative}' is reserved")
        return candidate

    def display(self, path: Path) -> str:
        """Tool-path spelling of an absolute path (the inverse of resolve)."""
        if self.project is not None:
            try:
                return PROJECT_PREFIX + path.relative_to(self.project.source_path).as_posix()
            except ValueError:
                pass
        return path.relative_to(self.ws.root).as_posix()

    def check_write(self, agent: AgentSpec, relative: str, task_id: str) -> Path:
        path = self.resolve(relative)
        if agent.permission_level < 1:
            raise PolicyError(f"Agent '{agent.id}' (level 0) may not write files")

        if is_project_path(relative):
            # DEC-005: project repos are written only by level-2 agents, only if the project allows it,
            # and every single write is confirmed by the Commander.
            if agent.permission_level < 2:
                raise PolicyError(f"Agent '{agent.id}' (level {agent.permission_level}) may not write project files")
            if not self.project.writable:
                raise PolicyError(f"Project '{self.project.id}' is registered read-only")
            if agent.id == "qa_auditor":
                raise PolicyError("qa_auditor never edits the deliverable it reviews (DEC-003)")
            if not self.approver(f"{agent.id} wants to write {relative} in project '{self.project.id}'"):
                raise PolicyError(f"Write to '{relative}' was not approved by the Commander")
            return path

        task_dir = (self.ws.tasks_dir / task_id).resolve()
        inside_task = path == task_dir or task_dir in path.parents
        if agent.permission_level == 1 and not inside_task:
            raise PolicyError(f"Agent '{agent.id}' (level 1) may write only inside tasks/{task_id}/")
        if agent.id == "qa_auditor" and not inside_task:
            # DEC-003: QA runs tests but never edits the deliverable it reviews.
            raise PolicyError("qa_auditor may write only its own review files in the task folder (DEC-003)")
        if not inside_task and not self.approver(f"{agent.id} wants to write {relative}"):
            raise PolicyError(f"Write to '{relative}' was not approved by the Commander")
        return path
