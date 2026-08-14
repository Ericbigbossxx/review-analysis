# Agent Quick Start

### What is this?

Weekly Review Tracker is a governed weekly workflow for monitoring public product reviews on Walmart, The Home Depot (THD), and Lowe's.
Its purpose is to identify newly visible low-star reviews, review-content changes, recurring complaint themes, and consumer feedback that needs operational follow-up.

### Current operating mode

`MANUAL_WEEKLY_OPERATION`

- Recommended manual cadence: Thursday at 10:00 China time.
- This is a working cadence, not a Scheduler guarantee.
- Hermes automatic Weekly Run did not enter production.
- Windows Scheduler and Hermes Kanban registration are not active.
- Do not restart automation unless the user explicitly reopens that project.

### Current authoritative Review scope

- Authority: `config/listing_master.xlsx`, sheet `Listing Master`.
- Scope rule: `active == TRUE AND monitor_review == TRUE`.
- Walmart: 15; THD: 10; Lowe's: 10; total: 35.
- Listing Master total rows: 41.
- Historical Review DB: 436 Review rows.
- SQLite integrity: `ok`; foreign-key errors: 0.

The database `products.monitor_review` flag is not the Review-scope authority: it currently has 0 enabled rows.
Until explicitly redesigned, Listing Master is authoritative for Weekly Review scope.
If the user asks to run the Weekly Review, use the existing manual workflow; do not redesign the system.

# Current Known State

Verified from the live workspace on 2026-08-13:

```text
Operating Mode: MANUAL_WEEKLY_OPERATION

Review Scope:
Walmart = 15
THD = 10
Lowe's = 10
Total = 35

Listing Master:
41 rows; 41 active; 15 monitor_listing; 15 monitor_rank; 35 monitor_review

Historical Reviews:
436 rows across 26 Listings
THD = 258; Lowe's = 82; Walmart = 96

Review Snapshots: 35
Review Changes: 0

DB Integrity:
integrity_check = ok
foreign_key_check errors = 0
duplicate Review identity groups = 0

Windows Scheduler: NOT REGISTERED
Hermes Kanban Task: review_tracker_weekly NOT PRESENT
Hermes Weekly Production: NOT ACTIVE
Automation Status: CLOSED / DEFERRED
Current Worktree: DIRTY
```

Handoff status: `READY_FOR_MANUAL_WEEKLY_OPERATION`. This is a manual operating handoff, not production or automation readiness.

The last successful published Review run is `runs/2026-08-06-biweekly-review-analysis`. It is historical evidence, not proof of current platform state. That run covered 35 Listings, obtained usable current data for 34, recorded one Walmart `LISTING_PAGE_NOT_FOUND`, performed no DB writes, and published a report.

The later `runs/SUPERVISED_WEEKLY_DRY_RUN_20260812_HERMES_V1` completed only a protected dry run. It built and froze the 35-row scope and passed read-only preflight, but invoked no collector, report, archive, publish, notification, Scheduler, or DB write.

# Business Purpose

The system exists to provide a weekly, evidence-backed view of consumer feedback for the monitored US local-channel Listings. Its practical value is:

- identify newly visible public low-star Review text;
- identify Review text or metadata changes when a stable identity permits comparison;
- surface 1-star and 2-star negative feedback and watch 3-star mixed feedback;
- identify product quality, battery, assembly, manual/content, logistics, fulfillment, customer-service, connectivity, and performance issues only when supported by Review text;
- show repeated complaint themes across Listings and platforms;
- give the weekly operating review consumer-side evidence;
- preserve historical Review evidence for later comparison.

This is a bounded retail-operations workflow. It is not a claim of complete market, platform, or customer intelligence.

# What This System Is NOT

- It is not a system for generating Reviews.
- It is not a system for modifying or deleting platform Reviews.
- It is not a Review-manipulation tool.
- It is not a full-platform sentiment or social-listening system.
- It is not a CRM or automated customer service.
- It is not the primary data source for STORM.
- It is not part of Walmart Operation System and does not depend on it.
- It is not currently an autonomous Agent production workflow.
- It is not authority for Listing Detail or Search Rank scope merely because those modules share the Listing Master.
- It is not authorized to bypass CAPTCHA, Robot Check, access controls, account restrictions, or unavailable public content.

# Sources of Truth

## A. Listing Scope

The live Review-scope authority is:

- File: `config/listing_master.xlsx`
- Sheet: `Listing Master`
- Grain: one row per platform Listing
- Stable relationship key: `record_id`, normally `PLATFORM_INTERNALSKU`
- Platform: `platform`
- Product identity: `internal_sku`, `model`, `platform_item_id`, `product_name`, and `listing_url`
- Master enablement: `active`
- Review enablement: `monitor_review`
- Separate feature flags: `monitor_listing` and `monitor_rank`

