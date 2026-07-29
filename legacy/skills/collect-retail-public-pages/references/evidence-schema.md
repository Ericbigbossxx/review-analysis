# Evidence Schema

## Run-Level Fields

| Field | Meaning |
|---|---|
| run_id | Stable identifier for the collection run |
| platform | Retailer and country site |
| search_keyword | Exact submitted search text |
| search_url | Public search page URL |
| zip_or_store | Confirmed location context |
| session_state | Signed in, unsigned, new, or reused |
| sort_state | Displayed sort state |
| filters_applied | Boolean plus filter details |
| collection_time_utc | ISO 8601 timestamp |
| evidence_method | Browser, official API/feed, public page reader, or manual verification |
| run_status | PASS, LIMITED_SCOPE, or BLOCKED |
| block_reason | Exact CAPTCHA, access, render, rate, or location issue |

## Raw Slot Fields

| Field | Meaning |
|---|---|
| page_number | Search page number |
| page_raw_position | Position on that page |
| total_raw_position | Position across captured pages |
| card_title | Full visible card title |
| displayed_brand | Brand shown on card |
| displayed_model | Model shown on card |
| sponsored | True or False from page label |
| displayed_price | Price shown on search card |
| platform_item_id | SKU, item ID, product ID, or ASIN |
| card_url | Original card href |
| screenshot_evidence | Screenshot filename or reference |
| raw_classification | whole_machine, accessory, service, duplicate, or uncertain |
| classification_reason | Evidence for the classification |

## Normalized Listing Fields

At minimum retain:

`platform`, `search_keyword`, `search_rank`, `organic_rank`, `sponsored`, `brand`, `model`, `full_title`, `current_price`, `list_price`, `discount_amount`, `discount_percent`, `coupon`, `deal_type`, `new_product`, `coverage_acre`, `coverage_sqft`, `navigation_type`, `wire_free`, `rtk`, `lidar`, `vision`, `awd`, `max_slope_percent`, `cutting_width_inch`, `cutting_height_min_inch`, `cutting_height_max_inch`, `rating`, `review_count`, `amazon_bsr`, `product_url`, `product_url_valid`, `product_url_status`, `product_url_error`, `availability`, `collection_time`, `source_page`, `platform_item_id`, `evidence_method`.

Use `N/A` for unconfirmed values.

## Product URL Status Taxonomy

| Status | Use when |
|---|---|
| VALID | Public detail page opens and exact identity matches |
| NOT_LISTED | Platform search and reasonable platform checks found no listing |
| BLOCKED_CAPTCHA | CAPTCHA prevents validation |
| BLOCKED_ACCESS | Login, WAF, geographic, or explicit access denial |
| RATE_LIMITED | HTTP 429 persists after bounded retries |
| TRANSIENT_ERROR | 5xx or temporary network failure persists |
| DYNAMIC_RENDER_UNAVAILABLE | Visible product cards or page identity cannot be extracted |
| SEARCH_OR_CATEGORY_URL | URL is not a unique detail page |
| MODEL_MISMATCH | Page is for another model or variant |
| ACCESSORY_OR_SERVICE | Page is not a complete machine |
| NOT_FOUND | Confirmed 404, removed, or unavailable page |
| MANUAL_REVIEW | Evidence is conflicting or insufficient |

## Validity Rule

Set `product_url_valid=True` only when:

1. the normalized URL is a unique product-detail page;
2. it is publicly accessible through an allowed method;
3. platform item ID or exact model identity matches;
4. the item is a complete machine;
5. the normalized URL reopens successfully.

Otherwise set `False` and populate both status and error.

## Rank Rule

- `search_rank`: visible total valid whole-machine order, including sponsored items.
- `organic_rank`: visible valid whole-machine order excluding sponsored items.
- Store raw positions separately so the calculation remains auditable.
- Never assign a rank from a product detail page, BSR, recommendation module, sales estimate, or external search result.
