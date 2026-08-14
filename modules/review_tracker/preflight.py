"""Read-only Review Tracker preflight with dynamic frozen scope validation."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from modules.review_tracker.scope import load_review_scope, normalize_platform, read_json, scope_hash, sha256


EXPECTED_REVIEW_COLUMNS = {
    "reviews": {"review_id", "record_id", "rating", "review_text"},
    "review_snapshots": {"review_snapshot_id", "run_id", "record_id", "total_review_count", "rating_1_count", "rating_2_count", "rating_3_count"},
    "review_changes": {"review_change_id", "run_id", "record_id", "change_type"},
}


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str


def load_scope(path: Path) -> tuple[list[dict[str, Any]], dict[str, int]]:
    rows = read_json(path)
    if not isinstance(rows, list):
        raise ValueError("listing_sources.json must contain a JSON array")
    counts: dict[str, int] = {}
    for row in rows:
        platform = normalize_platform(row.get("platform_code") or row.get("platform"))
        for required in ("record_id", "sku", "url"):
            if not str(row.get(required, "")).strip():
                raise ValueError(f"listing source is missing {required}")
        counts[platform] = counts.get(platform, 0) + 1
    return rows, counts


def _readonly_connection(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def _table_count(connection: sqlite3.Connection, table: str) -> int:
    return int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f'PRAGMA table_info("{table}")')}


def _review_counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {table: _table_count(connection, table) for table in ("reviews", "review_snapshots", "review_changes")}


def run_preflight(
    project_root: Path,
    frozen_scope_path: Path,
    listing_master_path: Path | None = None,
    scope_manifest_path: Path | None = None,
    expected_lock_run_id: str | None = None,
) -> dict[str, Any]:
    root = project_root.resolve()
    database = root / "database" / "tracker.db"
    listing_master = (listing_master_path or root / "config" / "listing_master.xlsx").resolve()
    frozen_scope = (frozen_scope_path if frozen_scope_path.is_absolute() else root / frozen_scope_path).resolve()
    manifest_path = (scope_manifest_path or frozen_scope.parent / "scope_manifest.json").resolve()
    policy_path = root / "config" / "review_tracker_policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8-sig"))
    checks: list[Check] = []

    db_hash_before = sha256(database)
    config_hashes_before = {str(path): sha256(path) for path in (listing_master, policy_path)}
    master_scope = load_review_scope(listing_master)
    frozen_rows, frozen_counts = load_scope(frozen_scope)
    manifest = read_json(manifest_path)
    master_ids = [row["record_id"] for row in master_scope]
    checks.append(Check("listing_master_readable", True, str(listing_master)))
    checks.append(Check("active_scope_non_empty", bool(master_scope), f"rows={len(master_scope)}"))
    checks.append(Check("frozen_scope_count", len(frozen_rows) == manifest.get("active_scope_count"), f"rows={len(frozen_rows)}"))
    checks.append(Check("frozen_scope_ids", master_ids == manifest.get("active_record_ids"), f"ids={len(master_ids)}"))
    checks.append(Check("frozen_scope_hash", scope_hash(frozen_rows) == manifest.get("scope_hash"), str(manifest.get("scope_hash"))))
    checks.append(Check("source_file_hash", sha256(listing_master) == manifest.get("source_file_hash"), str(manifest.get("source_file_hash"))))
    checks.append(Check("platform_counts", frozen_counts == manifest.get("platform_counts"), str(frozen_counts)))

    with _readonly_connection(database) as connection:
        counts_before = _review_counts(connection)
        expected_reviews = int(policy.get("protected_review_history_count", counts_before["reviews"]))
        checks.append(Check("protected_review_history", counts_before["reviews"] == expected_reviews, f"reviews={counts_before['reviews']}"))
        missing_schema: dict[str, list[str]] = {}
        for table, expected in EXPECTED_REVIEW_COLUMNS.items():
            missing = sorted(expected - _columns(connection, table))
            if missing:
                missing_schema[table] = missing
        checks.append(Check("review_schema", not missing_schema, f"missing={missing_schema}"))
        listing_writes = int(
            connection.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM review_snapshots rs JOIN collection_runs cr ON cr.run_id=rs.run_id WHERE cr.module_name='listing_monitor') +
                    (SELECT COUNT(*) FROM review_changes rc JOIN collection_runs cr ON cr.run_id=rc.run_id WHERE cr.module_name='listing_monitor') +
                    (SELECT COUNT(*) FROM reviews r JOIN collection_runs cr ON cr.run_id=r.first_seen_run_id WHERE cr.module_name='listing_monitor') +
                    (SELECT COUNT(*) FROM reviews r JOIN collection_runs cr ON cr.run_id=r.last_seen_run_id WHERE cr.module_name='listing_monitor')
                """
            ).fetchone()[0]
        )
        checks.append(Check("listing_review_writes", listing_writes == 0, f"rows={listing_writes}"))
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        foreign_key_errors = len(connection.execute("PRAGMA foreign_key_check").fetchall())
        checks.append(Check("database_integrity", integrity == "ok", f"integrity_check={integrity}"))
        checks.append(Check("foreign_keys", foreign_key_errors == 0, f"errors={foreign_key_errors}"))
        counts_after = _review_counts(connection)

    review_lock = root / "runtime" / "review_tracker.lock"
    listing_lock = root / "runtime" / "daily_tracker.lock"
    lock_owner = None
    if review_lock.exists():
        try:
            lock_owner = read_json(review_lock).get("run_id")
        except (ValueError, json.JSONDecodeError):
            lock_owner = "INVALID"
    lock_ok = lock_owner == expected_lock_run_id if expected_lock_run_id else not review_lock.exists()
    checks.append(Check("review_lock", lock_ok, f"owner={lock_owner}"))
    checks.append(Check("lock_isolation", review_lock.resolve() != listing_lock.resolve(), "review_tracker.lock is distinct from daily_tracker.lock"))

    db_hash_after = sha256(database)
    config_hashes_after = {str(path): sha256(path) for path in (listing_master, policy_path)}
    checks.append(Check("database_unchanged", db_hash_before == db_hash_after, db_hash_after))
    checks.append(Check("review_counts_unchanged", counts_before == counts_after, str(counts_after)))
    checks.append(Check("configuration_unchanged", config_hashes_before == config_hashes_after, str(config_hashes_after)))
    passed = all(check.passed for check in checks)
    return {
        "status": "PREFLIGHT_PASSED" if passed else "PREFLIGHT_FAILED",
        "database_sha256_before": db_hash_before,
        "database_sha256_after": db_hash_after,
        "review_counts_before": counts_before,
        "review_counts_after": counts_after,
        "scope": frozen_counts,
        "scope_path": str(frozen_scope),
        "checks": [asdict(check) for check in checks],
    }
