from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from shared.database import apply_initial_schema, connect, transaction
from shared.logging import redact
from shared.matching import build_record_id, canonical_platform, legacy_review_key, normalize_url, platform_from_url


ROOT = Path(__file__).resolve().parents[1]


class Phase1FoundationTests(unittest.TestCase):
    def test_schema_is_complete_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "tracker.db"
            connection = connect(database_path)
            apply_initial_schema(connection, ROOT / "database" / "schema.sql")
            apply_initial_schema(connection, ROOT / "database" / "schema.sql")
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertTrue({"products", "listing_snapshots", "ranking_snapshots", "review_snapshots", "reviews", "listing_changes", "review_changes", "collection_runs", "collection_errors", "evidence_files"}.issubset(tables))
            self.assertEqual(1, connection.execute("SELECT COUNT(*) FROM schema_migrations WHERE migration_id='0001_initial_schema'").fetchone()[0])
            connection.close()

    def test_foreign_key_and_transaction_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            connection = connect(Path(directory) / "tracker.db")
            apply_initial_schema(connection, ROOT / "database" / "schema.sql")
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("INSERT INTO listing_snapshots (run_id, record_id, observed_at, source_system, capture_status) VALUES ('missing','missing','2026-07-23T00:00:00Z','test','CAPTURED')")
            with self.assertRaises(RuntimeError):
                with transaction(connection):
                    connection.execute("INSERT INTO collection_runs (run_id,module_name,platform,run_mode,started_at,status,capture_status,source_system) VALUES ('rollback','review_tracker','THD','migration','2026-07-23T00:00:00Z','RUNNING','NOT_STARTED','test')")
                    raise RuntimeError("rollback")
            self.assertEqual(0, connection.execute("SELECT COUNT(*) FROM collection_runs WHERE run_id='rollback'").fetchone()[0])
            connection.close()

    def test_matching_and_legacy_key_stability(self) -> None:
        self.assertEqual("THD", canonical_platform("Homedepot"))
        self.assertEqual("THD_SKRM_S4", build_record_id("thd", "skrm s4"))
        self.assertEqual("https://www.homedepot.com/p/1", normalize_url("https://www.homedepot.com/p/1/?utm_source=x"))
        self.assertEqual("LOWES", platform_from_url("https://www.lowes.com/pd/example"))
        self.assertEqual(legacy_review_key("THD", "1", "a", "2026-01-01", 1, " title ", "body", ""), legacy_review_key("THD", "1", "a", "2026-01-01", 1, "title", "body", ""))

    def test_sensitive_logging_redaction(self) -> None:
        self.assertEqual({"token": "[REDACTED]", "nested": {"api_key": "[REDACTED]", "safe": "ok"}}, redact({"token": "secret", "nested": {"api_key": "secret", "safe": "ok"}}))


if __name__ == "__main__":
    unittest.main()
