# WEEKLY REVIEW RESULT — 2026-09-20

**Run:** `runs/2026-09-20-weekly-review-analysis/`
**Prior successful run:** `2026-09-10` (30-listing scope)
**Mode:** `MANUAL_WEEKLY_OPERATION` — collection + analysis only. No DB write, no `outputs/latest` promotion, no archive/publish, no notification, no scheduler change.

---

## 1. Scope (frozen)

| Platform | Listings |
|---|---|
| THD | 10 |
| Lowes | 10 |
| Walmart | 10 |
| **Total** | **30** |

- `scope_hash` `4283b4ef…`; `scope_diff` = **CONTINUING 30 / NEW 0 / REMOVED 0 / LINK_CHANGED 0 / RECORD_IDENTITY_CHANGED 0**.
- Source of truth `config/listing_master.xlsx` hash `a084716b…` — unchanged from the 09-10 baseline.
- `PREFLIGHT_PASSED` (run against the frozen manifest, not before it).

## 2. Collection

| Collector | Result |
|---|---|
| THD + Lowe's BV (`run_review_tracker_bv.py`) | 20/20 listings, `failed: 0`, 415 low-star rows |
| Walmart aux feed (`run_review_tracker_walmart_bv.py`) | 10/10 listings, `failed: 0`, 420 ratings rows |
| Walmart storefront (CDP worker, 1 SKU/run, `--delay-ms 12000`) | **10/10 AVAILABLE, 0 challenges** |

The formerly risk-flagged controlled profile (`browser_profile/walmart`) again started clean via the launcher and completed all 10 SKUs with zero Robot Check — consistent with 09-03/09-10.

## 3. Headline comparison vs 2026-09-10

| Metric | 2026-09-10 | 2026-09-20 | Δ |
|---|---|---|---|
| Total ratings | 1,967 | **1,979** | +12 |
| Low-star (1–3★) | 504 | **509** | +5 |
| Low-star rate | 25.62% | **25.72%** | +0.10 pt |
| Merged low-star rows | 482 | 487 | +5 |
| — readable (title or text) | 412 | **416** | +4 |
| — text-less (`ratingsOnly`) | 70 | 71 | +1 |
| **New readable low-star** | — | **4** | — |

Per platform (merged low-star rows, readable): THD 272 (226) / Lowes 143 (118) / Walmart 72 (72).

**Reconciliation of the summary-vs-detail gap:** `review_summary.json` low-star = 509, merged detail rows = 487. The 22-row gap is **entirely Walmart** (summary 94 vs merged 72): the merged file is a text-only subset for Walmart, so feed rows with zero low-star *text* are dropped. THD/Lowe's carry all their low-star rows including text-less ones (flagged `ratingsOnly`). This is the known, expected shape — not data loss.

**Carry-forward effect on the headline:** the two identity-compromised SKUs (§7) report prior-period values, which is why total ratings move +12 rather than the +15 the raw live feeds would have produced. Low-star and new-review counts are unaffected.

## 4. New readable low-star reviews (4)

Every year-to-date figure below is verified by identity anti-join **and** a date filter (`> 2026-09-10`), per the skill's false-positive rule.

| Platform | SKU | Date | ★ | Review ID | Complaint |
|---|---|---|---|---|---|
| Lowes | WB26BCI | 2026-09-16 | 1 | 271997173 | Trimmer head (bump/spool) disintegrated after one season; warranty claim filed inside the 3-year window |
| THD | WB31CCED | 2026-09-14 | 1 | 306595631 | "Doesn't start" — brand new unit will not start |
| Walmart | WB40V18PLM | 2026-09-17 | 1 | 440941646 | Delivered with **no screws/bolts/washers** — unit cannot be assembled; awaiting seller |
| Walmart | WB40V18PLM | 2026-09-16 | 1 | 440811134 | Delivered to the wrong address (no title) |

Anti-join hygiene: THD/Lowe's raw anti-join produced 3 hits → **2** after the date filter; Walmart produced 2 → **2**. No old reviews resurfaced as new this run.

## 5. Cross-platform themes

