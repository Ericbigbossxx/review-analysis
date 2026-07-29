"""Structured logging with deterministic sensitive-value redaction."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SENSITIVE_KEYS = re.compile(r"token|key|secret|password|cookie|authorization|webhook", re.IGNORECASE)


def redact(value: Any, key: str = "") -> Any:
    if SENSITIVE_KEYS.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {name: redact(item, name) for name, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def write_event(log_path: Path, run_id: str, event: str, **context: Any) -> None:
    payload = {"timestamp": datetime.now(timezone.utc).isoformat(), "run_id": run_id, "event": event, "context": redact(context)}
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
