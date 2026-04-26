"""Simple SQLite job store — no ORM, no async, just sqlite3."""

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from concurrent.futures import ThreadPoolExecutor

DB_PATH = Path(__file__).parent / "jobs.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    original_filename TEXT NOT NULL,
    video_path TEXT NOT NULL,
    output_dir TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    progress REAL NOT NULL DEFAULT 0.0,
    current_step TEXT,
    progress_detail_current INTEGER,
    progress_detail_total INTEGER,
    progress_detail_label TEXT,
    metrics_json TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);
"""

_MIGRATIONS: dict[str, str] = {
    "progress_detail_current": "ALTER TABLE jobs ADD COLUMN progress_detail_current INTEGER",
    "progress_detail_total": "ALTER TABLE jobs ADD COLUMN progress_detail_total INTEGER",
    "progress_detail_label": "ALTER TABLE jobs ADD COLUMN progress_detail_label TEXT",
}

_executor = ThreadPoolExecutor(max_workers=2)

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.executescript(_SCHEMA)
        _apply_migrations(conn)
        conn.commit()
        _local.conn = conn
    return conn


def init_db() -> None:
    conn = _get_conn()
    conn.executescript(_SCHEMA)
    _apply_migrations(conn)
    conn.commit()


def _apply_migrations(conn: sqlite3.Connection) -> None:
    existing = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(jobs)").fetchall()
    }
    for column, ddl in _MIGRATIONS.items():
        if column not in existing:
            conn.execute(ddl)


def create_job(original_filename: str, video_path: str, output_dir: str) -> str:
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    conn.execute(
        "INSERT INTO jobs (id, original_filename, video_path, output_dir, status, created_at) VALUES (?, ?, ?, ?, 'queued', ?)",
        (job_id, original_filename, video_path, output_dir, now),
    )
    conn.commit()
    return job_id


def get_job(job_id: str) -> dict[str, Any] | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if row is None:
        return None
    return dict(row)


def update_job(job_id: str, **fields: Any) -> None:
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [job_id]
    conn = _get_conn()
    conn.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", values)
    conn.commit()


def list_jobs(limit: int = 50) -> list[dict[str, Any]]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


def run_analysis_in_thread(job_id: str) -> None:
    """Run analysis in a thread pool — suitable for FastAPI BackgroundTasks."""
    from .tasks.analyze import run_analysis
    _executor.submit(run_analysis, job_id)
