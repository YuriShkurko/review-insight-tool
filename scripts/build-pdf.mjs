/**
 * build-pdf.mjs
 *
 * Generates INTERVIEW_PREP.pdf from INTERVIEW_PREP.md with Mermaid diagrams
 * pre-rendered to SVG via @mermaid-js/mermaid-cli + system Chrome.
 *
 * Usage: node scripts/build-pdf.mjs
 */

import { execSync } from "child_process";
import fs from "fs";
import os from "os";
import path from "path";
import { fileURLToPath } from "url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const INPUT = path.join(ROOT, "INTERVIEW_PREP.md");
const OUTPUT = path.join(ROOT, "INTERVIEW_PREP.pdf");

const CHROME_PATH =
  process.env.CHROME_PATH ||
  "C:/Program Files/Google/Chrome/Application/chrome.exe";

const TMP = fs.mkdtempSync(path.join(os.tmpdir(), "pdf-build-"));

function run(cmd, opts = {}) {
  return execSync(cmd, { stdio: "pipe", timeout: 120_000, ...opts });
}

try {
  // Write puppeteer config pointing at system Chrome (avoids Chromium download)
  const puppeteerCfg = path.join(TMP, "puppeteer.json");
  fs.writeFileSync(
    puppeteerCfg,
    JSON.stringify({
      executablePath: CHROME_PATH,
      args: ["--no-sandbox", "--disable-setuid-sandbox"],
    })
  );

  // Let mmdc process the entire markdown: it finds all ```mermaid blocks,
  // renders each to SVG in TMP, and outputs a new .md with <img> references.
  const processedMd = path.join(TMP, "INTERVIEW_PREP.md");
  console.log("Rendering Mermaid diagrams…");
  run(
    `npx --yes @mermaid-js/mermaid-cli` +
      ` -i "${INPUT}"` +
      ` -o "${processedMd}"` +
      ` -a "${TMP}"` +
      ` -p "${puppeteerCfg}"` +
      ` --quiet`
  );

  // Generate PDF — point basedir at TMP so md-to-pdf can resolve the SVG files
  console.log("Generating PDF…");
  run(
    `npx md-to-pdf "${processedMd}"` +
      ` --basedir "${TMP}"` +
      ` --css ".mermaid-diagram, img[src$='.svg'] { max-width: 100%; height: auto; page-break-inside: avoid; margin: 1.5em 0; }"`,
    { stdio: "inherit" }
  );

  fs.copyFileSync(path.join(TMP, "INTERVIEW_PREP.pdf"), OUTPUT);
  console.log(`✓  PDF written → ${OUTPUT}`);
} finally {
  fs.rmSync(TMP, { recursive: true, force: true });
}
