"""Dynamic, immutable Review Tracker scope management.

The Listing Master is the long-lived authority.  Every run receives a frozen
JSON projection so a later workbook edit cannot change the meaning of an
already-started run.
"""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse
from xml.etree import ElementTree as ET


ALLOWED_PLATFORMS = {"THD", "LOWES", "WALMART"}
PLATFORM_LABELS = {"THD": "Homedepot", "LOWES": "Lowes", "WALMART": "Walmart"}
IDENTITY_FIELDS = ("platform_code", "internal_sku", "model")
SUCCESS_STATES = {"SUCCESS", "SUCCESS_WITH_PLATFORM_LIMITATION"}
_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _scope_hash(rows: Iterable[dict[str, Any]]) -> str:
    canonical = [canonical_scope_row(row) for row in rows]
    canonical.sort(key=lambda row: row["record_id"])
    return hashlib.sha256(_json_bytes(canonical)).hexdigest()


def normalize_platform(value: Any) -> str:
    normalized = str(value or "").strip().upper().replace("'", "")
    return {
        "HOMEDEPOT": "THD",
        "HOME DEPOT": "THD",
        "THD": "THD",
        "LOWES": "LOWES",
        "WALMART": "WALMART",
    }.get(normalized, normalized)


def parse_bool(value: Any, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    normalized = str(value or "").strip().upper()
    if normalized in {"TRUE", "1", "YES", "Y"}:
        return True
    if normalized in {"FALSE", "0", "NO", "N"}:
        return False
    raise ValueError(f"{field} must be TRUE or FALSE; got {value!r}")


def _column_index(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference.upper())
    if not letters:
        raise ValueError(f"invalid XLSX cell reference: {reference}")
    index = 0
    for letter in letters.group(0):
        index = index * 26 + ord(letter) - ord("A") + 1
    return index - 1


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return ["".join(node.text or "" for node in item.iter(f"{{{_MAIN_NS}}}t")) for item in root]


def _sheet_target(archive: zipfile.ZipFile, sheet_name: str) -> str:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationship_id = None
    for sheet in workbook.iter(f"{{{_MAIN_NS}}}sheet"):
        if sheet.attrib.get("name") == sheet_name:
            relationship_id = sheet.attrib.get(f"{{{_DOC_REL_NS}}}id")
            break
    if not relationship_id:
        raise ValueError(f"worksheet {sheet_name!r} was not found")
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    for relation in relationships.iter(f"{{{_PKG_REL_NS}}}Relationship"):
        if relation.attrib.get("Id") == relationship_id:
            target = relation.attrib["Target"].replace("\\", "/").lstrip("/")
            return target if target.startswith("xl/") else f"xl/{target}"
    raise ValueError(f"worksheet relationship {relationship_id!r} was not found")


def _cell_value(cell: ET.Element, shared: list[str]) -> Any:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.iter(f"{{{_MAIN_NS}}}t"))
    value_node = cell.find(f"{{{_MAIN_NS}}}v")
    if value_node is None:
        return None
    value = value_node.text or ""
    if cell_type == "s":
        return shared[int(value)]
    if cell_type == "b":
        return value == "1"
    if cell_type in {"str", "e"}:
        return value
    try:
        number = float(value)
        return int(number) if number.is_integer() else number
    except ValueError:
        return value


def read_listing_master(path: Path, sheet_name: str = "Listing Master") -> list[dict[str, Any]]:
    """Read a simple XLSX table with only Python's standard library."""

    with zipfile.ZipFile(path) as archive:
        shared = _shared_strings(archive)
        root = ET.fromstring(archive.read(_sheet_target(archive, sheet_name)))
    matrix: list[list[Any]] = []
    for row in root.iter(f"{{{_MAIN_NS}}}row"):
        values: dict[int, Any] = {}
        for cell in row.findall(f"{{{_MAIN_NS}}}c"):
            values[_column_index(cell.attrib["r"])] = _cell_value(cell, shared)
        if values:
            width = max(values) + 1
            matrix.append([values.get(index) for index in range(width)])
    header_index = next(
        (index for index, row in enumerate(matrix) if "record_id" in {str(value or "").strip() for value in row}),
        None,
    )
    if header_index is None:
        raise ValueError("Listing Master header row containing record_id was not found")
    headers = [str(value or "").strip() for value in matrix[header_index]]
    rows: list[dict[str, Any]] = []
    for values in matrix[header_index + 1 :]:
        if not any(str(value or "").strip() for value in values):
            continue
        rows.append({header: values[index] if index < len(values) else None for index, header in enumerate(headers) if header})
    return rows


def _validate_url(platform: str, value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"invalid listing_url for {platform}: {value!r}")
    host = parsed.netloc.lower()
    expected = {"THD": "homedepot.com", "LOWES": "lowes.com", "WALMART": "walmart.com"}[platform]
    if expected not in host:
        raise ValueError(f"listing_url host {host!r} does not match platform {platform}")


