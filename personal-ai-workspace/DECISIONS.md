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
4. `~/.claude/skills/` is an **install target only**. It is never edited by hand; refresh it by reinstalling from the published repository.

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