`modules/review_tracker/scope.py` reads this sheet, normalizes `HOMEDEPOT` to `THD`, requires a supported platform and valid platform URL, rejects duplicate `record_id` and duplicate active platform/SKU pairs, and includes only rows where both `active` and `monitor_review` are true.

Current workbook facts:

- 41 total rows: Walmart 15, THD 14, Lowe's 12.
- 41 rows have `active=TRUE`.
- 35 rows have `monitor_review=TRUE`: Walmart 15, THD 10, Lowe's 10.
- 15 rows have `monitor_listing=TRUE` and the same 15 have `monitor_rank=TRUE`.
- 9 rows are enabled for both Listing/Rank and Review.
- 6 rows are Listing/Rank-only.
- 26 rows are Review-only.
- Duplicate `record_id`: 0.
- Review-scope rows with blank Listing URL: 0.

The Review scope reconciles exactly with the frozen 35-row source in `runs/2026-08-06-biweekly-review-analysis/listing_sources.json` and the later supervised dry-run manifest.

The database is not the current Review-scope authority. `database/tracker.db` has 41 `products` rows, but only 15 are active for Listing/Rank and `monitor_review=1` is 0. This is a known cross-source ownership gap, not permission to rewrite the DB.

> Until explicitly redesigned, Listing Master is authoritative for Weekly Review scope.

The root `README.md` still describes the Phase 0 blank-master state. Treat that paragraph as historical and stale; do not use it to override the live workbook or this handoff.

## B. Review Historical Database

- Path: `database/tracker.db`
- Format: SQLite
- Schema source: `database/schema.sql`
- Run boundary: `collection_runs`
- Product projection: `products`
- Per-Listing Review statistics: `review_snapshots`
- Review details: `reviews`
- Detected Review deltas: `review_changes`
- Errors: `collection_errors`
- Evidence index: `evidence_files` and `evidence_file_metadata`

Current Review-table counts:

| Table | Rows | Meaning |
|---|---:|---|
| `products` | 41 | Shared Listing projection; not current Review-scope authority |
| `review_snapshots` | 35 | Historical per-Listing Review-statistics baseline |
| `reviews` | 436 | Migrated historical low-star Review details |
| `review_changes` | 0 | No production incremental change rows exist |

The 436 historical Review rows came from the controlled migration of `runs/2026-07-23-biweekly-review-analysis/low_star_reviews.json`. They represent 26 Listings, not all 35 current Review-scope Listings.

The source did not contain a confirmed universal official platform Review ID. Therefore all 436 rows use:

- `platform_review_id = NULL`;
- `review_id_source = LEGACY_CONTENT_HASH`;
- `identity_confidence = LEGACY_HASH`;
- `source_review_id = legacy_review_key`.

The legacy key is an internal SHA-256 fingerprint over normalized source fields; it is not a platform-provided ID.

The `reviews` table enforces three identity-safe uniqueness constraints:

- `UNIQUE(record_id, source_review_id)`;
- `UNIQUE(record_id, platform_review_id)`;
- `UNIQUE(record_id, legacy_review_key)`.

Live validation found no duplicate group under any of those keys. `PRAGMA integrity_check` returned `ok` and `PRAGMA foreign_key_check` returned no rows.

## C. Current Platform Data and Collectors

### THD

- Current scope: 10 Listings.
- Collector: `modules/review_tracker/bazaarvoice.py` via `scripts/run_review_tracker_bv.py`.
- It reads the numeric product ID from the Listing URL and uses the public Bazaarvoice Review feed configured by the frozen run's `raw/bv_config/homedepot_bvapi.js`.
- It requests pages of 100, sorted newest first, preserves raw page files with hashes, and reconciles rating distribution, total Review count, endpoint row count, and readable-text coverage.
- It emits aggregate statistics and Review-detail rows only for ratings 1, 2, and 3.
- The platform `Id` is emitted as `sourceReviewId`.
- A failed HTTP/API call raises an error; it must not be converted to `NO_CHANGE`.

### Lowe's

- Current scope: 10 Listings.
- Collector: the same Bazaarvoice collector and CLI as THD, using `raw/bv_config/lowes_bvapi.js`.
- It uses the numeric product ID from the Listing URL, preserves raw page files and hashes, and applies the same rating/text reconciliation.
- Ratings-only submissions are kept separate from readable Review text.
- Ratings 1, 2, and 3 are emitted as low-star detail; the platform `Id` is emitted as `sourceReviewId`.
- Review collection is separate from Lowe's Search Rank rules. Fixed ZIP, logged-out state, and default sort govern Rank collection, not this Review API path.

