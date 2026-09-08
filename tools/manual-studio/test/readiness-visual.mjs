/** Local-only rendering evidence for the readiness deck; artifacts must stay outside the repo. */
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { buildReadinessMaturityDeck } from "../readiness-maturity.js";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
const output = process.argv[2];
assert.ok(output && isAbsolute(output), "Provide an absolute artifact directory outside the repository.");
const outputRelation = relative(root, resolve(output));
assert.ok(outputRelation === ".." || outputRelation.startsWith(`..${sep}`) || isAbsolute(outputRelation), "Rendering artifacts must stay outside the repository.");
const modes = (process.argv[3] ?? "desktop,tablet,mobile,fullscreen,print").split(",");
const viewports = {
  desktop: { width: 1440, height: 900 },
  tablet: { width: 993, height: 641 },
  mobile: { width: 390, height: 844 },
  fullscreen: { width: 1440, height: 900 },
  print: { width: 1536, height: 864 },
};
assert.ok(modes.every(mode => mode in viewports), "Unknown rendering mode.");
const require = createRequire(join(root, "console/package.json"));
const { chromium } = require("playwright");
const slides = buildReadinessMaturityDeck();
const problems = [];
const networkFailures = [];
const pageErrors = [];
const results = [];
const browser = await chromium.launch({ headless: true, timeout: 15000 });

