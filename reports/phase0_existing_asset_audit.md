# Phase 0 — existing asset audit

**Project root:** `C:\Users\admin\Documents\Weekly review analysis`  
**Audit scope:** local files only; no platform requests, collection runs, report regeneration, or historical-data writes were performed.  
**Result:** `READY_FOR_MIGRATION_REVIEW`

## Executive assessment

The existing root is an established review-analysis and GitHub Pages archive, not a disposable prototype. It is therefore the correct root for **US Local Channel Listing Tracker**; creating a nested `us-local-channel-listing-tracker/` directory would split source history and published assets.

The audit found **47 pre-existing files** (about **2.0 MB**). The formal 2026-07-23 run has 35 Listing-level review summary rows (THD 10, Lowe's 10, Walmart 15) and 436 retained low-star review rows (THD 258, Lowe's 82, Walmart 96). Its review summary already contains platform, SKU, item ID, URL, star distribution, QA status, theme, urgency, source, and date fields. This is reusable Review Tracker history, but it is not yet normalized to the new `record_id` model.

## Asset inventory and recommendation

| Asset group | Current status | Reusable | Proposed action | Dependencies / known issue |
|---|---|---:|---|---|
| `DATA/Top10listing&新品 差评分析.xlsx` | Original Listing workbook | Yes | KEEP | Preserve as source evidence; map only after approved field review |
| `listing_sources.json` | Earlier THD/Lowe's Listing extraction | Yes, with mapping | REVIEW_REQUIRED | Uses `Homedepot` naming and has no unified `record_id` |
| `runs/2026-07-23-biweekly-review-analysis/*.json` | Immutable 2026-07-23 review run | Yes | KEEP | Source for approved history migration; do not rewrite |
| `review_summary.json`, `negative_reviews.json` | Legacy root copies | Conditional | REVIEW_REQUIRED | Superseded in coverage by the dated run; preserve until retention decision |
| `reports/*.html`, `index.html`, `archive_manifest.json`, `.nojekyll` | Published report/archive assets | Yes | KEEP | Root behavior may be GitHub Pages; do not relocate during Phase 0 |
| `build_biweekly_report_data.ps1` | Review aggregation and theme logic | Yes | REFACTOR | Extract generic review normalization/theme functions only after test baselines |
| `build_review_dashboard.ps1` | Legacy THD/Lowe's collection-plus-dashboard script | Partial | REVIEW_REQUIRED | Contains hard-coded third-party access parameters; must not be copied into modules |
| `build_visual_dashboard.ps1`, `update_archive_portal.ps1` | 2026-07-23 report/publish builders | Yes | REFACTOR | Parameterize source paths and separate presentation from tracking ingestion |
| `build_pages_dashboard.ps1`, `build_static_dashboard.ps1`, `build_archive_portal.ps1` | Older duplicate HTML builders | Partial | DEPRECATE | Retain for reproducibility; consolidate only after published-archive regression check |
| `runs/.../*.js`, `bv_collection_preview.html`, raw API probes | Captured technical evidence | Conditional | KEEP | Do not execute or treat as supported adapters without compliance review |
| Browser/shared/database/notification layers | Not present | No | MOVE | Target folders created as placeholders only; implementation is deferred |
| Feishu notification scripts, test suite, dependency manifest | Not found | N/A | REVIEW_REQUIRED | Phase 0 must not invent integrations or automation |

## Existing Review Tracker mapping

| Existing source / field | Target destination | Migration rule |
|---|---|---|
| `review_summary.json`: `platform`, `sku`, `productId`, `url` | `products` | Create a platform-specific `record_id`; validate unique platform + internal SKU and retain source row/path |
| `review_summary.json`: counts, rating, QA, source | `review_snapshots` | One approved historical `run_id` per dated snapshot; retain `raw_evidence_path` |
| `low_star_reviews.json`: `rating`, `title`, `text`, `date`, `verified`, `syndicated` | `reviews` | Require platform review ID or a reviewed deterministic legacy-key policy before inserting; no guessed key |
| Existing summary deltas | `review_changes` | Derive only where comparable dated snapshots and keys exist; otherwise mark `NOT_AVAILABLE` |
| `runs/...` HTML/JSON/JS | `data/history/` and `evidence_files` index | Copy only after approval; preserve source directories and hashes |

## Key risks and decisions required

1. The local `.git` directory is not a valid Git worktree (`git` reports no repository). Any source-control or publishing change needs a separate remote/repository verification.
2. Root-level files are both historical data and Pages artifacts. Moving them now risks breaking the existing public archive; Phase 0 leaves them in place.
3. Historical review JSON lacks a confirmed universal source-review key in the audit summary. The `reviews` unique constraint must not be populated until the legacy-key policy is approved.
4. Walmart historical material exists in the 2026-07-23 run, but the original `listing_sources.json` only represents prior THD/Lowe's scope. A unified master must be reconciled from verified sources, not fabricated.
5. `build_review_dashboard.ps1` has hard-coded external access parameters. Treat it as sensitive legacy code; replace parameter handling before reuse and do not expose credentials in documentation or configuration.

The detailed per-file record is in `reports/phase0_file_manifest.csv`.
