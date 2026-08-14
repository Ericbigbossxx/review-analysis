"""Collect Walmart's public Bazaarvoice display feed for one report run.

The legacy display feed exposes a page-wide rating histogram, the number of
ratings-only submissions, and paginated written reviews. Those three values
are retained separately so text analysis never claims ratings-only coverage.
"""

from __future__ import annotations

import hashlib
import html
import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


BASE_URL = "https://walmart.ugc.bazaarvoice.com/1336"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ReviewTracker/1.0"
REVIEW_START = re.compile(
    r'<div id="BVRRDisplayContentReviewID_(\d+)" class="([^"]*)">'
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _item_id(url: str) -> str:
    match = re.search(r"/(\d+)(?:[/?#]|$)", url.rstrip("/"))
    if not match:
        raise ValueError(f"No Walmart item ID in URL: {url}")
    return match.group(1)


def _request_djs(item_id: str, page: int, timeout: int = 90) -> str:
    params = urllib.parse.urlencode(
        {
            "format": "embeddedhtml",
            "num": "100",
            "page": str(page),
            "sort": "submissionTime",
            "dir": "desc",
        }
    )
    request = urllib.request.Request(
        f"{BASE_URL}/{item_id}/reviews.djs?{params}",
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Walmart Bazaarvoice HTTP {exc.code}") from exc


def _extract_materials(djs: str) -> dict[str, str]:
    marker = "var materials="
    start = djs.find(marker)
    if start < 0:
        raise ValueError("Bazaarvoice materials payload was not found")
    value, _ = json.JSONDecoder().raw_decode(djs[start + len(marker) :])
    if not isinstance(value, dict) or "BVRRSourceID" not in value:
        raise ValueError("Bazaarvoice review material was not found")
    return {str(key): str(item) for key, item in value.items()}


def _plain(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text).replace("\xa0", " ")
    return re.sub(r"[ \t\r\f\v]+", " ", text).strip()


def _capture(block: str, pattern: str) -> str:
    match = re.search(pattern, block, flags=re.IGNORECASE | re.DOTALL)
    return _plain(match.group(1)) if match else ""


def _parse_review_blocks(review_html: str) -> list[dict[str, Any]]:
    starts = list(REVIEW_START.finditer(review_html))
    rows: list[dict[str, Any]] = []
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(review_html)
        block = review_html[match.start() : end]
        rating_text = _capture(
            block,
            r'itemprop="ratingValue"[^>]*>(.*?)</span>',
        )
        if not rating_text.isdigit():
            continue
        date_match = re.search(
            r'<meta\s+itemprop="datePublished"\s+content="([^"]+)"\s*/?>',
            block,
            flags=re.IGNORECASE,
        )
        rows.append(
            {
                "date": date_match.group(1) if date_match else "",
                "id": match.group(1),
                "nickname": _capture(
                    block,
                    r'itemprop="author"[^>]*class="[^"]*BVRRNickname[^"]*"[^>]*>(.*?)</span>',
                ),
                "rating": int(rating_text),
                "referenceId": None,
                "syndicationSource": None,
                "text": _capture(
                    block,
                    r'<div\s+itemprop="description"[^>]*>(.*?)</div>\s*<div class="RRBeforeFeedbackContainerSpacer',
                ),
                "title": _capture(
                    block,
                    r'itemprop="name"[^>]*class="[^"]*BVRRReviewTitle[^"]*"[^>]*>(.*?)</span>',
                ),
                "verified": "BVDI_BAContentVerifiedPurchaser" in match.group(2),
            }
        )
    return rows


def _summary(first_page_djs: str) -> dict[str, Any]:
    materials = _extract_materials(first_page_djs)
    summary_html = materials.get("BVRRRatingSummarySourceID", "")
    review_html = materials["BVRRSourceID"]
    rating_rows = re.findall(
        r'BVRRHistogramBarRow([1-5])".*?BVRRHistAbsLabel">(\d+)</span>',
        summary_html,
        flags=re.DOTALL,
    )
    ratings = {word: 0 for word in ("one", "two", "three", "four", "five")}
    names = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}
    for star, count in rating_rows:
        ratings[names[int(star)]] = int(count)
    review_count_match = re.search(r'itemprop="reviewCount"\s+content="(\d+)"', summary_html)
    average_match = re.search(
        r'itemprop="ratingValue"[^>]*class="[^"]*BVRRRatingNumber[^"]*"[^>]*>([0-9.]+)</span>',
        summary_html,
    )
    ratings_only_match = re.search(r'"numRatingsOnlyReviews":(\d+)', first_page_djs)
    product_name = _capture(
        review_html,
        r'<span class="BVRRDisplayContentSubtitleProductDescription">(.*?)</span>',
    )
    total_reviews = int(review_count_match.group(1)) if review_count_match else sum(ratings.values())
    ratings_only = int(ratings_only_match.group(1)) if ratings_only_match else 0
    return {
        "productName": product_name,
        "totalReviewCount": total_reviews,
        "reviewsWithTextCount": max(0, total_reviews - ratings_only),
        "ratingsOnlyReviewCount": ratings_only,
        "averageOverallRating": float(average_match.group(1)) if average_match else None,
        "ratings": ratings,
    }


def collect_listing(source: dict[str, Any], raw_dir: Path) -> dict[str, Any]:
    item_id = _item_id(str(source["url"]))
    pages: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    page = 1
    stats: dict[str, Any] | None = None

    while stats is None or page <= max(1, math.ceil(stats["reviewsWithTextCount"] / 100)):
        raw_path = raw_dir / "walmart" / f"{source['sku']}_{item_id}_page_{page}.djs"
        if raw_path.exists():
            djs = raw_path.read_text(encoding="utf-8-sig")
        else:
            djs = _request_djs(item_id, page)
            _write_text(raw_path, djs)
        materials = _extract_materials(djs)
        if stats is None:
            stats = _summary(djs)
        page_reviews = _parse_review_blocks(materials["BVRRSourceID"])
        reviews.extend(page_reviews)
        pages.append(
            {
                "page": page,
                "count": len(page_reviews),
                "sha256": _sha256(raw_path),
                "path": str(raw_path),
            }
        )
        if not page_reviews:
            break
        page += 1
        time.sleep(0.05)

    if stats is None:
        raise RuntimeError(f"No Walmart Bazaarvoice statistics for {source['sku']}")
    unique_reviews = {str(row["id"]): row for row in reviews}
    reviews = list(unique_reviews.values())
    star_sum = sum(int(value) for value in stats["ratings"].values())
    collected_rating_counts = {
        name: sum(1 for row in reviews if int(row["rating"]) == star)
        for star, name in ((1, "one"), (2, "two"), (3, "three"), (4, "four"), (5, "five"))
    }
    low_star_reviews = [row for row in reviews if int(row["rating"]) in (1, 2, 3)]
    low_star_text_total = sum(collected_rating_counts[name] for name in ("one", "two", "three"))
    qa_passed = (
        len(reviews) == stats["reviewsWithTextCount"]
        and star_sum == stats["totalReviewCount"]
    )
    return {
        "platform": "Walmart",
        "sku": source["sku"],
        "brand": source.get("brand"),
        "category": source.get("category"),
        "url": source["url"],
        "itemId": item_id,
        "productName": stats["productName"],
        "stats": {
            **stats,
            "textRatings": collected_rating_counts,
            "ratingDistributionScope": "ALL_RATINGS_INCLUDING_RATINGS_ONLY",
            "textRatingDistributionScope": "WRITTEN_REVIEWS_ONLY",
            "pageWideRatingDistributionAvailable": True,
        },
        "reviews": low_star_reviews,
        "qa": {
            "starSum": star_sum,
            "textStarSum": sum(collected_rating_counts.values()),
            "collectedWrittenReviews": len(reviews),
            "collectedWrittenRatings": collected_rating_counts,
            "collectedLowStarText": len(low_star_reviews),
            "starSumMatchesTotal": star_sum == stats["totalReviewCount"],
            "textStarSumMatchesTotal": sum(collected_rating_counts.values()) == stats["reviewsWithTextCount"],
            "writtenReviewCountMatches": len(reviews) == stats["reviewsWithTextCount"],
            "lowStarTextTotalMatches": len(low_star_reviews) == low_star_text_total,
            "pageWideRatingDistributionAvailable": True,
            "storefrontCrossValidation": "PENDING",
            "passed": qa_passed,
            "rawPages": pages,
        },
        "errors": [
            "Public Bazaarvoice values are internally reconciled; the Walmart storefront remains pending as an independent cross-validation source."
        ],
    }


def collect_walmart_bazaarvoice(run_dir: Path) -> dict[str, Any]:
    sources = json.loads((run_dir / "listing_sources.json").read_text(encoding="utf-8-sig"))
    walmart_sources = [row for row in sources if str(row.get("platform", "")).lower() == "walmart"]
    output: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    raw_dir = run_dir / "raw" / "walmart_bv"
    for source in walmart_sources:
        try:
            output.append(collect_listing(source, raw_dir))
        except Exception as exc:  # The run report must retain per-SKU failures.
            failures.append({"sku": str(source.get("sku")), "error": str(exc)})
    output_path = run_dir / "walmart_bv_raw.json"
    _write_json(output_path, output)
    result = {
        "listings": len(walmart_sources),
        "collected": len(output),
        "passed": sum(1 for row in output if row["qa"]["passed"]),
        "failed": len(failures),
        "totalReviews": sum(row["stats"]["totalReviewCount"] for row in output),
        "writtenReviews": sum(row["stats"]["reviewsWithTextCount"] for row in output),
        "ratingsOnly": sum(row["stats"]["ratingsOnlyReviewCount"] for row in output),
        "output": str(output_path),
        "failures": failures,
    }
    _write_json(run_dir / "walmart_bv_collection_summary.json", result)
    return result
