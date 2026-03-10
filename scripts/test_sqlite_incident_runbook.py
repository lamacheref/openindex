#!/usr/bin/env python3
"""Simulation locale du runbook incident SQLite (absence + corruption)."""

from __future__ import annotations

import shutil
import sqlite3
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
WORK_DIR = ROOT_DIR / ".tmp" / "sqlite_runbook_test"

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    id TEXT PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    size INTEGER,
    checksum TEXT,
    last_modified TEXT,
    is_directory INTEGER NOT NULL DEFAULT 0,
    is_duplicate INTEGER DEFAULT 0,
    duplicate_of TEXT,
    created_at TEXT,
    updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);
"""


def ensure_clean_workspace() -> None:
    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    WORK_DIR.mkdir(parents=True, exist_ok=True)


def bootstrap_sqlite_schema(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SQLITE_SCHEMA)


def scenario_absent_db() -> float:
    start = time.perf_counter()
    absent_db = WORK_DIR / "openindex.absent.db"

    assert not absent_db.exists()
    bootstrap_sqlite_schema(absent_db)

    with sqlite3.connect(absent_db) as conn:
        cursor = conn.execute("PRAGMA integrity_check;")
        assert cursor.fetchone()[0] == "ok"

    return time.perf_counter() - start


def scenario_corrupted_db() -> float:
    db_path = WORK_DIR / "openindex.corrupted.db"
    backup_path = WORK_DIR / "openindex.backup.db"
    recovered_path = WORK_DIR / "openindex.recovered.db"

    bootstrap_sqlite_schema(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO files
            (id, path, name, is_directory, is_duplicate, created_at, updated_at)
            VALUES ('00000000-0000-0000-0000-000000000001', '/share/docs', 'docs', 1, 0, datetime('now'), datetime('now'))
            """
        )
        conn.commit()

    start = time.perf_counter()
    shutil.copy2(db_path, backup_path)

    with open(db_path, "r+b") as handle:
        handle.seek(0)
        handle.write(b"corruption")

    corruption_detected = False
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA integrity_check;").fetchone()
    except sqlite3.DatabaseError:
        corruption_detected = True

    assert corruption_detected, "La corruption doit être détectée"

    shutil.copy2(backup_path, recovered_path)

    with sqlite3.connect(recovered_path) as conn:
        assert conn.execute("PRAGMA integrity_check;").fetchone()[0] == "ok"
        recovered_rows = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]

    assert recovered_rows >= 1
    return time.perf_counter() - start


def main() -> None:
    ensure_clean_workspace()

    absent_seconds = scenario_absent_db()
    corrupted_seconds = scenario_corrupted_db()
    total_seconds = absent_seconds + corrupted_seconds

    print("SQLite runbook simulation:")
    print(f"- absent_db_recovery_seconds={absent_seconds:.3f}")
    print(f"- corrupted_db_recovery_seconds={corrupted_seconds:.3f}")
    print(f"- total_recovery_seconds={total_seconds:.3f}")


if __name__ == "__main__":
    main()
