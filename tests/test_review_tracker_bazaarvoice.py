import tempfile
import unittest
from pathlib import Path

from modules.review_tracker.bazaarvoice import _product_id, _rating_distribution, _theme, extract_passkey


class BazaarvoiceCollectorTests(unittest.TestCase):
    def test_extracts_product_id(self):
        self.assertEqual("311424786", _product_id("https://www.homedepot.com/p/311424786"))
        self.assertEqual("5016678663", _product_id("https://www.lowes.com/pd/name/5016678663"))

    def test_extracts_public_passkey(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bvapi.js"
            path.write_text('apiconfig:{passkey:"public-key"}', encoding="utf-8")
            self.assertEqual("public-key", extract_passkey(path))

    def test_rating_distribution_fills_missing_stars(self):
        result = _rating_distribution({"RatingDistribution": [{"RatingValue": 5, "Count": 4}, {"RatingValue": 1, "Count": 2}]})
        self.assertEqual({1: 2, 2: 0, 3: 0, 4: 0, 5: 4}, result)

    def test_theme_is_operational(self):
        self.assertEqual("电池/充电", _theme("Battery would not charge", "Robot Mower"))
        self.assertEqual("启动/动力故障", _theme("Engine will not start", "String Trimmer"))


if __name__ == "__main__":
    unittest.main()