### Walmart

- Current scope: 15 Listings.
- Auxiliary Review collector: `modules/review_tracker/walmart_bazaarvoice.py` via `scripts/run_review_tracker_walmart_bv.py`.
- It reads the public Bazaarvoice `reviews.djs` display feed, parses visible Review IDs and text, paginates by 100, hashes raw pages, and deduplicates parsed rows in memory by Review ID.
- It keeps page-wide rating distribution, ratings-only count, and written-Review coverage separate.
- It emits only 1-star, 2-star, and 3-star Review detail in `walmart_bv_raw.json`.
- Walmart product-page/storefront verification is a separate supervised input. CAPTCHA or Robot Check requires a human stop; no automated resolution is permitted.
- The last successful historical run recorded 14/15 storefront Listings available and one `LISTING_PAGE_NOT_FOUND`.

The current Walmart production wiring is incomplete: the auxiliary collector writes `walmart_bv_raw.json`, while `build_biweekly_report_data.ps1` reads `walmart_raw.json`. The existing `scripts/build_walmart_review_input.py` creates `walmart_raw.json` by merging supervised storefront data with the auxiliary feed, but `modules/review_tracker/hermes_runtime.py` does not call that merge step. Do not call the production branch complete.

The final merged `low_star_reviews.json` also drops Walmart's parsed Review ID even though it exists in the raw collector output. Use `walmart_bv_raw.json` for Walmart identity comparison and evidence; do not claim deterministic Walmart “new Review” identity from the merged row alone.

### Detail, Rank, and Review relationship

Listing Detail, Search Rank, and Review are modules of the same project and share `record_id` and Listing Master, but they are independent capabilities controlled by separate feature flags. Weekly Review collection does not establish a Search Rank, and Ranking evidence does not establish Review content. Platform-specific detail/rank rules remain in `docs/platform_collection_rules.md`.

# Weekly Review Data Flow

```text
Listing Master
      |
      v
Resolve active AND monitor_review scope
      |
      v
Freeze run-specific listing_sources.json + scope_manifest.json
      |
      v
THD/Lowe's Bazaarvoice collector + Walmart auxiliary collector
      |
      v
Supervised Walmart storefront verification and merge
      |
      v
Normalize aggregate statistics and low-star Review detail
      |
      v
Compare with previous successful run and historical evidence
      |
      v
Validate availability, rating totals, identities, and duplicates
      |
      v
Weekly Review Result
      |
      v
Manual operational review and follow-up
```

Important limitations:

- The working collectors retain individual detail only for 1-star through 3-star Reviews; all-star coverage is aggregate.
- The existing period comparison calculates aggregate deltas and counts readable low-star rows dated after the prior report date.
- It does not perform a complete identity anti-join against the SQLite Review history.
- It does not implement production writes to `reviews`, `review_snapshots`, or `review_changes`.
- A first comparable observation is a baseline, not a change.

# Weekly Operating Procedure

Recommended manual cadence: Thursday, 10:00 China time. This is not an automated appointment.

## Step 0 — Authorization boundary

Run collection only when the user explicitly asks for the Weekly Review. A request to inspect, document, diagnose, or prepare does not authorize collection, formal History, `outputs/latest` promotion, archive publication, Git publication, notification, or scheduling.

## Step 1 — Preflight

Before any platform access:

1. Confirm `config/listing_master.xlsx` exists and is readable.
2. Resolve `active AND monitor_review` scope and print platform counts.
3. Confirm total scope equals the live Listing Master result.
4. Confirm `database/tracker.db` exists.
5. Run SQLite integrity and foreign-key checks.
6. Record `reviews`, `review_snapshots`, and `review_changes` counts.
7. Record DB and Listing Master SHA-256 hashes.
8. Inspect `git status`. A dirty worktree is a stop for automated commit/push, not permission to reset, stash, clean, or include user changes.
9. Confirm no active `runtime/review_tracker.lock` and no incomplete prior manual run with the same report date.
10. Confirm which platform routes are accessible without bypassing controls.

If any critical preflight result is inconsistent, stop before collection and investigate.

## Step 2 — Resolve and freeze scope

Print:

```text
Walmart: <count>
THD: <count>
Lowe's: <count>
Total: <count>
```

For the current verified workbook the expected result is 15 / 10 / 10 / 35. Do not hardcode those values into logic: recalculate them from the workbook every run.

