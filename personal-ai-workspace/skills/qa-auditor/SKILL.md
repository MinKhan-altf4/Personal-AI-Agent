---
name: qa-auditor
description: Independently verify deliverables against requirements, evidence, and safety rules.
---

# QA & Auditor Skill

## Procedure
1. Read the original task and acceptance criteria.
2. Inspect the deliverable and relevant source artifacts.
3. Map each requirement to evidence.
4. Verify factual claims and citations.
5. Check consistency, completeness, and edge cases.
6. Review permission and data-handling compliance.
7. Classify defects by severity.
8. Return a review outcome and remediation list.

## Acceptance matrix
For each requirement, record:
- Requirement
- Evidence inspected
- Result: pass / fail / not verified / not applicable
- Finding
- Required action

## Review outcome
- PASS: all critical acceptance criteria verified.
- PASS WITH NOTES: acceptable with non-blocking issues disclosed.
- FAIL: one or more core requirements fail.
- BLOCKED: required evidence or access is unavailable.

## Guardrails
Do not infer success from an agent's assertion. Do not claim tests passed without test output. Distinguish not verified from failed.
