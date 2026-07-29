"""Pure identity helpers; no browser or network operations."""

from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

PLATFORM_ALIASES = {"WALMART": "WALMART", "THD": "THD", "HOMEDEPOT": "THD", "LOWES": "LOWES", "LOWE'S": "LOWES"}


def canonical_platform(value: str) -> str:
    normalized = re.sub(r"\s+", "", (value or "").upper())
    return PLATFORM_ALIASES.get(normalized, normalized)


def platform_from_url(url: str) -> str | None:
    host = (urlsplit(url).hostname or "").lower()
    if "walmart." in host:
        return "WALMART"
    if "homedepot." in host:
        return "THD"
    if "lowes." in host:
        return "LOWES"
    return None


def normalize_url(url: str) -> str:
    parts = urlsplit((url or "").strip())
    keep = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if not key.lower().startswith(("utm_", "ref", "source"))]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), urlencode(keep), ""))


def build_record_id(platform: str, internal_sku: str) -> str:
    safe_sku = re.sub(r"[^A-Z0-9]+", "_", (internal_sku or "").upper()).strip("_")
    return f"{canonical_platform(platform)}_{safe_sku}"


def legacy_review_key(*parts: object) -> str:
    normalized = "\u241f".join(re.sub(r"\s+", " ", str(part or "").replace("\r\n", "\n").replace("\r", "\n")).strip() for part in parts)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
