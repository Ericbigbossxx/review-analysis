"""Merge Walmart storefront statistics with the auxiliary Bazaarvoice text feed."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


RATING_NAMES = ("one", "two", "three", "four", "five")


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def build_rows(storefront: dict[str, Any], bazaarvoice: list[dict[str, Any]], prior: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bv_by_sku = {str(row["sku"]): row for row in bazaarvoice}
    prior_by_sku = {str(row["sku"]): row for row in prior}
    rows: list[dict[str, Any]] = []

    for current in storefront["results"]:
        sku = str(current["sku"])
        bv = bv_by_sku.get(sku)
        previous = prior_by_sku.get(sku)
        available = bool(current.get("dataAvailable"))
        errors: list[str] = []
        if bv:
            errors.extend(str(item) for item in bv.get("errors") or [])
        if not available:
            errors.append(f"Current storefront data unavailable: {current.get('status') or current.get('error')}")

        if available:
            ratings = {name: int((current.get("ratings") or {}).get(name, 0)) for name in RATING_NAMES}
            total = int(current["totalReviewCount"])
            text_total = int(current["reviewsWithTextCount"])
            text_ratings = {
                name: int((((bv or {}).get("stats") or {}).get("textRatings") or {}).get(name, 0))
                for name in RATING_NAMES
            }
            reviews = list((bv or {}).get("reviews") or [])
            star_sum = sum(ratings.values())
            bv_text_total = int((((bv or {}).get("stats") or {}).get("reviewsWithTextCount", 0)) or 0)
            bv_text_star_sum = sum(text_ratings.values())
            low_text_total = sum(text_ratings[name] for name in ("one", "two", "three"))
            qa_passed = bool(current.get("qaPassed")) and star_sum == total
            stats: dict[str, Any] = {
                "totalReviewCount": total,
                "reviewsWithTextCount": text_total,
                "ratingsOnlyReviewCount": total - text_total,
                "averageOverallRating": float(current["averageOverallRating"]),
                "ratings": ratings,
                "textRatings": text_ratings,
                "textRatingSource": "Walmart public Bazaarvoice auxiliary feed",
            }
            qa = {
                "starSum": star_sum,
                "textStarSum": bv_text_star_sum,
                "starSumMatchesTotal": star_sum == total,
                "textStarSumMatchesTotal": bv_text_star_sum == bv_text_total,
                "lowStarTextTotalMatches": len(reviews) == low_text_total,
                "storefrontTextCount": text_total,
                "bazaarvoiceTextCount": bv_text_total,
                "storefrontTextMatchesBazaarvoice": text_total == bv_text_total,
                "storefrontCrossValidation": "EXACT" if text_total == bv_text_total else "BV_AUXILIARY_PARTIAL_COVERAGE",
                "passed": qa_passed,
            }
        else:
            reviews = list((bv or {}).get("reviews") or [])
            stats = {
                "totalReviewCount": None,
                "reviewsWithTextCount": None,
                "ratingsOnlyReviewCount": None,
                "averageOverallRating": None,
                "ratings": {name: None for name in RATING_NAMES},
                "textRatings": {name: None for name in RATING_NAMES},
                "textRatingSource": "Walmart public Bazaarvoice auxiliary feed",
            }
            qa = {
                "starSum": None,
                "textStarSum": None,
                "starSumMatchesTotal": False,
                "textStarSumMatchesTotal": False,
                "lowStarTextTotalMatches": False,
                "storefrontCrossValidation": "CURRENT_UNAVAILABLE",
                "passed": False,
            }

        previous_total = int(previous["stats"]["totalReviewCount"]) if previous and previous["stats"].get("totalReviewCount") is not None else None
        previous_low = (
            sum(int(previous["stats"]["ratings"][name]) for name in ("one", "two", "three"))
            if previous
            and previous["stats"].get("ratings")
            and all(previous["stats"]["ratings"].get(name) is not None for name in ("one", "two", "three"))
            else None
        )
        current_low = (
            sum(int(stats["ratings"][name]) for name in ("one", "two", "three"))
            if available
            else None
        )
        comparison = {
            "priorReportDate": "2026-07-23",
            "status": "COMPARABLE" if available and previous else "CURRENT_UNAVAILABLE" if not available else "NO_PRIOR",
            "priorTotalReviews": previous_total,
            "currentTotalReviews": stats["totalReviewCount"],
            "totalReviewDelta": int(stats["totalReviewCount"]) - previous_total if available and previous_total is not None else None,
            "priorLowStarReviews": previous_low,
            "currentLowStarReviews": current_low,
            "lowStarDelta": current_low - previous_low if current_low is not None and previous_low is not None else None,
        }
        rows.append(
            {
                "platform": "Walmart",
                "sku": sku,
                "brand": current.get("brand"),
                "category": current.get("category"),
                "url": current.get("url"),
                "itemId": current.get("itemId"),
                "productName": current.get("productName"),
                "dataAvailable": available,
                "availabilityStatus": current.get("status"),
                "stats": stats,
                "reviews": reviews,
                "qa": qa,
                "comparison": comparison,
                "evidence": current.get("evidence"),
                "errors": errors,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--prior-run-dir", type=Path, required=True)
    args = parser.parse_args()
    storefront = _read(args.run_dir / "walmart_storefront_current.json")
    bazaarvoice = _read(args.run_dir / "walmart_bv_raw.json")
    prior = _read(args.prior_run_dir / "walmart_raw.json")
    rows = build_rows(storefront, bazaarvoice, prior)
    output = args.run_dir / "walmart_raw.json"
    _write(output, rows)
    available = sum(1 for row in rows if row["dataAvailable"])
    print(json.dumps({"rows": len(rows), "available": available, "unavailable": len(rows) - available, "output": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
