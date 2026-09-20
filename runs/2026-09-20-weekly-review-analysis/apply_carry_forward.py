"""Apply the 2026-09-20 user ruling to the two identity-compromised Walmart SKUs.

Ruling (verbatim): "那个Walmart的问题，沿用上一期的数据就行，现在是产品unpublish了，
所以被重新定位。"
=> Carry forward the PRIOR period's (2026-09-10) data for the affected SKUs.

This supersedes the earlier IDENTITY_COMPROMISED_USE_AUX_FEED handling, which
used THIS run's feed values. Follows the 2026-09-10 precedent procedure
(decisions/2026-09-10_WB40VCOMBO_carry_forward.json):

  1. copy the prior run's DATA fields for each affected SKU into the current row;
  2. keep the frozen url/itemId (scope authority is the workbook, not the page);
  3. record carriedForwardFrom + carryForwardReason (verbatim) + observedAnomaly;
  4. leave the raw CDP batches untouched as evidence.

Reads  : pre_carryforward/walmart_storefront_current.json  (pre-override snapshot)
Writes : walmart_storefront_current.json
"""
from __future__ import annotations

import json
from pathlib import Path

RUN = Path(__file__).resolve().parent
PRIOR = RUN.parent / "2026-09-10-weekly-review-analysis"
PRIOR_DATE = "2026-09-10"
RULING = "那个Walmart的问题，沿用上一期的数据就行，现在是产品unpublish了，所以被重新定位。"

# The two rows the ruling covers, with this run's observed foreign landing.
TARGETS = {
    "WB20VTRSBL": {"landed": "864525478", "kind": "CROSS_SKU_COLLISION"},
    "WB40VCOMBO": {"landed": "15830216038", "kind": "FOREIGN_BRAND_REDIRECT"},
}

# Data fields taken from the prior row. Item-identity fields NOT copied:
#   itemId / url    -> frozen scope values owned by the workbook
#   status          -> recomputed below from the ruling
#   sku / challenge / method / verifiedAt / ms -> always this run's own observation
COPY_FIELDS = [
    "finalUrl", "title", "productName",
    "averageRating", "totalRatings", "totalReviews", "ratingsDistribution",
    "pageTotalRatings", "pageTotalReviews", "pageAverageRating",
    "totalReviewCount", "reviewsWithTextCount", "averageOverallRating",
    "ratings", "qaPassed", "qaWarnings",
]


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    current = read(RUN / "pre_carryforward" / "walmart_storefront_current.json")
    prior = {r["sku"]: r for r in read(PRIOR / "walmart_storefront_current.json")["results"]}
    prior_summary = {
        r["sku"]: r for r in read(PRIOR / "review_summary.json") if r["platform"] == "Walmart"
    }

    applied = {}
    for row in current["results"]:
        sku = row["sku"]
        if sku not in TARGETS:
            continue
        src = prior[sku]

        # 1) preserve this run's own observation as evidence BEFORE overwriting
        prior_obs = row.get("observedAnomaly") or {}
        # snapshot this run's own pre-override values BEFORE the copy loop mutates row
        superseded = {
            "totalReviewCount": row.get("totalReviewCount"),
            "averageOverallRating": row.get("averageOverallRating"),
            "ratings": row.get("ratings"),
            "note": "this run's aux-feed values, discarded in favour of the prior period",
        }
        anomaly = {
            "observedAt": row.get("verifiedAt"),
            "type": TARGETS[sku]["kind"],
            "frozenItemId": row.get("itemId"),
            "frozenUrl": row.get("url"),
            "landedItemId": TARGETS[sku]["landed"],
            "landedFinalUrl": prior_obs.get("landedFinalUrl"),
            "landedTitle": prior_obs.get("landedTitle"),
            "landedProductName": prior_obs.get("landedProductName"),
            "landedPageCounts": prior_obs.get("landedPageCounts"),
            "note": (
                "scope_diff reports LINK_CHANGED=0 because the WORKBOOK url is unchanged; "
                "the platform-side landing target moved. Preserved verbatim as evidence — "
                "no value from the landed page is attributed to this SKU."
            ),
        }

        # 2) apply the prior period's data fields
        for field in COPY_FIELDS:
            row[field] = src.get(field)

        # 3) identity stays frozen; flag the carry-forward
        row["status"] = "CARRY_FORWARD_PRIOR_PERIOD"
        row["availabilityStatus"] = "CARRY_FORWARD_PRIOR_PERIOD"
        row["carriedForwardFrom"] = PRIOR_DATE
        row["carryForwardReason"] = RULING
        row["identityCompromised"] = True
        row["observedAnomaly"] = anomaly
        row["storefrontCrossValidation"] = "CARRY_FORWARD_PRIOR_PERIOD"

        applied[sku] = {
            "priorValuesApplied": {f: src.get(f) for f in COPY_FIELDS},
            "priorSummaryTotalReviews": prior_summary[sku]["totalReviews"],
            "priorSummaryLowStar": (
                prior_summary[sku]["rating1"]
                + prior_summary[sku]["rating2"]
                + prior_summary[sku]["rating3"]
            ),
            "supersededObservationFromThisRun": superseded,
        }

    expected = set(TARGETS)
    if set(applied) != expected:
        raise SystemExit(f"ABORT: expected {sorted(expected)}, applied {sorted(applied)}")

    write(RUN / "walmart_storefront_current.json", current)
    write(RUN / "pre_carryforward" / "carry_forward_applied.json", applied)

    print(f"CARRIED FORWARD {len(applied)} rows from {PRIOR_DATE}: {sorted(applied)}")
    for sku in sorted(applied):
        row = next(r for r in current["results"] if r["sku"] == sku)
        print(
            f"  {sku}: status={row['status']} "
            f"totalReviewCount={row['totalReviewCount']} "
            f"averageOverallRating={row['averageOverallRating']} "
            f"ratings={row['ratings']}"
        )


if __name__ == "__main__":
    main()
