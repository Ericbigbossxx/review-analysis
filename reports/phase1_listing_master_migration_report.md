# Phase 1 — Listing Master migration draft report

**Source:** `runs/2026-07-23-biweekly-review-analysis/review_summary.json`  
**Output:** `config/listing_master_migration_draft.xlsx`

| Measure | Count |
|---|---:|
| Extracted Listing records | 35 |
| THD / Lowe's / Walmart | 10 / 10 / 15 |
| Missing URL | 0 |
| Missing platform Item ID | 0 |
| Missing SKU | 0 |
| Duplicate `record_id` candidate | 0 |
| Platform / URL mismatch | 0 |
| Rows with data-quality exception | 0 |
| Rows marked `READY_FOR_USER_REVIEW` | 35 |

Each row retains `source_file` and `source_row`; URLs come directly from local historical data. `active`, `monitor_listing`, `monitor_rank`, and `monitor_review` are all `FALSE`. No keyword, ZIP, seller, model, or other unavailable field was guessed.

The blank `config/listing_master.xlsx` remains unchanged. This separate draft is not an activation file and needs user review before any value is promoted.
