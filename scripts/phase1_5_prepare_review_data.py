"""Build offline Phase 1.5 review data without mutating master inputs or SQLite business rows."""

from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

from shared.matching import canonical_platform, platform_from_url


ROOT = Path(__file__).resolve().parents[1]
DRAFT_JSON = ROOT / "data" / "processed" / "phase1_listing_master_draft.json"
DRAFT_XLSX = ROOT / "config" / "listing_master_migration_draft.xlsx"
DATABASE = ROOT / "database" / "tracker.db"
OUT_JSON = ROOT / "data" / "processed" / "phase1_5_review_package.json"
ISSUES_CSV = ROOT / "reports" / "phase1_5_master_data_issues.csv"
SOURCE_HASHES = ROOT / "data" / "processed" / "phase1_5_input_hashes.json"
SKILL_ZIP = Path(r"C:\Users\admin\AppData\Local\Temp\skill-export-collect-retail-public-pages-1785307505188.zip")
SKILL_DIR = ROOT / "legacy" / "skills" / "collect-retail-public-pages"
SKILL_HASHES = ROOT / "reports" / "phase1_5_skill_file_hashes.csv"
EXPECTED_ZIP_SHA256 = "A55EFB88DCD74E2E6BEEF1D25B011E8A715C025184F9E7361C749D5368748BA8"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def valid_zip(value: str) -> bool:
    return len(value) == 5 and value.isdigit()


def field_present(value: object) -> bool:
    return value not in (None, "")


def completeness(row: dict, review_associated: bool, platform_match: str) -> tuple[int, str]:
    weights = {
        "record_id": 10, "platform": 10, "internal_sku": 10, "model": 10,
        "platform_item_id": 10, "product_name": 5, "listing_url": 10,
        "primary_keyword": 10, "zip_code": 5, "monitor_fields": 5,
        "review_association": 5, "platform_url_match": 10,
    }
    score = 0
    for field in ("record_id", "platform", "internal_sku", "model", "platform_item_id", "product_name", "listing_url", "primary_keyword"):
        score += weights[field] if field_present(row.get(field)) else 0
    score += weights["zip_code"] if valid_zip(str(row.get("zip_code") or "")) else 0
    monitor_values = [row.get(name) for name in ("active", "monitor_listing", "monitor_rank", "monitor_review")]
    score += weights["monitor_fields"] if all(value in ("TRUE", "FALSE") for value in monitor_values) else 0
    score += weights["review_association"] if review_associated else 0
    score += weights["platform_url_match"] if platform_match == "MATCH" else 0
    if not row.get("record_id") or not row.get("listing_url") or not row.get("internal_sku"):
        return score, "CRITICAL_IDENTITY_ISSUE"
    if score >= 90:
        return score, "READY_FOR_REVIEW"
    if score >= 70:
        return score, "PARTIAL_DATA"
    return score, "INCOMPLETE"


def add_issue(issues: list[dict], record: dict, severity: str, field: str, issue_type: str, current: str, action: str, blocks: bool, notes: str) -> None:
    issues.append({
        "issue_id": f"ISS-{len(issues) + 1:03d}", "severity": severity,
        "record_id": record["record_id"], "platform": record["platform"], "field": field,
        "issue_type": issue_type, "current_value": current or "[blank]",
        "recommended_action": action, "blocking_phase2": "TRUE" if blocks else "FALSE", "notes": notes,
    })


