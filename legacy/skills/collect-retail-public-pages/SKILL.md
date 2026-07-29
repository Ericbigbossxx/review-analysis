---
name: collect-retail-public-pages
description: Collect, validate, and audit publicly accessible retail search results and exact product-detail pages for Walmart US, The Home Depot US, Lowe's US, Amazon US, and similar retailers. Use when Workbuddy must preserve displayed search-slot order, distinguish sponsored and organic results, validate product identity and canonical URLs, handle dynamic rendering, CAPTCHA, rate limits, ZIP-dependent results, or produce an evidence-backed retail ranking dataset without bypassing access controls.
---

# Collect Retail Public Pages

## Purpose

Create a reproducible retail-search snapshot with verifiable product-detail links. Treat access friction as an evidence and workflow problem, never as permission to defeat platform controls.

## Non-Negotiable Boundary

- Do not solve or automate CAPTCHA challenges.
- Do not spoof browser fingerprints, rotate proxies or accounts, reuse stolen sessions, conceal automation, or access non-public endpoints.
- Do not evade login, WAF, robots.txt, rate limits, geographic restrictions, or retailer terms.
- Stop the affected route when a CAPTCHA, login wall, access-denied page, or explicit automation block appears.
- A public product-page reader may validate an already-known public detail URL only when that page is independently accessible. It must not reconstruct search rank or claim to represent the blocked search page.
- Never infer rank, price, availability, specifications, or BSR from brand reputation or another platform.

## Required Inputs

Before collection, obtain or define:

- platform and country site;
- exact search keywords;
- target raw slot count and pagination limit;
- ZIP or store location;
- signed-in or unsigned session state;
- allowed official APIs, feeds, browser tools, and public-page readers;
- output directory and collection timestamp standard.

Use `N/A` for unavailable evidence. Do not silently substitute values.

## Workflow

### 1. Preflight

1. Check the retailer's current public-access rules, robots.txt, and available official API or feed.
2. Prefer an official API or retailer-provided feed when it exposes the required search order.
3. Otherwise use a visible browser with a consistent ZIP, session state, search keyword, sort state, and filter state.
4. Create a run identifier and record tool, user agent class, ZIP, session state, start time, keyword, and requested pages.
5. Define the retailer's product-detail URL pattern before accepting links.

### 2. Capture Search Slots

1. Open the public search page in a visible browser.
2. Wait for user-visible product cards, not only network idle.
3. Record every displayed product slot in page order, including sponsored slots.
4. For each raw slot, capture page number, page position, total position, title, displayed brand/model, sponsored flag, displayed price, item identifier, card URL, and screenshot reference.
5. Continue pagination until the requested raw-slot target is reached or the retailer exposes no more results.
6. Preserve the original raw capture before filtering or deduplication.

### 3. Handle Access Friction

Use this decision order:

1. **CAPTCHA, login wall, WAF, or access denied:** save URL, page title, timestamp, screenshot, and reason; stop automated collection on that route. If the operator manually completes a normal challenge, record that human action and resume only under the same session conditions.
2. **HTTP 429 or transient 5xx:** honor `Retry-After`; reduce to one request or page at a time; use bounded exponential backoff with jitter; stop after three failed retries and record the last status.
3. **Empty dynamic DOM:** confirm the visible page state, wait for a visible card selector, scroll only as a normal user would to load already-public cards, and retry once. If cards remain unavailable, mark `DYNAMIC_RENDER_UNAVAILABLE`.
4. **ZIP or store mismatch:** set the requested location through the normal site control, reload, and record the confirmed location. Do not claim a national ranking.
5. **Blocked search but known detail URLs:** validate those exact public detail pages through an allowed browser or public-page reader. Mark the evidence method separately. Do not assign or change search rank from this validation.

### 4. Normalize and Filter

1. Classify each raw slot as whole machine, accessory, service, duplicate, or uncertain.
2. Keep sponsored and organic whole-machine listings.
3. Exclude blades, garages, boundary wire, batteries, installation, replacement parts, and multi-product category pages.
4. Deduplicate by stable platform item identifier first, then canonical URL, then exact brand plus model.
5. Retain the highest displayed raw slot for duplicates and preserve all duplicate evidence in the raw file.
6. Do not remove small, unknown, or long-tail brands merely because they are unfamiliar.

### 5. Calculate Ranks

- `search_rank` is the total displayed whole-machine slot order after applying only the documented whole-machine rule. Preserve raw page positions separately.
- `organic_rank` increments only for non-sponsored valid whole-machine results.
- `sponsored` is a boolean from the page label.
- Amazon `amazon_bsr` is a separate product-detail-page field and never substitutes for search rank.
- If the visible page order cannot be captured, set rank to `N/A` and state why.

### 6. Validate Exact Product Pages

For every retained listing:

1. Open the card's exact detail URL.
2. Confirm the page is publicly accessible and not a search, category, brand, collection, or error page.
3. Confirm platform item ID when available.
4. Match brand and exact model against the page title, H1, structured data, or specification table.
5. Confirm the item is a complete mower rather than an accessory or service.
6. Remove unnecessary tracking parameters while preserving required variant or item identifiers.
7. Reopen the normalized URL and repeat the identity check.
8. Set `product_url_valid`, `product_url_status`, `product_url_error`, and `evidence_method`.

Do not accept a URL merely because it returns HTTP 200.

### 7. Apply Platform Rules

Read [platform-playbook.md](references/platform-playbook.md) before collecting any of the four supported retailers.

### 8. Produce Evidence

Use the fields and status taxonomy in [evidence-schema.md](references/evidence-schema.md).

Produce:

- immutable raw slot capture;
- normalized deduplicated listing table;
- product-page validation table;
- run log with blocks, retries, manual actions, and location state;
- screenshots for first page, pagination boundary, and any blocking page;
- acceptance summary by platform.

## Acceptance Gates

For each platform, report:

- requested and actually scanned raw slots;
- valid whole-machine slots;
- deduplicated products;
- sponsored products;
- long-tail brands;
- valid detail-page URLs;
- failed or blocked URLs;
- missing search ranks;
- failed pages and exact reasons.

Do not claim completion if any critical row lacks a confirmed detail URL or displayed rank. A blocked platform remains `LIMITED-SCOPE` unless the stated deliverable explicitly permits missing evidence.

## Final Response Rules

- Lead with what was actually verified.
- Separate search-page evidence from detail-page evidence.
- Name every platform, URL, and reason that was blocked or incomplete.
- State collection time, ZIP, session state, sort state, filter state, and evidence method.
- Never describe this workflow as bypassing anti-bot controls.
