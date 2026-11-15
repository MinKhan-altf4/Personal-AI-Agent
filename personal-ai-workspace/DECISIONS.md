# Workspace Decision Log

Global (cross-project) decisions for the Personal AI-Agent Workspace.
Project-specific decisions belong in `projects/<project>/DECISIONS.md`.

Rules (see `skills/knowledge-management/SKILL.md`):
- Never delete a decision. Mark replaced decisions as `superseded` and link the replacement.
- Status values: `proposed` / `approved` / `rejected` / `superseded`.

---

## DEC-001 — Split skills into a domain library and agent procedures

- **Date:** 2026-11-15
- **Status:** approved
- **Approver:** Commander (workspace owner)
- **Source task:** TASK-20261115-001 (Orchestrator trial run)

### Context
The repository has two skill sets that looked like duplicates:
- `skills/` (repository root) — 8 specialist persona skills (e.g. `software-engineer`, `system-architect`, `study-tutor`), published and installed with `npx skills add`.
- `personal-ai-workspace/skills/` — 5 agent procedure skills (e.g. `engineering`, `orchestration`), referenced by `config/agent-registry.yaml`.

Installed copies in `~/.claude/skills/` were stale (6 of 8 skills, old UTF-8 BOM).

Inspection showed the sets serve different purposes: root skills define a specialist role and domain principles; workspace skills define how an agent operates (procedure, report format, guardrails). Only `engineering` and `software-engineer` partially overlap.

### Decision
1. `skills/` at the repository root is the **single source of truth for domain knowledge** (specialist personas). It is what gets published and installed.
2. `personal-ai-workspace/skills/` contains **agent procedures only** — how an agent works, reports, and stays within permissions. It must not duplicate domain knowledge from `skills/`.
3. Agents reference domain skills through the `domain_skills` field in `config/agent-registry.yaml` instead of copying their content.
4. ~~`~/.claude/skills/` is an **install target only**. It is never edited by hand; refresh it by reinstalling from the published repository.~~ *Superseded by DEC-006.*

### Alternatives considered
- **Merge `engineering` into `software-engineer`** — rejected: mixes agent procedure with specialist role and breaks the registry's agent/skill boundary.
- **Delete root `skills/`** — rejected: loses the reusable, publishable library usable by other AI clients.
- **Delete workspace `skills/`** — rejected: agents would lose their operating procedures and report contracts.

### Consequences
- `config/agent-registry.yaml` gains a `domain_skills` field per agent.
- When editing `skills/engineering/SKILL.md`, keep it procedural; put domain guidance in `../skills/software-engineer/SKILL.md`.
- After pushing, reinstall skills: `npx skills add MinKhan-altf4/Personal-AI-Agent --all`.

---

## DEC-002 — Close framework gaps from the first Orchestrator trial

- **Date:** 2026-11-15
- **Status:** approved
- **Approver:** Commander (workspace owner)
- **Source task:** TASK-20261115-002

### Context
The trial run (TASK-20261115-001) exposed four gaps: (a) no task output area for level-1 drafts; (b) tool names in `agent-registry.yaml` did not map to actions in `permissions.yaml`; (c) permissions were enforced only by prompt compliance; (d) no rule for allocating Task IDs.

### Decision
1. **(a)** `tasks/<TASK-ID>/` is the task output area. Level-1 agents write only there.
2. **(d)** Task IDs are `TASK-YYYYMMDD-NNN`, allocated from `tasks/INDEX.md`. Workspace decisions are `DEC-NNN`; project decisions are `<PROJECT>-DEC-NNN`.
3. **(b)** `permissions.yaml` gains a `tools:` catalog. Every registry tool must be listed with a `min_level`; an agent may use a tool only if its `permission_level` is at least that level.
4. **(c)** Until the Phase 3 runtime exists, Claude Code is the enforcement layer: `.claude/settings.json` at the repository root hard-denies reading or editing secrets and asks before `git push` and destructive commands. Other AI clients remain prompt-only.

### Alternatives considered
- **Build the Python runtime now to enforce permissions** — rejected: premature per `PROJECT_CONTEXT.md` (Phase 3 comes after Phase 2 validation).
- **Rename registry tools to match permission actions** — rejected: tools and actions are different concepts; a mapping keeps both readable.
- **Global sequential Task IDs (`TASK-001`)** — rejected: date-based IDs show age at a glance and avoid conflicts across parallel sessions.

### Consequences
- Claude Code enforcement applies only in Claude Code sessions opened in this repository, and only from a new session after the settings file was created.
- **Open conflict, not resolved by this decision:** `qa_auditor` is level 1 but uses `approved_test_runner` (min level 2). The Commander must either raise QA to level 2 or remove the tool from QA. → Resolved by DEC-003.

---

## DEC-003 — Raise QA & Auditor to permission level 2

- **Date:** 2026-11-15
- **Status:** approved
- **Approver:** Commander (workspace owner)
- **Source task:** TASK-20261115-002

### Context
DEC-002 found that `qa_auditor` (level 1) lists `approved_test_runner`, whose `min_level` is 2. One side had to change.

### Decision
Raise `qa_auditor` to `permission_level: 2` so QA can run approved tests itself and verify results independently.

To keep QA independent, `agents/qa-auditor/AGENT.md` adds a rule: QA must not edit the deliverable under review. It reports defects for the primary agent to fix and writes only its own review files in `tasks/<TASK-ID>/`.

### Alternatives considered
- **Remove `approved_test_runner` from QA** — rejected by the Commander. It would keep least privilege, but QA would depend on test output produced by the agent it is reviewing.

