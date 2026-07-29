import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const inputPath = path.join(root, "config", "listing_master_migration_draft.xlsx");
const dataPath = path.join(root, "data", "processed", "phase1_5_review_package.json");
const outputPath = path.join(root, "config", "listing_master_user_review.xlsx");
const data = JSON.parse(await fs.readFile(dataPath, "utf8"));
const input = await FileBlob.load(inputPath);
const sourceWorkbook = await SpreadsheetFile.importXlsx(input);
const sourceCheck = await sourceWorkbook.inspect({ kind: "sheet", include: "name", maxChars: 1000 });
if (!sourceCheck.ndjson.includes("Migration Draft")) throw new Error("Migration draft workbook is not readable.");

const headers = ["review_status", "user_decision", "record_id", "active", "platform", "url_detected_platform", "platform_match_status", "brand", "product_line", "internal_sku", "model", "platform_item_id", "product_name", "listing_url", "link_display", "primary_keyword", "secondary_keyword", "third_keyword", "zip_code", "expected_seller", "monitor_listing", "monitor_rank", "monitor_review", "max_search_pages", "review_count_in_database", "legacy_listing_data_present", "data_completeness_score", "data_completeness_status", "missing_required_fields", "duplicate_candidate", "identity_warning", "source_file", "source_row", "user_notes", "codex_notes"];
const workbook = Workbook.create();
const master = workbook.worksheets.add("Master Review");
master.showGridLines = false;
master.getRange("A1:AI1").values = [headers];
master.getRange("A2:AI36").values = data.master.map((row) => headers.map((header) => row[header] ?? ""));
master.getRange("O2").formulas = [["=HYPERLINK(N2,\"Open Listing\")"]];
master.getRange("O2:O36").fillDown();
master.getRange("A1:AI1").format = { fill: "#17365D", font: { bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true, borders: { preset: "outside", style: "thin", color: "#17365D" } };
master.getRange("A1:AI1").format.rowHeight = 34;
master.getRange("A2:AI36").format = { verticalAlignment: "top", wrapText: true, borders: { preset: "insideHorizontal", style: "thin", color: "#D9E2F3" } };
master.freezePanes.freezeRows(1);
const widths = [17, 23, 25, 10, 12, 16, 18, 18, 18, 17, 16, 18, 34, 48, 16, 20, 20, 20, 12, 20, 16, 14, 16, 18, 18, 20, 18, 22, 24, 18, 24, 48, 11, 38, 46];
for (let index = 0; index < widths.length; index += 1) master.getRangeByIndexes(0, index, 36, 1).format.columnWidth = widths[index];
master.getRange("A2:A201").dataValidation = { rule: { type: "list", values: ["NOT_REVIEWED", "REVIEWED"] } };
master.getRange("B2:B201").dataValidation = { rule: { type: "list", values: ["APPROVE", "APPROVE_WITH_CHANGES", "EXCLUDE", "NEEDS_INVESTIGATION"] } };
for (const column of ["D", "U", "V", "W"]) master.getRange(`${column}2:${column}201`).dataValidation = { rule: { type: "list", values: ["TRUE", "FALSE"] } };
master.getRange("A2:B36").format.fill = "#FFF2CC";
master.getRange("AH2:AH36").format.fill = "#FFF2CC";
master.getRange("AI2:AI36").format.fill = "#F3F6FA";
master.getRange("AA2:AB36").format.fill = "#E2F0D9";

const guide = workbook.worksheets.add("Field Guide");
guide.showGridLines = false;
const guideRows = [["Field / rule", "Definition or review guidance"],
  ["review_status", "默认 NOT_REVIEWED；完成一行人工审核后才改为 REVIEWED。"],
  ["user_decision", "仅由用户选择：APPROVE、APPROVE_WITH_CHANGES、EXCLUDE 或 NEEDS_INVESTIGATION。"],
  ["listing_url / link_display", "URL 保留历史原值；Open Listing 为可点击链接，但本工作簿未访问或验证页面。"],
  ["data_completeness_score", "0-100 离线完整度，不代表页面真实有效性。权重：record_id/platform/internal_sku/model/item ID/URL/keyword/URL平台匹配各 10；product name/ZIP/monitor 字段/Review关联各 5。"],
  ["status bands", "READY_FOR_REVIEW 90-100；PARTIAL_DATA 70-89；INCOMPLETE 低于 70；缺 URL、record_id 或 SKU 为 CRITICAL_IDENTITY_ISSUE。"],
  ["monitor flags", "全部默认 FALSE；任何 TRUE 均须由用户审核后手动决定。"],
  ["rank scope", "primary_keyword、ZIP、max_search_pages 仅影响未来经批准的排名范围；本阶段不补造也不采集。"],
  ["historical Review", "review_count_in_database 来自迁移数据库；legacy_review_key 不是平台官方 Review ID。"]];
guide.getRange("A1:B9").values = guideRows;
guide.getRange("A1:B1").format = { fill: "#17365D", font: { bold: true, color: "#FFFFFF" } };
guide.getRange("A1:B9").format = { wrapText: true, verticalAlignment: "top", borders: { preset: "insideHorizontal", style: "thin", color: "#D9E2F3" } };
guide.getRange("A1:A9").format.columnWidth = 28; guide.getRange("B1:B9").format.columnWidth = 110; guide.getRange("A2:B9").format.rowHeight = 34;

const summary = workbook.worksheets.add("Platform Summary");
summary.showGridLines = false;
const summaryHeaders = ["platform", "listing_total", "missing_url", "missing_item_id", "review_history_listings", "missing_primary_keyword", "platform_url_mismatch", "duplicate_candidates", "ready_for_review", "partial_data", "incomplete"];
summary.getRange("A1:K1").values = [summaryHeaders];
summary.getRange("A2:K5").values = data.platform_summary.map((row) => summaryHeaders.map((header) => row[header] ?? 0));
summary.getRange("A1:K1").format = { fill: "#17365D", font: { bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", wrapText: true };
summary.getRange("A1:K5").format = { borders: { preset: "insideHorizontal", style: "thin", color: "#D9E2F3" } };
summary.getRange("A1:K5").format.columnWidth = 20;

const issues = workbook.worksheets.add("Issues");
issues.showGridLines = false;
const issueHeaders = ["issue_id", "severity", "record_id", "platform", "field", "issue_type", "current_value", "recommended_action", "blocking_phase2", "notes"];
issues.getRange(`A1:J${data.issues.length + 1}`).values = [issueHeaders, ...data.issues.map((row) => issueHeaders.map((header) => row[header] ?? ""))];
issues.getRange("A1:J1").format = { fill: "#9C0006", font: { bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", wrapText: true };
issues.getRange(`A2:J${data.issues.length + 1}`).format = { verticalAlignment: "top", wrapText: true, borders: { preset: "insideHorizontal", style: "thin", color: "#F4CCCC" } };
for (let index = 0; index < 10; index += 1) issues.getRangeByIndexes(0, index, data.issues.length + 1, 1).format.columnWidth = [14, 12, 25, 12, 22, 28, 32, 52, 18, 45][index];
issues.freezePanes.freezeRows(1);

const instructions = workbook.worksheets.add("Approval Instructions");
instructions.showGridLines = false;
const instructionRows = [["步骤", "用户操作"],
  ["1", "点击 Open Listing，并由人工确认商品页面与 SKU、型号、Item ID 是否匹配。此工作簿不会访问链接。"],
  ["2", "在 user_decision 选择 APPROVE、APPROVE_WITH_CHANGES、EXCLUDE 或 NEEDS_INVESTIGATION。"],
  ["3", "确认 active 是否应为 TRUE；默认保持 FALSE。"],
  ["4", "分别确认 monitor_listing、monitor_rank、monitor_review；至少一个 monitor 为 TRUE 才可能成为未来 Phase 2 候选。"],
  ["5", "如需排名监控，填写 primary_keyword、可选 secondary_keyword，并确认五位 ZIP 与 max_search_pages。"],
  ["6", "填写 user_notes，并将 review_status 改为 REVIEWED。"],
  ["Phase 2 候选门槛", "仅当 REVIEWED、APPROVE 或 APPROVE_WITH_CHANGES、active=TRUE、URL/SKU/平台已确认，且至少一个 monitor=TRUE 时，才可在后续单独审批进入候选范围。此工作簿不会批准或启用任何记录。"]];
instructions.getRange("A1:B8").values = instructionRows;
instructions.getRange("A1:B1").format = { fill: "#17365D", font: { bold: true, color: "#FFFFFF" } };
instructions.getRange("A1:B8").format = { wrapText: true, verticalAlignment: "top", borders: { preset: "insideHorizontal", style: "thin", color: "#D9E2F3" } };
instructions.getRange("A1:A8").format.columnWidth = 22; instructions.getRange("B1:B8").format.columnWidth = 110; instructions.getRange("A2:B8").format.rowHeight = 38;

const check = await workbook.inspect({ kind: "table", range: "Master Review!A1:AI4", include: "values,formulas", tableMaxRows: 4, tableMaxCols: 35 });
console.log(check.ndjson);
const formulaErrors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 50 }, summary: "formula error scan" });
console.log(formulaErrors.ndjson);
await fs.mkdir(path.dirname(outputPath), { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
const preview = await workbook.render({ sheetName: "Master Review", range: "A1:AI4", scale: 1.0, format: "png" });
await fs.writeFile(`${outputPath}.png`, new Uint8Array(await preview.arrayBuffer()));
process.exit(0);
