# Phase 1.5 — master data review summary

**Status:** `READY_FOR_USER_MASTER_REVIEW`  
**Scope:** offline review package only. No retail URL was opened, no monitoring flag was enabled, and no database business row was changed.

## Review-workbook result

`config/listing_master_user_review.xlsx` was generated with five sheets: Master Review, Field Guide, Platform Summary, Issues, and Approval Instructions. It contains 35 rows with `review_status = NOT_REVIEWED`, blank `user_decision`, and all active/monitoring fields retained as `FALSE`.

| Metric | Result |
|---|---:|
| Total Listings | 35 |
| Walmart / THD / Lowe's / Unknown | 15 / 10 / 10 / 0 |
| Completeness score 90+ | 0 |
| PARTIAL_DATA | 35 |
| Missing Listing URL | 0 |
| Missing Item ID | 0 |
| Missing primary keyword | 35 |
| Platform / URL mismatch | 0 |
| Duplicate candidate | 0 |
| Listing with historical Review Snapshot | 35 |
| Listing with migrated low-star Review detail | 26 |
| Offline issues | 106 |

The 106 issues are 35 missing models, 35 missing primary keywords, 35 missing/invalid ZIP values, and one missing historical product name. No value was inferred or filled.

## User action required

For each Listing, manually inspect the link, choose a decision, determine whether any monitor should eventually be active, provide approved keyword/ZIP/model information if applicable, add notes, and mark the row `REVIEWED`. Only a separately approved future phase may act on selected records.
