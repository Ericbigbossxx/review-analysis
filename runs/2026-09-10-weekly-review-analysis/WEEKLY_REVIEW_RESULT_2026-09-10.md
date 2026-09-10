# WEEKLY REVIEW RESULT — 2026-09-10

**Run**: `runs/2026-09-10-weekly-review-analysis`（手动、已授权执行）
**对比基线**: 成功上期 2026-09-03
**Scope**: **30 Listings**（Walmart 10 / THD 10 / Lowe's 10）
**scope_diff**: `CONTINUING 30 · NEW_TO_SCOPE 0 · REMOVED_FROM_SCOPE 0 · LINK_CHANGED 0 · RECORD_IDENTITY_CHANGED 0`
**闭环位置**: **报告处停止** — 未写 DB、未提升 `outputs/latest`、未发送通知、未创建/修改调度。**已授权执行**：证据提交 master + 报告发布 GitHub Pages（见文末）。

---

## 一、范围与采集（30/30 成功）

| 平台 | Scope | 采集成功 | 失败 | Storefront | 可用 |
|---|---|---|---|---|---|
| THD | 10 | 10/10 | 0 | n/a | 10 |
| Lowe's | 10 | 10/10 | 0 | n/a | 10 |
| Walmart | 10 | 10/10 | 0 | **10/10 AVAILABLE** | 10 |
| **合计** | **30** | **30/30** | **0** | | **30/30** |

- 预检 `PREFLIGHT_PASSED`（本次已复核重跑）；`runtime/review_tracker.lock` 不存在
- 冻结 scope = 工作簿实时 scope（30 行），与上期同口径
- THD+Lowe's BV 采集 `lowStarRows: 412`、`totalReviews: 1557`
- Walmart 辅助 feed：`totalReviews 410`（`writtenReviews 272` / `ratingsOnly 138`）
- Walmart 店面：受控 profile、逐 SKU 单次、`--delay-ms 12000`；**本轮零 CAPTCHA/Robot Check**（`challenge=false` ×10）
- 店面文本数 ↔ BV 辅助 feed：**10/10 `storefrontCrossValidation = EXACT`**

## 二、汇总（同口径 30/30 可比）

| 指标 | 本期 09-10 | 上期 09-03 | Δ |
|---|---|---|---|
| 总评论 | **1,967** | 1,957 | **+10** |
| 低星（1–3★） | **504** | 502 | **+2** |
| 低星率 | **25.62%** | 25.65% | **−0.03pp** |
| 低星明细行 | 482 | — | 有正文 412 / 无正文 70 |

| 平台 | 评论 | 低星(1–3★) | 低星率 | vs 上期 |
|---|---|---|---|---|
| THD | 1,015 | 270 | 26.6% | 1,009/268 → **+6 / +2** |
| Lowe's | 542 | 142 | 26.2% | 541/142 → **+1 / 0** |
| Walmart | 410 | 92 | 22.4% | 407/92 → **+3 / 0** |

> **本周为平稳周**：总评 +10、低星 +2、低星率 −0.03pp，无恶化。新增低星 2 条与 THD 的 +2 完全对应。

## 三、新增评论（identity 级确认：**仅 2 条，全部无正文**）

| # | 平台 | SKU | 日期 | 星级 | 正文 | Review ID |
|---|---|---|---|---|---|---|
| 1 | THD | `WB31CCED` | 2026-09-04 | 1★ | 无 | `306371136` |
| 2 | THD | `SKRMX5` | 2026-09-09 | 1★ | 无 | `306504500` |

- **`newReadableLowStarReviews = 0`（三平台均为 0）** —— 本期无新增「可读」低星，故无新增文本归因
- 跨期 anti-join（`platform+sku+sourceReviewId`）：上期 → 本期 **新增 2 / 消失 0**；上期 480 行全部保留
- Walmart 独立以权威 `walmart_bv_raw.json` 校验 `(sku, id)`：**新增 0 / 消失 0**（70 → 70 条 Review ID 完全一致）
- **去重验收 = 0**：THD/Lowe's `(sku, sourceReviewId)` 0 重复；Walmart `(sku, id)` 0 重复；合并输出精确重复 0

