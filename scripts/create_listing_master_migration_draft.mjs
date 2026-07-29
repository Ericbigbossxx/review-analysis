import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const inputPath = path.join(root, "data", "processed", "phase1_listing_master_draft.json");
const outputPath = path.join(root, "config", "listing_master_migration_draft.xlsx");
const rows = JSON.parse(await fs.readFile(inputPath, "utf8"));
const headers = ["record_id", "active", "platform", "brand", "product_line", "internal_sku", "model", "platform_item_id", "product_name", "listing_url", "primary_keyword", "secondary_keyword", "third_keyword", "zip_code", "expected_seller", "monitor_listing", "monitor_rank", "monitor_review", "max_search_pages", "source_file", "source_row", "migration_status", "missing_required_fields", "notes"];

const workbook = Workbook.create();
const sheet = workbook.worksheets.add("Migration Draft");
sheet.showGridLines = false;
sheet.getRange("A1:X1").values = [headers];
sheet.getRange("A2:X36").values = rows.map((row) => headers.map((header) => row[header] ?? ""));
sheet.getRange("A1:X1").format = { fill: "#17365D", font: { bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true, borders: { preset: "outside", style: "thin", color: "#17365D" } };
sheet.getRange("A1:X1").format.rowHeight = 32;
sheet.getRange("A2:X36").format = { verticalAlignment: "top", wrapText: true, borders: { preset: "insideHorizontal", style: "thin", color: "#D9E2F3" } };
sheet.freezePanes.freezeRows(1);
const widths = [27, 10, 12, 18, 18, 17, 15, 18, 36, 52, 20, 20, 20, 12, 20, 16, 14, 16, 18, 46, 11, 25, 25, 46];
for (let index = 0; index < widths.length; index += 1) sheet.getRangeByIndexes(0, index, 36, 1).format.columnWidth = widths[index];
sheet.getRange("B2:B201").dataValidation = { rule: { type: "list", values: ["TRUE", "FALSE"] } };
sheet.getRange("C2:C201").dataValidation = { rule: { type: "list", values: ["WALMART", "THD", "LOWES"] } };
sheet.getRange("P2:R201").dataValidation = { rule: { type: "list", values: ["TRUE", "FALSE"] } };
sheet.getRange("V2:V36").conditionalFormats.add("containsText", { text: "READY_FOR_USER_REVIEW", format: { fill: "#E2F0D9", font: { color: "#375623" } } });

const notes = workbook.worksheets.add("Review Notes");
notes.showGridLines = false;
notes.getRange("A1:B1").merge();
notes.getRange("A1").values = [["Phase 1 controlled migration draft — user review required"]];
notes.getRange("A1:B1").format = { fill: "#17365D", font: { bold: true, color: "#FFFFFF", size: 14 }, verticalAlignment: "center" };
notes.getRange("A3:B7").values = [["Rule", "Meaning"], ["Source", "All 35 rows are extracted from the dated local review_summary.json; source_file and source_row are retained."], ["Activation", "active and all monitor flags are FALSE. This draft does not start monitoring or collection."], ["Identity", "No missing URL, SKU, Item ID, duplicate candidate, or platform/URL mismatch was found in the historical summary."], ["Approval", "Review and copy approved rows into listing_master.xlsx in a later, explicitly approved master-data step."]];
notes.getRange("A3:B3").format = { fill: "#D9EAF7", font: { bold: true } };
notes.getRange("A3:B7").format = { wrapText: true, borders: { preset: "insideHorizontal", style: "thin", color: "#D9E2F3" } };
notes.getRange("A1:A7").format.columnWidth = 18;
notes.getRange("B1:B7").format.columnWidth = 96;
notes.getRange("A4:B7").format.rowHeight = 34;

const check = await workbook.inspect({ kind: "table", range: "Migration Draft!A1:X4", include: "values", tableMaxRows: 4, tableMaxCols: 24 });
console.log(check.ndjson);
await fs.mkdir(path.dirname(outputPath), { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
const preview = await workbook.render({ sheetName: "Migration Draft", range: "A1:X4", scale: 1.1, format: "png" });
await fs.writeFile(`${outputPath}.png`, new Uint8Array(await preview.arrayBuffer()));
process.exit(0);
