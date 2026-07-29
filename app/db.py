"""SQLite access layer: schema, connections, and tiny query helpers.

One file, no migrations framework, no ORM. A shared chore list is a few hundred
rows for its entire life, and SQLite in WAL mode handles that on a Raspberry Pi
without noticing.
"""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.environ.get("HOUSETASKS_DB", "housetasks.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    assignee TEXT DEFAULT '',
    due TEXT,
    priority TEXT DEFAULT 'normal',
    repeat_rule TEXT DEFAULT '',
    done INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    done_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_task_due ON tasks(done, due);

-- Every completion, kept even for repeating chores that never reach a 'done'
-- state. This is what streaks are counted from, and `prev_due` is what lets an
-- undo put a rolled-forward chore back on exactly the date it came from.
CREATE TABLE IF NOT EXISTS task_log (
    id INTEGER PRIMARY KEY,
    task_id INTEGER,
    title TEXT NOT NULL,
    assignee TEXT DEFAULT '',
    prev_due TEXT,
    done_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_task_log_day ON task_log(done_at);
"""


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init():
    with connect() as conn:
        conn.executescript(SCHEMA)


def query(sql, params=()):
    with connect() as conn:
        return conn.execute(sql, params).fetchall()


def query_one(sql, params=()):
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql, params=()):
    with connect() as conn:
        return conn.execute(sql, params).lastrowid


init()
