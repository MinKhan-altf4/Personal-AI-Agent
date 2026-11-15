# Tasks — task records and output area

This folder is the **task output area** referenced by permission level 1
(`create_drafts_in_task_output_area` in `config/permissions.yaml`).

Agents at level 1 (`draft`) may create and edit files **only inside `tasks/<TASK-ID>/`**.
Writing anywhere else in the workspace requires level 2 (`controlled_modify`).

## Layout

```text
tasks/
├── README.md          # This file
├── INDEX.md           # Task register — the source of the next Task ID
└── <TASK-ID>/
    ├── TASK.md        # Brief, from templates/task-template.md
    ├── REPORT.md      # Final report, from templates/agent-report.md
    └── drafts/        # Proposals, draft documents, intermediate outputs
```

Only create the files a task actually needs. Simple tasks may have only `TASK.md` or only `REPORT.md`.

## ID conventions

| Record | Format | Example | Rule |
|---|---|---|---|
| Task | `TASK-YYYYMMDD-NNN` | `TASK-20261115-001` | `YYYYMMDD` = creation date; `NNN` restarts at `001` each day |
| Workspace decision | `DEC-NNN` | `DEC-001` | Sequential across the whole workspace, never reused |
| Project decision | `<PROJECT>-DEC-NNN` | `FDE-DEC-001` | Sequential within that project's `DECISIONS.md` |

### Allocating a new Task ID
1. Open `INDEX.md`.
2. Find rows whose ID starts with today's `TASK-YYYYMMDD-`.
3. Use the highest `NNN` + 1, or `001` if none exist.
4. Add the row to `INDEX.md` **before** creating `tasks/<TASK-ID>/`.

IDs are never reused, including for cancelled tasks.

## Lifecycle
- Status values come from `config/workspace.yaml` (`pending`, `in_progress`, `review`, `completed`, `partial`, `blocked`, `cancelled`).
- Update the status in both `INDEX.md` and the task's own files.
- Durable outcomes move out of `tasks/`: decisions go to `DECISIONS.md`, project facts to `projects/<project>/`, reusable knowledge to `knowledge/`.
