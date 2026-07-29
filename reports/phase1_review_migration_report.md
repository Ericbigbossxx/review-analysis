# Phase 1 — Review history migration report

**Source:** `runs/2026-07-23-biweekly-review-analysis/low_star_reviews.json`

| Measure | First controlled migration | Idempotence re-run |
|---|---:|---:|
| Source Review rows | 436 | 436 |
| Inserted Review rows | 436 | 0 |
| Existing rows retained | 0 | 436 |
| Duplicate source keys | 0 | 0 |
| Unmatched Listing rows | 0 | 0 |
| Missing required review fields | 0 | 0 |
| Failed rows | 0 | 0 |

All historical reviews are associated with the migrated platform Listing and retain rating, date, title, text, verified/syndicated flags, source file, source row, and migration timestamp.

The source has no confirmed universal official platform Review ID. Every imported legacy row therefore uses `platform_review_id = NULL`, `review_id_source = LEGACY_CONTENT_HASH`, `identity_confidence = LEGACY_HASH`, and a deterministic internal `legacy_review_key`. The key is used only for internal deduplication and is not presented as a platform-provided identifier.