Overall low-star themes: **启动/动力故障 120**, 客服/履约 81, 割草/修剪效果 66, 质量/耐久 52, 电池/充电 49, 重量/人体工学 27, APP/导航/连接 8, 其他 13, (no text) 71.

- **启动/动力故障 is a THD/Lowe's gas-tool problem** — THD 87, Lowes 27, but only 6 on Walmart. Concentrated in the 26cc/52cc gas platforms.
- **电池/充电 is the Walmart signature** — 28 of Walmart's 72 rows (vs 49 platform-wide), i.e. the 20V/40V cordless line.
- 客服/履约 is the second-largest theme everywhere (81 platform-wide) — a shared service concern, not a product one.

## 6. P0 clusters

| SKU | Ratings | Low | Rate | Δ low vs 09-10 | Dominant theme |
|---|---|---|---|---|---|
| Lowes WB31CCED | 12 | 7 | 58.3% | 0 | 启动/动力故障 |
| Lowes WBP52BCI | 28 | 15 | 53.6% | 0 | 客服/履约 |
| THD SKRMX3PLUS | 6 | 4 | 66.7% | 0 | 割草/修剪效果 (new-product watch) |
| THD ORIONX7 | 5 | 2 | 40.0% | 0 | 客服/履约 (new-product watch) |
| Walmart WB20V16LM | 46 | 16 | 34.8% | 0 | 电池/充电 |
| THD WBP52BCI | 407 | 124 | 30.5% | 0 | 启动/动力故障 (47) |
| Lowes WB26BCI | 116 | 34 | 29.3% | **+1** | 启动/动力故障 |
| THD WB26BCI | 522 | 125 | 23.9% | 0 | 启动/动力故障 (38) |
| Lowes WBPMT26P | 134 | 36 | 26.9% | 0 | 客服/履约 (10) |
| Lowes WB40V18PLM | 131 | 32 | 24.4% | 0 | 电池/充电 (15) |
| Walmart WB20VTAB | 212 | 46 | 21.7% | 0 | 电池/充电 (13) |
| Walmart WB40V18PLM | 61 | 13 | 21.3% | **+2** | 电池/充电 (6) |

**Movement is almost entirely flat.** The whole week produced +5 low-star ratings; the only P0 cluster that genuinely grew is **Walmart WB40V18PLM (+2 low-star, +4 ratings)** — driven by the two new 1★ reviews above, both fulfilment/assembly defects (missing hardware, mis-delivery), not product performance. That is a packaging/3PL issue and the cheapest thing on this page to fix.

## 7. Identity anomalies — 2 SKUs (carried forward per your ruling)

Your ruling: **"那个Walmart的问题，沿用上一期的数据就行，现在是产品unpublish了，所以被重新定位。"** — carry forward the prior period's data. Applied at the storefront row, then both sanctioned builders were re-run so nothing downstream is hand-edited. Both rows now read `status` / `availabilityStatus` = `CARRY_FORWARD_PRIOR_PERIOD`, and **no value from either foreign page is attributed to its SKU** (the TNTANTS brand greps to 0 across all three outputs).

Both are cases where the frozen `itemId` did **not** equal the id in the page's final URL, while `scope_diff` reports `LINK_CHANGED: 0` (the workbook URL is unchanged — the platform-side target moved, so the diff cannot catch it).

**WB40VCOMBO — recurring (2nd consecutive run).** Frozen `/ip/17598657653` again served TNTANTS itemId `15830216038` (3.7★ / 1,029 ratings / 336 reviews, up from 983/314 — a live foreign listing). Carried forward from 2026-09-10 → **0 reviews / 0 ratings / null average**, matching the 09-10 handling. Its values remain the 2026-09-03 baseline, unchanged for a third period. Numeric impact: **none**. → `decisions/2026-09-20_WB40VCOMBO_carry_forward.json`

