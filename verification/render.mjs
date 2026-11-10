#!/usr/bin/env node
// Render checked Mermaid artifacts with the statechart skill's pinned renderer.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

const root = path.resolve(import.meta.dirname, "..");
const cache = path.join(process.env.XDG_CACHE_HOME ?? path.join(os.homedir(), ".cache"),
  "bend-window-capture-verification", "renderer");
const entry = process.env.PELE_MODULE ?? path.join(cache, "node_modules/pele/dist/pele.js");
if (!fs.existsSync(entry)) {
  throw new Error(`Install the renderer outside the repo: npm install --prefix ${cache} --no-audit --no-fund pele@1.9.0`);
}
const metadata = JSON.parse(fs.readFileSync(path.resolve(entry, "../../package.json"), "utf8"));
if (metadata.version !== "1.9.0") throw new Error("The statechart renderer must be pele@1.9.0");
const { render } = await import(pathToFileURL(entry).href);
const style = `
.pele { --pele-bg: transparent; --pele-fg: var(--foreground, #1c1c1c);
  --pele-muted: var(--muted-foreground, #656565); --pele-line: var(--muted-foreground, #808080);
  --pele-surface: var(--card, #fcfcfc); --pele-surface-alt: var(--secondary, #f1f1f1);
  --pele-border: var(--border, #c9c9c9); --pele-font: var(--font-sans, sans-serif); }
.pele .blue rect { fill: color-mix(in srgb, var(--info, #c3e0ff) 20%, var(--card, #ffffff)); }
.pele .teal rect { fill: color-mix(in srgb, var(--success, #bfe3df) 20%, var(--card, #ffffff)); }
.pele .orange rect { fill: color-mix(in srgb, var(--warning, #f0d3bf) 20%, var(--card, #ffffff)); }
.pele .breaks rect { fill: var(--destructive-surface, #ffecee) !important;
  stroke: var(--destructive, #e72e3b) !important; stroke-width: 2.5px !important; }
.pele .breaks text { fill: var(--destructive, #cd2834) !important; }
.pele .mayBreak rect { fill: var(--warning-surface, #fff3e6) !important;
  stroke: var(--warning, #e8730c) !important; stroke-width: 2.5px !important; }
.pele .mayBreak text { fill: var(--warning, #b85a06) !important; }
.pele .bugPath rect { stroke: var(--info, #1680f3) !important; stroke-width: 2.5px !important; }
.pele .repeats rect { stroke: var(--chart-3, #9b35d6) !important; stroke-width: 2.5px !important; stroke-dasharray: 6 3; }
@media (prefers-color-scheme: dark) {
 .pele { --pele-fg: var(--foreground, #f5f5f5); --pele-muted: var(--muted-foreground, #acacac);
   --pele-line: var(--muted-foreground, #939393); --pele-surface: var(--card, #121212);
   --pele-surface-alt: var(--secondary, #2c2c2c); --pele-border: var(--border, #4e4e4e); }
 .pele .blue rect { fill: color-mix(in srgb, var(--info, #1b3857) 20%, var(--card, #121212)); }
 .pele .teal rect { fill: color-mix(in srgb, var(--success, #174641) 20%, var(--card, #121212)); }
 .pele .orange rect { fill: color-mix(in srgb, var(--warning, #573117) 20%, var(--card, #121212)); }
 .pele .breaks rect { fill: var(--destructive-surface, #2e2021) !important; }
 .pele .breaks text { fill: var(--destructive, #ff6463) !important; }
}
`;
function* charts(folder) {
  for (const item of fs.readdirSync(folder, { withFileTypes: true })) {
    const file = path.join(folder, item.name);
    if (item.isDirectory()) yield* charts(file);
    else if (item.name.endsWith(".mmd")) yield file;
  }
}
const files = [...charts(path.join(root, "verification/charts")),
  ...charts(path.join(root, "verification/mutation-evidence"))];
for (const file of files) {
  const { svg } = render(fs.readFileSync(file, "utf8"),
    { limit: 1_000_000, outputLimit: 8_000_000, maxEdges: 10_000 });
  fs.writeFileSync(file.replace(/\.mmd$/, ".svg"), svg.replace(/(<svg\b[^>]*>)/, `$1<style>${style}</style>`));
}
console.log(`Rendered ${files.length} charts with pele@1.9.0`);

const escape = (text) => text.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
const results = JSON.parse(fs.readFileSync(path.join(root, "verification/results.json"), "utf8"));
const mutationCount = Object.values(results).reduce((sum, result) => sum + result.mutations.length, 0);
const sourceOnlyCount = Object.values(results).flatMap(result => result.mutations)
  .filter(mutation => mutation.rule.startsWith("Source behavioral oracle")).length;
const pairedCount = mutationCount - sourceOnlyCount;
const names = {
  "window-lifecycle": "Window lifecycle", "capture-transaction": "Capture decisions",
  "x11-error-trap": "X11 error handling", "pixel-ownership": "Pixel ownership",
  "effect-registration": "Effect registration", "check-runner": "Check runner",
};
function diagram(folder, compact = false) {
  const svg = fs.readFileSync(path.join(folder, "chart.svg"), "utf8");
  const mmd = fs.readFileSync(path.join(folder, "chart.mmd"), "utf8");
  return `<div class="chart-tools"><button data-zoom="in">Zoom in</button><button data-zoom="fit">Fit</button><span>Scroll to pan when enlarged.</span></div>
    <div class="diagram${compact ? " compact" : ""}">${svg}</div>
    <details class="source"><summary>Mermaid source</summary><pre><code class="language-mermaid">${escape(mmd)}</code></pre></details>`;
}
const primary = ["window-lifecycle", "capture-transaction"].map((area, index) =>
  `<section role="tabpanel" id="panel-${area}" aria-labelledby="tab-${area}" ${index ? "hidden" : ""}>
    <p class="caption">${index ? "Capture returns the same window with either a snapshot or an error. EAGAIN lets the caller decide whether to retry." : "The example closes the returned window before printing pixels or reporting a capture error. Opening failure exits directly."}</p>
    ${diagram(path.join(root, "verification/charts", area))}</section>`).join("");
