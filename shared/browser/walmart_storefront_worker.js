"use strict";
// Background CDP storefront verification for Walmart listings.
// Connects to the project-owned Walmart Chrome profile (CDP 9224) via Playwright,
// reads rating/review DOM data from each product page, and reports Robot Check
// challenges without bypassing them. No foreground window required.
//
// Usage:
//   node shared/browser/walmart_storefront_worker.js --list <json-file> --out <jsonl-file> --delay-ms 9000 --batch-limit 10

const { chromium } = require("C:/Users/admin/AppData/Local/hermes/hermes-agent/node_modules/playwright");

const ENDPOINT = "http://127.0.0.1:9224";

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i].startsWith("--")) args[argv[i].slice(2)] = argv[i + 1];
  }
  return args;
}

const compact = (value, limit = 200) =>
  String(value || "").replace(/\s+/g, " ").trim().slice(0, limit);

// Extract product rating block from the DOM (Walmart product page).
async function extractRating(page) {
  return page.evaluate(() => {
    const compact = (value, limit = 200) =>
      String(value || "").replace(/\s+/g, " ").trim().slice(0, limit);
    const norm = (value) => String(value || "").replace(/\s+/g, " ").trim();
    const bodyText = norm(document.body ? document.body.innerText : "");
    const ratingText = norm(document.title || "");
    const result = {
      ratingFound: false,
      averageRating: null,
      totalRatings: null,
      totalReviews: null,
      ratingsDistribution: null,
      productName: "",
      challenge: /robot or human|captcha|press and hold|verify you are human|are you a human|access denied|access blocked/i.test(bodyText),
    };
    if (result.challenge) return result;

    // Product name: og:title or h1
    const ogTitle = document.querySelector('meta[property="og:title"]');
    const h1 = document.querySelector("h1");
    result.productName = compact(
      (ogTitle && ogTitle.getAttribute("content")) || (h1 && h1.innerText) || ratingText,
      300
    );

    // Rating summary text: e.g. "4.2 out of 5 stars" + "329 ratings" + "116 reviews"
    const starMatch = bodyText.match(/(\d+(?:\.\d+)?)\s*out of 5 stars?/i);
    if (starMatch) result.averageRating = parseFloat(starMatch[1]);

    const ratingsMatch = bodyText.match(/(\d[\d,]*)\s+ratings?/i);
    if (ratingsMatch) result.totalRatings = parseInt(ratingsMatch[1].replace(/,/g, ""), 10);

    const reviewsMatch = bodyText.match(/(\d[\d,]*)\s+reviews?\b/i);
    if (reviewsMatch) result.totalReviews = parseInt(reviewsMatch[1].replace(/,/g, ""), 10);

    // Distribution: "N ratings are rated X stars, P% of all ratings"
    const dist = { one: 0, two: 0, three: 0, four: 0, five: 0 };
    const starNames = { 1: "one", 2: "two", 3: "three", 4: "four", 5: "five" };
    for (const line of bodyText.split(/\n+/)) {
      const m = line.match(/^(\d+)\s+ratings? are rated (\d) stars?/i);
      if (m) dist[starNames[parseInt(m[2], 10)]] = parseInt(m[1].replace(/,/g, ""), 10);
    }
    if (Object.values(dist).some((v) => v > 0)) result.ratingsDistribution = dist;
    result.ratingFound = Boolean(starMatch || ratingsMatch || result.ratingsDistribution);
    return result;
  });
}

async function verifyOne(browser, listing) {
  const contexts = browser.contexts();
  const context = contexts[0];
  const pages = context.pages();
  const page = pages[0] || (await context.newPage());
  const url = listing.listing_url || listing.url;
  const started = Date.now();
  try {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForTimeout(2500);
    const rating = await extractRating(page);
    return {
      sku: listing.record_id ? listing.record_id.split("_").pop() : listing.sku,
      itemId: listing.platform_item_id || listing.itemId || "",
      url,
      finalUrl: page.url(),
      title: compact(await page.title(), 160),
      status: rating.challenge ? "VERIFICATION_REQUIRED" : "AVAILABLE",
      dataAvailable: !rating.challenge,
      ...rating,
      ms: Date.now() - started,
      verifiedAt: new Date().toISOString(),
      method: "cdp_playwright_background",
    };
  } catch (error) {
    return {
      sku: listing.record_id ? listing.record_id.split("_").pop() : listing.sku,
      itemId: listing.platform_item_id || listing.itemId || "",
      url,
      status: "ERROR",
      dataAvailable: false,
      error: compact(error && error.message ? error.message : String(error), 200),
      ms: Date.now() - started,
      verifiedAt: new Date().toISOString(),
      method: "cdp_playwright_background",
    };
  }
}

async function main() {
  const args = parseArgs(process.argv);
  const listFile = args.list;
  const outFile = args.out || args.list + ".verified.jsonl";
  const delayMs = Number(args["delay-ms"] || "9000");
  const batchLimit = Number(args["batch-limit"] || "10");

  if (!listFile) throw new Error("--list <file> required");
  const fs = require("fs");
  const listings = JSON.parse(fs.readFileSync(listFile, "utf-8"));
  const batch = listings.slice(0, batchLimit);

  const browser = await chromium.connectOverCDP(ENDPOINT);
  const out = [];
  try {
    for (let i = 0; i < batch.length; i += 1) {
      const result = await verifyOne(browser, batch[i]);
      out.push(result);
      process.stdout.write(JSON.stringify(result) + "\n");
      if (i < batch.length - 1) await new Promise((r) => setTimeout(r, delayMs));
    }
  } finally {
    await browser.close().catch(() => {});
  }
  fs.writeFileSync(outFile, out.map((row) => JSON.stringify(row)).join("\n") + "\n");
  process.stdout.write(`WROTE ${outFile} rows=${out.length}\n`);
}

main().catch((error) => {
  process.stderr.write(JSON.stringify({ error_code: compact(error && error.message ? error.message : String(error), 220) }));
  process.exit(1);
});
