import json
import tempfile
import unittest
from pathlib import Path

from modules.review_tracker.scope import diff_scopes, evaluate_scope_gate, find_previous_successful_weekly_run


POLICY = {"scope_change_review_ratio": 0.2, "platform_zero_requires_review": True, "record_identity_change_requires_review": True}


def row(record_id, platform="WALMART", url=None, model="M1"):
    sku = record_id.split("_", 1)[1]
    url = url or f"https://www.walmart.com/ip/{sku}"
    return {"record_id": record_id, "platform_code": platform, "internal_sku": sku, "model": model, "listing_url": url}


class ReviewTrackerScopeTests(unittest.TestCase):
    def test_add_one(self):
        previous = [row("WALMART_A")]
        result = diff_scopes(previous + [row("WALMART_B")], previous)
        self.assertEqual(1, result["summary"]["NEW_TO_SCOPE"])

    def test_remove_one(self):
        previous = [row("WALMART_A"), row("WALMART_B")]
        result = diff_scopes([row("WALMART_A")], previous)
        self.assertEqual(1, result["summary"]["REMOVED_FROM_SCOPE"])

    def test_add_two_remove_three_and_ratio_gate(self):
        previous = [row(f"WALMART_{letter}") for letter in "ABCDE"]
        current = [row("WALMART_D"), row("WALMART_E"), row("WALMART_F"), row("WALMART_G")]
        diff = diff_scopes(current, previous)
        gate = evaluate_scope_gate(diff, current, previous, POLICY)
        self.assertEqual(2, diff["summary"]["NEW_TO_SCOPE"])
        self.assertEqual(3, diff["summary"]["REMOVED_FROM_SCOPE"])
        self.assertTrue(gate["requires_review"])

    def test_url_change(self):
        previous = [row("WALMART_A", url="https://www.walmart.com/ip/1")]
        current = [row("WALMART_A", url="https://www.walmart.com/ip/2")]
        self.assertEqual(1, diff_scopes(current, previous)["summary"]["LINK_CHANGED"])

    def test_record_identity_change(self):
        previous = [row("WALMART_A", model="M1")]
        current = [row("WALMART_A", model="M2")]
        diff = diff_scopes(current, previous)
        gate = evaluate_scope_gate(diff, current, previous, POLICY)
        self.assertEqual(1, diff["summary"]["RECORD_IDENTITY_CHANGED"])
        self.assertTrue(gate["requires_review"])

    def test_platform_count_change_without_zero(self):
        previous = [row("WALMART_A"), row("WALMART_B"), row("THD_C", platform="THD")]
        current = [row("WALMART_A"), row("THD_C", platform="THD")]
        gate = evaluate_scope_gate(diff_scopes(current, previous), current, previous, {**POLICY, "scope_change_review_ratio": 0.9})
        self.assertFalse(gate["requires_review"])

    def test_platform_count_to_zero(self):
        previous = [row("WALMART_A"), row("THD_B", platform="THD")]
        current = [row("WALMART_A")]
        gate = evaluate_scope_gate(diff_scopes(current, previous), current, previous, {**POLICY, "scope_change_review_ratio": 0.9})
        self.assertTrue(any(reason["code"] == "PLATFORM_SCOPE_DROPPED_TO_ZERO" for reason in gate["reasons"]))

    def test_previous_period_uses_latest_successful_weekly_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            runs = Path(temporary)
            for name, date, state in (("older", "2026-07-30", "SUCCESS"), ("latest", "2026-08-06", "SUCCESS_WITH_PLATFORM_LIMITATION"), ("failed", "2026-08-10", "TECHNICAL_FAILED")):
                run_dir = runs / name
                run_dir.mkdir()
                (run_dir / "listing_sources.json").write_text("[]", encoding="utf-8")
                (run_dir / "run_state.json").write_text(json.dumps({"run_id": name, "report_date": date, "mode": "PRODUCTION", "state": state}), encoding="utf-8")
            self.assertEqual("latest", find_previous_successful_weekly_run(runs, "2026-08-13").name)


if __name__ == "__main__":
    unittest.main()
