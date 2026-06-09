"""SQLite schema migrations."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from watchtower.utils.paths import find_repo_root


def migrations_dir(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "schemas" / "sqlite"


def get_applied_versions(conn: sqlite3.Connection) -> set[int]:
    try:
        rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
        return {row[0] for row in rows}
    except sqlite3.OperationalError:
        return set()


def apply_migrations(conn: sqlite3.Connection, repo_root: Path | None = None) -> list[int]:
    """Apply pending SQL migrations in order."""
    applied: list[int] = []
    mig_dir = migrations_dir(repo_root)
    existing = get_applied_versions(conn)

    for sql_file in sorted(mig_dir.glob("*.sql")):
        version = int(sql_file.stem.split("_")[0])
        if version in existing:
            continue
        sql = sql_file.read_text(encoding="utf-8")
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO schema_migrations (version) VALUES (?)",
            (version,),
        )
        conn.commit()
        applied.append(version)

    return applied