def build_package() -> dict:
    source_rows = json.loads(DRAFT_JSON.read_text(encoding="utf-8"))
    read_only_uri = f"file:{DATABASE.resolve().as_posix()}?mode=ro"
    connection = sqlite3.connect(read_only_uri, uri=True)
    review_counts = {record_id: count for record_id, count in connection.execute("SELECT record_id, COUNT(*) FROM reviews GROUP BY record_id")}
    snapshot_counts = {record_id: count for record_id, count in connection.execute("SELECT record_id, COUNT(*) FROM review_snapshots GROUP BY record_id")}
    product_sources = {record_id: source for record_id, source in connection.execute("SELECT record_id, legacy_source FROM products")}
    connection.close()

    record_counts = Counter(row["record_id"] for row in source_rows)
    url_counts = Counter(row.get("listing_url") for row in source_rows if row.get("listing_url"))
    platform_item_counts = Counter((canonical_platform(row.get("platform", "")), row.get("platform_item_id")) for row in source_rows if row.get("platform_item_id"))
    issues: list[dict] = []
    master: list[dict] = []
    for row in source_rows:
        platform = canonical_platform(row.get("platform", ""))
        detected = platform_from_url(row.get("listing_url", "")) or "UNKNOWN"
        match = "MATCH" if detected == platform else "MISMATCH"
        review_count = review_counts.get(row["record_id"], 0)
        review_associated = snapshot_counts.get(row["record_id"], 0) > 0
        score, state = completeness({**row, "platform": platform}, review_associated, match)
        duplicate = record_counts[row["record_id"]] > 1 or url_counts.get(row.get("listing_url"), 0) > 1 or platform_item_counts.get((platform, row.get("platform_item_id")), 0) > 1
        record = {
            "review_status": "NOT_REVIEWED", "user_decision": "", "record_id": row["record_id"],
            "active": row.get("active", "FALSE"), "platform": platform, "url_detected_platform": detected,
            "platform_match_status": match, "brand": row.get("brand", ""), "product_line": row.get("product_line", ""),
            "internal_sku": row.get("internal_sku", ""), "model": row.get("model", ""),
            "platform_item_id": row.get("platform_item_id", ""), "product_name": row.get("product_name", ""),
            "listing_url": row.get("listing_url", ""), "link_display": "Open Listing", "primary_keyword": row.get("primary_keyword", ""),
            "secondary_keyword": row.get("secondary_keyword", ""), "third_keyword": row.get("third_keyword", ""), "zip_code": row.get("zip_code", ""),
            "expected_seller": row.get("expected_seller", ""), "monitor_listing": row.get("monitor_listing", "FALSE"),
            "monitor_rank": row.get("monitor_rank", "FALSE"), "monitor_review": row.get("monitor_review", "FALSE"),
            "max_search_pages": row.get("max_search_pages", ""), "review_count_in_database": review_count,
            "legacy_listing_data_present": "TRUE" if product_sources.get(row["record_id"]) else "FALSE", "data_completeness_score": score,
            "data_completeness_status": state, "missing_required_fields": row.get("missing_required_fields", ""),
            "duplicate_candidate": "TRUE" if duplicate else "FALSE", "identity_warning": "" if match == "MATCH" else "PLATFORM_URL_MISMATCH",
            "source_file": row.get("source_file", ""), "source_row": row.get("source_row", ""), "user_notes": "", "codex_notes": "Offline review only; no Listing URL was opened or verified.",
        }
        master.append(record)
        if not record["listing_url"]:
            add_issue(issues, record, "CRITICAL", "listing_url", "MISSING_LISTING_URL", "", "Provide an existing verified source URL; do not guess.", True, "Required identity anchor is missing.")
        if not record["internal_sku"]:
            add_issue(issues, record, "CRITICAL", "internal_sku", "MISSING_INTERNAL_SKU", "", "Confirm the internal SKU from source records.", True, "Do not fabricate an SKU.")
        if not record["platform_item_id"]:
            add_issue(issues, record, "HIGH", "platform_item_id", "MISSING_PLATFORM_ITEM_ID", "", "Confirm from retained source; do not infer from product name.", True, "Item identity is incomplete.")
        if not record["product_name"]:
            add_issue(issues, record, "MEDIUM", "product_name", "IDENTITY_UNCERTAIN", "", "Confirm the product name from retained source or manual page review; do not infer it.", False, "Historical source contains no product name.")
        if match != "MATCH":
            add_issue(issues, record, "HIGH", "listing_url", "PLATFORM_URL_MISMATCH", record["listing_url"], "Confirm platform or source URL manually.", True, "Detected from URL hostname only.")
        if record_counts[record["record_id"]] > 1:
            add_issue(issues, record, "HIGH", "record_id", "DUPLICATE_RECORD_ID", record["record_id"], "Resolve duplicate identity before approval.", True, "Offline duplicate check.")
        if url_counts.get(record["listing_url"], 0) > 1:
            add_issue(issues, record, "HIGH", "listing_url", "DUPLICATE_LISTING_URL", record["listing_url"], "Resolve duplicate Listing URL before approval.", True, "Offline duplicate check.")
        if platform_item_counts.get((platform, record["platform_item_id"]), 0) > 1:
            add_issue(issues, record, "HIGH", "platform_item_id", "DUPLICATE_PLATFORM_ITEM_ID", record["platform_item_id"], "Resolve duplicate platform item ID before approval.", True, "Offline duplicate check.")
        if not record["model"]:
            add_issue(issues, record, "MEDIUM", "model", "MISSING_MODEL", "", "User to confirm product model before Phase 2 selection.", False, "No model was inferred from product name.")
        if not record["primary_keyword"]:
            add_issue(issues, record, "HIGH", "primary_keyword", "MISSING_PRIMARY_KEYWORD", "", "User to provide the intended primary keyword; do not infer it.", False, "Blocks rank-monitor scope approval only.")
        if not valid_zip(record["zip_code"]):
            add_issue(issues, record, "MEDIUM", "zip_code", "INVALID_ZIP_CODE", record["zip_code"], "User to provide a five-digit US ZIP if rank monitoring is requested.", False, "ZIP is required only for applicable location-sensitive rank scope.")
        if not review_associated:
            add_issue(issues, record, "HIGH", "review_count_in_database", "REVIEW_ASSOCIATION_MISSING", "0", "Review Listing-to-history mapping before approval.", False, "No historical Review association found.")

    summaries = []
    for platform in ("WALMART", "THD", "LOWES", "UNKNOWN"):
        rows = [row for row in master if row["platform"] == platform]
        summaries.append({
            "platform": platform, "listing_total": len(rows), "missing_url": sum(not row["listing_url"] for row in rows),
            "missing_item_id": sum(not row["platform_item_id"] for row in rows), "review_history_listings": sum(snapshot_counts.get(row["record_id"], 0) > 0 for row in rows),
            "missing_primary_keyword": sum(not row["primary_keyword"] for row in rows), "platform_url_mismatch": sum(row["platform_match_status"] != "MATCH" for row in rows),
            "duplicate_candidates": sum(row["duplicate_candidate"] == "TRUE" for row in rows), "ready_for_review": sum(row["data_completeness_status"] == "READY_FOR_REVIEW" for row in rows),
            "partial_data": sum(row["data_completeness_status"] == "PARTIAL_DATA" for row in rows), "incomplete": sum(row["data_completeness_status"] in ("INCOMPLETE", "CRITICAL_IDENTITY_ISSUE") for row in rows),
        })
    candidates = defaultdict(list)
    for row in sorted(master, key=lambda item: (-item["data_completeness_score"], item["record_id"])):
        eligible = row["platform_match_status"] == "MATCH" and bool(row["internal_sku"]) and bool(row["platform_item_id"]) and bool(row["model"]) and bool(row["primary_keyword"]) and row["duplicate_candidate"] == "FALSE"
        if eligible and len(candidates[row["platform"]]) < 3:
            candidates[row["platform"]].append({"record_id": row["record_id"], "score": row["data_completeness_score"], "reason": "CANDIDATE_ONLY_NOT_APPROVED"})
    package = {"master": master, "issues": issues, "platform_summary": summaries, "candidates": dict(candidates), "score_weights": {"record_id": 10, "platform": 10, "internal_sku": 10, "model": 10, "platform_item_id": 10, "product_name": 5, "listing_url": 10, "primary_keyword": 10, "zip_code": 5, "monitor_fields": 5, "review_association": 5, "platform_url_match": 10}}
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
    with ISSUES_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["issue_id", "severity", "record_id", "platform", "field", "issue_type", "current_value", "recommended_action", "blocking_phase2", "notes"])
        writer.writeheader(); writer.writerows(issues)
    hashes = {"listing_master_migration_draft.xlsx": sha256(DRAFT_XLSX), "tracker.db": sha256(DATABASE), "listing_master.xlsx": sha256(ROOT / "config" / "listing_master.xlsx")}
    SOURCE_HASHES.write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    return package


def audit_skill() -> dict:
    rows = []
    for path in sorted(SKILL_DIR.rglob("*")):
        if path.is_file():
            rows.append({"relative_path": path.relative_to(SKILL_DIR).as_posix(), "file_size": path.stat().st_size, "sha256": sha256(path)})
    with SKILL_HASHES.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["relative_path", "file_size", "sha256"]); writer.writeheader(); writer.writerows(rows)
    actual = sha256(SKILL_ZIP)
    return {"zip_path": str(SKILL_ZIP), "zip_sha256": actual, "expected_sha256": EXPECTED_ZIP_SHA256, "zip_match": actual == EXPECTED_ZIP_SHA256, "file_count": len(rows), "content_verdict": "UNKNOWN_NO_REFERENCE_MANIFEST"}


if __name__ == "__main__":
    result = {"package": build_package(), "skill": audit_skill()}
    print(json.dumps({"records": len(result["package"]["master"]), "issues": len(result["package"]["issues"]), "skill": result["skill"]}, ensure_ascii=False))