## 四、跨平台低星主题（482 条明细）

| 主题 | 条数 | 集中 (平台 · SKU) |
|---|---|---|
| 启动/动力故障 | 119 | THD WBP52BCI 47、THD WB26BCI 38、Lowes WB26BCI 9、Lowes WBPMT26P 9 |
| 客服/履约 | 78 | THD WB26BCI 22、THD WBP52BCI 21、Lowes WBPMT26P 10、Lowes WBP52BCI 6 |
| **（无正文，不可分类）** | **70** | THD 45、Lowes 25 |
| 割草/修剪效果 | 66 | THD WB26BCI 20、THD WBP52BCI 12、Lowes WB26BCI 6 |
| 质量/耐久 | 52 | THD WB26BCI 18、THD WBP52BCI 14、Walmart WB20VTAB 6 |
| 电池/充电 | 49 | Lowes WB40V18PLM 15、Walmart WB20VTAB 13 |
| 重量/人体工学 | 27 | THD WBP52BCI 12 |
| 其他 | 13 | Walmart WB20VTAB 7 |
| APP/导航/连接 | 8 | — |

> 合计 482。`theme=null` 的 70 条为无正文行（THD 45 / Lowes 25），不计入主题归因。

**高优先簇**（均与上期一致，本期**未新增**）：

| 平台 | SKU | 总评论 | 低星 | 低星率 | 紧急度 |
|---|---|---|---|---|---|
| THD | `WB26BCI` | 522 | 125 | 23.9% | P0 |
| THD | `WBP52BCI` | 407 | 124 | 30.5% | P0 |
| Lowes | `WBPMT26P` | 134 | 36 | 26.9% | P0 |
| Lowes | `WB40V18PLM` | 130 | 32 | 24.6% | P0 |
| Lowes | `WB26BCI` | 115 | 33 | 28.7% | P0 |
| Lowes | `WBP52BCI` | 28 | 15 | **53.6%** | P0 |
| Lowes | `WB31CCED` | 12 | 7 | **58.3%** | P0 |
| Walmart | `WB20VTAB` | 210 | 46 | 21.9% | P0 |
| Walmart | `WB20V16LM` | 46 | 16 | **34.8%** | P0 |

小样本新簇：THD `SKRMX3PLUS` 6/4（66.7%，P0 新品护航）、THD `ORIONX7` 5/2（40.0%，P0 新品护航）。

## 五、需要你处理的数据缺陷

### 1️⃣ Walmart `WB40VCOMBO` 落地页被第三方品牌接管 → **已按裁决沿用上期数据**

**你的裁决（原文）**：「WB40VCOMBO这个sku目前listing异常，沿用上期数据就好」

**异常事实（保留为证据）**：

| 项 | 值 |
|---|---|
| 冻结 URL | `http://www.walmart.com/ip/17598657653` |
| 实际落地 | `.../TNTANTS-...-String-Trimmer-.../` **itemId `15830216038`** |
| 落地页标题 | **TNTANTS** Weed Wacker Cordless 3-in-1（24V） |
| 落地页计数 | 3.7★ / 983 评分 / 314 评价（**不计入本 SKU**） |
| BV 辅助 feed | **total = 0** |
| 上期同一 URL | 仍为 Wild Badger 组合套装页 |

**已执行的处置**：按「沿用上期数据」把该 SKU 在本轮产物中的**数据字段还原为上期值**，异常观测值另行留档，不参与任何统计：