**WB20VTRSBL — new this run.** Frozen `/ip/5629858326` redirected to `864525478`, which is **WB20VTAB's own frozen itemId** — a cross-SKU collision. Landing was identical across two independent worker runs 20 minutes apart, and the same URL resolved correctly on 09-03 and 09-10, so it is platform-side, not a transient read. Carried forward from 2026-09-10 → **59 ratings / 4.1★ / 43 with text**. The live feed had reported 62; the 3-rating difference is the carry-forward effect. **WB20VTAB itself verified normally under its own itemId — the two SKUs' figures are deliberately not merged.** → `decisions/2026-09-20_WB20VTRSBL_carry_forward.json`

Under this ruling the workbook URL is **not** changed and neither listing is marked inactive — the ruling constrains the run's data only. The underlying URL/identity question therefore remains **deferred, not resolved** (§10.1).

## 8. Data-quality checks

- **Dedupe acceptance — both identity keys = 0 duplicates:** THD/Lowe's `(platform, sku, sourceReviewId)` over 415 raw rows → **0**; Walmart `(sku, id)` over 72 raw reviews → **0**. No null identity keys in either key set. (Checked on the source files — the merged `low_star_reviews.json` is a projection that drops `sourceReviewId`, so it cannot be used for this check.)
- **`ratingsOnly` flag undercounts text-less rows by 13.** Measured two ways over the 487 merged rows: by content (no non-blank `title` **and** no non-blank `text`) = **71** text-less (THD 46 / Lowes 25); by the `ratingsOnly` boolean = **58** (THD 46 / Lowes 12). The 13-row difference is **entirely** Lowes rows whose flag is `false` despite carrying no text. Both numbers are given rather than picking one; **§5's theme counts exclude all 71**, since an unclassified row contributes nothing to a theme regardless of its flag.
- **Storefront `pageTotalReviews` / `pageTotalRatings` remain unreliable and were excluded from every delta.** Ratio-swap (reviews > ratings) hit **WB40V18PLM (2,637 vs 115)** and **WB40VTBCC (330 vs 30)** this run — a *different* set of SKUs than 09-10's (WB20VCOMBODP, WB20VTRSBL, WB40VTBCC), which confirms the field is nondeterministically broken rather than SKU-specific. Flagged per row as `pageTotalsRatioSwap`. The trustworthy storefront signal remains text-count cross-validated against the aux feed.
- **No TNTANTS contamination** in any output (`review_summary.json`, `low_star_reviews.json`, `walmart_raw.json` all grep to 0).
- Known limitation carried forward: `build_walmart_review_input.py:113` hardcodes `comparison.priorReportDate = "2026-07-23"`. Values are correct; the date label is wrong and is **not quoted** here.

## 9. Database — verified unchanged

| Check | Baseline (09-10) | Now |
|---|---|---|
| `database/tracker.db` SHA-256 | `ef625f44…` | **`ef625f444f523b4e315e6b1d4285448c0a559d6eadd26f453d59aee22f9c6e3a`** |
| products / reviews / review_snapshots / review_changes | 41 / 436 / 35 / 0 | **41 / 436 / 35 / 0** |
| `integrity_check` / FK errors | ok / 0 | **ok / 0** |
| New `collection_runs` rows for this run | — | **0** |
| `runtime/review_tracker.lock`, `data/run.lock` | absent | **absent** |

The run wrote no formal History, promoted nothing to `outputs/latest`, and touched no scheduler or external system.

## 10. Follow-up

1. **WB40VCOMBO / WB20VTRSBL URL decision (deferred, needs you).** Both listing URLs have now served the wrong target while the master URL is unchanged. `/ip/17598657653` has failed two runs straight; `/ip/5629858326` collides with another monitored SKU. This run's data is carried forward and honest, but the listing itself is now producing no usable current signal — a workbook URL/scope decision is required outside this run. **The question is open, not resolved.**
2. **Walmart WB40V18PLM fulfilment defect** — two 1★ reviews in one week for missing hardware and mis-delivery. Worth a 3PL/packaging check, not a product change.
3. **启动/动力故障 on THD/Lowe's gas platforms** remains the largest single theme (120 rows) and is essentially unchanged for a third consecutive run.
4. **71 text-less low-star rows** (THD 46 / Lowes 25) stay unclassifiable by theme; excluding them understates every theme count above and is stated rather than silently dropped.
