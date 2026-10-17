"""
Storage for the Task Tracker.

- Online (shared by everyone): Supabase, when supabase_url + supabase_key are given.
- Local testing: a SQLite file (tasks.db), used automatically when Supabase isn't set up.

Every action writes only the one row it changes, so two employees working at
the same time never overwrite each other's work.
"""

from __future__ import annotations  # lets the "list" method sit next to list[...] type hints

import sqlite3
from pathlib import Path

TASK_COLUMNS = [
    "id", "title", "description", "priority", "due", "assignee", "status",
    "created_at", "created_by", "updated_at", "updated_by", "completed_at",
]
USER_COLUMNS = ["name_key", "name", "pin_hash", "created_at", "last_seen"]


class SupabaseStore:
    name = "Supabase (online)"

    def __init__(self, url: str, key: str):
        from supabase import create_client  # imported here so local testing doesn't need it
        self.client = create_client(url, key)

    # ----- tasks -----
    def list(self) -> list[dict]:
        return self.client.table("tasks").select("*").execute().data or []

    def add(self, task: dict) -> None:
        self.client.table("tasks").insert(task).execute()

    def update(self, task_id: str, fields: dict) -> None:
        self.client.table("tasks").update(fields).eq("id", task_id).execute()

    def delete(self, task_id: str) -> None:
        self.client.table("tasks").delete().eq("id", task_id).execute()

    def delete_completed(self) -> None:
        self.client.table("tasks").delete().eq("status", "Completed").execute()

    # ----- users -----
    def list_users(self) -> list[dict]:
        return self.client.table("users").select("*").execute().data or []

    def get_user(self, name_key: str) -> dict | None:
        rows = self.client.table("users").select("*").eq("name_key", name_key).execute().data
        return rows[0] if rows else None

    def add_user(self, user: dict) -> None:
        self.client.table("users").insert(user).execute()

    def update_user(self, name_key: str, fields: dict) -> None:
        self.client.table("users").update(fields).eq("name_key", name_key).execute()

    def delete_user(self, name_key: str) -> None:
        self.client.table("users").delete().eq("name_key", name_key).execute()


class SQLiteStore:
    name = "Local file (testing only)"

    def __init__(self, path: Path):
        self.path = str(path)
        with self._conn() as c:
            c.execute(f"CREATE TABLE IF NOT EXISTS tasks ({', '.join(f'{k} TEXT' for k in TASK_COLUMNS)},"
                      " PRIMARY KEY (id))")
            c.execute(f"CREATE TABLE IF NOT EXISTS users ({', '.join(f'{k} TEXT' for k in USER_COLUMNS)},"
                      " PRIMARY KEY (name_key))")

    def _conn(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _insert(self, table, cols_allowed, row):
        cols = [k for k in cols_allowed if k in row]
        with self._conn() as c:
            c.execute(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                      [row[k] for k in cols])

    def _update(self, table, cols_allowed, key_col, key, fields):
        fields = {k: v for k, v in fields.items() if k in cols_allowed and k != key_col}
        if fields:
            with self._conn() as c:
                c.execute(f"UPDATE {table} SET {', '.join(f'{k} = ?' for k in fields)} WHERE {key_col} = ?",
                          [*fields.values(), key])

    # ----- tasks -----
    def list(self) -> list[dict]:
        with self._conn() as c:
            return [dict(r) for r in c.execute("SELECT * FROM tasks")]

    def add(self, task: dict) -> None:
        self._insert("tasks", TASK_COLUMNS, task)

    def update(self, task_id: str, fields: dict) -> None:
        self._update("tasks", TASK_COLUMNS, "id", task_id, fields)

    def delete(self, task_id: str) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM tasks WHERE id = ?", [task_id])

    def delete_completed(self) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM tasks WHERE status = 'Completed'")

    # ----- users -----
    def list_users(self) -> list[dict]:
        with self._conn() as c:
            return [dict(r) for r in c.execute("SELECT * FROM users")]

    def get_user(self, name_key: str) -> dict | None:
        with self._conn() as c:
            r = c.execute("SELECT * FROM users WHERE name_key = ?", [name_key]).fetchone()
            return dict(r) if r else None

    def add_user(self, user: dict) -> None:
        self._insert("users", USER_COLUMNS, user)

    def update_user(self, name_key: str, fields: dict) -> None:
        self._update("users", USER_COLUMNS, "name_key", name_key, fields)

    def delete_user(self, name_key: str) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM users WHERE name_key = ?", [name_key])
