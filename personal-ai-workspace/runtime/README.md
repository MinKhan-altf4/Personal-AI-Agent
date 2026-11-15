# Runtime — Phase 3 (v0.1)

Minimal Python runtime that executes the workspace's agents with Claude. Design: `DEC-004` in `../DECISIONS.md`.

```text
request ──► Orchestrator (intake, structured plan)
              │  chooses one primary agent from the active registry
              ▼
           Primary agent ──tool loop──► read_file / list_dir / write_task_file / write_file / run_tests
              │                              ▲ every call checked by policy.py, logged to SQLite
              ▼
           QA & Auditor (optional) ──► OUTCOME: PASS | PASS WITH NOTES | FAIL | BLOCKED
              ▼
           tasks/<TASK-ID>/TASK.md + REPORT.md, row in tasks/INDEX.md
```

## Setup (Windows, PowerShell)

Run from `personal-ai-workspace\runtime`:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Credentials are read from the environment, never from files in this repository:

```powershell
$env:ANTHROPIC_API_KEY = "<your key>"   # current terminal only
```

Alternatively, `ant auth login` stores a profile the SDK picks up automatically.

## Commands

| Command | What it does | Cost |
|---|---|---|
| `python -m agent_runtime check` | Validate registry, permissions, skills, model profiles | free |
| `python -m agent_runtime run "<request>" --dry-run` | Full loop with an offline scripted model | free |
| `python -m agent_runtime run "<request>"` | Real run with Claude | API usage |
| `python -m agent_runtime run "<request>" --yes` | Same, auto-approving writes outside the task folder | API usage |
| `python -m agent_runtime list` | Recent runtime tasks | free |
| `python -m agent_runtime show <TASK-ID>` | Status and full audit log of one task | free |

Use `.\.venv\Scripts\python.exe` in place of `python` unless the venv is activated (`.\.venv\Scripts\Activate.ps1`).

Exit codes: `0` finished (completed or partial), `1` configuration error, `2` model error, `3` task blocked.

## Permission enforcement

`agent_runtime/policy.py` enforces `config/permissions.yaml` in code:

- An agent gets only tools that are in its registry entry **and** implemented in v0.1, and only if its level ≥ the tool's `min_level`.
- Paths are confined to the workspace; `.env*`, `*.pem`, `*.key`, `secrets/`, `runtime/data/`, `.git/` are always denied.
- Level 1 agents write only inside `tasks/<TASK-ID>/`.
- Level 2 writes outside the task folder ask the Commander in the terminal (`y/N`); with no terminal they are refused. `--yes` approves them.
- `qa_auditor` never writes outside the task folder (DEC-003).
- `run_tests` runs only `python -m unittest discover` in a workspace directory, with a 300 s timeout.

Not implemented in v0.1 (agents simply do not receive them): `approved_web_search`, `approved_shell`, `git`.

## Models

Configured in `config/model-routing.yaml` → `runtime`. All profiles use `claude-opus-5-5` with different `effort`; server-side refusal fallback is on. System prompts are built from `AGENTS.md`, `PROJECT_CONTEXT.md`, the agent's `AGENT.md`/`SKILL.md` and its `domain_skills`, in a fixed order with a cache breakpoint, so repeated runs reuse the prompt cache. `REPORT.md` records token usage including cache reads.

## Data

- `runtime/data/runtime.sqlite` — task state and audit log (git-ignored).
- `tasks/<TASK-ID>/` — brief and report (committed like any other task record).

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests run on a temporary copy of the workspace and never call the API.
