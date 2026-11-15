# IT Agent Skills

Reusable specialist instructions for AI coding agents and IT workflows.

## Purpose

This repository provides a collection of focused AI skills for software development, system design, databases, data science, machine learning, and DevOps.

Each skill is maintained as a standalone `SKILL.md` using the Agent Skills format.

## Available skills

| Skill | Intended use |
|---|---|
| `system-architect` | Requirements, system architecture, APIs, UML, and technical trade-offs |
| `software-engineer` | Implementation, debugging, refactoring, testing, and code review |
| `database-architect` | Data modeling, SQL, integrity, and query performance |
| `data-scientist` | Data cleaning, statistics, experiments, and insights |
| `ai-ml-engineer` | Machine learning pipelines, training, evaluation, and deployment |
| `devops-engineer` | CI/CD, containers, infrastructure, and observability |
| `software-technology-tutor` | Teaching software and IT concepts from first principles |
| `study-tutor` | Teaching from uploaded textbooks, slides, papers, and course notes |

## Repository structure

```text
skills/
├── system-architect/SKILL.md
├── software-engineer/SKILL.md
├── database-architect/SKILL.md
├── data-scientist/SKILL.md
├── ai-ml-engineer/SKILL.md
├── devops-engineer/SKILL.md
├── software-technology-tutor/SKILL.md
└── study-tutor/SKILL.md
personal-ai-workspace/   # Personal AI-agent workspace (context, agents, config)
```

See [`personal-ai-workspace/README.md`](personal-ai-workspace/README.md) for the agent workspace.

## Installation

Install the skills using the open-source Skills CLI:

```bash
npx skills add MinKhan-altf4/Personal-AI-Agent
```

To install all skills for all supported agents:

```bash
npx skills add MinKhan-altf4/Personal-AI-Agent --all
```

Compatibility depends on the AI client and its support for Agent Skills.

## Design principles

- One source of truth.
- Small, focused, reusable skills.
- Clear activation descriptions.
- Evidence-based recommendations.
- Maintainability, security, and testability.
- No unsupported claims about real-world credentials or experience.

## License

No license has been chosen yet. Until a `LICENSE` file is added, all rights are reserved by the author.