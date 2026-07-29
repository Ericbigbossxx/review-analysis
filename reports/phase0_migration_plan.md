# Phase 0 — safe migration plan

**Status:** `READY_FOR_MIGRATION_REVIEW`  
**Execution in Phase 0:** none. No source file, report, JSON record, or database row has been moved, rewritten, or deleted.

## Approval gates

| Gate | Required evidence | Owner decision |
|---|---|---|
| G1: source inventory | Approved manifest and source hashes for workbook/JSON/run directories | Confirm retained sources and allowed copy set |
| G2: Listing Master | Reviewed non-empty rows, platform IDs, URLs, ZIPs, and `record_id` mapping | Approve `products` projection |
| G3: review identity | Platform review IDs or documented deterministic legacy-key method with collision report | Approve `reviews` dedupe policy |
| G4: historical load | Dry-run counts reconcile by run/platform/SKU; duplicate and null-key report is zero or explicitly accepted | Approve transaction execution |
| G5: publication safety | Existing Pages archive checks pass before/after any relocation | Approve optional path migration |

## Ordered migration procedure

1. Copy—not move—the approved source assets to a dated staging area. Generate SHA-256 manifest and preserve original paths.
2. Populate a reviewed copy of `config/listing_master.xlsx`; validate required fields, unique `record_id`, allowed platform codes, and URL/item identity.
3. Apply the reviewed schema to `database/tracker.db` and register the initial migration. No collection run is initiated.
4. Create `products` from the approved Listing Master and record `source_path`, source row, and file hash.
5. Load dated historical review aggregates into `review_snapshots` using an explicit historical `run_id`; reconcile total rows and aggregate counts against each source JSON.
6. Load `reviews` only after the source-review-key gate. Preserve text, verified/syndicated flags, source system, and evidence path; do not recompute or recollect reviews.
7. Generate `review_changes` only from comparable ordered snapshots. If a prior comparable baseline is absent, store no change and label the result `NOT_AVAILABLE`.
8. Keep the old root assets in place through archive regression verification. Only then consider copying them under `data/history/`; never delete the originals during this project phase.

## Acceptance checklist

- Per run/platform/SKU: source summary row count, total review counts, and low-star counts reconcile exactly.
- `(record_id, source_review_id)` has no duplicates; every imported row has a verified key policy.
- `products` has one platform Listing per `record_id`; `platform + internal_sku` conflicts are reviewed.
- Evidence and source paths resolve to preserved files; no existing report is altered.
- Database transaction rolls back fully on a reconciliation, duplicate, or required-field failure.

## Explicit non-actions

- No actual platform collection or browser run.
- No scheduled task, Feishu notification, or external deployment.
- No deletion, overwrite, or relocation of review history.
- No assumption that a historical value represents a current Listing state.
