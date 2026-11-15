---
name: engineering
description: Analyze, design, implement, test, and review software systems.
---

# Engineering Skill

## Procedure
1. Inspect the repository, architecture, and existing conventions.
2. Clarify functional and non-functional requirements.
3. Identify constraints, dependencies, and risks.
4. Propose the smallest maintainable design.
5. Define interfaces, data contracts, and acceptance criteria.
6. Implement in small, reviewable changes.
7. Run relevant tests, linters, and static checks when available.
8. Inspect the diff for unintended changes and security issues.
9. Update documentation and report verification.

## Design principles
- Separation of concerns
- High cohesion and low coupling
- Explicit interfaces and data contracts
- Secure defaults and input validation
- Observability and useful error handling
- Testability and maintainability
- Avoid premature optimization and abstraction

## Code-change report
Include:
- Files inspected
- Files created or modified
- Design decisions and trade-offs
- Commands/tests actually run
- Test results
- Known limitations
- Suggested next step

## Guardrails
Do not overwrite unrelated work, expose secrets, or claim unexecuted tests passed. Ask before destructive operations or production changes.
