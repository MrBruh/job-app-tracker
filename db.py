"""SQLite data layer for the Job Application Tracker.

All SQL lives here; the UI calls these functions and never writes SQL.

Connection model (per SPEC.md): every function takes an open ``sqlite3.Connection``
as its first argument. ``connect()`` configures it (foreign keys ON, Row factory),
runs migrations, and seeds the default stages. The app holds one connection for its
lifetime; tests pass a ``:memory:`` or ``tmp_path`` connection.

Stage changes go through ``set_stage`` ONLY, so a ``stage_event`` is always
recorded. ``update_application`` deliberately never touches ``current_stage_id``.

Timestamps are UTC ISO 8601 strings. Rows come back as ``sqlite3.Row`` (dict-like).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 2

DEFAULT_DB_PATH = Path.home() / ".job-app-tracker" / "jobtracker.db"

# Seeded pipeline stages, research-backed defaults: (name, sort_order, kind).
DEFAULT_STAGES = [
    ("Applied", 20, "active"),
    ("Online Assessment", 30, "active"),
    ("Phone/Recruiter Screen", 40, "active"),
    ("Interview", 50, "active"),
    ("Final/Onsite", 60, "active"),
    ("Offer", 70, "active"),
    ("Accepted", 80, "terminal_positive"),
    ("Rejected", 90, "terminal_negative"),
    ("Withdrawn", 100, "terminal_negative"),
    ("Ghosted/No-response", 110, "terminal_negative"),
]

_SCHEMA_V1 = """
CREATE TABLE stage (
  id          INTEGER PRIMARY KEY,
  name        TEXT    NOT NULL,
  sort_order  INTEGER NOT NULL,
  kind        TEXT    NOT NULL CHECK (kind IN ('active','terminal_positive','terminal_negative'))
);

CREATE TABLE application (
  id               INTEGER PRIMARY KEY,
  company          TEXT    NOT NULL,
  role             TEXT    NOT NULL,
  job_url          TEXT,
  location         TEXT,
  source           TEXT,
  current_stage_id INTEGER NOT NULL REFERENCES stage(id),
  date_applied     TEXT,
  notes            TEXT,
  created_at       TEXT    NOT NULL,
  updated_at       TEXT    NOT NULL
);

CREATE TABLE stage_event (
  id             INTEGER PRIMARY KEY,
  application_id INTEGER NOT NULL REFERENCES application(id) ON DELETE CASCADE,
  stage_id       INTEGER NOT NULL REFERENCES stage(id),
  changed_at     TEXT    NOT NULL,
  note           TEXT
);

CREATE TABLE qa_entry (
  id             INTEGER PRIMARY KEY,
  application_id INTEGER NOT NULL REFERENCES application(id) ON DELETE CASCADE,
  question       TEXT    NOT NULL,
  answer         TEXT,
  created_at     TEXT    NOT NULL,
  updated_at     TEXT    NOT NULL
);
"""


def _utcnow() -> str:
    """Current time as a UTC ISO 8601 string (the one source of truth for stamps)."""
    return datetime.now(timezone.utc).isoformat()


# ── connection / migration / seed ────────────────────────────────────────

def connect(path=DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open the DB, enable foreign keys, set the Row factory, migrate, and seed.

    ``path`` may be a path-like or the literal ``":memory:"``. For a file path the
    parent directory is created if missing (sqlite3 will not create it, nor expand
    ``~``). Returns the configured connection.
    """
    if path == ":memory:":
        target = ":memory:"
    else:
        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        target = str(p)

    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    # Foreign keys are per-connection and OFF by default; required for ON DELETE
    # CASCADE and reference enforcement. Set outside any transaction.
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)
    seed_stages(conn)
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    """Apply schema migrations in order, tracked by ``PRAGMA user_version``."""
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version < 1:
        conn.executescript(_SCHEMA_V1)
        conn.execute("PRAGMA user_version = 1")
        conn.commit()
    if version < 2:
        # v2 retires the "Saved" stage. Anything still on it is reassigned to
        # "Applied" before the row is deleted (foreign keys are ON, so the
        # references in application/stage_event must be repointed first).
        _migrate_v2_remove_saved(conn)
        conn.execute("PRAGMA user_version = 2")
        conn.commit()


