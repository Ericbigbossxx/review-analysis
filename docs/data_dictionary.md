# Data dictionary

## Listing Master (`config/listing_master.xlsx`)

| Field | Definition | Required / validation |
|---|---|---|
| `record_id` | Stable cross-module listing key, normally `PLATFORM_INTERNALSKU` | Required; unique; text |
| `active` | Master enable/disable switch | Required; `TRUE` or `FALSE` |
| `platform` | Business platform code | Required; `WALMART`, `THD`, or `LOWES` |
| `brand`, `product_line`, `internal_sku`, `model`, `product_name` | Product identity attributes | `internal_sku` required; do not invent values |
| `platform_item_id` | Platform product/listing identifier | Optional until verified from public listing |
| `listing_url` | Product-detail-page access anchor | Required for monitored Listing or Review rows; URL |
| `primary_keyword`, `secondary_keyword`, `third_keyword` | Search terms for rank observations | Optional; preserve configured search intent |
| `zip_code` | Configured market ZIP | Required for Lowe's rank runs; text to preserve leading zeros |
| `expected_seller` | Expected seller of record | Optional; discrepancies become evidence-backed changes |
| `monitor_listing`, `monitor_rank`, `monitor_review` | Feature flags | Required; `TRUE` or `FALSE` |
| `max_search_pages` | Upper bound for visible result pages | Positive integer when `monitor_rank=TRUE` |
| `notes` | Human-maintained scope notes | Optional |

## SQLite entity conventions

All business tables carry `record_id`, timestamps, source attribution, `run_id` or a run relationship, capture/error state as applicable, and evidence location. `collection_runs` establishes the run boundary; `collection_errors` stores errors without falsifying a snapshot. `UNIQUE(run_id, record_id)` prevents a repeated attempt from creating uncontrolled duplicate observations in the same run.

| Table | Grain | Primary purpose |
|---|---|---|
| `products` | one configured platform Listing | Canonical Listing Master projection |
| `listing_snapshots` | one Listing observation per run | Listing Monitor facts and evidence |
| `ranking_snapshots` | one keyword/rank-kind observation per Listing run | Visible organic/sponsored search evidence |
| `review_snapshots` | one review-statistics observation per Listing run | Rating/review counts and coverage |
| `reviews` | one source review per Listing | Public review detail and identity-safe dedupe; legacy rows use `platform_review_id = NULL` and a content-hash key |
| `listing_changes`, `review_changes` | one detected field/change type per run | Auditable deltas from comparable baseline |
| `collection_runs`, `collection_errors` | one run / one error | Operational state and error trace |

## Legacy review identity

Historical records without an official platform review identifier must retain `platform_review_id = NULL`. Their `legacy_review_key` is an internal SHA-256 fingerprint of normalized platform, item ID, URL, date, rating, title, body, and reviewer name (when available). `review_id_source` is `LEGACY_CONTENT_HASH` and `identity_confidence` is `LEGACY_HASH`; neither is an official platform ID.
| `evidence_files` | one immutable evidence file | Screenshot/raw evidence index |
