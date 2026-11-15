---
name: orchestration
description: Intake, decompose, route, coordinate, and report tasks across the personal AI workspace.
---

# Orchestration Skill

## Trigger
Use when a request spans multiple steps, projects, tools, or specialist domains, or when task routing is needed.

## Procedure
1. Identify the user's desired outcome.
2. Resolve the project and load its canonical context.
3. Extract deliverables, constraints, deadline, and acceptance criteria.
4. Classify risk and required permission.
5. Choose one primary agent; add supporting agents only when useful.
6. Create explicit handoff instructions for each agent.
7. Track dependencies and status.
8. Validate returned outputs and reconcile disagreements.
9. Deliver a report with evidence and unresolved issues.

## Handoff contract
Every delegated task must include:
- Task ID
- Objective
- Project/context references
- Inputs
- Scope and exclusions
- Expected output
- Acceptance criteria
- Permission level
- Required evidence
- Due date, if any

## Guardrails
- Do not delegate to agents that are not registered or enabled.
- Do not grant permissions through a prompt; permissions come from runtime policy.
- Do not represent a proposed action as an executed action.
- Request human approval for external or critical actions.