Freeze the resolved rows into the new run directory as `listing_sources.json` and `scope_manifest.json`, including source file hash, active IDs, per-platform counts, and scope hash. Do not overwrite an existing run artifact with different content.

If the frozen scope does not exactly match the live resolved scope, stop. Do not collect a partial or guessed scope.

## Step 3 — Collect

Run each platform deliberately and record:

- requested Listings;
- successful Listings;
- `ACCESS_BLOCKED`;
- `VERIFICATION_REQUIRED`;
- `DATA_UNAVAILABLE_CURRENT`;
- `PARTIAL`;
- failed Listings.

THD and Lowe's use the existing Bazaarvoice collector. Walmart requires both the auxiliary Review feed and supervised current storefront evidence. Do not retry prohibited access failures. Do not use prior data as current data.

## Step 4 — Normalize

For every usable Review-detail row retain, when available:

- `record_id`;
- normalized platform code;
- internal SKU and model;
- Listing URL and platform item ID;
- platform Review ID or explicit fallback identity;
- rating;
- title and Review text;
- Review date;
- reviewer display name;
- verified/syndicated flags;
- collection timestamp/run ID;
- source URL, raw evidence path, and evidence hash.

Do not replace missing identity, text, date, or evidence with invented values. Ratings-only submissions are not readable Review text.

Current normalized low-star output is not field-complete. THD/Lowe's rows carry platform, SKU, URL, `sourceReviewId`, rating, title/text, date, ratings-only, syndicated, and verified fields. The merged Walmart rows omit the raw Review ID. Neither output consistently carries `record_id`, model, reviewer display name, collected timestamp, or an evidence hash on every row. Resolve identity through the frozen scope and raw run evidence, and leave unavailable fields explicit.

## Step 5 — Compare

Compare the current run with the previous successful comparable run:

- `NEW_REVIEW`: stable Review identity is present now and absent from the comparable prior data;
- `UPDATED_REVIEW`: the same stable identity exists but material fields changed;
- `UNCHANGED_REVIEW`: the same stable identity and normalized content are unchanged;
- `UNAVAILABLE_REVIEW`: current evidence is unavailable or non-comparable;
- `DUPLICATE_CANDIDATE`: the same stable identity appears more than once.

Use THD/Lowe's `sourceReviewId` from the raw or low-star collector output. Use Walmart raw `id` from `walmart_bv_raw.json`. The merged Walmart low-star file is not identity-complete.

The current `build_review_period_comparison.py` output is useful for aggregate total/low-star deltas and date-based readable low-star counts, but it is not a complete Review-identity change detector. Report that limitation explicitly.

## Step 6 — Deduplicate

Acceptance rule:

`duplicate_review_count must be 0`

Preferred keys:

1. `(record_id, platform_review_id)` when a verified platform Review ID exists;
2. `(record_id, source_review_id)` for collector-provided stable IDs;
3. `(record_id, legacy_review_key)` only for the approved historical content-hash identity.

For Walmart, deduplicate before the merge using the raw parsed `id`. If no reliable ID or approved fallback can be produced, mark the row `MANUAL_REVIEW_REQUIRED` and do not call it a deterministic new Review.

Never edit historical Review text to make deduplication pass.

## Step 7 — Persist / Archive

### Historical capability

- A controlled offline migration populated 436 historical Review rows and 35 historical Review snapshots.
- That migration was idempotent on rerun and retained approved legacy identity semantics.
- Historical published runs and local report builders exist.

### Current production capability

`database_incremental_write_enabled=false`

The current Weekly path does not implement the production incremental-write contract for:

- `reviews`;
- `review_snapshots`;
- `review_changes`.

There is no approved routine manual DB-upsert procedure for a Weekly Review run.

Therefore:

`NOT IMPLEMENTED / MANUAL DECISION REQUIRED`

Do not write the DB merely because a manual collection completed. Keep current-run artifacts in a distinct run directory. Formal History, archive update, `outputs/latest` promotion, publication, Git commit/push, and external notification each require separate explicit authorization.

# Weekly Output Specification

The user-facing result should be concise and evidence-led:

```markdown
# WEEKLY REVIEW RESULT

## Overview
- Scope
- Successfully checked
- Platform limitations
- New Reviews
- New low-star Reviews
- Critical issues

## Walmart
For each actionable SKU / model:
- Rating
- Review date
- Key complaint
- Severity
- Evidence

## THD
Same fields.

## Lowe's
Same fields.

## Cross-platform Themes
Only themes present in actual Review text.

## Recommended Follow-up
Only actions supported by evidence:
- Product
- Listing/content
- Logistics
- Customer service
- Manual/instructions
- Quality
```

