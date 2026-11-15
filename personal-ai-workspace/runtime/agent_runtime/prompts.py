"""System prompts built from the workspace's canonical documents.

Everything here is static per agent (no dates, task IDs or other volatile values) so the
system prompt stays byte-identical across requests and prompt caching can hit.
"""

from __future__ import annotations

from .config import AgentSpec, ProjectSpec, Workspace

PROJECT_INSTRUCTIONS = """\
This task belongs to the external project repository described above.
- Address its files with the 'project:' prefix (e.g. 'project:README.md', 'project:KnightServer').
  Paths without the prefix point to the AI workspace, not the project.
- The project's own rules are mandatory and override general habits. Read the relevant source before changing it.
- Every write to the project needs the Commander's approval. Make the smallest change that meets the criteria.
- You cannot commit, branch or push. State in your report which project files you changed, so the Commander
  can review `git diff` and commit.
"""

RUNTIME_PREAMBLE = """\
You are running inside the Personal AI-Agent Workspace runtime (v0.1, Phase 3) as the agent named below.
The Commander is the human owner and final decision-maker. The workspace rules and your role definition follow.

How this runtime works:
- File paths in tools are relative to the workspace root (the folder containing AGENTS.md).
- Tools are checked against config/permissions.yaml before they run. A refused call returns an error:
  do not retry it in another way; report it as a blocker instead.
- You cannot send messages, browse the web, run arbitrary shell commands, or use git in this runtime.
- Never claim an action, file change, or test result that a tool result does not show.
- Write user-facing text in Vietnamese; keep code, identifiers and file names in English (AGENTS.md section 9).
"""

EXECUTE_INSTRUCTIONS = """\
When you finish, reply with a report in this structure (templates/agent-report.md):
## 1. Objective / ## 2. Actions taken / ## 3. Results / ## 4. Evidence / ## 5. Issues and limitations /
## 6. Recommendations / ## 7. Handoff
List only actions you actually performed with tools. End with exactly one line:
STATUS: completed | partial | blocked
Use `completed` only if every acceptance criterion was checked (AGENTS.md section 10).
"""

REVIEW_INSTRUCTIONS = """\
You are reviewing another agent's work. Inspect the actual files and evidence with your tools; do not trust
the summary alone. Do not edit the deliverable (DEC-003). Classify findings as Critical / High / Medium / Low.
End with exactly one line:
OUTCOME: PASS | PASS WITH NOTES | FAIL | BLOCKED
"""

CLASSIFY_INSTRUCTIONS = """\
You are doing intake only. Turn the Commander's request into a task plan and choose exactly one primary agent
from the executor list. Use the smallest sufficient team. Set needs_qa to true for code changes, multi-step or
high-impact work. If a missing detail blocks safe execution, put one focused question in clarification_needed;
otherwise leave it empty. Write title, objective and criteria in Vietnamese.
"""


def _section(title: str, body: str) -> str:
    return f"<{title}>\n{body.strip()}\n</{title}>"


def project_sections(project: ProjectSpec) -> list[str]:
    parts = []
    if project.context_path and project.context_path.is_file():
        parts.append(_section(f"project_context id=\"{project.id}\"",
                              project.context_path.read_text(encoding="utf-8-sig")))
    for rule in project.rules:
        text = (project.source_path / rule).read_text(encoding="utf-8-sig")
        parts.append(_section(f"project_rules file=\"project:{rule}\"", text))
    access = "read and write (each write approved)" if project.writable else "read only"
    parts.append(f"Project '{project.id}' ({project.name}). Access: {access}.\n" + PROJECT_INSTRUCTIONS)
    return parts


def system_blocks(ws: Workspace, agent: AgentSpec, mode: str, project: ProjectSpec | None = None) -> list[dict]:
    """Ordered system blocks; the last one carries the cache breakpoint."""
    parts = [RUNTIME_PREAMBLE + f"\nYour agent id: {agent.id} ({agent.name}). Permission level: {agent.permission_level}."]
    parts.append(_section("workspace_rules file=\"AGENTS.md\"", ws.read_text("AGENTS.md")))
    parts.append(_section("project_context file=\"PROJECT_CONTEXT.md\"", ws.read_text("PROJECT_CONTEXT.md")))
    if agent.agent_path:
        parts.append(_section("agent_role", agent.agent_path.read_text(encoding="utf-8-sig")))
    if agent.skill_path:
        parts.append(_section("agent_procedure", agent.skill_path.read_text(encoding="utf-8-sig")))
    for path in agent.domain_skill_paths:
        parts.append(_section(f"domain_skill name=\"{path.parent.name}\"", path.read_text(encoding="utf-8-sig")))
    if project is not None:
        parts.extend(project_sections(project))
    if mode == "classify":
        parts.append(_section("agent_registry file=\"config/agent-registry.yaml\"",
                              ws.read_text("config/agent-registry.yaml")))
        parts.append(CLASSIFY_INSTRUCTIONS)
    elif mode == "review":
        parts.append(REVIEW_INSTRUCTIONS)
    else:
        parts.append(EXECUTE_INSTRUCTIONS)
    blocks = [{"type": "text", "text": p} for p in parts]
    blocks[-1]["cache_control"] = {"type": "ephemeral"}
    return blocks


def classify_schema(executors: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "project": {"type": "string"},
            "primary_agent": {"type": "string", "enum": executors},
            "objective": {"type": "string"},
            "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
            "needs_qa": {"type": "boolean"},
            "clarification_needed": {"type": "string"},
        },
        "required": ["title", "project", "primary_agent", "objective", "acceptance_criteria",
                     "needs_qa", "clarification_needed"],
        "additionalProperties": False,
    }