| 产物 | 处置 |
|---|---|
| `decisions/2026-09-10_WB40VCOMBO_carry_forward.json` | **新增**：裁决记录，逐字保留裁决原文 + 异常观测值（含 TNTANTS 落地计数），供后续追溯 |
| `walmart_storefront_current.json` | 该行数据字段（`productName`/`brand`/`url`/`finalUrl`/`title`/评分/计数）**还原为 09-03 值**；新增 `carriedForwardFrom: 2026-09-03`、`observedAnomaly{...}`；页面级字段置 `null` |
| `walmart_raw.json` | 该行 `productName`/`brand`/`stats` 还原为 09-03 值；标记 `carriedForwardFrom` |
| `review_summary.json` | 由既有 builder 重新生成 → 该行恢复为 **Wild Badger** 名称（**TNTANTS 名称已清除**） |
| `walmart_storefront_cdp_batch*.jsonl` + `pre_carryforward/` | **原始证据完整保留**，未改写（含迁移前的衍生文件快照） |

**数值影响：无。** 该 SKU 两期均为 0 评论 / 0 低星，沿用不改变任何汇总数字（总量 1,967、低星 504 均不含该 SKU 的任何外部数据）。冻结 URL 与 `itemId` **保持工作簿原值未改**（未更新 URL、未标记失效）——「沿用上期数据」仅约束本轮数据口径。

**QA 为何没拦住**：
- 本轮店面对**全部 10 个 SKU 都丢失了 `qaWarnings`**（该字段为空数组）。提示实际被写到了 `walmart_raw.json` 的 `errors` 字段（原文：*"Public Bazaarvoice values are internally reconciled; the Walmart storefront remains pending as an independent cross-validation source."*），而**不是** summary 的 `qaWarnings` —— 我早前「`qaWarnings=[]` 说明 QA 无异常」的说法是**错的**，已更正。
- 但即便读到该提示，它只说明「店面待独立校验」，**并不构成品牌/重定向一致性校验**。流水线当前**没有**任何「落地页品牌 vs 冻结库品牌」的断言 —— 异常只能靠人工读落地页标题发现。

**`scope_diff LINK_CHANGED=0` 属正常**：工作簿 `listing_url` 未变，变的是平台侧落地目标。

> ⚠️ **仍待你后续决定**：本轮按裁决沿用数据；但该 URL 的**身份问题依然存在**。下期是否更新 URL / 标记失效，仍需你另行裁决（见 §七）。

### 2️⃣ 全部 10 个 Walmart 冻结 URL 都发生 302（存储形态为旧式短链）

实测 10/10 `url != finalUrl`。存储形态 `http://www.walmart.com/ip/<itemId>`（无 slug）→ 平台 302 到规范 slug URL。

- **9/10 落到同一 Wild Badger 产品**（仅 URL 形态变化，非身份变化）
- **1/10（`WB40VCOMBO`）落到不同品牌**（见上）

即 URL 重定向**本身是常态**，只有 `WB40VCOMBO` 的重定向**改变了产品身份**。校验逻辑应比较**落地页的 itemId/品牌**，而非把「发生过重定向」当作异常。

### 3️⃣ Storefront `pageTotalReviews` / `pageTotalRatings` 字段有**互换缺陷**

本期首次提取页面级计数，与行内 `totalRatings`/`totalReviews` 同值。**10 个 SKU 中 3 个出现「评价数 > 评分数」（语义上不可能，评价是评分的子集）**：

| SKU | pageTotalRatings | pageTotalReviews |
|---|---|---|
| `WB20VCOMBODP` | 10 | **336** |
| `WB20VTRSBL` | 101 | **264** |
| `WB40VTBCC` | 29 | **209** |

**该字段不得进入任何对比**；可信口径是**文本数交叉验证**（10/10 EXACT）。上期该字段为 `null`。另：店面页总数与 BV feed 总数不同源（`WB20VTAB` 页面 118 vs feed 210），跨源不可比。

### 4️⃣ `walmart_raw.json` 的 `priorReportDate` 为**硬编码日期**（标签错误，数值正确）

`scripts/build_walmart_review_input.py:113` 硬编码 `"priorReportDate": "2026-07-23"`，导致本轮及**此前各期**（08-06 / 08-14 / 08-21 / 09-03）的 `walmart_raw.json` 全部标为对比 07-23。

