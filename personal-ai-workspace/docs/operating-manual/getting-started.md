# Getting Started — Personal AI-Agent Workspace

## First session

1. Read `PROJECT_CONTEXT.md`.
2. Read `AGENTS.md`.
3. Review `config/permissions.yaml`.
4. Check the registry and confirm which agents are active.
5. Select one real, low-risk task to test the workflow.

## Recommended first test

Ask an AI client to:
- Read the workspace context and rules.
- Summarize the active agent registry.
- Propose a task plan for one small project task.
- Identify which agent and skill would handle it.
- Produce a draft report without changing files.

Then compare the result with the expected behavior in `AGENTS.md`.

## Before enabling tools

- Configure credentials outside the repository.
- Start with read-only access.
- Restrict filesystem access to approved folders.
- Keep external actions disabled.
- Test permission enforcement, not just prompt compliance.
- Add logging that does not expose secrets.

## Before adding more agents

Confirm that the current workflow has:
- A clear task schema
- Reliable context loading
- A stable handoff format
- Verifiable completion criteria
- A usable audit trail

Add a new agent only when it provides a distinct capability that cannot be handled more simply by an existing agent plus a skill.
