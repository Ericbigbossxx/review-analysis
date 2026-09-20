"""Assemble this run's walmart_storefront_current.json from the CDP batch rows.

Run-local helper: the repo has NO builder for this artifact (the generated file
exists only as a per-run hand-assembled artifact; grep for `expectedListings`
matches run outputs only). Keeping it inside the run dir avoids touching
production surface while making the assembly reproducible/auditable.

Shape mirrors runs/2026-09-10-weekly-review-analysis/walmart_storefront_current.json
exactly (same key set), plus the anomaly fields the two user rulings require.

User rulings 2026-09-20 (recorded verbatim in decisions/):
  WB40VCOMBO  -> IDENTITY_COMPROMISED, use THIS run's BV auxiliary feed values.
  WB20VTRSBL  -> IDENTITY_COMPROMISED, use THIS run's BV auxiliary feed values.

A row is identity-compromised when the frozen itemId does not equal the id in
the page's final URL. Foreign-page figures are preserved under `observedAnomaly`
and never counted toward the SKU (skill: "A frozen listing URL can 302-redirect
to a DIFFERENT brand's page").
"""

from __future__ import annotations

import json
from pathlib import Path

RUN = Path(__file__).resolve().parent
REPORT_DATE = "2026-09-20"
ANOMALY_RULE = "IDENTITY_COMPROMISED_USE_AUX_FEED"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def trailing_id(url: str | None) -> str:
    return (url or "").rstrip("/").split("/")[-1]


def main() -> int:
    storefront_list = read(RUN / "walmart_storefront_list.json")
    bv_rows = {str(r["sku"]): r for r in read(RUN / "walmart_bv_raw.json")}

    # CDP batch rows, in frozen list order. batch4_retry is an independent
    # re-verification of the same observation and is kept as evidence only.
    cdp: dict[str, dict] = {}
    for i in range(1, 11):
        p = RUN / f"walmart_storefront_cdp_batch{i}.jsonl"
        row = json.loads(p.read_text(encoding="utf-8").strip().splitlines()[-1])
        cdp[str(row["sku"])] = row

    results = []
    compromised = []
    for entry in storefront_list:
        sku = str(entry["sku"])
        frozen_item_id = str(entry["itemId"])
        obs = cdp[sku]
        landed = trailing_id(obs.get("finalUrl"))
        identity_ok = landed == frozen_item_id

        bv = bv_rows.get(sku) or {}
        stats = bv.get("stats") or {}
        total = stats.get("totalReviewCount")
        ratings = {n: int((stats.get("ratings") or {}).get(n, 0) or 0) for n in ("one", "two", "three", "four", "five")}

        row = {
            "sku": sku,
            "itemId": frozen_item_id,
            "url": entry["listing_url"],
            "finalUrl": obs.get("finalUrl"),
            "title": obs.get("title"),
            "status": obs.get("status"),
            "dataAvailable": bool(obs.get("dataAvailable")),
            "ratingFound": obs.get("ratingFound"),
            # Page-level figures: extracted but UNRELIABLE (known ratio-swap
            # defect) and must never enter a delta. Nulled for compromised rows
            # because the page belongs to a foreign product.
            "averageRating": obs.get("averageRating"),
            "totalRatings": obs.get("totalRatings"),
            "totalReviews": obs.get("totalReviews"),
            "ratingsDistribution": obs.get("ratingsDistribution"),
            "productName": obs.get("productName"),
            "challenge": obs.get("challenge"),
            "ms": obs.get("ms"),
            "verifiedAt": obs.get("verifiedAt"),
            "method": obs.get("method"),
            "pageTotalRatings": obs.get("totalRatings"),
            "pageTotalReviews": obs.get("totalReviews"),
            "pageAverageRating": obs.get("averageRating"),
            # Feed-derived values (the frozen per-SKU source of record).
            "totalReviewCount": total,
            "reviewsWithTextCount": stats.get("reviewsWithTextCount"),
            "averageOverallRating": stats.get("averageOverallRating"),
            "ratings": ratings,
            "qaPassed": bool(bv.get("qa", {}).get("passed")),
            "qaWarnings": [],
        }

        page_totals_swapped = (
            isinstance(obs.get("totalReviews"), int)
            and isinstance(obs.get("totalRatings"), int)
            and obs["totalReviews"] > obs["totalRatings"]
        )
        row["pageTotalsRatioSwap"] = page_totals_swapped

        if not identity_ok:
            compromised.append(sku)
            # Foreign page must not contribute any figure to this SKU.
            row.update(
                status=ANOMALY_RULE,
                dataAvailable=True,  # data comes from the aux feed, per ruling
                availabilityStatus=ANOMALY_RULE,
                identityCompromised=True,
                frozenItemId=frozen_item_id,
                landedItemId=landed,
                finalUrl=None,
                title=None,
                productName=None,
                averageRating=None,
                totalRatings=None,
                totalReviews=None,
                pageTotalRatings=None,
                pageTotalReviews=None,
                pageAverageRating=None,
                observedAnomaly={
                    "observedAt": obs.get("verifiedAt"),
                    "frozenItemId": frozen_item_id,
                    "frozenUrl": entry["listing_url"],
                    "landedItemId": landed,
                    "landedFinalUrl": obs.get("finalUrl"),
                    "landedTitle": obs.get("title"),
                    "landedProductName": obs.get("productName"),
                    "landedPageCounts": {
                        "averageRating": obs.get("averageRating"),
                        "totalRatings": obs.get("totalRatings"),
                        "totalReviews": obs.get("totalReviews"),
                    },
                    "resolution": ANOMALY_RULE,
                    "resolutionNote": "Use this run's BV auxiliary feed values; foreign page excluded.",
                },
            )
        results.append(row)

    available = sum(1 for r in results if r["dataAvailable"])
    out = {
        "reportDate": REPORT_DATE,
        "expectedListings": len(storefront_list),
        "availableListings": available,
        "identityCompromisedListings": compromised,
        "results": results,
    }
    target = RUN / "walmart_storefront_current.json"
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "rows": len(results),
                "available": available,
                "challenges": [r["sku"] for r in results if r.get("challenge")],
                "identityCompromised": compromised,
                "pageTotalsRatioSwap": [r["sku"] for r in results if r.get("pageTotalsRatioSwap")],
                "output": str(target),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