def _migrate_v2_remove_saved(conn: sqlite3.Connection) -> None:
    """Reassign any application/stage_event on 'Saved' to 'Applied', then drop
    'Saved'. A no-op when 'Saved' is absent (e.g. a fresh DB seeded without it)."""
    saved = conn.execute("SELECT id FROM stage WHERE name = 'Saved'").fetchone()
    if saved is None:
        return
    saved_id = saved["id"]
    applied = conn.execute("SELECT id FROM stage WHERE name = 'Applied'").fetchone()
    if applied is not None:
        target_id = applied["id"]
    else:
        # Defensive fallback: if 'Applied' is missing, use the lowest remaining
        # stage so existing rows keep a valid stage reference.
        row = conn.execute(
            "SELECT id FROM stage WHERE id != ? ORDER BY sort_order LIMIT 1",
            (saved_id,),
        ).fetchone()
        if row is None:
            return
        target_id = row["id"]
    conn.execute(
        "UPDATE application SET current_stage_id = ? WHERE current_stage_id = ?",
        (target_id, saved_id),
    )
    conn.execute(
        "UPDATE stage_event SET stage_id = ? WHERE stage_id = ?",
        (target_id, saved_id),
    )
    conn.execute("DELETE FROM stage WHERE id = ?", (saved_id,))


def seed_stages(conn: sqlite3.Connection) -> None:
    """Insert the default stages, but only when the table is empty (idempotent)."""
    count = conn.execute("SELECT COUNT(*) FROM stage").fetchone()[0]
    if count == 0:
        conn.executemany(
            "INSERT INTO stage (name, sort_order, kind) VALUES (?, ?, ?)",
            DEFAULT_STAGES,
        )
        conn.commit()


# ── stages ───────────────────────────────────────────────────────────────

def list_stages(conn: sqlite3.Connection):
    """All stages in pipeline order."""
    return conn.execute("SELECT * FROM stage ORDER BY sort_order").fetchall()


# ── applications ──────────────────────────────────────────────────────────

