"""Approval-gated initializer for the empty US Local Channel Listing Tracker database."""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "database" / "schema.sql"
MIGRATION_ID = "0001_initial_schema"


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply the Phase 0 SQLite schema to an approved database path.")
    parser.add_argument("database_path", type=Path, help="Target SQLite path; no collection data is inserted.")
    parser.add_argument("--approve", action="store_true", help="Required acknowledgement of the approved migration plan.")
    args = parser.parse_args()
    if not args.approve:
        raise SystemExit("Refusing to initialize a database without --approve.")

    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    checksum = hashlib.sha256(schema.encode("utf-8")).hexdigest()
    args.database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(args.database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(schema)
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (migration_id TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, checksum TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT OR IGNORE INTO schema_migrations (migration_id, checksum) VALUES (?, ?)",
            (MIGRATION_ID, checksum),
        )
    print(f"Applied {MIGRATION_ID} to {args.database_path}")


if __name__ == "__main__":
    main()
