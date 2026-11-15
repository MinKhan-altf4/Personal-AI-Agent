"""Permission enforcement: the runtime counterpart of config/permissions.yaml (DEC-002, DEC-004)."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable

from .config import AgentSpec, Workspace

# Paths no agent may read or write, whatever its level (permissions.yaml global_denials).
SECRET_PATTERNS = (".env", ".env.*", "*.pem", "*.key", "secrets", "secrets/*")
# Runtime internals that agents must not touch directly.
PROTECTED_PREFIXES = ("runtime/data", "runtime/.venv", ".git")


class PolicyError(Exception):
    """Raised when an action is outside the agent's granted permissions."""


Approver = Callable[[str], bool]


def deny_all(_: str) -> bool:
    return False


def approve_all(_: str) -> bool:
    return True


@dataclass
class Policy:
    ws: Workspace
    approver: Approver = deny_all

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
    def resolve(self, relative: str) -> Path:
        """Resolve a workspace-relative path and reject anything outside the workspace or secret."""
        if not relative or relative.strip() in {".", ""}:
            return self.ws.root
        candidate = (self.ws.root / relative).resolve()
        try:
            rel = candidate.relative_to(self.ws.root)
        except ValueError as exc:
            raise PolicyError(f"Path '{relative}' is outside the workspace") from exc
        posix = PurePosixPath(rel.as_posix())
        for part in posix.parts:
            if any(fnmatch.fnmatch(part, pat) for pat in SECRET_PATTERNS):
                raise PolicyError(f"Access to secret path '{relative}' is denied")
        if any(posix.as_posix() == p or posix.as_posix().startswith(p + "/") for p in PROTECTED_PREFIXES):
            raise PolicyError(f"Path '{relative}' is reserved for the runtime")
        return candidate

    def check_write(self, agent: AgentSpec, relative: str, task_id: str) -> Path:
        path = self.resolve(relative)
        task_dir = (self.ws.tasks_dir / task_id).resolve()
        inside_task = path == task_dir or task_dir in path.parents
        if agent.permission_level < 1:
            raise PolicyError(f"Agent '{agent.id}' (level 0) may not write files")
        if agent.permission_level == 1 and not inside_task:
            raise PolicyError(f"Agent '{agent.id}' (level 1) may write only inside tasks/{task_id}/")
        if agent.id == "qa_auditor" and not inside_task:
            # DEC-003: QA runs tests but never edits the deliverable it reviews.
            raise PolicyError("qa_auditor may write only its own review files in the task folder (DEC-003)")
        if not inside_task and not self.approver(f"{agent.id} wants to write {relative}"):
            raise PolicyError(f"Write to '{relative}' was not approved by the Commander")
        return path
