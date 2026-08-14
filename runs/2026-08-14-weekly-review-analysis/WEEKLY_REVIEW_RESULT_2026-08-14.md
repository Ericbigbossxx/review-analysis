# WEEKLY REVIEW RESULT — 2026-08-14

> 运行模式: MANUAL_WEEKLY_OPERATION（受控手动链路，Step 0-6）
> 仅本地分析：无 DB 写入、无归档发布、无 Git 发布、无通知（Step 7 门禁未授权）

## Overview

- **Scope**: 35 Listings（Walmart 15 / THD 10 / Lowe's 10），与 Listing Master 实时解析一致；与上一成功 run（2026-08-06）scope 完全一致（0 新增 / 0 移除 / 0 链接变更 / 0 身份变更）
- **成功检查**: THD 10/10 ✅、Lowe's 10/10 ✅、Walmart 辅助 feed 15/15 ✅；Walmart storefront **人工验证 5/15 通过**（ORIONX7、SKRMS4、SKRMV3、WB20VTAB、WB26MTSE，均为真实商品页读取、零拦截）
- **平台限制**: Walmart storefront 剩余 10 个 Listing 被 Robot Check 拦截（"Robot or human?" 验证页），按规则立即停止，未绕过、未重试；即使人工验证通过后快速连续导航仍会重新触发。受控 profile `browser_profile/walmart`（08-04 起用）已被 Walmart 风控标记（10/10 全拦截），已停用。Walmart 侧结论基于**本期实采的辅助 Bazaarvoice feed**（`walmart_bv_raw.json`，15/15 成功、470 条评论 / 103 条低星）+ 5 个已验证 storefront 统计；未验证的 10 个 SKU 标记 `VERIFICATION_REQUIRED`（stats 不伪造，回退辅助 feed 数据）
- **New Reviews（身份级反查）**: THD/Lowe's 6 条新身份（3 条可读 + 3 条 ratings-only）；Walmart 2 条新身份（1 条可读 + 1 条旧评论差异）
- **New low-star Reviews（可读）**: 4 条（3 条 1★ + 1 条 3★）
- **Critical issues**: 无 P0 级新证据；Walmart 10 个 Listing storefront 仍不可验证是本期最大限制

## 新增可读低星评论（身份反查，证据齐全）

### THD

| SKU | Rating | Review date | Key complaint | Severity | Evidence |
|---|---|---|---|---|---|
| WBP31BCF | 1★ | 2026-08-10 | "Waste of money"：商用草坪维护从业者，使用一次后线轴间歇性出线异常；"$100 plus to trim my home one time" | P1（单条，启动/动力故障） | THD 311424784, reviewId 305582246 |
| WBP52TS | 1★ | 2026-08-10 | "No spark after 6 months of use"：使用数月后无火花，被评价为质量/耐久问题，建议改买电动 | P1（单条，质量/耐久） | THD 342971888, reviewId 305591869 |
| WBP31TS | 2★ | 2026-08-05 | "Has difficulty starting"：多次尝试无法启动，次日才启动成功 | P2（单条，启动/动力故障） | THD 342971818, reviewId 305283160 |

*另 3 条新身份为 ratings-only（无文字）：WBBPBL43 ×2（1★，08-12）、SKRMS4（3★，08-13）——仅评分无文本，不作评论分析。*

### Walmart（辅助 feed）

| SKU | Rating | Review date | Key complaint | Severity | Evidence |
|---|---|---|---|---|---|
| SKRMX3PLUS | 3★ | 2026-08-10 | "to much to change blades that often"——刀片更换频率过高 | P2（单条，割草/修剪效果） | Walmart id 435989008 |
| WB20V16LM | 1★ | 2025-06-29 | 西语评论（电池掉电快、噪音大、割草差、想退货）——**旧评论，上期采集遗漏**，非本期新增 | P2（历史差异） | Walmart id 419980860 |

### Lowe's

本期无新可读低星身份（86 条低星全部与上期身份一致或为既有评论）。

## Cross-platform Themes（仅基于本期实际文本）

- **启动/动力故障**：THD WBP31BCF（无法启动/出线异常）、WBP31TS（启动困难）——与历史高频主题一致
- **质量/耐久**：THD WBP52TS（6 个月无火花）——符合历史"早期失效"模式
- **割草/修剪效果**：Walmart SKRMX3PLUS（刀片更换频繁）
- 未发现新的跨平台主题

## Recommended Follow-up（仅证据支持的）

- **产品**：核查 THD WBP31BCF 线轴供线机构与 WBP52TS 点火系统（均为 08-10 新证据，与历史启动/动力、质量主题叠加）
- **运营**：Walmart 剩余 10 个 Listing 的 storefront 需人工低频补验证（Robot Check 解除后，每次间隔 ≥60s）；WB40VCOMBO 上期即 LISTING_PAGE_NOT_FOUND，本期未验证，需确认是否下架/迁移；受控 profile `browser_profile/walmart` 建议清除重建（已被风控标记）
- **内容**：Walmart WB20V16LM 存在西语评论，页面可评估是否补充西语描述/FAQ

## 数据与证据

- Run 目录: `runs/2026-08-14-weekly-review-analysis/`（含 scope 冻结、raw 证据、汇总、对比、去重）
- 汇总: 35 rows / 1845 总评分 / 458 低星 / 低星率 24.8%（可比口径 25 listings：+91 总评 / -16 低星 / 低星率 -2.2pp；Walmart 10 个 VERIFICATION_REQUIRED 不纳入可比，不伪造）
- 去重: THD/Lowe's `(sku, sourceReviewId)` 400 唯一；Walmart `(sku, id)` 103 唯一 → **duplicate=0** ✅
- Preflight: `PREFLIGHT_PASSED`（16/16 检查）；DB 未写入（reviews 436 / snapshots 35 / changes 0 不变）
- 限制声明: 完整身份级 NEW/UPDATED/UNCHANGED 对比仅覆盖低星（1-3★）；Walmart 10 个 SKU storefront 交叉验证不可用（VERIFICATION_REQUIRED，辅助 feed 数据覆盖）；合并产物 Walmart 行不含 review id（沿用 raw feed 身份）；已验证 5 SKU 的 ratings 分布来自辅助 feed 交叉验证（页面仅确认总数）
