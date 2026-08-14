"""Public Bazaarvoice collection for the isolated Review Tracker report run."""

from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any


API_URL = "https://api.bazaarvoice.com/data/reviews.json"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ReviewTracker/1.0"


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_passkey(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"passkey[\"']?\s*[:=]\s*[\"']([^\"']+)", text, flags=re.IGNORECASE)
    if not match:
        raise ValueError(f"Bazaarvoice passkey was not found in {path}")
    return match.group(1)


def _request_json(params: list[tuple[str, str]], timeout: int = 60) -> dict[str, Any]:
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json", "Accept-Language": "en-US,en;q=0.9"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Bazaarvoice HTTP {exc.code}") from exc
    if payload.get("HasErrors") or payload.get("Errors"):
        raise RuntimeError(f"Bazaarvoice API error: {payload.get('Errors')}")
    return payload


def _product_id(url: str) -> str:
    match = re.search(r"/(\d+)(?:[/?#]|$)", url.rstrip("/"))
    if not match:
        raise ValueError(f"No numeric product ID in URL: {url}")
    return match.group(1)


def _theme(text: str, category: str) -> str:
    value = f"{text} {category}".lower()
    rules = [
        (r"customer service|support|email|tracking|inventory|shipping|delivery|delivered|never came|not received|scam|reply|warranty|parts unavailable", "客服/履约"),
        (r"\bapp\b|gps|rtk|boundary|map|connect|bluetooth|wifi|wi-fi|signal|navigation|initialize|initializing", "APP/导航/连接"),
        (r"battery|batteries|charge|charger|charging|runtime|volt|\bah\b|power pack", "电池/充电"),
        (r"start|started|pull|string kept|engine|motor|smok|fire|won't run|would not run|stopped|stall|carb|fuel|gas|oil|no power|low power|not much power", "启动/动力故障"),
        (r"defective|broke|broken|return|returned|quit|failed|dead|replace|warranty|quality|cheaply made|missing piece|missing screw", "质量/耐久"),
        (r"heavy|weight|balance|vibration|wrist|handle|ergonomic|strap", "重量/人体工学"),
        (r"cut|mow|trimming|weed|grass|blade|line|guard|string|brush|deck|height|advance|edger", "割草/修剪效果"),
        (r"assemble|assembly|setup|install|manual|instruction", "安装/设置"),
        (r"price|value|expectation|expected|money|cost", "价格/预期"),
    ]
    for pattern, label in rules:
        if re.search(pattern, value):
            return label
    return "其他"


def _verified(review: dict[str, Any]) -> bool:
    badges = review.get("Badges") or {}
    if any("verified" in str(key).lower() for key in badges):
        return True
    values = review.get("ContextDataValues") or {}
    return any(
        "verified" in str(key).lower() and str((item or {}).get("Value", "")).lower() == "true"
        for key, item in values.items()
    )


def _rating_distribution(statistics: dict[str, Any]) -> dict[int, int]:
    result = {rating: 0 for rating in range(1, 6)}
    for row in statistics.get("RatingDistribution") or []:
        rating = int(row.get("RatingValue", 0))
        if rating in result:
            result[rating] = int(row.get("Count", 0))
    return result