Do not return a large technical log as the primary result. Keep unavailable and partial coverage visible. If no deterministic new Reviews can be proven, say so; do not manufacture a zero-change conclusion.

# Review Severity Logic

The current code has two related classifications:

1. Review-star grouping:
   - 1-star and 2-star are counted as negative.
   - 3-star is counted as neutral or mixed but is included in the working “low-star” detail set.
   - 4-star and 5-star contribute to aggregate rating distribution but are not emitted as individual detail by the current collectors.
2. Listing-level urgency in `build_biweekly_report_data.ps1`:
   - `P0` for defined combinations of new/core product status, low-star count/rate, high low-star volume, or severe themes;
   - `P1` for material low-star count/rate or low-sample concern;
   - `P2` for sample building or continued observation.

The complete current threshold order is:

- if total Reviews is 0: `P2 建样本`;
- if total Reviews is below 10 and the Listing is core-new with at least 2 low-star Reviews: `P0 新品护航`;
- otherwise, if total Reviews is below 10 and any low-star Review exists: `P1 样本不足`;
- otherwise, if total Reviews is below 10: `P2 建样本`;
- for totals of at least 10, `P0 立即处理` if any condition is true:
  - core-new, at least one low-star Review, and low-star rate at least 12%;
  - low-star count at least 30;
  - low-star rate at least 25% and low-star count at least 5;
  - a severe theme is present and low-star count is at least 10;
- otherwise `P1 本周处理` if low-star count is at least 5 or low-star rate is at least 12%;
- otherwise `P2 持续观察`.

`coreNew` means brand `SUNSEEKER` or a product category containing `robot`. Severe themes are starting/power failure, quality/durability, or battery/charging.

The theme classifier is keyword-based and currently recognizes customer service/fulfillment, app/navigation/connectivity, battery/charging, starting/power failure, quality/durability, ergonomics, cutting performance, assembly/setup, price/expectation, and other.

Do not add a new scoring model in a Weekly run. For individual user-facing Review severity, keep the star rating visible and use business judgment only when the evidence supports it.

# Evidence Rules

Every deterministic Review conclusion should trace to:

- platform;
- `record_id` and Listing URL;
- Review ID or explicitly labeled stable fallback;
- rating;
- title/Review text;
- Review date;
- collection run and timestamp;
- source URL or raw evidence record;
- evidence path and hash when produced.

If those elements cannot be verified, do not present the row as a confirmed new Review. Preserve raw evidence for completed runs; do not overwrite a prior baseline.

The latest historical collectors preserve raw API/display files and SHA-256 hashes. THD/Lowe's merged low-star rows retain `sourceReviewId`. Walmart's raw collector retains `id`, but the current final merge drops it; use the raw artifact until that production gap is explicitly redesigned and approved.

# Platform Limitation Semantics

### VALID

Current data was obtained and passed required reconciliation for the claimed fields.

### VERIFICATION_REQUIRED

The Listing may exist, but CAPTCHA, Robot Check, or another verification barrier prevents a current validated observation. Stop the affected automated route.

### ACCESS_BLOCKED

The platform or required public content is blocked. Preserve the block evidence and do not bypass it.

### DATA_UNAVAILABLE_CURRENT

No valid current detail can be obtained. Prior valid data remains historical only.

### PARTIAL

Some fields are usable, but one or more key fields, identities, text coverage, or storefront checks are missing. State exactly what is and is not usable.

These relationships are mandatory:

- `ACCESS_BLOCKED != NO_CHANGE`
- `DATA_UNAVAILABLE_CURRENT != NO_CHANGE`
- `VERIFICATION_REQUIRED != CURRENT_VALID_DATA`
- `PARTIAL != FULLY_VALID`

The current collector outputs do not uniformly emit every canonical status above. The manual operator must classify the result from retained evidence without weakening the meaning.

# Completed and Incomplete Capabilities

## Completed and currently usable with the stated boundaries

- Shared 41-row Listing Master with independent Listing/Rank/Review flags.
- Live, dynamically resolved 35-Listing Review scope.
- Immutable per-run scope projection and scope-diff code.
- Read-only Review preflight with hash, schema, integrity, foreign-key, history-count, and lock checks.
- THD/Lowe's public Bazaarvoice aggregate and low-star detail collection.
- Walmart auxiliary public Review feed parsing and raw-ID deduplication.
- Historical 436-row low-star Review migration with approved legacy identity.
- Aggregate Review QA, theme classification, local report-data generation, and period comparison.
- A protected supervised dry run that invoked no production side effects.

## Not completed or not production validated

