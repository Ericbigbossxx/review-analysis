# Platform Playbook

Use these rules in addition to the main workflow. Retail sites change frequently; verify current public behavior at run time.

## Walmart US

- Use the visible public search page first and preserve displayed card order.
- Record sponsored labels exactly as shown.
- Product pages normally contain a stable `/ip/` item identifier. Keep that identifier in the canonical URL.
- If the browser shows `Robot or human?`, a CAPTCHA, or a blocked URL, save the evidence and stop automated search collection.
- An allowed public product-page reader may confirm an already-known `/ip/` page's title, H1, and item identity. Label this `PUBLIC_PRODUCT_PAGE_READER_AFTER_BROWSER_BLOCK`.
- Detail-page validation does not provide search rank. Keep the previously captured rank only if it came from an earlier timestamped search-page capture; otherwise use `N/A`.

## The Home Depot US

- Use the public search or robotic-mower category page only when its product grid order is visible.
- Normal detail pages contain `/p/` and a numeric product identifier.
- Recommendation carousels, recently viewed products, and promoted modules outside the main result grid are not search slots.
- Record ZIP/store because price, inventory, and sometimes result order vary by location.
- Prefer the platform specification table or manufacturer page for technical attributes.

## Lowe's US

- Use a new or consistent unsigned session and a fixed ZIP.
- Record the page's initial order without manually applying sort or filters unless the requested methodology says otherwise.
- For the Sunseeker project, the proven method was `DEFAULT_ORGANIC_INITIAL_ORDER`, ZIP `10001`, keyword `robotic lawn mower`, two pages, no manual sort or filters.
- Preserve all raw positions. Sponsored whole mowers remain in raw evidence but do not receive an organic rank.
- Exclude non-whole mowers before calculating the filtered organic rank.
- Normal detail pages contain `/pd/` and a stable item identifier.
- Label ranks as ZIP-, date-, keyword-, session-, and initial-order-dependent.

## Amazon US

- Use the visible search results page and record each result card's displayed order.
- Retain the ASIN and normalize accepted detail URLs to a direct `/dp/{ASIN}` form when possible.
- Sponsored status comes only from the visible `Sponsored` label.
- If the browser-visible DOM exposes no result cards, mark `DYNAMIC_RENDER_UNAVAILABLE`; do not infer rank from best-seller pages, recommendations, or external search engines.
- Collect BSR only when it is explicitly confirmed on the product detail page or another authoritative Amazon product-data source.
- Store BSR separately from search rank and include its category context when available.

## Cross-Platform Retry Limits

- Concurrency: one active browser page or request per retailer by default.
- Transient failures: maximum three retries.
- Backoff example: 5 seconds, 15 seconds, 45 seconds, with small random jitter and `Retry-After` taking precedence.
- CAPTCHA, login, WAF, or explicit access denial: zero automated retries on the same route until a human reviews the block.
- Never rotate identity, IP address, account, or browser fingerprint to continue a blocked run.
