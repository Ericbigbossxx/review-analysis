# US Local Channel Listing Tracker

One governed project for public US retail Listing monitoring and Review tracking across Walmart US, Home Depot, and Lowe's.

## Phase 0 status

`READY_FOR_MIGRATION_REVIEW`

Phase 0 audited the existing review-analysis workspace and added a target architecture, a blank unified Listing Master, and a SQLite schema/migration. It deliberately does **not** run collection, create scheduled jobs, migrate historical review data, or modify published reports.

## Modules

- `modules/listing_monitor/`: price, promotion, rating, count, inventory, delivery, seller, page state, rank, sponsored placement, and daily changes.
- `modules/review_tracker/`: public review snapshots, newly observed reviews, review metadata, changes, and negative-theme analysis.

## Key paths

- [Listing Master](config/listing_master.xlsx): editable configuration template; intentionally contains headers only.
- [Platform collection rules](docs/platform_collection_rules.md): access and evidence boundaries.
- [Data dictionary](docs/data_dictionary.md): configuration and database definitions.
- [Schema](database/schema.sql): canonical SQLite DDL.
- [Phase 0 audit](reports/phase0_existing_asset_audit.md): inventory and reuse assessment.
- [Migration plan](reports/phase0_migration_plan.md): approval-gated mapping; no data has moved.

## Applying the database schema after approval

After approval, run `scripts/apply_initial_schema.py database/tracker.db --approve`; it applies the canonical DDL and records `0001_initial_schema` in the same SQLite transaction boundary. The database file is not initialized in Phase 0 so that no collection or migration is implied.

## Historical asset protection

Existing root-level dashboards, reports, JSON, source workbooks, and the immutable `runs/` snapshot are retained in place. The proposed `data/history/` destination is a future migration target only.
