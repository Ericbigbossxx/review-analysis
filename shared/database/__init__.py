"""Small, transaction-safe SQLite foundation; it never starts a collection."""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def connect(database_path: Path | str) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def apply_initial_schema(connection: sqlite3.Connection, schema_path: Path | str) -> str:
    schema = Path(schema_path).read_text(encoding="utf-8")
    checksum = hashlib.sha256(schema.encode("utf-8")).hexdigest()
    connection.executescript(schema)
    connection.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations (migration_id TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, checksum TEXT NOT NULL)"
    )
    connection.execute(
        "INSERT OR IGNORE INTO schema_migrations (migration_id, checksum) VALUES (?, ?)",
        ("0001_initial_schema", checksum),
    )
    return checksum


@contextmanager
def transaction(connection: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    nested = connection.in_transaction
    savepoint = "controlled_transaction"
    try:
        if nested:
            connection.execute(f"SAVEPOINT {savepoint}")
        else:
            connection.execute("BEGIN")
        yield connection
    except Exception:
        if nested:
            connection.execute(f"ROLLBACK TO {savepoint}")
            connection.execute(f"RELEASE {savepoint}")
        else:
            connection.rollback()
        raise
    else:
        if nested:
            connection.execute(f"RELEASE {savepoint}")
        else:
            connection.commit()


def upsert_product(connection: sqlite3.Connection, row: dict[str, object]) -> None:
    columns = list(row)
    updates = ", ".join(f"{column}=excluded.{column}" for column in columns if column != "record_id")
    placeholders = ", ".join(f":{column}" for column in columns)
    connection.execute(
        f"INSERT INTO products ({', '.join(columns)}) VALUES ({placeholders}) ON CONFLICT(record_id) DO UPDATE SET {updates}",
        row,
    )