def validate_listing_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    active_scope: list[dict[str, Any]] = []
    all_record_ids: set[str] = set()
    active_keys: set[tuple[str, str]] = set()
    for row_number, row in enumerate(rows, start=2):
        record_id = str(row.get("record_id") or "").strip()
        if not record_id:
            raise ValueError(f"row {row_number}: record_id is required")
        if record_id in all_record_ids:
            raise ValueError(f"row {row_number}: duplicate record_id {record_id}")
        all_record_ids.add(record_id)
        platform = normalize_platform(row.get("platform"))
        if platform not in ALLOWED_PLATFORMS:
            raise ValueError(f"row {row_number}: unsupported platform {row.get('platform')!r}")
        active = parse_bool(row.get("active"), f"row {row_number} active")
        monitor_review = parse_bool(row.get("monitor_review"), f"row {row_number} monitor_review")
        for flag in ("monitor_listing", "monitor_rank"):
            parse_bool(row.get(flag), f"row {row_number} {flag}")
        if not monitor_review:
            continue
        if not active:
            raise ValueError(f"row {row_number}: monitor_review=TRUE requires active=TRUE")
        internal_sku = str(row.get("internal_sku") or "").strip()
        listing_url = str(row.get("listing_url") or "").strip()
        if not internal_sku:
            raise ValueError(f"row {row_number}: internal_sku is required for Review scope")
        if not listing_url:
            raise ValueError(f"row {row_number}: listing_url is required for Review scope")
        _validate_url(platform, listing_url)
        expected_prefix = f"{platform}_"
        if not record_id.startswith(expected_prefix):
            raise ValueError(f"row {row_number}: record_id {record_id!r} does not match platform {platform}")
        key = (platform, internal_sku)
        if key in active_keys:
            raise ValueError(f"row {row_number}: duplicate active platform/SKU {key}")
        active_keys.add(key)
        normalized = dict(row)
        normalized.update(
            {
                "record_id": record_id,
                "platform_code": platform,
                "platform": PLATFORM_LABELS[platform],
                "internal_sku": internal_sku,
                "sku": internal_sku,
                "listing_url": listing_url,
                "url": listing_url,
                "model": str(row.get("model") or "").strip(),
                "brand": str(row.get("brand") or "").strip(),
                "product_line": str(row.get("product_line") or "").strip(),
                "category": str(row.get("product_line") or "").strip(),
                "product_name": str(row.get("product_name") or "").strip(),
                "platform_item_id": str(row.get("platform_item_id") or "").strip(),
            }
        )
        active_scope.append(normalized)
    if not active_scope:
        raise ValueError("Review active scope is empty; monitor_review=TRUE is required")
    return sorted(active_scope, key=lambda row: row["record_id"])


def load_review_scope(path: Path) -> list[dict[str, Any]]:
    return validate_listing_rows(read_listing_master(path))


def canonical_scope_row(row: dict[str, Any]) -> dict[str, Any]:
    platform = normalize_platform(row.get("platform_code") or row.get("platform"))
    sku = str(row.get("internal_sku") or row.get("sku") or "").strip()
    record_id = str(row.get("record_id") or "").strip() or f"{platform}_{sku}"
    return {
        "record_id": record_id,
        "platform_code": platform,
        "internal_sku": sku,
        "model": str(row.get("model") or "").strip(),
        "listing_url": str(row.get("listing_url") or row.get("url") or "").strip(),
        "platform_item_id": str(row.get("platform_item_id") or row.get("productId") or "").strip(),
        "brand": str(row.get("brand") or "").strip(),
        "product_line": str(row.get("product_line") or row.get("category") or "").strip(),
        "product_name": str(row.get("product_name") or row.get("productName") or "").strip(),
    }


def frozen_source_row(row: dict[str, Any]) -> dict[str, Any]:
    canonical = canonical_scope_row(row)
    return {
        **canonical,
        "platform": PLATFORM_LABELS[canonical["platform_code"]],
        "sku": canonical["internal_sku"],
        "url": canonical["listing_url"],
        "category": canonical["product_line"],
    }


