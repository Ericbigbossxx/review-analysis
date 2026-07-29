"""Feishu-compatible configuration boundary. Sending is intentionally absent in Phase 1."""

from __future__ import annotations

import os


def feishu_webhook_from_environment() -> str | None:
    return os.environ.get("FEISHU_WEBHOOK_URL")


def delivery_enabled() -> bool:
    return False
