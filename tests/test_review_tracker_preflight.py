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
        rows = load_review_scope(ROOT / "config" / "listing_master.xlsx")
        self.assertEqual(35, len(rows))
        self.assertEqual(Counter({"WALMART": 15, "LOWES": 10, "THD": 10}), Counter(row["platform_code"] for row in rows))

    def test_repository_preflight_is_read_only_and_passes(self):
        database = ROOT / "database" / "tracker.db"
        db_before = sha256(database)
        master_before = sha256(ROOT / "config" / "listing_master.xlsx")
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "run"
            build_frozen_scope(ROOT / "config" / "listing_master.xlsx", run_dir, "TEST_DYNAMIC_SCOPE", "2026-08-13", "2026-08-12T00:00:00+00:00")
            rows, counts = load_scope(run_dir / "listing_sources.json")
            self.assertEqual(35, len(rows))
            self.assertEqual({"LOWES": 10, "THD": 10, "WALMART": 15}, counts)
            result = run_preflight(ROOT, run_dir / "listing_sources.json")
        self.assertEqual("PREFLIGHT_PASSED", result["status"])
        self.assertEqual(db_before, sha256(database))
        self.assertEqual(master_before, sha256(ROOT / "config" / "listing_master.xlsx"))
        self.assertEqual(result["database_sha256_before"], result["database_sha256_after"])


if __name__ == "__main__":
    unittest.main()
