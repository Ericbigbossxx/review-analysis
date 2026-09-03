import tempfile
import unittest
from collections import Counter
from pathlib import Path

from modules.review_tracker.preflight import load_scope, normalize_platform, run_preflight
from modules.review_tracker.scope import build_frozen_scope, load_review_scope, sha256


ROOT = Path(__file__).resolve().parents[1]


class ReviewTrackerPreflightTests(unittest.TestCase):
    def test_platform_normalization(self):
        self.assertEqual("THD", normalize_platform("Homedepot"))
        self.assertEqual("LOWES", normalize_platform("Lowes"))
        self.assertEqual("WALMART", normalize_platform("Walmart"))

    def test_listing_master_has_dynamic_review_scope(self):
        # Scope is dynamic (2026-09-03: 35 -> 30 per the approved 9.3 product
        # list). Assert against the live workbook rather than a frozen count so
        # a legitimate scope change does not rot this test.
        rows = load_review_scope(ROOT / "config" / "listing_master.xlsx")
        live = Counter(row["platform_code"] for row in rows)
        self.assertEqual(sum(live.values()), len(rows))
        for platform in ("THD", "LOWES", "WALMART"):
            self.assertGreaterEqual(live[platform], 1)
        self.assertTrue(len(rows) > 0)

    def test_repository_preflight_is_read_only_and_passes(self):
        database = ROOT / "database" / "tracker.db"
        db_before = sha256(database)
        master_before = sha256(ROOT / "config" / "listing_master.xlsx")
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "run"
            build_frozen_scope(ROOT / "config" / "listing_master.xlsx", run_dir, "TEST_DYNAMIC_SCOPE", "2026-08-13", "2026-08-12T00:00:00+00:00")
            rows, counts = load_scope(run_dir / "listing_sources.json")
            # Frozen scope must exactly match the live workbook scope.
            live_rows = load_review_scope(ROOT / "config" / "listing_master.xlsx")
            self.assertEqual(len(live_rows), len(rows))
            self.assertEqual(
                Counter(row["platform_code"] for row in live_rows),
                Counter(row["platform_code"] for row in rows),
            )
            result = run_preflight(ROOT, run_dir / "listing_sources.json")
        self.assertEqual("PREFLIGHT_PASSED", result["status"])
        self.assertEqual(db_before, sha256(database))
        self.assertEqual(master_before, sha256(ROOT / "config" / "listing_master.xlsx"))
        self.assertEqual(result["database_sha256_before"], result["database_sha256_after"])


if __name__ == "__main__":
    unittest.main()
