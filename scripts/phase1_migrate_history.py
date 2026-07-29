"""Offline, idempotent Phase 1 migration of the approved dated review artifacts."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from shared.database import apply_initial_schema, connect, transaction, upsert_product
from shared.matching import build_record_id, canonical_platform, legacy_review_key, normalize_url, platform_from_url


ROOT = Path(__file__).resolve().parents[1]
SUMMARY_PATH = ROOT / "runs" / "2026-07-23-biweekly-review-analysis" / "review_summary.json"
REVIEWS_PATH = ROOT / "runs" / "2026-07-23-biweekly-review-analysis" / "low_star_reviews.json"
SCHEMA_PATH = ROOT / "database" / "schema.sql"
RESULT_PATH = ROOT / "data" / "processed" / "phase1_migration_results.json"
DRAFT_PATH = ROOT / "data" / "processed" / "phase1_listing_master_draft.json"


def load_json(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def run_id_for(platform: str) -> str:
    return f"legacy-20260723-review-summary-{platform.lower()}"


def source_relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def draft_row(item: dict, row_number: int) -> dict:
    platform = canonical_platform(item.get("platform", ""))
    url = normalize_url(item.get("url", ""))
    inferred = platform_from_url(url)
    missing = []
    if not item.get("sku"):
        missing.append("internal_sku")
    if not url:
        missing.append("listing_url")
    if not item.get("productId"):
        missing.append("platform_item_id")
    if inferred and inferred != platform:
        status = "PLATFORM_URL_MISMATCH"
    elif missing:
        status = "MISSING_REQUIRED_FIELD"
    elif not platform or not item.get("sku"):
        status = "IDENTITY_UNCERTAIN"
    else:
        status = "READY_FOR_USER_REVIEW"
    record_id = build_record_id(platform, item.get("sku", "")) if platform and item.get("sku") else f"LEGACY_LISTING_{legacy_review_key(platform, item.get('productId'), url)[:16].upper()}"
    return {
        "record_id": record_id,
        "active": "FALSE",
        "platform": platform,
        "brand": item.get("brand") or "",
        "product_line": item.get("category") or "",
        "internal_sku": item.get("sku") or "",
        "model": "",
        "platform_item_id": str(item.get("productId") or ""),
        "product_name": item.get("productName") or "",
        "listing_url": url,
        "primary_keyword": "",
        "secondary_keyword": "",
        "third_keyword": "",
        "zip_code": "",
        "expected_seller": "",
        "monitor_listing": "FALSE",
        "monitor_rank": "FALSE",
        "monitor_review": "FALSE",
        "max_search_pages": "",
        "source_file": source_relative(SUMMARY_PATH),
        "source_row": row_number,
        "migration_status": status,
        "missing_required_fields": ", ".join(missing),
        "notes": "Historical review-summary source; monitoring remains disabled pending user review.",
    }


def migrate(database_path: Path) -> dict:
    summaries = load_json(SUMMARY_PATH)
    reviews = load_json(REVIEWS_PATH)
    drafts = [draft_row(item, index) for index, item in enumerate(summaries, start=1)]
    record_ids = [row["record_id"] for row in drafts]
    duplicate_candidates = len(record_ids) - len(set(record_ids))
    results = {
        "source_listing_records": len(summaries), "listing_migrated": 0, "listing_skipped": 0,
        "listing_existing": 0,
        "listing_duplicate_candidates": duplicate_candidates, "source_review_records": len(reviews),
        "review_migrated": 0, "review_existing": 0, "review_duplicates": 0, "review_unmatched": 0, "review_missing_fields": 0,
        "review_failed": 0, "platform_url_mismatch": sum(row["migration_status"] == "PLATFORM_URL_MISMATCH" for row in drafts),
        "needs_user_review": sum(row["migration_status"] != "READY_FOR_USER_REVIEW" for row in drafts),
        "schema_checksum": "", "schema_tables": [], "run_ids": [],
    }
    DRAFT_PATH.parent.mkdir(parents=True, exist_ok=True)
    DRAFT_PATH.write_text(json.dumps(drafts, ensure_ascii=False, indent=2), encoding="utf-8")
    connection = connect(database_path)
    try:
        with transaction(connection):
            results["schema_checksum"] = apply_initial_schema(connection, SCHEMA_PATH)
            for platform in sorted({row["platform"] for row in drafts}):
                run_id = run_id_for(platform)
                connection.execute(
                    "INSERT INTO collection_runs (run_id,module_name,platform,run_mode,started_at,completed_at,status,capture_status,source_system) VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(run_id) DO UPDATE SET completed_at=excluded.completed_at,status=excluded.status,capture_status=excluded.capture_status",
                    (run_id, "review_tracker", platform, "migration", "2026-07-23T00:00:00+00:00", "2026-07-23T00:00:00+00:00", "SUCCEEDED", "CAPTURED", "legacy_json"),
                )
                results["run_ids"].append(run_id)
            for item, draft in zip(summaries, drafts):
                existing_product = connection.execute("SELECT 1 FROM products WHERE record_id=?", (draft["record_id"],)).fetchone()
                if existing_product:
                    results["listing_existing"] += 1
                else:
                    results["listing_migrated"] += 1
                upsert_product(connection, {
                    "record_id": draft["record_id"], "active": 0, "platform": draft["platform"], "brand": draft["brand"] or None,
                    "product_line": draft["product_line"] or None, "internal_sku": draft["internal_sku"], "model": None,
                    "platform_item_id": draft["platform_item_id"] or None, "product_name": draft["product_name"] or None,
                    "listing_url": draft["listing_url"], "primary_keyword": None, "secondary_keyword": None, "third_keyword": None,
                    "zip_code": None, "expected_seller": None, "monitor_listing": 0, "monitor_rank": 0, "monitor_review": 0,
                    "max_search_pages": None, "notes": draft["notes"], "source_path": draft["source_file"],
                    "source_row_number": draft["source_row"], "source_hash": None, "identity_status": "NEEDS_USER_CONFIRMATION" if draft["migration_status"] != "READY_FOR_USER_REVIEW" else "CONFIRMED_FROM_SOURCE",
                    "legacy_source": "review_summary.json", "migrated_at": datetime.now(timezone.utc).isoformat(),
                })
                connection.execute(
                    "INSERT INTO review_snapshots (run_id,record_id,observed_at,source_system,capture_status,average_rating,total_review_count,rating_1_count,rating_2_count,rating_3_count,rating_4_count,rating_5_count,readable_review_count,raw_evidence_path) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(run_id,record_id) DO UPDATE SET average_rating=excluded.average_rating,total_review_count=excluded.total_review_count,rating_1_count=excluded.rating_1_count,rating_2_count=excluded.rating_2_count,rating_3_count=excluded.rating_3_count,rating_4_count=excluded.rating_4_count,rating_5_count=excluded.rating_5_count,readable_review_count=excluded.readable_review_count",
                    (run_id_for(draft["platform"]), draft["record_id"], item.get("lastReview") or "2026-07-23T00:00:00+00:00", "legacy_review_summary_json", "CAPTURED", item.get("avgRating"), item.get("totalReviews"), item.get("rating1"), item.get("rating2"), item.get("rating3"), item.get("rating4"), item.get("rating5"), item.get("textNegativeReviews"), draft["source_file"]),
                )
            by_platform_sku = {(row["platform"], row["internal_sku"]): row for row in drafts}
            seen_keys: set[tuple[str, str]] = set()
            for row_number, item in enumerate(reviews, start=1):
                platform = canonical_platform(item.get("platform", ""))
                draft = by_platform_sku.get((platform, item.get("sku") or ""))
                if not draft:
                    results["review_unmatched"] += 1
                    continue
                missing = [name for name in ("rating", "date") if item.get(name) in (None, "")]
                if missing:
                    results["review_missing_fields"] += 1
                key = legacy_review_key(platform, item.get("productId"), normalize_url(item.get("url", "")), item.get("date"), item.get("rating"), item.get("title"), item.get("text"), item.get("reviewer_name", ""))
                pair = (draft["record_id"], key)
                if pair in seen_keys:
                    results["review_duplicates"] += 1
                    continue
                seen_keys.add(pair)
                exists = connection.execute("SELECT 1 FROM reviews WHERE record_id=? AND legacy_review_key=?", pair).fetchone()
                if exists:
                    results["review_existing"] += 1
                    continue
                connection.execute(
                    "INSERT INTO reviews (record_id,first_seen_run_id,last_seen_run_id,source_system,source_review_id,platform_review_id,review_id_source,legacy_review_key,identity_confidence,rating,review_date,title,review_text,verified_purchase,syndicated,raw_evidence_path,source_file,source_row,migrated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (draft["record_id"], run_id_for(platform), run_id_for(platform), "legacy_low_star_reviews_json", key, None, "LEGACY_CONTENT_HASH", key, "LEGACY_HASH", item.get("rating"), item.get("date"), item.get("title"), item.get("text"), int(bool(item.get("verified"))) if item.get("verified") is not None else None, int(bool(item.get("syndicated"))) if item.get("syndicated") is not None else None, source_relative(REVIEWS_PATH), source_relative(REVIEWS_PATH), row_number, datetime.now(timezone.utc).isoformat()),
                )
                results["review_migrated"] += 1
            tables = connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
            results["schema_tables"] = [row[0] for row in tables]
        RESULT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        return results
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the offline Phase 1 migration after an approved backup.")
    parser.add_argument("--database", type=Path, default=ROOT / "database" / "tracker.db")
    parser.add_argument("--approve", action="store_true", help="Required acknowledgement that the Phase 1 backup is verified.")
    args = parser.parse_args()
    if not args.approve:
        raise SystemExit("Refusing migration without --approve.")
    print(json.dumps(migrate(args.database), ensure_ascii=False))


if __name__ == "__main__":
    main()