def _write_json_immutable(path: Path, payload: Any) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8-sig"))
        if existing != payload:
            raise RuntimeError(f"immutable run artifact already exists with different content: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def build_frozen_scope(
    listing_master: Path,
    run_dir: Path,
    run_id: str,
    report_date: str,
    generated_at: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    scope = load_review_scope(listing_master)
    frozen = [frozen_source_row(row) for row in scope]
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()
    counts = Counter(row["platform_code"] for row in frozen)
    manifest = {
        "run_id": run_id,
        "report_date": report_date,
        "generated_at": generated_at,
        "source_file": str(listing_master.resolve()),
        "source_file_hash": sha256(listing_master),
        "active_scope_count": len(frozen),
        "platform_counts": dict(sorted(counts.items())),
        "active_record_ids": [row["record_id"] for row in frozen],
        "scope_hash": _scope_hash(frozen),
    }
    _write_json_immutable(run_dir / "listing_sources.json", frozen)
    _write_json_immutable(run_dir / "scope_manifest.json", manifest)
    return frozen, manifest


def diff_scopes(current: list[dict[str, Any]], previous: list[dict[str, Any]]) -> dict[str, Any]:
    current_map = {canonical_scope_row(row)["record_id"]: canonical_scope_row(row) for row in current}
    previous_map = {canonical_scope_row(row)["record_id"]: canonical_scope_row(row) for row in previous}
    categories: dict[str, list[dict[str, Any]]] = {
        "CONTINUING": [],
        "NEW_TO_SCOPE": [],
        "REMOVED_FROM_SCOPE": [],
        "LINK_CHANGED": [],
        "RECORD_IDENTITY_CHANGED": [],
    }
    for record_id in sorted(current_map.keys() | previous_map.keys()):
        current_row = current_map.get(record_id)
        previous_row = previous_map.get(record_id)
        if previous_row is None:
            categories["NEW_TO_SCOPE"].append({"record_id": record_id, "current": current_row})
            continue
        if current_row is None:
            categories["REMOVED_FROM_SCOPE"].append({"record_id": record_id, "previous": previous_row})
            continue
        identity_changes = {
            field: {"previous": previous_row.get(field), "current": current_row.get(field)}
            for field in IDENTITY_FIELDS
            if previous_row.get(field)
            and current_row.get(field)
            and previous_row.get(field) != current_row.get(field)
        }
        if identity_changes:
            categories["RECORD_IDENTITY_CHANGED"].append(
                {"record_id": record_id, "previous": previous_row, "current": current_row, "changes": identity_changes}
            )
        elif previous_row["listing_url"] != current_row["listing_url"]:
            categories["LINK_CHANGED"].append(
                {"record_id": record_id, "previous": previous_row, "current": current_row}
            )
        else:
            categories["CONTINUING"].append({"record_id": record_id, "previous": previous_row, "current": current_row})
    summary = {name: len(rows) for name, rows in categories.items()}
    return {"summary": summary, "categories": categories}


def evaluate_scope_gate(diff: dict[str, Any], current: list[dict[str, Any]], previous: list[dict[str, Any]], policy: dict[str, Any]) -> dict[str, Any]:
    summary = diff["summary"]
    previous_count = len(previous)
    changed = summary["LINK_CHANGED"] + summary["RECORD_IDENTITY_CHANGED"]
    numerator = summary["NEW_TO_SCOPE"] + summary["REMOVED_FROM_SCOPE"] + changed
    ratio = numerator / previous_count if previous_count else None
    reasons: list[dict[str, Any]] = []
    if previous_count and ratio is not None and ratio > float(policy["scope_change_review_ratio"]):
        reasons.append({"code": "SCOPE_CHANGE_RATIO_EXCEEDED", "ratio": ratio, "threshold": policy["scope_change_review_ratio"]})
    previous_counts = Counter(canonical_scope_row(row)["platform_code"] for row in previous)
    current_counts = Counter(canonical_scope_row(row)["platform_code"] for row in current)
    if policy.get("platform_zero_requires_review", True):
        for platform in sorted(ALLOWED_PLATFORMS):
            if previous_counts[platform] > 0 and current_counts[platform] == 0:
                reasons.append({"code": "PLATFORM_SCOPE_DROPPED_TO_ZERO", "platform": platform})
    if policy.get("record_identity_change_requires_review", True) and summary["RECORD_IDENTITY_CHANGED"]:
        reasons.append({"code": "RECORD_IDENTITY_CHANGED", "count": summary["RECORD_IDENTITY_CHANGED"]})
    return {
        "requires_review": bool(reasons),
        "scope_change_ratio": ratio,
        "previous_scope_count": previous_count,
        "current_scope_count": len(current),
        "changed_count": changed,
        "reasons": reasons,
    }


def _run_is_successful(run_dir: Path) -> tuple[bool, str | None, str | None]:
    state_path = run_dir / "run_state.json"
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8-sig"))
        if state.get("mode") == "PRODUCTION" and state.get("state") in SUCCESS_STATES:
            return True, str(state.get("report_date") or ""), str(state.get("updated_at") or "")
    manifest_path = run_dir / "run_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        if manifest.get("status") == "REPORT_PUBLISHED" and str(manifest.get("report_type", "")).lower() in {"weekly", "biweekly"}:
            return True, str(manifest.get("report_date") or ""), str(manifest.get("started_at") or "")
    return False, None, None


def find_previous_successful_weekly_run(runs_root: Path, report_date: str, exclude_run_id: str | None = None) -> Path | None:
    candidates: list[tuple[str, str, Path]] = []
    for run_dir in runs_root.iterdir() if runs_root.exists() else []:
        if not run_dir.is_dir() or run_dir.name == exclude_run_id or not (run_dir / "listing_sources.json").exists():
            continue
        successful, candidate_date, timestamp = _run_is_successful(run_dir)
        if successful and candidate_date and candidate_date < report_date:
            candidates.append((candidate_date, timestamp or "", run_dir))
    return max(candidates, default=None, key=lambda item: (item[0], item[1]))[2] if candidates else None


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def scope_hash(rows: Iterable[dict[str, Any]]) -> str:
    return _scope_hash(rows)
