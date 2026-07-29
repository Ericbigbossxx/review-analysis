"""Safe configuration shape for a future reviewed adapter; it never calls a platform."""

from __future__ import annotations

import os


def public_review_adapter_config() -> dict[str, str | None]:
    return {"client_id": os.environ.get("RETAIL_REVIEW_CLIENT_ID"), "api_key": os.environ.get("RETAIL_REVIEW_API_KEY")}
