# WEEKLY REVIEW RESULT — 2026-08-21

> 运行模式: MANUAL_WEEKLY_OPERATION（受控手动链路，Step 0-6）
> 仅本地分析：无 DB 写入、无归档发布、无 Git 发布、无通知（Step 7 门禁未授权）

## Overview

- **Scope**: 35 Listings（Walmart 15 / THD 10 / Lowe's 10），与 Listing Master 实时解析一致；与上一成功 run（2026-08-14）scope 完全一致（0 新增 / 0 移除 / 0 链接变更 / 0 身份变更）
- **成功检查**: THD 10/10 ✅、Lowe's 10/10 ✅、Walmart 辅助 feed 15/15 ✅；Walmart storefront **CDP 后台验证 11/15 + 人工协助 1/15（ORIONX7）= 12/15 可用**（受控 profile 一次 1 链接、间隔 ≥12s，多数通过）
- **平台限制**: Walmart storefront 3 个 SKU 未获页面数据 —— SKRMV3 触发 Robot Check（`walmart.com/blocked`，按规则停止未绕过）；**WB26MTSE、WB53CULT 页面显示 "We couldn't find this page"（疑似下架/迁移，需人工确认）**。这 3 个 SKU 按既定方案用本期实采辅助 feed 统计回填（保留 VERIFICATION_REQUIRED 标签）
- **New Reviews（身份级反查）**: THD/Lowe's 2 条新可读低星（实为 1 条评论被 2 个 SKU 引用，见下）；Walmart 1 条新可读低星
- **New low-star Reviews（可读）**: 2 条唯一评论（1 条 THD/Lowe's + 1 条 Walmart）
- **Critical issues**: WB26MTSE、WB53CULT 页面 404（疑似下架），WB40VCOMBO 上期 404 本期恢复可用（5.0★/3 ratings）；Lowes 数据质量：同一条评论（id 269140977）被同时归属到 WB20V16LM 与 WB40V18PLM 两个 SKU

## 新增可读低星评论（身份反查，证据齐全）

### THD / Lowe's（Bazaarvoice）

| SKU | Rating | Review date | Key complaint | Severity | Evidence |
|---|---|---|---|---|---|
| WB20V16LM / WB40V18PLM（同一评论） | 1★ | 2026-08-17 | "Awful!!"：宣称可覆盖 1 英亩，实际 0.65 英亩就停机——功率/续航不达预期 | P1（单条，续航/动力） | Lowes reviewId **269140977**，同时出现在 WB20V16LM 与 WB40V18PLM 两个 SKU 下（同一 feed 记录，疑似串 SKU） |

*注：反查发现该评论 ID 被两个 SKU 的 feed 同时收录，按 1 条唯一评论计；这是 Lowes 端数据归属问题，需向平台核实。*

### Walmart（辅助 feed）

| SKU | Rating | Review date | Key complaint | Severity | Evidence |
|---|---|---|---|---|---|
| WB20V16LM | 3★ | 2026-08-18 | "I CAN NOT REALLY ADJUST THE HEIGHT TO FIT MY NEEDS"——割草高度调节不符合需求 | P2（单条，使用体验） | Walmart id 437338470 |

## Cross-platform Themes（仅基于本期实际文本）

- **续航/动力不达预期**：Lowes 269140977（宣称 1 英亩实际 0.65 英亩停机）——与历史"动力/续航"主题一致
- **使用体验/调节**：Walmart WB20V16LM（高度调节不便）
- 未发现新的跨平台主题

## Recommended Follow-up（仅证据支持的）

- **产品**：核查 WB20V16LM / WB40V18PLM 的续航宣传口径（新 1★ 评论直指"宣称覆盖 vs 实际停机"）
- **运营**：
  - **WB26MTSE、WB53CULT 页面 404 需人工确认**是否下架/迁移（本周 feed 仍有数据，但 storefront 页面不可见，与上期 WB40VCOMBO 情况类似）
  - WB40VCOMBO 本期页面恢复（5.0★/3 ratings），可解除"失效"标记并重立基线
  - Lowes 评论串 SKU 问题（id 269140977 同时归属两 SKU）需向平台核实，避免重复计数
- **内容**：Walmart WB20V16LM 新增 3★ 反馈高度调节不便，页面可评估补充调节说明

## 数据与证据

- Run 目录: `runs/2026-08-21-weekly-review-analysis/`（含 scope 冻结、raw 证据、CDP storefront 逐链接验证、汇总、对比、去重）
- 汇总: 35 rows / **2154 总评分 / 528 低星 / 低星率 24.5%**；可比 34 SKU（WB40VCOMBO 上期不可用）：总 2067→2154（**+87**，主要 Walmart WB20VTAB 329→331、WB20V16LM 45→98、WBPMT26P 71→119 等 storefront 口径），低星 527→528（+1）
- ⚠️ 口径说明：本期 Walmart 12 个 SKU 为 storefront 页面统计（页面 total 为主口径，星级分布来自辅助 feed 交叉验证）；3 个 VERIFICATION_REQUIRED 用本期辅助 feed 统计。上期 08-14 的 Walmart 5 个 storefront + 9 个 feed。跨期 delta 为同口径近似（页面↔页面、feed↔feed 混合），非严格同源
- 去重: THD/Lowe's `(sku, sourceReviewId)` 402 唯一；Walmart `(sku, id)` 104 唯一 → **duplicate=0** ✅（注：Lowes 存在同一 reviewId 跨 SKU 归属，属数据质量问题已标注）
- Preflight: `PREFLIGHT_PASSED`（16/16 检查）；DB 未写入（reviews 436 / snapshots 35 / changes 0 不变，collection_runs 无 review_tracker 新行）
- Storefront 验证方法: 受控 CDP profile（CDP 9224）+ `walmart_storefront_worker.js`，**一次 1 链接、间隔 ≥12s**（用户规则），遇 Robot Check 即停即报；**个人 Chrome 方案已按用户指令删除禁用**
- 限制声明: 完整身份级 NEW/UPDATED/UNCHANGED 对比仅覆盖低星（1-3★）；WB26MTSE/WB53CULT 页面 404 存疑（feed 有数据但页面不可见）；SKRMV3 人机拦截未绕过；Walmart 星级分布来自辅助 feed 交叉验证（页面仅确认总数）
