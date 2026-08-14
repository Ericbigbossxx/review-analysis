"""Build a scope-aware comparison against the previous successful weekly run."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _platform(value: Any) -> str:
    normalized = str(value or "").strip().upper().replace("'", "")
    return {"HOMEDEPOT": "THD", "HOME DEPOT": "THD", "THD": "THD", "LOWES": "LOWES", "WALMART": "WALMART"}.get(normalized, normalized)


def _natural_key(row: dict[str, Any]) -> tuple[str, str]:
    return _platform(row.get("platform_code") or row.get("platform")), str(row.get("internal_sku") or row.get("sku") or "").strip()


def _record_id(row: dict[str, Any], scope_map: dict[tuple[str, str], str] | None = None) -> str:
    explicit = str(row.get("record_id") or "").strip()
    if explicit:
        return explicit
    key = _natural_key(row)
    return (scope_map or {}).get(key) or f"{key[0]}_{key[1]}"


def _available(row: dict[str, Any]) -> bool:
    return row.get("dataAvailable", True) is not False and row.get("totalReviews") is not None


def _low(row: dict[str, Any]) -> int:
    return sum(int(row.get(f"rating{star}") or 0) for star in (1, 2, 3))


def _date_after(value: Any, boundary: str) -> bool:
    if not value:
        return False
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        for fmt in ("%m/%d/%Y", "%b %d, %Y", "%B %d, %Y"):
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        else:
            return False
    return parsed.date().isoformat() > boundary


def _status_map(scope_diff: dict[str, Any] | None) -> dict[str, str]:
    result: dict[str, str] = {}
    if not scope_diff:
        return result
    categories = scope_diff.get("categories") or {}
    for status, rows in categories.items():
        for row in rows:
            result[str(row["record_id"])] = str(status)
    return result


def _scope_map(scope: list[dict[str, Any]] | None) -> dict[tuple[str, str], str]:
    return {_natural_key(row): str(row.get("record_id") or f"{_natural_key(row)[0]}_{_natural_key(row)[1]}") for row in (scope or [])}


def _aggregate(items: list[dict[str, Any]], recent: int) -> dict[str, Any]:
    available = [item for item in items if item["currentTotalReviews"] is not None]
    comparable = [item for item in items if item["comparable"]]
    current_total = sum(int(item["currentTotalReviews"]) for item in available)
    current_low = sum(int(item["currentLowStarReviews"]) for item in available)
    comparable_current_total = sum(int(item["currentTotalReviews"]) for item in comparable)
    comparable_current_low = sum(int(item["currentLowStarReviews"]) for item in comparable)
    prior_total = sum(int(item["priorTotalReviews"]) for item in comparable)
    prior_low = sum(int(item["priorLowStarReviews"]) for item in comparable)
    comparable_current_rate = comparable_current_low / comparable_current_total if comparable_current_total else None
    prior_rate = prior_low / prior_total if prior_total else None
    return {
        "currentScopeListings": len(items),
        "currentAvailableListings": len(available),
        "comparableListings": len(comparable),
        "newToScope": sum(1 for item in items if item["scopeStatus"] == "NEW_TO_SCOPE"),
        "linkChanged": sum(1 for item in items if item["scopeStatus"] == "LINK_CHANGED"),
        "currentUnavailable": sum(1 for item in items if item["status"] == "CURRENT_UNAVAILABLE"),
        "currentTotalReviews": current_total,
        "currentLowStarReviews": current_low,
        "currentLowStarRate": current_low / current_total if current_total else None,
        "comparableCurrentTotalReviews": comparable_current_total,
        "comparableCurrentLowStarReviews": comparable_current_low,
        "comparableCurrentLowStarRate": comparable_current_rate,
        "priorTotalReviews": prior_total if comparable else None,
        "priorLowStarReviews": prior_low if comparable else None,
        "priorLowStarRate": prior_rate,
        "totalReviewDelta": comparable_current_total - prior_total if comparable else None,
        "lowStarDelta": comparable_current_low - prior_low if comparable else None,
        "lowStarRateDelta": comparable_current_rate - prior_rate if comparable_current_rate is not None and prior_rate is not None else None,
        "newReadableLowStarReviews": recent,
    }


def build_comparison(
    current: list[dict[str, Any]],
    prior: list[dict[str, Any]],
    current_reviews: list[dict[str, Any]],
    prior_date: str,
    current_date: str,
    current_scope: list[dict[str, Any]] | None = None,
    prior_scope: list[dict[str, Any]] | None = None,
    scope_diff: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current_scope_map = _scope_map(current_scope)
    prior_scope_map = _scope_map(prior_scope)
    status_by_id = _status_map(scope_diff)
    active_ids = set(current_scope_map.values()) if current_scope else {_record_id(row) for row in current}
    prior_map = {_record_id(row, prior_scope_map): row for row in prior}
    sku_rows: list[dict[str, Any]] = []
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in current:
        record_id = _record_id(row, current_scope_map)
        if record_id not in active_ids:
            continue
        previous = prior_map.get(record_id)
        scope_status = status_by_id.get(record_id, "CONTINUING" if previous is not None else "NEW_TO_SCOPE")
        current_available = _available(row)
        comparable = (
            current_available
            and previous is not None
            and _available(previous)
            and scope_status in {"CONTINUING", "LINK_CHANGED"}
        )
        current_total = int(row["totalReviews"]) if current_available else None
        prior_total = int(previous["totalReviews"]) if comparable else None
        current_low = _low(row) if current_available else None
        prior_low = _low(previous) if comparable and previous else None
        if not current_available:
            display_status = "CURRENT_UNAVAILABLE"
        elif scope_status == "NEW_TO_SCOPE":
            display_status = "NEW_TO_SCOPE"
        elif scope_status == "LINK_CHANGED":
            display_status = "LINK_CHANGED"
        elif scope_status == "RECORD_IDENTITY_CHANGED":
            display_status = "RECORD_IDENTITY_CHANGED"
        elif comparable:
            display_status = "COMPARABLE"
        else:
            display_status = "NO_PRIOR"
        item = {
            "record_id": record_id,
            "platform": _platform(row.get("platform")),
            "sku": str(row.get("sku") or row.get("internal_sku") or ""),
            "status": display_status,
            "scopeStatus": scope_status,
            "comparable": comparable,
            "currentTotalReviews": current_total,
            "priorTotalReviews": prior_total,
            "totalReviewDelta": current_total - prior_total if comparable else None,
            "currentLowStarReviews": current_low,
            "priorLowStarReviews": prior_low,
            "lowStarDelta": current_low - prior_low if comparable else None,
            "currentLowStarRate": current_low / current_total if current_available and current_total else None,
            "priorLowStarRate": prior_low / prior_total if comparable and prior_total else None,
        }
        item["lowStarRateDelta"] = (
            item["currentLowStarRate"] - item["priorLowStarRate"]
            if comparable and item["currentLowStarRate"] is not None and item["priorLowStarRate"] is not None
            else None
        )
        sku_rows.append(item)
        grouped[item["platform"]].append(item)

    recent_counts: dict[str, int] = defaultdict(int)
    for review in current_reviews:
        review_id = _record_id(review, current_scope_map)
        readable = bool(str(review.get("title") or "").strip() or str(review.get("text") or "").strip())
        rating = int(review.get("rating") or 0)
        if review_id in active_ids and readable and rating in (1, 2, 3) and _date_after(review.get("date"), prior_date):
            recent_counts[_platform(review.get("platform"))] += 1

    platform_rows = []
    for platform in sorted(grouped):
        platform_rows.append({"platform": platform, **_aggregate(grouped[platform], recent_counts.get(platform, 0))})
    totals = _aggregate(sku_rows, sum(recent_counts.values()))
    categories = (scope_diff or {}).get("categories") or {}
    return {
        "currentReportDate": current_date,
        "priorReportDate": prior_date,
        "comparisonScope": "CURRENT_ACTIVE_SCOPE_WITH_LIKE_FOR_LIKE_DELTAS",
        "platforms": platform_rows,
        "totals": totals,
        "skus": sku_rows,
        "scopeChangeAudit": {
            "newToScope": categories.get("NEW_TO_SCOPE", []),
            "removedFromScope": categories.get("REMOVED_FROM_SCOPE", []),
            "linkChanged": categories.get("LINK_CHANGED", []),
            "recordIdentityChanged": categories.get("RECORD_IDENTITY_CHANGED", []),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--current-summary", type=Path, required=True)
    parser.add_argument("--prior-summary", type=Path, required=True)
    parser.add_argument("--current-reviews", type=Path, required=True)
    parser.add_argument("--current-date", required=True)
    parser.add_argument("--prior-date", required=True)
    parser.add_argument("--current-scope", type=Path)
    parser.add_argument("--prior-scope", type=Path)
    parser.add_argument("--scope-diff", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_comparison(
        _read(args.current_summary),
        _read(args.prior_summary),
        _read(args.current_reviews),
        args.prior_date,
        args.current_date,
        _read(args.current_scope) if args.current_scope else None,
        _read(args.prior_scope) if args.prior_scope else None,
        _read(args.scope_diff) if args.scope_diff else None,
    )
    _write(args.output, result)
    print(json.dumps(result["totals"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