def add_application(conn, *, company, role, stage_id, job_url=None, location=None,
                    source=None, date_applied=None, notes=None) -> int:
    """Insert an application and record its initial stage_event. Returns the new id."""
    now = _utcnow()
    with conn:
        cur = conn.execute(
            """INSERT INTO application
                 (company, role, job_url, location, source, current_stage_id,
                  date_applied, notes, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (company, role, job_url, location, source, stage_id, date_applied,
             notes, now, now),
        )
        app_id = cur.lastrowid
        conn.execute(
            "INSERT INTO stage_event (application_id, stage_id, changed_at) "
            "VALUES (?, ?, ?)",
            (app_id, stage_id, now),
        )
    return app_id


def update_application(conn, app_id, *, company, role, job_url=None, location=None,
                       source=None, date_applied=None, notes=None) -> None:
    """Update an application's fields. Never changes the stage — use set_stage."""
    conn.execute(
        """UPDATE application
              SET company=?, role=?, job_url=?, location=?, source=?,
                  date_applied=?, notes=?, updated_at=?
            WHERE id=?""",
        (company, role, job_url, location, source, date_applied, notes,
         _utcnow(), app_id),
    )
    conn.commit()


def get_application(conn, app_id):
    """One application row (or None)."""
    return conn.execute(
        "SELECT * FROM application WHERE id=?", (app_id,)
    ).fetchone()


def list_applications(conn, *, stage_id=None):
    """Applications joined with their current stage, newest-applied first.

    Pass ``stage_id`` to filter to one stage. Each row carries ``stage_name``,
    ``stage_kind`` and ``stage_sort`` for display.
    """
    sql = (
        "SELECT a.*, s.name AS stage_name, s.kind AS stage_kind, "
        "       s.sort_order AS stage_sort "
        "FROM application a JOIN stage s ON s.id = a.current_stage_id"
    )
    params = ()
    if stage_id is not None:
        sql += " WHERE a.current_stage_id = ?"
        params = (stage_id,)
    sql += " ORDER BY a.date_applied IS NULL, a.date_applied DESC, a.id DESC"
    return conn.execute(sql, params).fetchall()


def delete_application(conn, app_id) -> None:
    """Delete an application; cascades to its qa_entry and stage_event rows."""
    conn.execute("DELETE FROM application WHERE id=?", (app_id,))
    conn.commit()


def set_stage(conn, app_id, stage_id, note=None) -> None:
    """Change an application's stage atomically: update the column AND log an event."""
    now = _utcnow()
    with conn:  # transaction: both statements commit together or not at all
        conn.execute(
            "UPDATE application SET current_stage_id=?, updated_at=? WHERE id=?",
            (stage_id, now, app_id),
        )
        conn.execute(
            "INSERT INTO stage_event (application_id, stage_id, changed_at, note) "
            "VALUES (?, ?, ?, ?)",
            (app_id, stage_id, now, note),
        )


def list_stage_events(conn, app_id):
    """An application's stage history in chronological order (for a future chart)."""
    return conn.execute(
        "SELECT * FROM stage_event WHERE application_id=? ORDER BY changed_at, id",
        (app_id,),
    ).fetchall()


def list_stage_history(conn, app_id):
    """An application's stage changes joined with stage names, newest first.

    Read-only view for the detail screen; each row carries ``stage_name`` and
    ``stage_kind`` alongside ``changed_at`` and ``note``.
    """
    return conn.execute(
        """SELECT e.changed_at, e.note, s.name AS stage_name, s.kind AS stage_kind
             FROM stage_event e JOIN stage s ON s.id = e.stage_id
            WHERE e.application_id = ?
            ORDER BY e.changed_at DESC, e.id DESC""",
        (app_id,),
    ).fetchall()


# ── Q&A entries ───────────────────────────────────────────────────────────

def add_qa(conn, app_id, question, answer=None) -> int:
    """Add a Q&A entry to an application. Returns the new id."""
    now = _utcnow()
    cur = conn.execute(
        "INSERT INTO qa_entry (application_id, question, answer, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (app_id, question, answer, now, now),
    )
    conn.commit()
    return cur.lastrowid


def update_qa(conn, qa_id, question, answer=None) -> None:
    """Update a Q&A entry's question/answer."""
    conn.execute(
        "UPDATE qa_entry SET question=?, answer=?, updated_at=? WHERE id=?",
        (question, answer, _utcnow(), qa_id),
    )
    conn.commit()


def delete_qa(conn, qa_id) -> None:
    """Delete a Q&A entry."""
    conn.execute("DELETE FROM qa_entry WHERE id=?", (qa_id,))
    conn.commit()


def list_qa(conn, app_id):
    """An application's Q&A entries, oldest first."""
    return conn.execute(
        "SELECT * FROM qa_entry WHERE application_id=? ORDER BY created_at, id",
        (app_id,),
    ).fetchall()


def search_qa(conn, term):
    """Q&A entries whose question or answer contains ``term`` (case-insensitive).

    Returns rows carrying the source ``company`` and ``role``. An empty/blank term
    returns no rows (the search view shows its initial hint instead).
    """
    if not term or not term.strip():
        return []
    like = f"%{term.strip()}%"
    return conn.execute(
        """SELECT q.*, a.company AS company, a.role AS role
             FROM qa_entry q JOIN application a ON a.id = q.application_id
            WHERE q.question LIKE ? OR q.answer LIKE ?
            ORDER BY q.updated_at DESC""",
        (like, like),
    ).fetchall()
