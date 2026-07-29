# Phase 0 — target architecture

**Decision:** use the current workspace as the project root. No nested project folder is created.

```
Weekly review analysis/                         # US Local Channel Listing Tracker root
├── config/                                     # unified Listing Master
├── modules/
│   ├── listing_monitor/                        # orchestrates Listing facts/change detection
│   └── review_tracker/                         # orchestrates review facts/change detection
├── platforms/{walmart,thd,lowes}/              # platform-specific parsing only
├── shared/{browser,database,matching,evidence,logging,notification}/
├── database/{schema.sql,migrations/}           # SQLite design and ordered migrations
├── data/{raw,processed,exports,history}/       # immutable/raw separated from derived outputs
├── screenshots/  logs/  scripts/  tests/  docs/  reports/
└── existing root-level report and run assets   # retained in place during Phase 0
```

## Responsibility boundaries

| Layer | Owns | Must not own |
|---|---|---|
| `modules/listing_monitor` | workflow sequence, snapshots, Listing-change detection | retailer-specific selectors/parsing |
| `modules/review_tracker` | review snapshot/detail flow and review-change detection | separate browser startup or database logic |
| `platforms/*` | visible public-page parsing and platform data normalization | shared persistence, retry, screenshots, or notifications |
| `shared/browser` | one compliant persistent-profile/session interface | CAPTCHA bypass or evasion |
| `shared/matching` | URL normalization, ID extraction, identity matching | silently choosing an ambiguous item |
| `shared/evidence`, `shared/logging` | immutable evidence paths and structured operational events | deriving unobserved business facts |
| `shared/database` | transactions, migration runner, idempotent upserts | business parsing rules |

## Data flow and idempotency

```text
Listing Master -> run context -> shared browser -> platform parser
      |                                  |               |
      +-> products (approved sync)       +-> evidence     +-> normalized observation
                                                         -> snapshots / reviews
                                                         -> comparable change records
```

- A run starts in `collection_runs` and each observation is linked by `run_id` and `record_id`.
- `UNIQUE(run_id, record_id)` prevents duplicate Listing or review snapshot rows from a retried run.
- A source review is unique by `(record_id, source_review_id)`; no synthetic historic key is accepted without approval.
- `capture_status` and `error_status` are stored even when data is unavailable. A failed or blocked operation never overwrites a prior valid baseline.

## Phase 0 implementation boundary

Only directories, docs, a blank configuration workbook, canonical schema, and migration metadata are created. No platform adapter, browser automation, notification, data synchronization, or scheduler is implemented.
