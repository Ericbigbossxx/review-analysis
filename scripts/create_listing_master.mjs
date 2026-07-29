import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputPath = process.argv[2];
if (!outputPath) throw new Error("Output path is required.");

const headers = [
  "record_id", "active", "platform", "brand", "product_line", "internal_sku",
  "model", "platform_item_id", "product_name", "listing_url", "primary_keyword",
  "secondary_keyword", "third_keyword", "zip_code", "expected_seller",
  "monitor_listing", "monitor_rank", "monitor_review", "max_search_pages", "notes",
];

const workbook = Workbook.create();
const sheet = workbook.worksheets.add("Listing Master");
sheet.showGridLines = false;
sheet.getRange("A1:T1").values = [headers];
sheet.getRange("A1:T1").format = {
  fill: "#17365D",
  font: { bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
  borders: { preset: "outside", style: "thin", color: "#17365D" },
};
sheet.getRange("A1:T1").format.rowHeight = 32;
sheet.getRange("A1:T2").format.borders = { preset: "insideHorizontal", style: "thin", color: "#D9E2F3" };
sheet.freezePanes.freezeRows(1);

const widths = [24, 10, 12, 18, 18, 18, 18, 20, 32, 52, 22, 22, 22, 12, 22, 16, 14, 16, 18, 40];
for (let index = 0; index < widths.length; index += 1) {
  sheet.getRangeByIndexes(0, index, 2, 1).format.columnWidth = widths[index];
}

sheet.getRange("A2:T2").format = {
  fill: "#FFFDF5",
  verticalAlignment: "top",
  wrapText: true,
  borders: { preset: "outside", style: "thin", color: "#D9E2F3" },
};
sheet.getRange("B2:B201").dataValidation = { rule: { type: "list", values: ["TRUE", "FALSE"] } };
sheet.getRange("C2:C201").dataValidation = { rule: { type: "list", values: ["WALMART", "THD", "LOWES"] } };
sheet.getRange("P2:R201").dataValidation = { rule: { type: "list", values: ["TRUE", "FALSE"] } };
sheet.getRange("S2:S201").dataValidation = { rule: { type: "whole", operator: "greaterThan", formula1: 0 } };
sheet.getRange("N2:N201").setNumberFormat("@");

const notes = workbook.worksheets.add("Read Me");
notes.showGridLines = false;
notes.getRange("A1:B1").merge();
notes.getRange("A1").values = [["US Local Channel Listing Tracker — Listing Master guidance"]];
notes.getRange("A1:B1").format = {
  fill: "#17365D",
  font: { bold: true, color: "#FFFFFF", size: 14 },
  verticalAlignment: "center",
};
notes.getRange("A1:B1").format.rowHeight = 28;
notes.getRange("A3:B9").values = [
  ["Rule", "Guidance"],
  ["Grain", "One row is one platform Listing. The same SKU on different platforms uses distinct record_id values."],
  ["record_id", "Use PLATFORM_INTERNALSKU when stable, for example THD_SKRM_S4. Do not reuse it across platforms."],
  ["Source integrity", "Do not prefill invented Listings. Migrate verified existing configuration only with a retained source path and migration record."],
  ["listing_url", "This is the product-detail-page access anchor, not a search-results URL."],
  ["Controls", "active is the master switch; monitor_listing, monitor_rank, and monitor_review independently enable each capability."],
  ["ZIP / rank", "Keep ZIP as text. Rank collection is subject to the platform rules in docs/platform_collection_rules.md."],
];
notes.getRange("A3:B3").format = { fill: "#D9EAF7", font: { bold: true }, borders: { preset: "outside", style: "thin", color: "#9FBAD0" } };
notes.getRange("A3:B9").format.wrapText = true;
notes.getRange("A3:B9").format.borders = { preset: "insideHorizontal", style: "thin", color: "#D9E2F3" };
notes.getRange("A1:A9").format.columnWidth = 18;
notes.getRange("B1:B9").format.columnWidth = 92;
notes.getRange("A4:B9").format.rowHeight = 32;

const inspect = await workbook.inspect({ kind: "table", range: "Listing Master!A1:T2", include: "values", tableMaxRows: 3, tableMaxCols: 20 });
console.log(inspect.ndjson);
const output = await SpreadsheetFile.exportXlsx(workbook);
await fs.mkdir(path.dirname(outputPath), { recursive: true });
await output.save(outputPath);
const preview = await workbook.render({ sheetName: "Listing Master", range: "A1:T2", scale: 1.2, format: "png" });
await fs.writeFile(`${outputPath}.png`, new Uint8Array(await preview.arrayBuffer()));