- Production incremental writes to `reviews`, `review_snapshots`, and `review_changes`.
- Complete identity-based new/updated/unchanged comparison for all current Review text.
- Reliable Review-ID propagation into final merged Walmart low-star output.
- Automatic wiring of `build_walmart_review_input.py` into the Weekly orchestrator.
- A fully supervised Hermes production run.
- Safe automated publication in a dirty or pre-staged worktree.
- Hermes Kanban registration that guarantees `REGISTER != DISPATCH`.
- Windows Scheduler registration.
- Automatic notification.

# Important Historical Decisions

## Scope

The current Review scope is 35 monitored Listings, not all 41 Master rows. The Master is a union: 35 Review Listings plus six Listing/Rank-only rows, with nine rows shared across capabilities.

## Cadence

The operating cadence changed from biweekly to weekly. Thursday at 10:00 China time is the recommended manual slot.

## Source ownership

Listing Master, not `products.monitor_review`, owns the current Review scope. The DB projection remains intentionally unreconciled for Review monitoring.

## Agent execution

The proposed path was supervised Hermes Weekly Run followed by Scheduler automation. It did not enter production. The current decision is `MANUAL_WEEKLY_OPERATION`.

# Automation Attempt — Closed / Deferred

## Hermes Weekly Run

The existing code contains `DRY_RUN`, `SMOKE_TEST`, and `PRODUCTION` modes, but code presence is not production authorization.

The last completed Review workflow evidence is a protected `DRY_RUN`:

- state `SUPERVISED_DRY_RUN_COMPLETE`;
- preflight `PREFLIGHT_PASSED`;
- no collection;
- no report, archive, or publish;
- no notification;
- no Scheduler;
- no DB write.

The later real Gateway smoke effort stopped before task creation or dispatch. No `HERMES_REVIEW_TRACKER_SMOKE_TEST` run directory exists, and no `SMOKE_TEST_SUCCESS` evidence exists.

### Blocker 1 — No production incremental DB contract

`database_incremental_write_enabled=false`. The production branch does not insert or update `reviews`, `review_snapshots`, or `review_changes`, so production persistence, write deduplication, and before/after DB reconciliation cannot be validated.

### Blocker 2 — Unsafe publication interaction

The production branch runs report/archive generation, stages report/archive/index assets, commits, pushes, and verifies GitHub Pages. The live worktree is dirty. A pre-staged user change could be included in the automatic commit, and the branch would mutate a shared worktree without a clean ownership boundary.

### Blocker 3 — Scope ownership mismatch

Listing Master resolves 35 Review Listings; DB `products.monitor_review=1` resolves 0. Cross-source ownership is not unified.

### Blocker 4 — Incomplete Walmart production wiring

The orchestrator does not invoke the existing Walmart storefront/Bazaarvoice merge that creates the file consumed by the report builder, and the final merged low-star output loses Walmart Review IDs.

# Scheduler Attempt — Closed / Deferred

Neither scheduling mechanism is active:

- Windows task `Sunseeker Review Tracker Weekly`: not registered.
- Hermes Kanban task `review_tracker_weekly`: not present.

Hermes registration was blocked because the live Gateway task model cannot guarantee:

`REGISTER != DISPATCH`

Observed semantics:

- default creation yields `ready`, which can be claimed by the active dispatcher;
- `blocked` is not a safe parking state and can be recomputed to `ready`;
- `triage` can be processed by enabled auto-decomposition;
- no atomic `draft`, `disabled`, `paused`, `pending-approval`, or `inactive` creation state exists.

> Do not recreate Scheduler registration unless the user explicitly reopens the automation project.

The script `scripts/register_review_tracker_weekly_task.ps1` is a Windows production Scheduler registrar, not a Hermes Kanban registrar. Do not run it as a substitute.

# Agent Guardrails

1. Do not restart the Hermes automation project on your own.
2. Do not register either Scheduler mechanism.
3. Do not redesign the Review DB during a Weekly run.
4. Do not rebuild or replace Listing Master.
5. Do not treat DB `monitor_review` as scope authority merely because the field exists.
6. Do not delete or rewrite the 436 historical Review rows.
7. Do not reset, recreate, or migrate the DB without explicit authorization.
8. Do not auto-commit or push from a dirty or pre-staged worktree.
9. Do not interpret platform collection failure as no change.
10. Do not manufacture Reviews to test the pipeline.
11. Do not edit historical Reviews to pass deduplication.
12. Do not bind this project to STORM or Walmart Operation System.
13. Do not add complexity merely to restore automation.
14. Do not bypass CAPTCHA, Robot Check, access controls, or unavailable content.
15. Do not write formal History, update `outputs/latest`, archive, publish, notify, or collect beyond the user-authorized scope.