const internals = Object.keys(names).slice(2).map(area => `<details><summary>${names[area]}</summary>
  ${diagram(path.join(root, "verification/charts", area), true)}</details>`).join("");
const negative = files.filter(file => file.includes(`${path.sep}mutation-evidence${path.sep}`)).map(file => {
  const folder = path.dirname(file);
  const [area, mutation] = path.relative(path.join(root, "verification/mutation-evidence"), folder).split(path.sep);
  return `<details><summary>${names[area]} · ${escape(mutation)}</summary>
    <pre>${escape(fs.readFileSync(path.join(folder, "report.md"), "utf8"))}</pre>${diagram(folder, true)}</details>`;
}).join("");
const rows = Object.entries(results).map(([area, result]) => `<tr><td>${names[area]}</td><td>${result.states}</td><td>${result.source_cases}</td><td>${result.mutations.length}</td></tr>`).join("");
const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Capture verification flows</title><style>
:root { color-scheme: light dark; }
body { margin:0; font-family:var(--font-sans,system-ui); color:var(--foreground,CanvasText); line-height:1.45; }
* { box-sizing:border-box; } p { margin:10px 0; } .status { font-weight:600; }
.tabs,.chart-tools { display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin:12px 0; }
button { font:inherit; color:var(--foreground,CanvasText); background:var(--secondary,Canvas); border:1px solid var(--border,GrayText); border-radius:var(--radius,8px); padding:7px 12px; cursor:pointer; }
button[aria-selected="true"] { border-color:var(--primary,Highlight); background:var(--accent,ButtonFace); }
button:focus-visible,summary:focus-visible { outline:2px solid var(--ring,Highlight); outline-offset:2px; }
.caption,.note,.chart-tools span { color:var(--muted-foreground,GrayText); font-size:14px; }
.chart-tools button { font-size:13px; padding:4px 10px; }
.diagram { height:860px; overflow:auto; border:1px solid var(--border,GrayText); border-radius:var(--radius,8px); }
.diagram.compact { height:640px; } .diagram svg { display:block; margin:0 auto; }
@media (max-width:480px) { .diagram,.diagram.compact { height:520px; } }
details { margin:12px 0; border-top:1px solid var(--border,GrayText); padding-top:12px; }
summary { cursor:pointer; font-weight:600; } details.source { border:0; padding-top:0; }
pre { font:12px/1.5 var(--font-mono,monospace); overflow:auto; padding:16px; border-radius:var(--radius,8px); background:var(--code-background,Canvas); }
table { width:100%; border-collapse:collapse; margin:14px 0; font-size:13px; }
th,td { text-align:left; padding:8px 4px; border-bottom:1px solid var(--border,GrayText); }
[hidden] { display:none !important; }
</style></head><body>
<p class="status">All ${Object.keys(results).length} subsystem models pass. ${mutationCount} source mutations are caught.</p>
<div class="tabs" role="tablist" aria-label="Main user flows"><button id="tab-window-lifecycle" role="tab" aria-controls="panel-window-lifecycle" aria-selected="true" data-tab="window-lifecycle">Capture and close</button><button id="tab-capture-transaction" role="tab" aria-controls="panel-capture-transaction" aria-selected="false" data-tab="capture-transaction">Capture decisions</button></div>
${primary}
<p class="note">These charts collapse internal steps and terminal self-loops. The models cover one attempt under the documented bounds. Real X11 rendering, allocation failure, and arbitrary concurrent Xlib callers remain outside the proof.</p>
<details><summary>Four implementation protocols</summary>${internals}</details>
<details><summary>Verification evidence and scope</summary><table><thead><tr><th>Subsystem</th><th>Model states</th><th>Source cases</th><th>Mutations caught</th></tr></thead><tbody>${rows}</tbody></table>
<p class="note">${pairedCount} source mutations have matching TLA+ counterexamples. ${sourceOnlyCount} additional source checks corrupt row placement, color, or synchronization order. The source checks execute real Bend and C control flow with controlled X11 effects; they do not prove all C inputs.</p>
<pre><code>python3 verification/verify.py all --mutations</code></pre></details>
<details><summary>${pairedCount} deliberately broken models and their shortest failure paths</summary><p class="note">These counterexamples are negative controls. Current-code models pass.</p>${negative}</details>
<script>
for (const button of document.querySelectorAll("[data-tab]")) button.addEventListener("click", () => {
  for (const tab of document.querySelectorAll("[data-tab]")) tab.setAttribute("aria-selected", String(tab === button));
  for (const panel of document.querySelectorAll('[role="tabpanel"]')) panel.hidden = panel.id !== "panel-" + button.dataset.tab;
});
for (const button of document.querySelectorAll("[data-zoom]")) button.addEventListener("click", () => {
  const box = button.parentElement.nextElementSibling, svg = box.querySelector("svg");
  if (button.dataset.zoom === "fit") { svg.style.width = ""; svg.style.maxWidth = "100%"; box.scrollTo(0,0); }
  else { svg.style.width = svg.getBoundingClientRect().width * 1.25 + "px"; svg.style.maxWidth = "none"; }
});
</script></body></html>`;
fs.writeFileSync(path.join(root, "verification/flows.html"), html);
console.log("Wrote verification/flows.html");
