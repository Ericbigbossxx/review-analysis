# WEEKLY REVIEW RESULT — 2026-09-03

**Run**: `runs/2026-09-03-weekly-review-analysis`(手动、授权执行)
**对比**: vs 成功上期 2026-08-21
**Scope**: 35 → **30 Listings**(Walmart 10 / THD 10 / Lowe's 10;经 9.3 产品清单变更,commit `cadf920`)
**状态**: 数据链路完整;**报告处停止**(未写 DB、未发布、未通知)

---

## 1. 范围与采集结果

| 平台 | Scope | 采集成功 | Storefront | 可用 |
|---|---|---|---|---|
| THD | 10 | 10/10 BV (failed 0) | n/a | 10 |
| Lowe's | 10 | 10/10 BV (failed 0) | n/a | 10 |
| Walmart | 10 | 10/10 aux feed (failed 0) | **10/10 AVAILABLE** (CDP 受控) | 10 |
| **合计** | **30** | **30/30** | | **30/30** |

- Scope 变化: **CONTINUING 4 / LINK_CHANGED 8 / NEW_TO_SCOPE 18 / REMOVED_FROM_SCOPE 23**(scope_diff.json)
- 18 个新增 SKU 首次观察(基线);23 个移除项不再监控(master 保留、`monitor_review=FALSE`)
- Walmart storefront 本轮无 Robot Check(受控 profile 干净、逐 SKU 低频)

## 2. 汇总统计(30 全可用)

- **总评论 1,957** | 低星(1-3★) **502 (25.7%)** | 可读低星 412 | ratings-only 55(另有 33 无文本明细计入)
- 分平台:
  - THD: 1,009 总 / 268 低星 (26.6%)
  - Lowe's: 541 总 / 142 低星 (26.2%)
  - Walmart: 407 总 / 92 低星 (22.6%)
- **可比集(12 SKU, 同源口径)**: 899 总 / 242 低星 (26.9%) — 上期可比 1,142 / 238 (20.8%)
  - 低星率上升 +6.1pp,主要受 Walmart 可比项总评减少(分母缩)影响,非低星绝对数激增(低星 +4)

## 3. 本期新增低星评论(2026-08-21 之后, identity 级确认 5 条)

| # | 平台 | SKU | 日期 | 星级 | 标题/摘要 | 严重度 |
|---|---|---|---|---|---|---|
| 1 | THD | WBP52TS | 08-29 | 1★ | "Absolute garbage" — 油箱垫圈+化油器垫圈一开始就坏,漏油;自送线不送线;保修称引擎没坏不受理 | **高** |
| 2 | Lowe's | WB20VTRSBL | 09-02 | 1★ | "weak" — 2 电池不够用;电量低时变弱;转头当修边机时完全不出线,每 20 秒要手动拉线 | **高** |
| 3 | THD | WBP52TS | 08-26 | 2★ | 应附赠 extra spool,实际没给 | 低 |
| 4 | Lowe's | WBP52BCI | 08-24 | 3★ | 说明书不清、附带多余零件反有害;装配视频误导;对 5 年延保没信心 | 中 |
| 5 | Walmart | WB20VTAB | 08-30 | 3★ | "Okay, but has weak power." | 中 |

- 另识别 210 条「身份级相对上期新增」多为 **18 个新 SKU 的历史评论**(首次覆盖),非新增;已按日期过滤,不重复计入
- 去重: THD/Lowe's `(sku,sourceReviewId)` **0 重复**;Walmart `(sku,id)`(权威 walmart_raw)**0 重复**

## 4. 跨平台主题

- **WBP52TS 集中投诉**(THD): 油箱/化油器垫圈漏油、自送线失效、保修口径差 → 高优先跟进
- **打草机出线/供线问题**反复出现: WB20VTRSBL(Lowe's)、WB26BCI(THD 多条历史 1★) — 设计与装配体验差
- 新增 Sunseeker 机器人 THD ORIONX7/SKRMX5 已有历史低星(1★: 保修维修等待长、障碍避让差;2★: app 控制问题) — 首次基线,持续观察

## 5. 数据质量与限制

- Walmart feed 全部 EXACT cross-validation(storefront↔feed 文本数一致);2 个 SKU(WB40VCOMBO、WBP31TS)feed total=0(页面新上/评论未同步),如实保留,不置零
- **Walmart 6 个可比项总评论下降**(WB20V16LM 98→46、WB20VTAB 331→209 等): 同源 feed 口径真实下降,低星绝对数平稳(16/16、45/46);判断为评论被平台迁移/下架所致,非采集缺失(可用率 100%)
- 合并 `low_star_reviews.json` 的 Walmart 行仍缺 `sourceReviewId`(历史已知传播缺口);identity 校验基于权威 `walmart_raw.json`
- 报告用 summary 层 low-star 计数(502)与可读文本行(480)存在口径差(部分行仅 rating 无明细),已分别注明
- 新增行 product_line 由关键词推断(如 THD ORIONX7 标 Robotic Lawn Mower),不影响采集

## 6. 建议跟进

1. **THD WBP52TS 质量事件**(漏油/垫圈): 建议运营/品控复核近期批次与保修话术
2. **WB20VTRSBL 出线缺陷**(Lowe's 09-02): 留意同型号多平台反馈是否上升
3. 新增 SKU(尤其 THD 机器人 3 款、Lowe's 2 款 snow blower)为**首次基线**,下期起可做真实 delta
4. Walmart 6 个可比项总评下降: 建议抽查商品页确认评论迁移/合并状态

---
*证据文件: listing_sources.json / scope_manifest.json / scope_diff.json / walmart_storefront_current.json / walmart_raw.json / review_summary.json / low_star_reviews.json / period_comparison.json / qa 相关 json 均在本 run 目录。*