# Repository Map

```text
Weekly review analysis/
|-- config/
|   |-- listing_master.xlsx              # Live shared scope authority
|   '-- review_tracker_policy.json       # Review cadence, thresholds, DB-write flag
|-- database/
|   |-- tracker.db                       # Historical SQLite state
|   '-- schema.sql                       # Canonical DDL
|-- modules/review_tracker/              # Scope, preflight, collectors, Hermes runtime
|-- scripts/                             # Manual CLIs, comparison, Walmart merge, registrars
|-- docs/
|   |-- platform_collection_rules.md     # Access and evidence boundaries
|   |-- data_dictionary.md               # Field and table definitions
|   '-- WEEKLY_REVIEW_TRACKER_AGENT_HANDOFF.md
|-- runs/
|   |-- 2026-08-06-biweekly-review-analysis/
|   |                                      # Last successful published Review evidence
|   |-- SUPERVISED_WEEKLY_DRY_RUN_20260812_HERMES_V1/
|   |                                      # Completed no-side-effect dry run
|   '-- PHASE2A_HERMES_PRE_SMOKE_BASELINE/
|                                          # Pre-smoke protected baseline
|-- reports/
|   |-- review_tracker_hermes_productionization_v1.md
|   '-- phase2a_execution_checkpoint.md   # Current automation-block evidence
|-- runtime/                              # Locks and operational runtime state
|-- tests/                                # Scope, preflight, Hermes, collector tests
|-- backups/                              # Protected migration and pre-run backups
|-- archive_manifest.json                 # Formal archive control; approval-gated
'-- index.html                            # Published portal asset; approval-gated
```

# Known Safe Commands

Run from the project root. The current verified absolute interpreter is:

```powershell
$Python = 'C:\Users\admin\AppData\Local\Python\pythoncore-3.14-64\python.exe'
$env:PYTHONPATH = (Get-Location).Path
```

## Read-only inspection

Git state:

```powershell
git status --short --branch
```

Resolve live Review scope without writing:

```powershell
& $Python -c "from pathlib import Path; from collections import Counter; from modules.review_tracker.scope import load_review_scope; rows=load_review_scope(Path('config/listing_master.xlsx')); print(dict(sorted(Counter(r['platform_code'] for r in rows).items())), len(rows))"
```

This command was verified on 2026-08-13 and returned `{'LOWES': 10, 'THD': 10, 'WALMART': 15} 35`.

## Validation

Read-only validation of the existing frozen supervised dry run:

```powershell
& $Python scripts\run_review_tracker_preflight.py `
  --source runs\SUPERVISED_WEEKLY_DRY_RUN_20260812_HERMES_V1\listing_sources.json `
  --scope-manifest runs\SUPERVISED_WEEKLY_DRY_RUN_20260812_HERMES_V1\scope_manifest.json
```

It returned `PREFLIGHT_PASSED` on 2026-08-13. For a new run, point it only at that run's already-frozen scope and manifest.

## DB integrity

```powershell
& $Python -c "import sqlite3; p=r'database\tracker.db'; c=sqlite3.connect('file:'+p+'?mode=ro',uri=True); print(c.execute('pragma integrity_check').fetchone()[0]); print(c.execute('pragma foreign_key_check').fetchall()); print({t:c.execute('select count(1) from '+t).fetchone()[0] for t in ('products','reviews','review_snapshots','review_changes')})"
```

Expected current result: `ok`, no foreign-key rows, and counts `41 / 436 / 35 / 0`.

## Manual collector execution

These entrypoints exist and their CLI parsers were verified, but they perform network access and write run artifacts. They are not read-only and require an explicit user request to run the Weekly Review:

Create only a new run-local frozen scope:

```powershell
& $Python -c "from pathlib import Path; from modules.review_tracker.scope import build_frozen_scope; build_frozen_scope(Path('config/listing_master.xlsx'), Path(r'<RUN_DIR>'), '<RUN_ID>', '<YYYY-MM-DD>')"
```

The existing function writes `listing_sources.json` and `scope_manifest.json` immutably and refuses to replace different content at the same paths.

Build a run-local scope diff against the chosen previous successful run:

```powershell
& $Python -c "from pathlib import Path; from modules.review_tracker.scope import read_json,diff_scopes,write_json_atomic; run=Path(r'<RUN_DIR>'); prior=Path(r'<PRIOR_RUN_DIR>'); write_json_atomic(run/'scope_diff.json', diff_scopes(read_json(run/'listing_sources.json'), read_json(prior/'listing_sources.json')))"
```

