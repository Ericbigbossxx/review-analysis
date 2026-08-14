import unittest

from scripts.build_review_period_comparison import build_comparison


def scope(record_id, url="https://www.walmart.com/ip/1"):
    return {"record_id": record_id, "platform_code": "WALMART", "platform": "Walmart", "internal_sku": record_id.split("_", 1)[1], "sku": record_id.split("_", 1)[1], "listing_url": url, "url": url}


class ReviewPeriodComparisonTests(unittest.TestCase):
    def test_uses_like_for_like_scope_and_preserves_unavailable(self):
        current = [
            {"record_id": "WALMART_A", "platform": "Walmart", "sku": "A", "totalReviews": 12, "rating1": 2, "rating2": 0, "rating3": 1, "dataAvailable": True},
            {"record_id": "WALMART_B", "platform": "Walmart", "sku": "B", "totalReviews": None, "rating1": None, "rating2": None, "rating3": None, "dataAvailable": False},
        ]
        prior = [
            {"record_id": "WALMART_A", "platform": "Walmart", "sku": "A", "totalReviews": 10, "rating1": 1, "rating2": 0, "rating3": 1},
            {"record_id": "WALMART_B", "platform": "Walmart", "sku": "B", "totalReviews": 5, "rating1": 1, "rating2": 0, "rating3": 0},
        ]
        reviews = [{"record_id": "WALMART_A", "platform": "Walmart", "date": "2026-08-01", "rating": 2, "text": "bad"}]
        result = build_comparison(current, prior, reviews, "2026-07-23", "2026-08-06", [scope("WALMART_A"), scope("WALMART_B")])
        self.assertEqual(1, result["totals"]["comparableListings"])
        self.assertEqual(1, result["totals"]["currentUnavailable"])
        self.assertEqual(2, result["totals"]["totalReviewDelta"])
        self.assertEqual(1, result["totals"]["lowStarDelta"])
        self.assertEqual(1, result["totals"]["newReadableLowStarReviews"])

    def test_new_scope_enters_current_kpi_without_false_previous(self):
        current_scope = [scope("WALMART_A"), scope("WALMART_B")]
        prior_scope = [scope("WALMART_A")]
        diff = {"categories": {"CONTINUING": [{"record_id": "WALMART_A"}], "NEW_TO_SCOPE": [{"record_id": "WALMART_B"}], "REMOVED_FROM_SCOPE": [], "LINK_CHANGED": [], "RECORD_IDENTITY_CHANGED": []}}
        current = [
            {"record_id": "WALMART_A", "platform": "Walmart", "sku": "A", "totalReviews": 12, "rating1": 2, "rating2": 0, "rating3": 0},
            {"record_id": "WALMART_B", "platform": "Walmart", "sku": "B", "totalReviews": 8, "rating1": 1, "rating2": 0, "rating3": 0},
        ]
        prior = [{"record_id": "WALMART_A", "platform": "Walmart", "sku": "A", "totalReviews": 10, "rating1": 1, "rating2": 0, "rating3": 0}]
        result = build_comparison(current, prior, [], "2026-08-06", "2026-08-13", current_scope, prior_scope, diff)
        self.assertEqual(20, result["totals"]["currentTotalReviews"])
        new_row = next(row for row in result["skus"] if row["record_id"] == "WALMART_B")
        self.assertEqual("NEW_TO_SCOPE", new_row["status"])
        self.assertIsNone(new_row["priorTotalReviews"])
        self.assertIsNone(new_row["totalReviewDelta"])

    def test_removed_scope_is_only_in_scope_audit(self):
        diff = {"categories": {"CONTINUING": [{"record_id": "WALMART_A"}], "NEW_TO_SCOPE": [], "REMOVED_FROM_SCOPE": [{"record_id": "WALMART_B"}], "LINK_CHANGED": [], "RECORD_IDENTITY_CHANGED": []}}
        current = [{"record_id": "WALMART_A", "platform": "Walmart", "sku": "A", "totalReviews": 12, "rating1": 2, "rating2": 0, "rating3": 0}]
        prior = [
            {"record_id": "WALMART_A", "platform": "Walmart", "sku": "A", "totalReviews": 10, "rating1": 1, "rating2": 0, "rating3": 0},
            {"record_id": "WALMART_B", "platform": "Walmart", "sku": "B", "totalReviews": 99, "rating1": 20, "rating2": 0, "rating3": 0},
        ]
        result = build_comparison(current, prior, [], "2026-08-06", "2026-08-13", [scope("WALMART_A")], [scope("WALMART_A"), scope("WALMART_B")], diff)
        self.assertEqual(12, result["totals"]["currentTotalReviews"])
        self.assertEqual(["WALMART_A"], [row["record_id"] for row in result["skus"]])
        self.assertEqual("WALMART_B", result["scopeChangeAudit"]["removedFromScope"][0]["record_id"])


if __name__ == "__main__":
    unittest.main()
