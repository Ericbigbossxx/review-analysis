# US Local Channel Listing Tracker — Project Rules

## Scope and source of truth

- This project is **US Local Channel Listing Tracker**. `Listing Monitor` and `Review Tracker` are modules of one project, not separate projects.
- `config/listing_master.xlsx` is the unified product configuration source. Each row is one platform Listing; it must not contain invented Listings.
- `record_id` is the cross-module relationship key. Use `PLATFORM_INTERNALSKU` when it is stable; do not reuse a `record_id` across platforms.
- `listing_url` is the product-detail-page access anchor. Platform code belongs in `platforms/<platform>/`; common capabilities belong in `shared/`.
- Browser session/profile, database access, matching, evidence, logging, retry/error states, and notification are shared services. Do not copy a browser startup implementation into each module.

## Collection safety and integrity

- Do not bypass access controls, rotate proxies, spoof fingerprints, solve CAPTCHA automatically, use multiple accounts to evade controls, or call non-public APIs.
- If data is not visible, record an explicit unavailable or error state. Never infer a hidden rank or present yesterday's data as today's data.
- A first successful collection establishes a baseline only. Changes require a later comparable snapshot.
- No full collection run, scheduler, or automation may be introduced without approval. Phase 0 creates no production collection records.
- Preserve review history, prior reports, raw inputs, and evidence. Migration proposals must be approved before data movement, rewriting, or deletion.

## Platform constraints

- Walmart: stop on CAPTCHA/Robot Check; do not infer search rank when result cards are absent.
- Lowe's: fixed ZIP, logged-out session, default sort only; retain raw slot and organic whole-machine rank with evidence.
- Home Depot: use the primary product grid only; exclude recommendation modules and retain region/store conditions.

See `docs/platform_collection_rules.md` for the operative rules and `docs/data_dictionary.md` for field definitions.