/** Measure actual text ranges and region geometry, not just DOM presence. */
function inspectSlide(slide, mode) {
  const box = element => {
    const rect = element.getBoundingClientRect();
    return { x: rect.x, y: rect.y, right: rect.right, bottom: rect.bottom, width: rect.width, height: rect.height };
  };
  const canvas = box(slide);
  const scale = canvas.width / 1536;
  const tolerance = 1.2 * scale;
  const findings = [];
  const add = (kind, detail) => findings.push({ kind, detail });
  const outside = (child, parent) => child.x < parent.x - tolerance || child.y < parent.y - tolerance ||
    child.right > parent.right + tolerance || child.bottom > parent.bottom + tolerance;
  const label = element => element.textContent.trim().replace(/\s+/g, " ").slice(0, 105);
  const isCover = slide.classList.contains("slide-briefing-readiness-cover");
  const style = getComputedStyle(slide);
  if (Math.round(parseFloat(style.width)) !== 1536 || Math.round(parseFloat(style.height)) !== 864) add("canvas", "Canvas is not 1536x864.");
  if (mode !== "print") {
    if (document.documentElement.scrollWidth > innerWidth + 1) add("document-overflow", document.documentElement.scrollWidth);
    if (outside(canvas, box(document.querySelector("#slide-stage")))) add("stage-overflow", canvas);
  }
  const regionElements = [slide.querySelector(".slide-copy"), ...slide.querySelectorAll(".rm-meta, .rm-visual, .rm-takeaway, .rm-source")];
  const regions = regionElements.filter(element => element && box(element).height > 0);
  for (const region of regions) {
    if (outside(box(region), canvas)) add("region-outside", region.className);
  }
  if (!isCover) {
    for (let i = 0; i < regions.length; i += 1) {
      for (let j = i + 1; j < regions.length; j += 1) {
        const a = box(regions[i]), b = box(regions[j]);
        if (Math.min(a.right, b.right) - Math.max(a.x, b.x) > tolerance &&
            Math.min(a.bottom, b.bottom) - Math.max(a.y, b.y) > tolerance) {
          add("region-overlap", `${regions[i].className} / ${regions[j].className}`);
        }
      }
    }
  }
  const rgba = value => {
    const match = value.match(/^rgba?\(([^)]+)\)/);
    if (!match) return null;
    const values = match[1].split(/[, /]+/).map(Number);
    return [...values.slice(0, 3), values[3] ?? 1];
  };
  const luminance = color => color.slice(0, 3).map(value => {
    const v = value / 255;
    return v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4;
  }).reduce((sum, value, index) => sum + value * [.2126, .7152, .0722][index], 0);
  const contrast = (a, b) => (Math.max(luminance(a), luminance(b)) + .05) / (Math.min(luminance(a), luminance(b)) + .05);
  const backgrounds = element => {
    for (let current = element; current; current = current.parentElement) {
      const computed = getComputedStyle(current);
      if (computed.backgroundImage.includes("gradient")) {
        return [...computed.backgroundImage.matchAll(/rgba?\([^)]+\)/g)].map(match => rgba(match[0])).filter(Boolean);
      }
      const color = rgba(computed.backgroundColor);
      if (color && color[3] === 1) return [color];
    }
    return [[255, 255, 255, 1]];
  };
  let minimumContrast = Infinity;
  let minimumPrimaryFont = Infinity;
  const textRanges = [];
  const primary = [...slide.querySelectorAll(".rm-visual p:not(.rm-cover-note), .rm-visual blockquote, .rm-visual td, .rm-visual h3, .rm-takeaway")];
  for (const element of primary) {
    const fontSize = parseFloat(getComputedStyle(element).fontSize);
    minimumPrimaryFont = Math.min(minimumPrimaryFont, fontSize);
    if (fontSize < 24) add("body-font-floor", `${fontSize}px: ${label(element)}`);
  }
  for (const element of slide.querySelectorAll("*")) {
    if (element.matches("img, svg, svg *, i") || element.closest('[aria-hidden="true"]')) continue;
    const computed = getComputedStyle(element);
    if (computed.display === "none" || computed.visibility === "hidden") continue;
    const nodes = [...element.childNodes].filter(node => node.nodeType === Node.TEXT_NODE && node.textContent.trim());
    if (!nodes.length) continue;
    const fg = rgba(computed.color);
    if (fg) {
      const value = Math.min(...backgrounds(element).map(bg => contrast(fg, bg)));
      minimumContrast = Math.min(minimumContrast, value);
      if (value < 4.5) add("contrast", `${value.toFixed(2)}: ${label(element)}`);
    }
    for (const node of nodes) {
      const range = document.createRange();
      range.selectNodeContents(node);
      for (const rect of range.getClientRects()) {
        if (!rect.width || !rect.height) continue;
        const bounds = { x: rect.x, y: rect.y, right: rect.right, bottom: rect.bottom };
        if (outside(bounds, canvas)) add("text-outside-canvas", node.textContent.trim().slice(0, 90));
        if (!isCover) {
          const region = element.closest(".rm-visual, .rm-meta, .rm-takeaway, .rm-source, .slide-copy");
          if (region && outside(bounds, box(region))) add("text-outside-region", label(element));
        }
        if (element.matches("p, h2, h3, blockquote, td, th, dt, dd, figcaption") && outside(bounds, box(element))) {
          add("text-outside-block", label(element));
        }
        textRanges.push({ element, bounds, text: node.textContent.trim().slice(0, 60) });
      }
    }
  }
  for (let i = 0; i < textRanges.length; i += 1) {
    for (let j = i + 1; j < textRanges.length; j += 1) {
      const a = textRanges[i], b = textRanges[j];
      if (a.element.contains(b.element) || b.element.contains(a.element)) continue;
      const width = Math.min(a.bounds.right, b.bounds.right) - Math.max(a.bounds.x, b.bounds.x);
      const height = Math.min(a.bounds.bottom, b.bounds.bottom) - Math.max(a.bounds.y, b.bounds.y);
      if (width > tolerance && height > tolerance) add("text-overlap", `${a.text} / ${b.text}`);
    }
  }
  let connectors = 0;
  let maximumConnectorGap = 0;
  let maximumBarProportionError = 0;
  let maximumTimePositionError = 0;
  let maximumCategoryPositionError = 0;
  const coverage = slide.querySelector(".rm-coverage-strip");
  if (coverage) {
    const total = Number(coverage.dataset.rmTotal);
    const segments = [...coverage.querySelectorAll("[data-rm-count]")];
    const width = segments.reduce((sum, segment) => sum + box(segment).width, 0);
    for (const segment of segments) {
      const error = Math.abs(box(segment).width / width - Number(segment.dataset.rmCount) / total);
      maximumBarProportionError = Math.max(maximumBarProportionError, error);
      if (error > .001) add("bar-proportion", label(segment));
    }
    if (segments.reduce((sum, segment) => sum + Number(segment.dataset.rmCount), 0) !== total) add("bar-denominator", total);
  }
  for (const path of slide.querySelectorAll(".rm-path, .rm-graph")) {
    for (const link of path.querySelectorAll(".rm-link")) {
      const from = box(path.querySelector(`[data-rm-node="${link.dataset.rmFrom}"]`));
      const to = box(path.querySelector(`[data-rm-node="${link.dataset.rmTo}"]`));
      const edge = box(link.querySelector("i"));
      const direction = link.dataset.rmDirection ?? "right";
      const vertical = direction === "up" || direction === "down";
      const gap = (direction === "left" ? Math.max(Math.abs(edge.right - from.x), Math.abs(edge.x - to.right)) :
        direction === "down" ? Math.max(Math.abs(edge.y - from.bottom), Math.abs(edge.bottom - to.y)) :
        direction === "up" ? Math.max(Math.abs(edge.bottom - from.y), Math.abs(edge.y - to.bottom)) :
        Math.max(Math.abs(edge.x - from.right), Math.abs(edge.right - to.x))) / scale;
      maximumConnectorGap = Math.max(maximumConnectorGap, gap);
      const crosses = vertical ? edge.x >= from.x && edge.right <= from.right && edge.x >= to.x && edge.right <= to.right :
        edge.y >= from.y && edge.bottom <= from.bottom && edge.y >= to.y && edge.bottom <= to.bottom;
      if (gap > 1 || !crosses) add("connector", { gap, direction });
      connectors += 1;
    }
  }
  const axis = slide.querySelector(".rm-time-axis");
  if (axis) {
    const bounds = box(axis);
    for (const marker of axis.querySelectorAll(".rm-time-marker")) {
      const expected = Number(marker.dataset.rmMinute) / Number(axis.dataset.rmTotalMinutes);
      const observed = (box(marker).x - bounds.x) / bounds.width;
      const error = Math.abs(expected - observed);
      maximumTimePositionError = Math.max(maximumTimePositionError, error);
      if (error > .001) add("time-position", marker.dataset.rmMinute);
    }
    const window = slide.querySelector(".rm-time-window");
    const valid = window.querySelector(".rm-valid-window");
    if (Math.abs(box(valid).width / box(window).width - .5) > .001) add("time-window", "Valid interval is not 5 of 10 minutes.");
  }
  for (const axis of slide.querySelectorAll(".rm-category-axis")) {
    const selected = axis.querySelector(".is-current");
    if (axis.dataset.level === "unassessed") {
      if (selected || axis.querySelector("[data-category]")) add("unknown-category", "Unassessed must not have a score position.");
      continue;
    }
    const bounds = box(axis), marker = box(selected);
    const expected = (Number(axis.dataset.level.slice(1)) - .5) / 5;
    const observed = (marker.x + marker.width / 2 - bounds.x) / bounds.width;
    const error = Math.abs(expected - observed);
    maximumCategoryPositionError = Math.max(maximumCategoryPositionError, error);
    if (error > .001) add("category-position", axis.dataset.level);
  }
  const agenda = slide.querySelector(".rm-agenda-ring");
  if (agenda) {
    const arcs = [...agenda.querySelectorAll("circle")];
    let elapsed = 0;
    for (const arc of arcs) {
      const duration = Number(arc.dataset.rmMinutes);
      const computed = getComputedStyle(arc);
      const dash = computed.strokeDasharray.split(/[ ,]+/).map(Number.parseFloat);
      if (Number(arc.getAttribute("pathLength")) !== 90 || dash[0] !== duration || dash[1] !== 90 - duration ||
          parseFloat(computed.strokeDashoffset) !== -elapsed) add("agenda-proportion", duration);
      elapsed += duration;
    }
    if (elapsed !== 90) add("agenda-duration", elapsed);
  }
  const lines = selector => {
    const element = slide.querySelector(selector);
    return Math.round(element.clientHeight / parseFloat(getComputedStyle(element).lineHeight));
  };
  const titleLines = lines(".slide-copy h2");
  const leadLines = lines(".slide-copy > p");
  if (titleLines > 2) add("title-density", titleLines);
  if (leadLines > 2) add("lead-density", leadLines);
  return { slide: Number(slide.dataset.index) + 1, title: label(slide.querySelector("h2")), mode,
    titleLines, leadLines, minimumPrimaryFont: Number.isFinite(minimumPrimaryFont) ? minimumPrimaryFont : null,
    minimumContrast, connectors, maximumConnectorGap, maximumBarProportionError, maximumTimePositionError, maximumCategoryPositionError, findings };
}

