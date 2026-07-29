# Phase 1 — legacy security review

**Status:** `PASS_WITH_QUARANTINED_LEGACY`

## Finding

| Location | Type | Validity | Action |
|---|---|---|---|
| `legacy/review_required/build_review_dashboard.ps1` | Hard-coded third-party public-review access parameter | Unknown; not tested | Moved from root after backup, excluded from Git, and not executed |

The value is deliberately not reproduced in this report. No token, API key, webhook, cookie, authorization header, proxy parameter, browser profile path, password, or machine-specific access value was used or validated.

## Safe replacement boundary

- `modules/review_tracker/configuration.py` reads empty environment-variable placeholders only.
- `.env.example` documents `RETAIL_REVIEW_CLIENT_ID`, `RETAIL_REVIEW_API_KEY`, and `FEISHU_WEBHOOK_URL` without real values.
- `shared/logging` redacts sensitive-key names before writing structured events.
- `shared/notification` exposes configuration only and hard-disables delivery in Phase 1.

The quarantined script must remain outside formal modules until a separate approved refactor replaces access parameters with reviewed environment configuration.
