"""Task persistence (SQLite) and the human-readable register tasks/INDEX.md."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

STATUSES = ("pending", "in_progress", "review", "completed", "partial", "blocked", "cancelled")
ID_RE = re.compile(r"TASK-(\d{8})-(\d{3})")

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id            TEXT PRIMARY KEY,
    title         TEXT NOT NULL,
    request       TEXT NOT NULL,
    project       TEXT NOT NULL DEFAULT 'global',
    primary_agent TEXT,
    status        TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    seq      INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id  TEXT NOT NULL REFERENCES tasks(id),
    ts       TEXT NOT NULL,
    agent    TEXT,
    kind     TEXT NOT NULL,
    payload  TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class TaskRow:
    id: str
    title: str
    request: str
    project: str
    primary_agent: str | None
    status: str
    created_at: str
    updated_at: str


class TaskStore:
    def __init__(self, db_path: Path, index_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(db_path)
        self.db.executescript(SCHEMA)
        self.index_path = index_path

    def close(self) -> None:
        self.db.close()

    # --- IDs -------------------------------------------------------------
    def next_task_id(self, today: date | None = None) -> str:
        """TASK-YYYYMMDD-NNN, unique across both the database and tasks/INDEX.md (tasks/README.md)."""
        stamp = (today or date.today()).strftime("%Y%m%d")
        used = {int(n) for d, n in ID_RE.findall(self._index_text()) if d == stamp}
        for (task_id,) in self.db.execute("SELECT id FROM tasks WHERE id LIKE ?", (f"TASK-{stamp}-%",)):
            used.add(int(task_id[-3:]))
        return f"TASK-{stamp}-{max(used, default=0) + 1:03d}"

    # --- tasks -----------------------------------------------------------
    def create(self, request: str, title: str = "(classifying)", today: date | None = None) -> str:
        task_id = self.next_task_id(today)
        ts = _now()
        with self.db:
            self.db.execute(
                "INSERT INTO tasks (id, title, request, status, created_at, updated_at) VALUES (?,?,?,?,?,?)",
                (task_id, title, request, "pending", ts, ts),
            )
        self._append_index_row(task_id, title, "global", "-", "pending", ts[:10])
        return task_id

    def update(self, task_id: str, **fields) -> None:
        if "status" in fields and fields["status"] not in STATUSES:
            raise ValueError(f"Invalid status {fields['status']!r}")
        allowed = {"title", "project", "primary_agent", "status"}
        sets = {k: v for k, v in fields.items() if k in allowed}
        if not sets:
            return
        sets["updated_at"] = _now()
        cols = ", ".join(f"{k} = ?" for k in sets)
        with self.db:
            self.db.execute(f"UPDATE tasks SET {cols} WHERE id = ?", (*sets.values(), task_id))
        self._sync_index_row(task_id)

    def get(self, task_id: str) -> TaskRow | None:
        row = self.db.execute(
            "SELECT id, title, request, project, primary_agent, status, created_at, updated_at FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
        return TaskRow(*row) if row else None

    def list(self, limit: int = 20) -> list[TaskRow]:
        rows = self.db.execute(
            "SELECT id, title, request, project, primary_agent, status, created_at, updated_at "
            "FROM tasks ORDER BY created_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [TaskRow(*r) for r in rows]

    # --- audit log -------------------------------------------------------
    def log(self, task_id: str, kind: str, payload: dict, agent: str | None = None) -> None:
        with self.db:
            self.db.execute(
                "INSERT INTO events (task_id, ts, agent, kind, payload) VALUES (?,?,?,?,?)",
                (task_id, _now(), agent, kind, json.dumps(payload, ensure_ascii=False, sort_keys=True)),
            )

    def events(self, task_id: str) -> list[dict]:
        rows = self.db.execute(
            "SELECT ts, agent, kind, payload FROM events WHERE task_id = ? ORDER BY seq", (task_id,)
        ).fetchall()
        return [{"ts": ts, "agent": a, "kind": k, "payload": json.loads(p)} for ts, a, k, p in rows]

    # --- tasks/INDEX.md --------------------------------------------------
    def _index_text(self) -> str:
        return self.index_path.read_text(encoding="utf-8-sig") if self.index_path.is_file() else ""

    @staticmethod
    def _cell(text: str) -> str:
        return text.replace("|", "/").replace("\n", " ").strip()

    def _row(self, task_id, title, project, agent, status, created, outcome="") -> str:
        cells = [task_id, title, project, agent, status, created, outcome]
        return "| " + " | ".join(self._cell(str(c)) for c in cells) + " |"

    def _append_index_row(self, task_id, title, project, agent, status, created) -> None:
        text = self._index_text()
        if not text:
            return
        if not text.endswith("\n"):
            text += "\n"
        text += self._row(task_id, title, project, agent, status, created, "runtime") + "\n"
        self.index_path.write_text(text, encoding="utf-8")

    def _sync_index_row(self, task_id: str) -> None:
        task = self.get(task_id)
        text = self._index_text()
        if not task or not text:
            return
        outcome = f"[REPORT]({task_id}/REPORT.md)" if task.status in {"completed", "partial", "blocked"} else "runtime"
        new_row = self._row(task.id, task.title, task.project, task.primary_agent or "-", task.status,
                            task.created_at[:10], outcome)
        lines = [new_row if line.startswith(f"| {task_id} |") else line for line in text.splitlines()]
        self.index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