```powershell
& $Python scripts\run_review_tracker_bv.py --run-dir <RUN_DIR>
& $Python scripts\run_review_tracker_walmart_bv.py --run-dir <RUN_DIR>
```

The run directory must already contain the frozen `listing_sources.json`. THD and Lowe's also require retained `raw/bv_config` files from the approved prior successful source. Do not invent or fetch private configuration.

After supervised Walmart storefront evidence exists, the existing manual merge is:

```powershell
& $Python scripts\build_walmart_review_input.py --run-dir <RUN_DIR> --prior-run-dir <PRIOR_SUCCESSFUL_RUN_DIR>
```

## Output generation

Local report-data merge:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_biweekly_report_data.ps1 -RunDir <RUN_DIR>
```

Scope-aware comparison:

```powershell
& $Python scripts\build_review_period_comparison.py `
  --current-summary <RUN_DIR>\review_summary.json `
  --prior-summary <PRIOR_RUN_DIR>\review_summary.json `
  --current-reviews <RUN_DIR>\low_star_reviews.json `
  --current-date <YYYY-MM-DD> `
  --prior-date <YYYY-MM-DD> `
  --current-scope <RUN_DIR>\listing_sources.json `
  --prior-scope <PRIOR_RUN_DIR>\listing_sources.json `
  --scope-diff <RUN_DIR>\scope_diff.json `
  --output <RUN_DIR>\period_comparison.json
```

Do not run `scripts/run_weekly_review_tracker.ps1 -Mode Production`, `update_archive_portal.ps1`, the Scheduler registrar, Git publication, or notification as part of ordinary manual operation. Those paths are approval-gated or closed.

# Known Technical Debt

These are constraints, not an automatically authorized backlog:

### Review DB incremental persistence contract

Not completed.

### Listing Master vs DB monitoring ownership

Not unified.

### Production auto-publish and dirty-worktree interaction

Unsafe.

### Hermes automated weekly execution

Not production validated.

### Complete Review identity comparison

Only partial or date-based low-star comparison exists; full all-Review new/updated/unchanged classification is not implemented.

### Walmart merge and Review-ID propagation

The manual merge is not wired into the orchestrator, and final merged low-star rows drop the raw Walmart Review ID.

# If Automation Is Ever Reopened

Do not proceed unless all conditions are met:

1. Canonical Review-scope ownership is resolved.
2. Production incremental DB write is implemented.
3. Idempotent deduplication is verified.
4. Publishing is safe with a dirty or pre-staged worktree.
5. A safe non-dispatchable task-registration state exists.
6. `REGISTER` is proven not to equal `DISPATCH`.
7. One supervised Hermes production run passes.
8. Duplicate-report-date protection is runtime-verified.
9. Duplicate notification is prevented and verified.
10. The user explicitly authorizes reopening automation.

# Glossary

- **Listing Master**: `config/listing_master.xlsx`, the live shared Listing configuration.
- **Review DB**: `database/tracker.db`, the SQLite historical store.
- **Review Scope**: rows where `active` and `monitor_review` are both true.
- **Collector**: platform-specific code that obtains current public Review evidence.
- **Snapshot**: per-Listing Review statistics for a run.
- **Review Change**: an auditable, comparable change record; currently no production rows exist.
- **Evidence**: source URL, raw file, or screenshot plus run context and hash where produced.
- **Gateway**: Hermes service that watches and dispatches Kanban work.
- **Hermes**: the attempted orchestration owner; not the current operating path.
- **Weekly Run**: one date-bounded Review collection and comparison.
- **Manual Weekly Operation**: human-initiated, stepwise execution with explicit gates and no Scheduler.
- **VALID**: current evidence obtained and reconciled.
- **VERIFICATION_REQUIRED**: current validation is blocked pending human verification.
- **ACCESS_BLOCKED**: platform access is blocked; no bypass is permitted.
- **DATA_UNAVAILABLE_CURRENT**: no valid current data is available.
- **PARTIAL**: only some required current fields or evidence are valid.

# For the Next Agent

> If the user asks to run the Weekly Review, do not redesign the system.

1. Read Listing Master.
2. Resolve the current 35-or-current scope from `active AND monitor_review`.
3. Read the current Review DB and history without modifying them.
4. Run only the existing manual Review workflow after explicit collection authorization.
5. Compare current evidence against the previous successful comparable run and historical evidence.
6. Surface new, low-star, and actionable Reviews only when identity and evidence support the claim.
7. Preserve raw evidence, scope, hashes, statuses, and platform limitations.
8. Do not touch automation unless the user explicitly reopens it.

> Prefer the simplest reliable weekly workflow over rebuilding automation.