def collect_listing(source: dict[str, Any], passkey: str, raw_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    platform = "THD" if str(source["platform"]).lower() == "homedepot" else "Lowes"
    product_id = _product_id(str(source["url"]))
    pages: list[dict[str, Any]] = []
    all_reviews: list[dict[str, Any]] = []
    offset = 0
    total_results: int | None = None
    product: dict[str, Any] | None = None

    while total_results is None or offset < total_results:
        raw_path = raw_dir / platform.lower() / f"{source['sku']}_{product_id}_offset_{offset}.json"
        if raw_path.exists():
            payload = json.loads(raw_path.read_text(encoding="utf-8-sig"))
        else:
            payload = _request_json(
                [
                    ("apiversion", "5.5"),
                    ("passkey", passkey),
                    ("Filter", f"ProductId:{product_id}"),
                    ("Include", "Products"),
                    ("Stats", "Reviews"),
                    ("Limit", "100"),
                    ("Offset", str(offset)),
                    ("Sort", "SubmissionTime:desc"),
                ]
            )
            _write_json(raw_path, payload)
        total_results = int(payload.get("TotalResults", 0))
        results = list(payload.get("Results") or [])
        all_reviews.extend(results)
        includes = (payload.get("Includes") or {}).get("Products") or {}
        if product is None and includes:
            product = next(iter(includes.values()))
        pages.append({"offset": offset, "count": len(results), "sha256": _sha256(raw_path), "path": str(raw_path)})
        if not results:
            break
        offset += len(results)
        time.sleep(0.05)

    if product is None and int(total_results or 0) == 0:
        product = {"Name": "", "ReviewStatistics": {"TotalReviewCount": 0, "RatingsOnlyReviewCount": 0, "RatingDistribution": []}}
    if product is None:
        raise RuntimeError(f"No product statistics returned for {platform} {source['sku']}")

    statistics = product.get("ReviewStatistics") or {}
    distribution = _rating_distribution(statistics)
    total_reviews = int(statistics.get("TotalReviewCount", product.get("TotalReviewCount", 0)) or 0)
    ratings_only = int(statistics.get("RatingsOnlyReviewCount", 0) or 0)
    endpoint_text_reviews = [review for review in all_reviews if not bool(review.get("IsRatingsOnly"))]
    readable_reviews = [
        review
        for review in endpoint_text_reviews
        if str(review.get("Title") or "").strip() or str(review.get("ReviewText") or "").strip()
    ]
    low_star_reviews: list[dict[str, Any]] = []
    for review in all_reviews:
        rating = int(review.get("Rating", 0) or 0)
        if rating not in (1, 2, 3):
            continue
        title = review.get("Title")
        body = review.get("ReviewText")
        low_star_reviews.append(
            {
                "platform": platform,
                "sku": source["sku"],
                "brand": source.get("brand"),
                "category": source.get("category"),
                "productId": product_id,
                "productName": product.get("Name"),
                "url": source["url"],
                "sourceReviewId": review.get("Id"),
                "rating": rating,
                "theme": _theme(f"{title or ''} {body or ''}", str(source.get("category") or "")) if title or body else None,
                "title": title,
                "text": body,
                "date": review.get("SubmissionTime"),
                "ratingsOnly": bool(review.get("IsRatingsOnly")),
                "syndicated": bool(review.get("IsSyndicated")),
                "sourceClient": review.get("SourceClient") or platform.lower(),
                "verified": _verified(review),
            }
        )

    theme_counts = Counter(row["theme"] for row in low_star_reviews if row.get("theme"))
    text_negative = sum(1 for review in readable_reviews if int(review.get("Rating", 0) or 0) in (1, 2))
    text_neutral = sum(1 for review in readable_reviews if int(review.get("Rating", 0) or 0) == 3)
    rating_sum = sum(distribution.values())
    endpoint_text = len(endpoint_text_reviews)
    readable_text = len(readable_reviews)
    expected_text = total_reviews - ratings_only
    qa_passed = rating_sum == total_reviews == int(total_results or 0) and endpoint_text == expected_text
    core_new = str(source.get("brand", "")).upper() == "SUNSEEKER" or "robot" in str(source.get("category", "")).lower()
    summary = {
        "platform": platform,
        "sku": source["sku"],
        "brand": source.get("brand"),
        "category": source.get("category"),
        "productId": product_id,
        "productName": product.get("Name"),
        "url": source["url"],
        "totalReviews": total_reviews,
        "avgRating": round(float(statistics.get("AverageOverallRating", 0) or 0), 4),
        "rating1": distribution[1],
        "rating2": distribution[2],
        "rating3": distribution[3],
        "rating4": distribution[4],
        "rating5": distribution[5],
        "negativeReviews": distribution[1] + distribution[2],
        "neutralReviews": distribution[3],
        "negativeRate": round((distribution[1] + distribution[2]) / total_reviews, 4) if total_reviews else 0,
        "textNegativeReviews": text_negative,
        "textNeutralReviews": text_neutral,
        "ratingsOnlyReviews": ratings_only,
        "ratingDistributionSum": rating_sum,
        "endpointAllReviews": int(total_results or 0),
        "endpointTextReviews": endpoint_text,
        "expectedTextReviews": expected_text,
        "readableTextReviews": readable_text,
        "textCoverage": round(readable_text / expected_text, 4) if expected_text else 1,
        "negativeTextCoverage": round(text_negative / (distribution[1] + distribution[2]), 4) if distribution[1] + distribution[2] else 1,
        "ratingCheck": "OK" if rating_sum == total_reviews else "MISMATCH",
        "endpointCheck": "OK" if int(total_results or 0) == total_reviews else "MISMATCH",
        "textCheck": "OK" if endpoint_text == expected_text else "MISMATCH",
        "qaStatus": "可用于评分判断" if qa_passed else "需人工复核",
        "qaPassed": qa_passed,
        "topThemes": " / ".join(f"{name} {count}" for name, count in theme_counts.most_common(3)),
        "urgency": None,
        "reviewPlan": None,
        "actionItems": [],
        "firstReview": statistics.get("FirstSubmissionTime"),
        "lastReview": statistics.get("LastSubmissionTime"),
        "coreNew": core_new,
    }
    qa = {
        "platform": platform,
        "sku": source["sku"],
        "passed": qa_passed,
        "totalReviews": total_reviews,
        "ratingSum": rating_sum,
        "endpointAllReviews": int(total_results or 0),
        "expectedTextReviews": expected_text,
        "endpointTextReviews": endpoint_text,
        "rawPages": pages,
    }
    return summary, low_star_reviews, qa


def collect_bazaarvoice(run_dir: Path) -> dict[str, Any]:
    sources = json.loads((run_dir / "listing_sources.json").read_text(encoding="utf-8-sig"))
    config_dir = run_dir / "raw" / "bv_config"
    passkeys = {
        "Homedepot": extract_passkey(config_dir / "homedepot_bvapi.js"),
        "Lowes": extract_passkey(config_dir / "lowes_bvapi.js"),
    }
    summaries: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    qa_rows: list[dict[str, Any]] = []
    for source in sources:
        platform = str(source.get("platform"))
        if platform not in passkeys:
            continue
        summary, low_star, qa = collect_listing(source, passkeys[platform], run_dir / "raw" / "bv")
        summaries.append(summary)
        reviews.extend(low_star)
        qa_rows.append(qa)

    _write_json(run_dir / "review_summary_bv.json", summaries)
    _write_json(run_dir / "low_star_reviews_bv.json", reviews)
    _write_json(run_dir / "bv_collection_qa.json", qa_rows)
    return {
        "listings": len(summaries),
        "lowStarRows": len(reviews),
        "totalReviews": sum(int(row["totalReviews"]) for row in summaries),
        "passed": sum(bool(row["qaPassed"]) for row in summaries),
        "failed": sum(not bool(row["qaPassed"]) for row in summaries),
    }
