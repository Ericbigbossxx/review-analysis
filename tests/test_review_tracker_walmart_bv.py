import json
import unittest

from modules.review_tracker.walmart_bazaarvoice import (
    _extract_materials,
    _item_id,
    _parse_review_blocks,
    _summary,
)


SUMMARY = """
<span itemprop="aggregateRating"><span itemprop="ratingValue" class="BVRRNumber BVRRRatingNumber">3.0</span>
<meta itemprop="reviewCount" content="5" /></span>
<div class="BVRRHistogramBarRow BVRRHistogramBarRow5"><span class="BVRRHistAbsLabel">2</span></div>
<div class="BVRRHistogramBarRow BVRRHistogramBarRow4"><span class="BVRRHistAbsLabel">1</span></div>
<div class="BVRRHistogramBarRow BVRRHistogramBarRow3"><span class="BVRRHistAbsLabel">0</span></div>
<div class="BVRRHistogramBarRow BVRRHistogramBarRow2"><span class="BVRRHistAbsLabel">0</span></div>
<div class="BVRRHistogramBarRow BVRRHistogramBarRow1"><span class="BVRRHistAbsLabel">2</span></div>
"""

REVIEWS = """
<span class="BVRRDisplayContentSubtitleProductDescription">Example Tool</span>
<div id="BVRRDisplayContentReviewID_10" class="BVRRContentReview BVDI_BAContentVerifiedPurchaser">
<span itemprop="author" class="BVRRNickname">Alex</span>
<span itemprop="ratingValue" class="BVRRNumber BVRRRatingNumber">1</span>
<span itemprop="name" class="BVRRValue BVRRReviewTitle">No power</span>
<meta itemprop="datePublished" content="2026-08-01"/>
<div itemprop="description" class="BVRRReviewTextContainer"><div><span class="BVRRReviewText">Stopped &amp; failed</span></div></div>
<div class="RRBeforeFeedbackContainerSpacer"></div>
</div>
<div id="BVRRDisplayContentReviewID_11" class="BVRRContentReview">
<span itemprop="author" class="BVRRNickname">Sam</span>
<span itemprop="ratingValue" class="BVRRNumber BVRRRatingNumber">5</span>
<meta itemprop="datePublished" content="2026-08-02"/>
<div itemprop="description" class="BVRRReviewTextContainer"><div><span class="BVRRReviewText">Works well</span></div></div>
<div class="RRBeforeFeedbackContainerSpacer"></div>
</div>
"""


def fixture() -> str:
    materials = json.dumps(
        {"BVRRRatingSummarySourceID": SUMMARY, "BVRRSourceID": REVIEWS},
        separators=(",", ":"),
    )
    return f"prefix var materials={materials}, suffix \"numRatingsOnlyReviews\":3"


class WalmartBazaarvoiceCollectorTests(unittest.TestCase):
    def test_extracts_item_id(self):
        self.assertEqual("864525478", _item_id("https://www.walmart.com/ip/name/864525478"))

    def test_extracts_materials_without_executing_javascript(self):
        self.assertIn("BVRRSourceID", _extract_materials(fixture()))

    def test_parses_reviews(self):
        rows = _parse_review_blocks(REVIEWS)
        self.assertEqual(2, len(rows))
        self.assertEqual("Stopped & failed", rows[0]["text"])
        self.assertTrue(rows[0]["verified"])
        self.assertEqual(5, rows[1]["rating"])

    def test_summary_keeps_written_and_ratings_only_scopes_separate(self):
        result = _summary(fixture())
        self.assertEqual(5, result["totalReviewCount"])
        self.assertEqual(3, result["ratingsOnlyReviewCount"])
        self.assertEqual(2, result["reviewsWithTextCount"])
        self.assertEqual(2, result["ratings"]["one"])
        self.assertEqual(2, result["ratings"]["five"])


if __name__ == "__main__":
    unittest.main()
