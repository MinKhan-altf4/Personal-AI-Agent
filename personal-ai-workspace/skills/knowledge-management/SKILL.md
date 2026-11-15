---
name: knowledge-management
description: Curate global context, project documentation, task records, and decisions.
---

# Knowledge Management Skill

## Knowledge classes
- Global: cross-project preferences and operating principles.
- Project: goals, architecture, constraints, roadmap, and project decisions.
- Task: temporary task inputs, progress, and outputs.
- Decision: approved choices, rationale, alternatives, and consequences.

## Procedure
1. Identify the information and its provenance.
2. Determine whether it is durable and useful.
3. Select the narrowest appropriate scope.
4. Search for existing or conflicting records.
5. Validate freshness and approval status.
6. Update the canonical document or propose an update.
7. Preserve links and decision history.
8. Report the change.

## Decision record fields
- ID
- Date
- Status: proposed / approved / rejected / superseded
- Context
- Decision
- Alternatives
- Rationale
- Consequences
- Approver

## Guardrails
Do not save unverified model output as fact. Do not place project-specific detail in global context without a clear reason. Do not store credentials or unnecessary sensitive information.
