"""Client-side tools exposed to agents. Each maps to a registry tool name in permissions.yaml."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable

from .config import AgentSpec, Workspace
from .policy import Policy, PolicyError, is_project_path
from .store import TaskStore

MAX_READ_CHARS = 200_000
MAX_LIST_ENTRIES = 500
TEST_TIMEOUT_SECONDS = 300
DOTNET_TEST_TIMEOUT_SECONDS = 900

PATH_HELP = ("Paths are relative to the workspace root; prefix with 'project:' for the task's project "
             "repository (e.g. 'project:README.md').")


@dataclass
class ToolContext:
    ws: Workspace
    policy: Policy
    agent: AgentSpec
    task_id: str
    store: TaskStore


@dataclass(frozen=True)
class ToolSpec:
    name: str
    registry_tool: str
    description: str
    properties: dict
    handler: Callable[[ToolContext, dict], str]

    def to_api(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "strict": True,
            "input_schema": {
                "type": "object",
                "properties": self.properties,
                "required": list(self.properties),
                "additionalProperties": False,
            },
        }


# --- handlers --------------------------------------------------------------
def _read_file(ctx: ToolContext, args: dict) -> str:
    path = ctx.policy.resolve(args["path"])
    if not path.is_file():
        raise FileNotFoundError(f"No such file: {args['path']}")
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    if len(text) > MAX_READ_CHARS:
        return text[:MAX_READ_CHARS] + f"\n\n[NOTE: file truncated at {MAX_READ_CHARS} of {len(text)} characters]"
    return text


def _list_dir(ctx: ToolContext, args: dict) -> str:
    path = ctx.policy.resolve(args["path"])
    if not path.is_dir():
        raise NotADirectoryError(f"No such directory: {args['path']}")
    entries = []
    for child in sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
        rel = ctx.policy.display(child)
        try:
            ctx.policy.resolve(rel)
        except PolicyError:
            continue  # hide secrets and runtime internals
        entries.append(rel + ("/" if child.is_dir() else ""))
        if len(entries) >= MAX_LIST_ENTRIES:
            entries.append(f"[NOTE: listing stopped at {MAX_LIST_ENTRIES} entries]")
            break
    return "\n".join(entries) or "(empty directory)"


def _write_task_file(ctx: ToolContext, args: dict) -> str:
    name = args["filename"].replace("\\", "/").lstrip("/")
    rel = f"tasks/{ctx.task_id}/{name}"
    path = ctx.policy.check_write(ctx.agent, rel, ctx.task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(args["content"], encoding="utf-8")
    return f"Wrote {rel} ({len(args['content'])} characters)"


def _write_file(ctx: ToolContext, args: dict) -> str:
    rel = args["path"].replace("\\", "/")
    path = ctx.policy.check_write(ctx.agent, rel, ctx.task_id)
    existed = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(args["content"], encoding="utf-8")
    return f"{'Overwrote' if existed else 'Created'} {rel} ({len(args['content'])} characters)"


def _run_tests(ctx: ToolContext, args: dict) -> str:
    target = ctx.policy.resolve(args["directory"])
    if not target.is_dir():
        raise NotADirectoryError(f"No such directory: {args['directory']}")
    env = None
    timeout = TEST_TIMEOUT_SECONDS
    use_dotnet = is_project_path(args["directory"]) and ctx.policy.project.test_command == "dotnet"
    if use_dotnet:
        # Allow-listed: `dotnet test` on a folder that holds a project or solution file.
        if not any(target.glob("*.csproj")) and not any(target.glob("*.sln*")):
            raise ValueError(f"No .csproj or .sln in {args['directory']}; point run_tests at a test project folder")
        cmd = ["dotnet", "test", str(target), "--nologo"]
        env = {**os.environ, "DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1"}
        timeout = DOTNET_TEST_TIMEOUT_SECONDS
    else:
        # Allow-listed: the stdlib unittest runner. No arbitrary shell.
        cmd = [sys.executable, "-m", "unittest", "discover", "-s", str(target), "-t", str(target)]
    proc = subprocess.run(cmd, cwd=target, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout, env=env)
    output = (proc.stdout + proc.stderr)[-20_000:]
    return f"command={' '.join(cmd[:3])} ...\nexit_code={proc.returncode}\n{output}"


TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        "read_file", "read_workspace",
        "Read a UTF-8 text file. " + PATH_HELP,
        {"path": {"type": "string", "description": "File path"}},
        _read_file,
    ),
    ToolSpec(
        "list_dir", "read_workspace",
        "List files and folders in a directory. Use '.' for the workspace root or 'project:' for the project root. " + PATH_HELP,
        {"path": {"type": "string", "description": "Directory path"}},
        _list_dir,
    ),
    ToolSpec(
        "write_task_file", "task_planning",
        "Create or overwrite a draft file inside this task's own folder (tasks/<TASK-ID>/). "
        "Use for plans, drafts, and reviews. `filename` may include subfolders such as 'drafts/plan.md'.",
        {
            "filename": {"type": "string", "description": "Path inside the task folder"},
            "content": {"type": "string", "description": "Full file content"},
        },
        _write_task_file,
    ),
    ToolSpec(
        "write_file", "approved_file_edit",
        "Create or overwrite a file in the workspace or the project repository. Writes outside the task folder, "
        "and every write to the project repository, need the Commander's approval and may be refused. "
        "Always read a file before overwriting it and keep unrelated content unchanged. " + PATH_HELP,
        {
            "path": {"type": "string", "description": "File path"},
            "content": {"type": "string", "description": "Full new file content"},
        },
        _write_file,
    ),
    ToolSpec(
        "run_tests", "approved_test_runner",
        "Run tests and return the output. Workspace folders run Python unittest; a project folder that contains a "
        ".csproj runs `dotnet test` when the project allows it. " + PATH_HELP,
        {"directory": {"type": "string", "description": "Directory containing the tests"}},
        _run_tests,
    ),
)

_BY_NAME = {t.name: t for t in TOOLS}


def tools_for(agent: AgentSpec) -> list[ToolSpec]:
    """Tools the agent may receive: implemented ones whose registry tool the agent is registered for."""
    return [t for t in TOOLS if t.registry_tool in agent.tools]


def unimplemented_registry_tools(agent: AgentSpec) -> list[str]:
    implemented = {t.registry_tool for t in TOOLS}
    return [t for t in agent.tools if t not in implemented]


def execute(ctx: ToolContext, name: str, args: dict) -> tuple[str, bool]:
    """Run a tool call after the policy check. Returns (content, is_error); every call is audit-logged."""
    spec = _BY_NAME.get(name)
    try:
        if spec is None:
            raise PolicyError(f"Unknown tool '{name}'")
        ctx.policy.check_tool(ctx.agent, spec.registry_tool)
        missing = [k for k in spec.properties if not isinstance(args.get(k), str)]
        if missing:
            raise ValueError(f"Missing or invalid arguments: {', '.join(missing)}")
        result, is_error = spec.handler(ctx, args), False
    except (PolicyError, OSError, ValueError, subprocess.SubprocessError) as exc:
        result, is_error = f"Error: {exc}", True
    logged_args = {k: (v if k != "content" else f"<{len(v)} chars>") for k, v in args.items()}
    ctx.store.log(ctx.task_id, "tool_call",
                  {"tool": name, "args": logged_args, "is_error": is_error, "result_preview": result[:300]},
                  agent=ctx.agent.id)
    return result, is_error
