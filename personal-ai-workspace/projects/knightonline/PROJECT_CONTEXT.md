# Project Context — KnightOnline

**Status:** active
**Owner:** Commander
**Last updated:** 2026-11-15
**Source repository:** `D:/Project/KnightOnline` (local git repo, branch `main`; registered in `config/projects.yaml`)
**Primary language:** Vietnamese docs; C# (.NET 10 SDK on this machine, Unity client)

> Facts below were read from the source repository on 2026-11-15. Items marked **TBD** need the owner's input.
> The repository's own documents are canonical for project rules and status — this file only links to them.

## 1. Overview
A multiplayer online role-playing game built with Unity (client) and .NET (server). Also referred to in the workspace as *The World of Knights & Demons*. **TBD:** confirm whether these are the same project.

## 2. Objectives
**TBD** — see `Documentation/Trang_Thai_Du_An.md` in the source repo for current priorities (latest DevLog: 2026-11-14, "P0 stabilization and P1 world simulation").

## 3. Success criteria
**TBD.**

## 4. Users and stakeholders
Commander (owner, sole developer). **TBD:** players, testers, collaborators.

## 5. Scope
### In scope (repository components)
- `KnightClient/` — Unity client (assemblies: Core, Data, Gameplay, Input, Network, Root, Shared, UI)
- `KnightServer/` — .NET game server (Accounts, Characters, Combat, Configuration, Database, Hosting, Migrations, Monsters, Networking, ...)
- `KnightServer.Tests/` — server unit tests
- `KnightServer.IntegrationTests/` — integration tests (need PostgreSQL and networking)
- `KnightBot/` — bot project
- `Documentation/` — architecture, design, audits, DevLogs, production docs

### Out of scope for workspace agents
- Committing, pushing, or branching in the game repo (the runtime has no git tool; the Commander commits).
- Build outputs and caches: `.tmp/`, `Builds/`, `obj/`, `bin/`, Unity `Library/`, `Temp/`, `Logs/`, `UserSettings/`.

## 6. Constraints
- Every change must follow `Documentation/KNIGHT_PROJECT_CORE_RULES.md` (classify the change: Critical / Authoritative gameplay / Presentation / Tooling, and meet that level's minimum requirements).
- The repo's `AGENTS.md`: do not create a DevLog per small task; write one session summary only when the Commander asks.
- Secrets live in .NET user-secrets outside the repo; never add secrets to the repository.

## 7. Current state
See `Documentation/Trang_Thai_Du_An.md` (has its own verification date). Last commit seen: `e55c908 up` (2026-11-14).

## 8. Architecture and technology
See `Documentation/Architecture/` and `Documentation/README.md` (reading order) in the source repo.

## 9. Roadmap
Maintained in the source repo (`Documentation/Production/`, `Documentation/Trang_Thai_Du_An.md`).

## 10. Risks and assumptions
| Item | Type | Impact | Mitigation/verification |
|---|---|---|---|
| Agents edit server code in Critical areas (accounts, economy) | risk | High | Every write asks the Commander; QA reviews; Commander reviews `git diff` before committing |
| Integration tests need PostgreSQL | assumption | Medium | Run `KnightServer.Tests` (unit) by default; integration tests only when the database is up |
| Unity-dependent behaviour cannot be verified by the runtime | limitation | Medium | Commander verifies in Unity, as the repo README requires |

## 11. Decisions
Workspace-level: DEC-005 in `../../DECISIONS.md`. Project decisions: in the source repo's documentation.

## 12. Next actions
- [ ] Owner: fill the **TBD** items above.
- [ ] First runtime task: a read-only review (e.g. summarise current status from `Trang_Thai_Du_An.md`).

## 13. References
- Source repo `README.md`, `AGENTS.md`, `Documentation/README.md`, `Documentation/KNIGHT_PROJECT_CORE_RULES.md`
