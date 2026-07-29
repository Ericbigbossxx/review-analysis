from __future__ import annotations

import hashlib
import json
import sqlite3
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "data" / "processed" / "phase1_5_review_package.json"
WORKBOOK = ROOT / "config" / "listing_master_user_review.xlsx"
INPUT_HASHES = ROOT / "data" / "processed" / "phase1_5_input_hashes.json"


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Phase15ReviewPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.package = json.loads(PACKAGE.read_text(encoding="utf-8"))

    def test_master_has_35_unique_records(self) -> None:
        rows = self.package["master"]
        self.assertEqual(35, len(rows))
        self.assertEqual(35, len({row["record_id"] for row in rows}))

    def test_platform_urls_match_offline_detection(self) -> None:
        self.assertTrue(all(row["platform_match_status"] == "MATCH" for row in self.package["master"]))
        self.assertEqual({"WALMART": 15, "THD": 10, "LOWES": 10}, {key: sum(row["platform"] == key for row in self.package["master"]) for key in ("WALMART", "THD", "LOWES")})

    def test_duplicate_and_completeness_results(self) -> None:
        rows = self.package["master"]
        self.assertTrue(all(row["duplicate_candidate"] == "FALSE" for row in rows))
        self.assertEqual({70, 75}, {row["data_completeness_score"] for row in rows})
        self.assertEqual(1, sum(row["data_completeness_score"] == 70 for row in rows))
        self.assertTrue(all(row["data_completeness_status"] == "PARTIAL_DATA" for row in rows))

    def test_review_snapshot_association_exists(self) -> None:
        with sqlite3.connect(f"file:{(ROOT / 'database' / 'tracker.db').resolve().as_posix()}?mode=ro", uri=True) as connection:
            snapshot_records = {row[0] for row in connection.execute("SELECT DISTINCT record_id FROM review_snapshots")}
        self.assertEqual({row["record_id"] for row in self.package["master"]}, snapshot_records)

    def test_workbook_structure_validations_and_hyperlink_formula_exist(self) -> None:
        with zipfile.ZipFile(WORKBOOK) as archive:
            workbook_xml = archive.read("xl/workbook.xml").decode("utf-8")
            sheet_xml = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
        for name in ("Master Review", "Field Guide", "Platform Summary", "Issues", "Approval Instructions"):
            self.assertIn(name, workbook_xml)
        self.assertIn("dataValidations", sheet_xml)
        self.assertIn("HYPERLINK", sheet_xml)

    def test_original_inputs_are_unchanged(self) -> None:
        expected = json.loads(INPUT_HASHES.read_text(encoding="utf-8"))
        self.assertEqual(expected["listing_master_migration_draft.xlsx"], file_hash(ROOT / "config" / "listing_master_migration_draft.xlsx"))
        self.assertEqual(expected["listing_master.xlsx"], file_hash(ROOT / "config" / "listing_master.xlsx"))
        self.assertEqual(expected["tracker.db"], file_hash(ROOT / "database" / "tracker.db"))


if __name__ == "__main__":
    unittest.main()