- **已核实：只有日期标签错，`priorTotalReviews` 数值实际与 09-03 一致**（逐 SKU 比对 10/10 命中 09-03 值）
- 故本报告的 Walmart 周期 delta **有效**；但该字段本身不可信，需修脚本或改为从 prior run 读取

## 六、其他口径限制

1. **summary 与明细的计数差 = 22，全部来自 Walmart**：summary 低星 92 vs 明细行 70。明细行是「有正文」子集（`WB20V16LM` 10/16、`WB20VTAB` 37/46、`WB20VTRSBL` 10/13、`WB40V18PLM` 10/11、`WB40VTBCC` 3/4、`WB52CCBPB` 0/1、`WB52CCEA` 0/1）。
2. 合并 `low_star_reviews.json` 的 Walmart 行仍**缺 `sourceReviewId`**（70 行全为 null），故 Walmart identity 校验一律走权威 `walmart_bv_raw.json`。
3. THD/Lowe's 明细含 **70 条无正文行**（`ratingsOnly` 标记 57 条），不计入文本主题。**412 = 全部 482 条中有正文的行数**（THD 225 / Lowes 117 / Walmart 70），它同时等于 THD+Lowe's 明细总数（270+142），属数值巧合，勿混用。

## 七、建议跟进

1. ~~**[P0] `WB40VCOMBO` 身份裁定**~~ → **本轮已按你的裁决沿用上期数据**（见 §五.1）。遗留：该 URL 身份问题仍在，**下期需你决定**是否更新 URL / 标记失效。
2. **[P0] 给店面对齐加「品牌一致性断言」**：对齐时比较**落地页 itemId/品牌**与冻结库（而非「是否发生重定向」——10/10 都会重定向），不一致即标记身份受损并阻断该行进入 summary。
3. **[P0]** THD `WB26BCI`/`WBP52BCI` 启动·动力故障簇（合计 85 条）→ 品控复核化油器/启动系统批次 + 统一客服话术
4. **[P1]** Lowes `WB31CCED`(58.3%)、`WBP52BCI`(53.6%) 小样本高风险 → 补样本、核查近期批次
5. **[P1]** THD `SKRMX5`/`WB31CCED` 新增无正文 1★ → 下期观察是否扩散
6. **[P2]** 修复 `priorReportDate` 硬编码；停用或修正 `pageTotalReviews` 提取

## 八、合规确认

- **DB 未变更**：`tracker.db` SHA-256 `ef625f444f523b4e…`；`products 41`、`review_snapshots 35`、`reviews 436`、`review_changes 0`、`collection_runs 45`、`collection_errors 36`、`integrity_check=ok`、FK 违规 0
- `runtime/review_tracker.lock` 不存在；`outputs/` 目录不存在（未提升 latest）
- `runtime/notification_audit.jsonl` 最后写入 **2026-08-04**，本轮未触碰 → 未发送任何通知
- 未发布 Pages、未创建/修改调度任务、未动浏览器身份
- 非生产测试：`python3 -m unittest discover -s tests` **Ran 134 / 129 ok / 3 ERROR**；3 项 ERROR 均为既有环境缺 `PIL`（`test_binary_writer`、`test_phase2_3_recovery`、`test_phase4b_wr`），与本轮无关
- 工作树为脏（**用户既有**改动，178 条）；本轮 run 目录为未跟踪新增，**未触碰用户改动**

---

## 待你决定的下一步

1. ~~`WB40VCOMBO` 身份异常处置~~ → **已裁决：沿用上期数据**（本轮已执行，见 §五.1）
2. 本轮证据提交到 master — **已授权，执行中**
3. 报告发布到 GitHub Pages — **已授权，执行中**

> 注意：本次提交/发布**仅为产物落地**。`outputs/latest` 提升、通知发送、调度创建 **仍未执行、仍需单独授权**。`database_incremental_write_enabled=false` 未变更，DB 未写入。
