import unittest

from scripts.build_walmart_review_input import build_rows


class WalmartReviewInputTests(unittest.TestCase):
    def test_available_row_uses_storefront_totals_and_bv_text(self):
        storefront = {"results": [{
            "sku": "A", "brand": "B", "category": "Robot", "url": "u", "itemId": "1",
            "productName": "P", "dataAvailable": True, "status": "AVAILABLE", "qaPassed": True,
            "totalReviewCount": 5, "reviewsWithTextCount": 2, "averageOverallRating": 4.0,
            "ratings": {"one": 1, "two": 0, "three": 0, "four": 1, "five": 3},
        }]}
        bv = [{"sku": "A", "stats": {"reviewsWithTextCount": 1, "textRatings": {"one": 1, "two": 0, "three": 0, "four": 0, "five": 0}}, "reviews": [{"rating": 1}], "errors": []}]
        prior = [{"sku": "A", "stats": {"totalReviewCount": 4, "ratings": {"one": 1, "two": 0, "three": 0, "four": 1, "five": 2}}}]
        row = build_rows(storefront, bv, prior)[0]
        self.assertEqual(5, row["stats"]["totalReviewCount"])
        self.assertEqual(1, row["stats"]["textRatings"]["one"])
        self.assertEqual("BV_AUXILIARY_PARTIAL_COVERAGE", row["qa"]["storefrontCrossValidation"])
        self.assertEqual(1, row["comparison"]["totalReviewDelta"])

    def test_unavailable_row_keeps_metrics_null(self):
        storefront = {"results": [{"sku": "A", "dataAvailable": False, "status": "LISTING_PAGE_NOT_FOUND"}]}
        row = build_rows(storefront, [], [])[0]
        self.assertIsNone(row["stats"]["totalReviewCount"])
        self.assertFalse(row["qa"]["passed"])
        self.assertEqual("CURRENT_UNAVAILABLE", row["comparison"]["status"])


if __name__ == "__main__":
    unittest.main()
