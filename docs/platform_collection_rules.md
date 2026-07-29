# Platform collection rules

These rules govern both `Listing Monitor` and `Review Tracker`. They apply to public-page observations only and must be evaluated before a collection run is marked successful.

## Common rules

- Record the source URL, observed timestamp, `record_id`, run ID, and evidence path for every usable observation.
- Use a persistent browser profile only for continuity; it is not a bypass mechanism. No proxy rotation, fingerprint spoofing, CAPTCHA solving, account cycling, non-public API calls, or inferred invisible data is permitted.
- On access denial, CAPTCHA, Robot Check, missing result cards, or unavailable content, stop the affected operation and write the explicit collection/error status. Do not reuse a prior observation as current data.
- Keep screenshots and raw evidence paths immutable for completed runs. A failed run may not overwrite a prior baseline.

## Walmart US

- Stop searching or collecting after CAPTCHA or Robot Check. Do not attempt automated resolution.
- Validate known detail pages only through allowed public-page access.
- Do not claim a natural rank unless the relevant search result cards are visible and retained as evidence.

## Lowe's

- Use the configured fixed ZIP code, logged-out session, and platform default sort.
- Record both the raw result slot and organic full-product rank when visible, plus ZIP and search-evidence path.
- Do not collect a rank after manual re-sorting or a user-adjusted search condition.

## Home Depot

- Restrict rank collection to the primary product grid.
- Exclude recommendation carousels, related products, and other non-primary search modules.
- Record region/store conditions together with the evidence.

## Evidence and review boundaries

- Reviews must retain the platform-provided review identifier when available; text analysis must use readable public review text only.
- A rating count is not evidence that review text exists. Keep rating-only and readable-text coverage distinct.
- Existing review history is read-only until its migration mapping receives human approval.
