# Personal AI-Agent Workspace

> Your Personal AI Operating System — a modular workspace for learning, personal projects, research, and business experiments.

## 1. Purpose

This repository is the **control plane and knowledge foundation** for your personal AI-agent ecosystem. It stores:

- Workspace-wide context and operating rules
- Agent role definitions
- Reusable skills
- Agent registry and permission configuration
- Project context templates and execution-report templates

It does **not** replace the source repositories of products such as your MMORPG or desktop applications. Keep each product's source code in its own repository and link to it from the relevant project context.

## 2. Initial scope

The workspace supports five activity domains:

1. **Education** — university coursework, technical learning, and research.
2. **Career** — software engineering, FDE, data analysis, and portfolio development.
3. **Personal projects** — including *The World of Knights & Demons* and WinterArc.
4. **Business experiments** — market research, monetization, and small online-business experiments.
5. **Personal development** — goals, planning, time use, and periodic reviews.

## 3. Repository structure

```text
personal-ai-workspace/
├── README.md
├── PROJECT_CONTEXT.md
├── AGENTS.md
├── DECISIONS.md            # Workspace-level decision log
├── .gitignore
├── config/
│   ├── workspace.yaml
│   ├── agent-registry.yaml
│   ├── permissions.yaml
│   └── model-routing.yaml
├── agents/
│   ├── orchestrator/AGENT.md
│   ├── research/AGENT.md
│   ├── engineering/AGENT.md
│   ├── knowledge-manager/AGENT.md
│   └── qa-auditor/AGENT.md
├── skills/                 # Agent procedures only (domain skills live in ../skills/)
│   ├── orchestration/SKILL.md
│   ├── research/SKILL.md
│   ├── engineering/SKILL.md
│   ├── knowledge-management/SKILL.md
│   └── qa-auditor/SKILL.md
├── projects/
│   └── README.md
├── tasks/                  # Task register (INDEX.md) and per-task output area
│   ├── README.md
│   └── INDEX.md
├── knowledge/
│   └── README.md
├── runtime/                # Phase 3 Python runtime (agent_runtime/, tests/)
│   └── README.md
├── workflows/
│   └── task-execution.md
├── templates/
│   ├── project-context.md
│   ├── task-template.md
│   ├── decision-template.md
│   └── agent-report.md
└── docs/
    └── operating-manual/
        └── getting-started.md
```

## 4. Quick start on Windows

### Option A — GitHub Desktop

1. Download and extract `personal-ai-workspace.zip`.
2. Open GitHub Desktop.
3. Select **File → Add local repository**.
4. Choose the extracted `personal-ai-workspace` folder.
5. If GitHub Desktop says it is not a Git repository, choose **Create a repository** and use the existing folder.
6. Review the files, commit the initial version, then publish the repository to your GitHub account.
7. Keep the repository private initially if it contains personal plans or project context.

### Option B — PowerShell

```powershell
cd "path\to\personal-ai-workspace"
git init
git add .
git commit -m "Initial personal AI workspace foundation"
```

Create a private GitHub repository, then connect it using the remote URL GitHub provides:

```powershell
git remote add origin <YOUR_GITHUB_REPOSITORY_URL>
git branch -M main
git push -u origin main
```

Do not paste credentials or access tokens into files or commit history.

## 5. How to use the foundation

1. Read `PROJECT_CONTEXT.md`.
2. Read `AGENTS.md`.
3. Review `config/permissions.yaml` before connecting tools.
4. Use `config/agent-registry.yaml` as the source of truth for available agents.
5. Keep each agent's role in `agents/<agent-name>/AGENT.md`.
6. Keep agent procedures in `skills/<skill-name>/SKILL.md`. Keep domain/specialist knowledge in the root `../skills/` library and link it through `domain_skills` in the registry (DEC-001).
7. Create one folder per project under `projects/` and start from `templates/project-context.md`.
8. Record consequential decisions using `templates/decision-template.md`; global decisions go in `DECISIONS.md`.

## 6. Important implementation boundary

Since Phase 3 (DEC-004) the workspace includes a minimal Python runtime in `runtime/` that executes the active agents with Claude, enforces `config/permissions.yaml` in code, and records every task in SQLite and `tasks/`. See [`runtime/README.md`](runtime/README.md) for setup and commands.

It still does **not** schedule jobs, browse the web, run arbitrary shell commands, use git, send messages, or connect to external services. Add those only when a real workflow requires them (Phases 4–5).