### Consequences
- QA technically gains `edit_files_within_approved_workspace`. The no-edit rule is prompt-level only until the Phase 3 runtime can restrict actions per agent.
- Every active agent now has a `permission_level` that covers all its tools.

---

## DEC-004 — Phase 3 runtime design

- **Date:** 2026-11-15
- **Status:** approved (Commander instructed Phase 3 execution); revisit after Phase 3 validation
- **Approver:** Commander (workspace owner)
- **Source task:** TASK-20261115-003

### Context
`PROJECT_CONTEXT.md` §13 left open: AI provider, orchestration style, persistent store. Phase 3 needs a minimal choice for each.

### Decision
1. **Provider:** Anthropic Claude via the official `anthropic` Python SDK. Every routing profile uses `claude-opus-5-5`; profiles differ only by `effort`. Server-side refusal fallback (`fallbacks: "default"`) is on.
2. **Orchestration:** a small custom state machine (classify → execute → optional QA → report) with a manual tool loop. No LangGraph.
3. **Persistence:** SQLite (`runtime/data/runtime.sqlite`, git-ignored) for task state and an audit log of every tool call. `tasks/INDEX.md` stays the human-readable register; the runtime appends and updates its rows.
4. **Enforcement:** the runtime checks `permissions.yaml` before every tool call: the agent's level must cover the tool's `min_level`, file access is confined to the workspace, secret paths are always denied, level-1 agents write only in `tasks/<TASK-ID>/`, and level-2 writes require human confirmation unless `--yes` is passed.
5. **Tools implemented in v0.1:** `read_workspace`, `task_planning`, `approved_file_edit`, `approved_test_runner`. Not implemented: `approved_web_search` (network disabled by policy), `approved_shell`, `git`. Agents listing them simply do not receive them.

### Alternatives considered
- **LangGraph** — rejected for now: adds a framework before the workflow is proven.
- **Tool Runner (beta)** — rejected: a manual loop makes the per-call permission gate and audit log explicit.
- **Cheaper models for light profiles** — not chosen; the owner may change `model-routing.yaml` later based on measured quality.

### Consequences
- Running the runtime needs an Anthropic API key and costs money per task. `--dry-run` runs offline with a scripted model for testing.
- Phase 4 (more agents/integrations) and Phase 5 (dashboard) remain gated on demonstrated need, per the roadmap.

---

## DEC-005 — Let the runtime work on registered external project repositories

- **Date:** 2026-11-15
- **Status:** approved
- **Approver:** Commander (chose `D:/Project/KnightOnline` with read-and-approved-write access)
- **Source task:** TASK-20261115-005

### Context
Product source code lives in its own repositories (README §1, `projects/README.md`), but the runtime confined every path to this workspace, so agents could not work on KnightOnline.

### Decision
1. External repositories are registered in `config/projects.yaml` (id, `source_path`, `access`, `rules`, `exclude`, `test_command`). Context stays in `projects/<id>/PROJECT_CONTEXT.md`.
2. `run --project <id>` attaches one project to a task. Tools address its files with the `project:` prefix; unprefixed paths stay in the workspace.
3. The project's `rules` files (for KnightOnline: `AGENTS.md`, `Documentation/KNIGHT_PROJECT_CORE_RULES.md`) are loaded into every agent's system prompt for that task.
4. Writes to a project need level 2, `access: read_write`, and the Commander's approval **for every write**. `qa_auditor` never writes there. `.git`, secrets and `exclude` entries are never read or written.
5. `run_tests` may run `dotnet test` on a project folder that contains a `.csproj`/`.sln` when `test_command: dotnet`.
6. The runtime never commits, branches or pushes in the project; the Commander reviews `git diff` and commits.

### Alternatives considered
- **Copy project files into the workspace** — rejected: two sources of truth.
- **Register the project path as the workspace root** — rejected: loses workspace rules, task records and the permission model.

### Consequences
- `config/projects.yaml` contains a machine-specific path; on another machine `check` reports it as missing until edited.
- `dotnet test` writes build output (`bin/`, `obj/`) inside the project; these are git-ignored there.
- Only `qa_auditor` has the test runner; Engineering cannot run tests itself (registry unchanged).

---

## DEC-006 — Link Claude Code skills directly to the repository and rewrite domain skills

- **Date:** 2026-11-15
- **Status:** approved (Commander asked to install the repository's skills into Claude and improve them)
- **Approver:** Commander
- **Supersedes:** DEC-001 point 4

### Context
`~/.claude/skills/` held six skills installed on 2026-10-25 by `npx skills` from a different repository (`MinKhan-altf4/it-agent-skills`), stored in `~/.agents/skills/` with the old UTF-8 BOM. `study-tutor` and `software-technology-tutor` were not installed. Six domain skills shared one identical generic body.

### Decision
1. Each entry in `~/.claude/skills/<name>` is a **directory junction** to `skills/<name>` in this repository, so the repository is the single source and edits apply without publishing.
2. The six domain skills were rewritten with domain-specific workflows, checklists, pitfalls and output formats; all eight descriptions now include Vietnamese trigger phrases and boundaries between neighbouring skills.
3. `software-technology-tutor` moves its curriculum to `references/curriculum.md` (progressive disclosure).

### Alternatives considered
- **Reinstall with `npx skills`** — rejected: needs a push first and installs from a published copy, not the working tree.
- **Copy files into `~/.claude/skills/`** — rejected: copies drift from the repository.

### Consequences
- Junctions are machine-specific; on another machine run the link commands in the root `README.md`.
- The old copies in `~/.agents/skills/` and `~/.agents/.skill-lock.json` are untouched. Running `npx skills update` may recreate links to those old copies; re-run the link commands afterwards.
- Skill quality was not measured with evals in this change; trigger and output quality should be checked in real use.