try {
  const page = await browser.newPage({ viewport: viewports.desktop, reducedMotion: "reduce", locale: "ko-KR" });
  page.setDefaultTimeout(10000);
  await page.route("**/*", route => {
    if (new URL(route.request().url()).origin === "http://127.0.0.1:5474") return route.continue();
    networkFailures.push("External request blocked.");
    return route.abort();
  });
  page.on("requestfailed", request => networkFailures.push(new URL(request.url()).pathname));
  page.on("response", response => { if (response.status() >= 400) networkFailures.push(`${response.status()} ${new URL(response.url()).pathname}`); });
  page.on("pageerror", error => pageErrors.push(error.message));
  await mkdir(output, { recursive: true });
  for (const mode of modes) {
    console.log(`readiness-visual: ${mode} start (${slides.length} slides)`);
    await page.emulateMedia({ media: "screen", reducedMotion: "reduce" });
    await page.setViewportSize(viewports[mode]);
    await page.goto("http://127.0.0.1:5474/library?manual=readiness-maturity&slide=1", { waitUntil: "load", timeout: 15000 });
    await page.locator("#viewer[open] .manual-slide.active").waitFor();
    await page.evaluate(() => document.fonts.ready);
    assert.equal(await page.locator(".manual-slide").count(), slides.length);
    assert.deepEqual(await page.evaluate(() => ({ width: innerWidth, height: innerHeight })), viewports[mode]);
    if (mode === "fullscreen") {
      await page.locator("#fullscreen-manual").click();
      await page.waitForFunction(() => document.fullscreenElement?.id === "slide-stage");
    } else if (mode === "print") {
      await page.emulateMedia({ media: "print", reducedMotion: "reduce" });
    }
    const directory = join(output, mode);
    await mkdir(directory, { recursive: true });
    for (let index = 0; index < slides.length; index += 1) {
      const locator = page.locator(`.manual-slide[data-index="${index}"]`);
      if (mode !== "print") {
        if (index) await page.keyboard.press("ArrowRight");
        await page.waitForFunction(expected => document.querySelector(".manual-slide.active")?.dataset.index === String(expected), index);
      }
      const result = await locator.evaluate(inspectSlide, mode);
      results.push(result);
      problems.push(...result.findings.map(finding => ({ slide: index + 1, mode, ...finding })));
      await locator.screenshot({ path: join(directory, `${String(index + 1).padStart(2, "0")}-${slides[index].readiness.id}.png`), animations: "disabled" });
      if ((index + 1) % 8 === 0) console.log(`readiness-visual: ${mode} ${index + 1}/${slides.length}`);
    }
    if (mode === "print") {
      await page.pdf({ path: join(output, "readiness-maturity.pdf"), preferCSSPageSize: true, printBackground: true });
    }
    if (mode === "fullscreen") await page.evaluate(() => document.exitFullscreen());
  }
  const files = ["readiness-maturity.js", "readiness-slide-kit.js", "readiness-foundations.js", "readiness-ai.js", "readiness-maturity-model.js", "readiness-action-plan.js", "readiness-maturity.css", "readiness-visuals.css", "readiness-diagrams.js", "readiness-diagrams.css"];
  const sourceDigests = Object.fromEntries(await Promise.all(files.map(async file => [file, createHash("sha256").update(await readFile(join(root, "tools/manual-studio", file))).digest("hex")])));
  const summary = { reviewedAt: new Date().toISOString(), browser: browser.version(), modes, slideCount: slides.length,
    slideModeChecks: results.length, deckDigest: createHash("sha256").update(JSON.stringify(slides)).digest("hex"), sourceDigests,
    minimumPrimaryFont: Math.min(...results.map(result => result.minimumPrimaryFont ?? Infinity)),
    minimumTextContrastRatio: Math.min(...results.map(result => result.minimumContrast)),
    maximumTitleLines: Math.max(...results.map(result => result.titleLines)), maximumLeadLines: Math.max(...results.map(result => result.leadLines)),
    diagramConnectorsPerPass: results.filter(result => result.mode === modes[0]).reduce((sum, result) => sum + result.connectors, 0),
    maximumConnectorGapPx: Math.max(...results.map(result => result.maximumConnectorGap)),
    maximumBarProportionError: Math.max(...results.map(result => result.maximumBarProportionError)),
    maximumTimePositionError: Math.max(...results.map(result => result.maximumTimePositionError)),
    maximumCategoryPositionError: Math.max(...results.map(result => result.maximumCategoryPositionError)),
    findings: problems, failedRequests: networkFailures, pageErrors };
  await writeFile(join(output, `measurements-${modes.join("-")}.json`), JSON.stringify({ summary, results }, null, 2) + "\n");
  console.log(JSON.stringify(summary, null, 2));
  process.exitCode = problems.length || networkFailures.length || pageErrors.length ? 1 : 0;
} finally {
  await browser.close();
}
