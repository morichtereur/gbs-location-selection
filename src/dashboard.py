"""Build the interactive dashboard as one self-contained HTML file.

The static chart reports a conclusion. This lets someone disagree with it: move
the weights, watch the ranking reorder, and watch the stability meter say how
much of that new answer would survive somebody else's equally defensible
opinion. The argument of the whole study is easier to feel than to read.

Scoring is reimplemented in JavaScript because it has to run on every slider
drag. `tests/test_dashboard.py` asserts the two implementations agree on the
real panel, so the reimplementation cannot drift from `src/score.py`.
"""

from __future__ import annotations

import json

from src import config as C
from src.panel import Market, build, with_cities
from src.score import PILLARS
from src.stability import run

# Validated categorical palette — six slots, one per pillar. Checked with the
# data-viz validator against this surface: all hard gates pass; two slots sit
# under 3:1 contrast, which obliges visible labels and a table view. Both ship.
# Slot order is the colour-blindness safety mechanism, not a preference: the
# validator checks *adjacent* pairs, so which pillar gets which hue matters.
# An earlier hand-picked set put red beside yellow and failed the
# normal-vision floor in dark mode at deltaE 13.0.
PILLAR_COLORS = {
    "cost": "#2a78d6",
    "talent": "#eb6834",
    "risk": "#1baf7a",
    "capability": "#eda100",
    "timezone": "#e87ba4",
    "durability": "#008300",
}
PILLAR_COLORS_DARK = {
    "cost": "#3987e5",
    "talent": "#d95926",
    "risk": "#199e70",
    "capability": "#c98500",
    "timezone": "#d55181",
    "durability": "#008300",
}
PILLAR_LABELS = {
    "cost": "Cost",
    "talent": "Talent",
    "risk": "Governance",
    "capability": "Capability",
    "timezone": "Overlap",
    "durability": "Durability",
}
PILLAR_NOTES = {
    "cost": "Blended ISCO 2/3/4 wage basket, USD, aged to a common year",
    "talent": "Employed stock in the same three ISCO groups",
    "risk": "Mean of five World Bank governance dimensions",
    "capability": "What the market demonstrably staffs, from live postings",
    "timezone": "Working hours shared with the headquarters",
    "durability": "How slowly the wage gap has been closing",
}


def _entity(m: Market, archetype: str) -> dict:
    metric = C.ARCHETYPES[archetype]["capability_metric"]
    return {
        "id": m.iso2,
        "name": m.name,
        "parent": m.parent,
        "isCity": m.is_city,
        "marketType": m.market_type,
        "cost": m.cost_usd_aged or m.cost_usd,
        "costObserved": m.cost_usd,
        "costYear": m.cost_year,
        "costLag": m.cost_lag,
        "driftMeasured": m.drift_measured,
        "drift": m.drift_used,
        "regionIndex": m.region_index,
        "regionYear": m.region_year,
        "talent": m.talent_proxy,
        "risk": m.risk_score,
        "capability": getattr(m, metric),
        "timezone": m.timezone_overlap,
        "durability": m.durability,
        "postings": m.postings_in_scope,
    }


def payload() -> dict:
    countries = build()
    cities = with_cities(countries)
    data = {
        "pillars": list(PILLARS),
        "pillarLabels": PILLAR_LABELS,
        "pillarNotes": PILLAR_NOTES,
        "colors": PILLAR_COLORS,
        "colorsDark": PILLAR_COLORS_DARK,
        "lowerIsBetter": ["cost"],
        "logScaled": ["cost", "talent"],
        "archetypes": {
            k: {"label": v["label"], "weights": v["weights"]}
            for k, v in C.ARCHETYPES.items()
        },
        "offsets": C.UTC_OFFSET,
        "workingDay": list(C.WORKING_DAY),
        "hq": C.HQ,
        "topN": C.TOP_N,
        "robustAt": C.ROBUST_AT,
        "views": {},
        "reference": {},
    }
    for archetype in C.ARCHETYPES:
        data["views"].setdefault("country", {})[archetype] = [
            _entity(m, archetype) for m in countries.values() if m.complete
        ]
        data["views"].setdefault("city", {})[archetype] = [
            _entity(m, archetype) for m in cities.values() if m.complete
        ]
        # The 10,000-draw run at the declared weights, so the page can show what
        # the study concluded next to whatever the reader is now proposing.
        stability = run(countries, archetype)
        data["reference"][archetype] = {
            k: round(v, 4) for k, v in stability.frequency.items()
        }
    return data


def build_html() -> str:
    data = json.dumps(payload(), separators=(",", ":"))
    return TEMPLATE.replace("__DATA__", data).replace("__SCORING__", SCORING_JS)


def build_artifact() -> str:
    """The same page, without the document wrapper.

    Artifacts supply their own doctype, head and body, so publishing the full
    document would nest one inside another. Everything else — styles, markup,
    script, the three-state theme tokens — is identical to the file version.
    """
    html = build_html()
    head_open = html.index("<title>")
    head_close = html.index("</head>")
    body_open = html.index("<body>") + len("<body>")
    body_close = html.rindex("</body>")
    return html[head_open:head_close].rstrip() + "\n" + html[body_open:body_close].strip() + "\n"


def main() -> None:
    path = C.ROOT / "dashboard.html"
    path.write_text(build_html())
    size = path.stat().st_size / 1024
    print(f"wrote {path.name} ({size:.0f} kB)")
    artifact = C.ROOT / "dashboard.artifact.html"
    artifact.write_text(build_artifact())
    print(f"wrote {artifact.name} ({artifact.stat().st_size / 1024:.0f} kB)")


# The scoring half of the page, kept separate so tests/test_dashboard.py can
# run exactly this code under node and compare it to src/score.py on the real
# panel. A reimplementation that nobody checks is a reimplementation that
# drifts.
SCORING_JS = r"""/* ---- scoring: mirrors src/score.py exactly ---- */
function overlapHours(id, hq) {
  const market = DATA.offsets[id];
  if (market === undefined) return null;
  const shift = market - DATA.offsets[hq];
  const [s, e] = DATA.workingDay;
  return Math.max(0, Math.min(e, e - shift) - Math.max(s, s - shift));
}

function pillarValues(rows) {
  return rows.map((r) => {
    const parentId = r.parent || r.id;
    const tz = overlapHours(parentId, state.hq);
    return { row: r, v: {
      cost: r.cost, talent: r.talent, risk: r.risk,
      capability: r.capability, timezone: tz === null ? r.timezone : tz,
      durability: r.durability,
    }};
  });
}

function normalise(items) {
  const out = items.map((it) => ({ row: it.row, s: {} }));
  for (const p of DATA.pillars) {
    let vals = items.map((it) => it.v[p]);
    if (DATA.logScaled.includes(p)) vals = vals.map((v) => Math.log(v));
    const lo = Math.min(...vals), hi = Math.max(...vals), span = hi - lo;
    vals.forEach((v, i) => {
      const unit = span === 0 ? 0.5 : (v - lo) / span;
      out[i].s[p] = DATA.lowerIsBetter.includes(p) ? 1 - unit : unit;
    });
  }
  return out;
}

function scoreAll(scaled, weights) {
  const total = DATA.pillars.reduce((a, p) => a + weights[p], 0) || 1;
  return scaled.map((it) => {
    const parts = {};
    let sum = 0;
    for (const p of DATA.pillars) {
      const c = (weights[p] * it.s[p]) / total;
      parts[p] = c; sum += c;
    }
    return { row: it.row, score: sum, parts, scaled: it.s };
  }).sort((a, b) => b.score - a.score || a.row.name.localeCompare(b.row.name));
}
"""

TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GBS Location Selection</title>
<style>
:root {
  color-scheme: light;
  --bg: #e9eae4;
  --panel: #f4f4f0;
  --panel-2: #fbfbf8;
  --ink: #121a17;
  --ink-2: #4d554f;
  --ink-3: #7d857e;
  --rule: #d3d5cc;
  --rule-strong: #b6b9ae;
  --accent: #146b54;
  --warn: #b0374a;
  --shadow: 0 1px 2px rgba(18,26,23,.06);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --bg: #14171a;
    --panel: #1c2024;
    --panel-2: #232830;
    --ink: #eef1ee;
    --ink-2: #b3bab4;
    --ink-3: #848d86;
    --rule: #2e343a;
    --rule-strong: #454d54;
    --accent: #3fa585;
    --warn: #d97186;
    --shadow: none;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --bg: #14171a; --panel: #1c2024; --panel-2: #232830;
  --ink: #eef1ee; --ink-2: #b3bab4; --ink-3: #848d86;
  --rule: #2e343a; --rule-strong: #454d54;
  --accent: #3fa585; --warn: #d97186; --shadow: none;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  font-size: 15px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}
.mono { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; }
.wrap { max-width: 1240px; margin: 0 auto; padding: 32px 24px 72px; }

header { border-bottom: 1px solid var(--rule-strong); padding-bottom: 20px; margin-bottom: 28px; }
.eyebrow {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 11px; letter-spacing: .14em; text-transform: uppercase;
  color: var(--ink-3); margin: 0 0 10px;
}
h1 { font-size: clamp(26px, 3.4vw, 38px); line-height: 1.1; margin: 0 0 12px; letter-spacing: -.02em; font-weight: 700; }
.standfirst { margin: 0; max-width: 62ch; color: var(--ink-2); font-size: 16px; }

.layout { display: grid; grid-template-columns: 310px minmax(0,1fr); gap: 32px; align-items: start; }
@media (max-width: 940px) { .layout { grid-template-columns: minmax(0,1fr); } }

.rail { position: sticky; top: 20px; display: flex; flex-direction: column; gap: 20px; }
@media (max-width: 940px) { .rail { position: static; } }
.card { background: var(--panel); border: 1px solid var(--rule); padding: 16px; box-shadow: var(--shadow); }
.card h2 {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 11px; letter-spacing: .12em; text-transform: uppercase;
  color: var(--ink-3); margin: 0 0 12px; font-weight: 600;
}

.seg { display: flex; border: 1px solid var(--rule-strong); }
.seg button {
  flex: 1; padding: 7px 8px; font: inherit; font-size: 13px; cursor: pointer;
  background: transparent; color: var(--ink-2); border: 0; border-right: 1px solid var(--rule-strong);
}
.seg button:last-child { border-right: 0; }
.seg button[aria-pressed="true"] { background: var(--accent); color: #fff; }
.seg button:focus-visible { outline: 2px solid var(--ink); outline-offset: -2px; }

.slider-row { margin-bottom: 14px; }
.slider-head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; margin-bottom: 3px; }
.slider-name { display: flex; align-items: center; gap: 7px; font-size: 13.5px; }
.swatch { width: 10px; height: 10px; flex: none; border-radius: 2px; }
.slider-val { font-family: ui-monospace, Menlo, monospace; font-size: 12.5px; color: var(--ink-2); font-variant-numeric: tabular-nums; }
.slider-note { font-size: 11.5px; color: var(--ink-3); margin: 2px 0 0; line-height: 1.35; }
input[type=range] { width: 100%; accent-color: var(--accent); margin: 2px 0 0; }

select {
  width: 100%; padding: 6px 8px; font: inherit; font-size: 13px;
  background: var(--panel-2); color: var(--ink); border: 1px solid var(--rule-strong);
}

.reads { margin: 0; font-size: 13px; color: var(--ink-2); }
.reads strong { color: var(--ink); font-weight: 600; }

.belief {
  border-left: 3px solid var(--accent); padding: 10px 12px; background: var(--panel-2);
  font-size: 13.5px; line-height: 1.45;
}
.belief b { font-weight: 600; }

.board-head { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 6px; }
.board-head h2 { margin: 0; font-size: 19px; letter-spacing: -.01em; }
.hint { font-size: 12.5px; color: var(--ink-3); margin: 0; }

.rows { position: relative; margin-top: 14px; }
.row {
  display: grid; grid-template-columns: 26px minmax(120px, 190px) minmax(0,1fr) 96px;
  gap: 12px; align-items: center; padding: 7px 0; border-bottom: 1px solid var(--rule);
}
@media (max-width: 700px) { .row { grid-template-columns: 22px 1fr; row-gap: 6px; } .row .bar-cell, .row .stab { grid-column: 1 / -1; } }
.rank { font-family: ui-monospace, Menlo, monospace; font-size: 12px; color: var(--ink-3); text-align: right; font-variant-numeric: tabular-nums; }
.who { min-width: 0; }
.who .nm { display: block; font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.who .sub { display: block; font-size: 11px; color: var(--ink-3); font-family: ui-monospace, Menlo, monospace; }
.bar { display: flex; height: 20px; width: 100%; background: var(--panel-2); border: 1px solid var(--rule); }
.seg-fill { height: 100%; border-right: 2px solid var(--panel); position: relative; }
.seg-fill:last-child { border-right: 0; }
.stab { text-align: right; font-family: ui-monospace, Menlo, monospace; font-size: 12px; font-variant-numeric: tabular-nums; }
.stab .pct { display: block; }
.stab .tag { display: block; font-size: 10px; letter-spacing: .06em; text-transform: uppercase; }
.tag.robust { color: var(--accent); }
.tag.contingent { color: var(--ink-3); }
.tag.never { color: var(--warn); }
.in-top { box-shadow: inset 3px 0 0 var(--accent); }

.legend { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 14px; font-size: 12px; color: var(--ink-2); }
.legend span { display: inline-flex; align-items: center; gap: 6px; }

details { margin-top: 26px; border-top: 1px solid var(--rule-strong); padding-top: 14px; }
summary { cursor: pointer; font-size: 13.5px; color: var(--ink-2); }
table { border-collapse: collapse; width: 100%; margin-top: 12px; font-size: 12.5px; }
th, td { text-align: right; padding: 5px 8px; border-bottom: 1px solid var(--rule); font-variant-numeric: tabular-nums; }
th:first-child, td:first-child { text-align: left; font-variant-numeric: normal; }
th { font-family: ui-monospace, Menlo, monospace; font-size: 10.5px; text-transform: uppercase; letter-spacing: .07em; color: var(--ink-3); font-weight: 600; }
caption { caption-side: top; text-align: left; font-size: 12px; color: var(--ink-3); padding-bottom: 8px; }

footer { margin-top: 40px; border-top: 1px solid var(--rule-strong); padding-top: 16px; font-size: 12.5px; color: var(--ink-3); }
footer a { color: var(--accent); }
footer p { max-width: 78ch; }

.tooltip {
  position: fixed; pointer-events: none; z-index: 9; background: var(--ink); color: var(--bg);
  padding: 7px 9px; font-size: 12px; line-height: 1.4; max-width: 260px; opacity: 0;
  transition: opacity .1s; font-family: ui-monospace, Menlo, monospace;
}
.tooltip.on { opacity: 1; }

@media (prefers-reduced-motion: no-preference) {
  .row { transition: transform .42s cubic-bezier(.22,.61,.36,1); }
}
</style>
</head>
<body>
<div class="wrap">
<header>
  <p class="eyebrow">GBS Location Selection · ten markets, six pillars</p>
  <h1>The shortlist is a function of your weights.</h1>
  <p class="standfirst">
    Move a weight and watch the ranking reorder. The stability column shows how often each
    market keeps a top-three place across 2,000 weightings drawn around wherever you have just
    put the sliders — so you can see which part of your answer is in the data and which part
    is in your opinion.
  </p>
</header>

<div class="layout">
  <aside class="rail">
    <div class="card">
      <h2>Centre type</h2>
      <div class="seg" id="archetype" role="group" aria-label="Centre type"></div>
      <p class="slider-note" style="margin-top:9px" id="archetype-note"></p>
    </div>

    <div class="card">
      <h2>Weights</h2>
      <div id="sliders"></div>
      <p class="reads" id="weight-sum"></p>
    </div>

    <div class="card">
      <h2>Headquarters</h2>
      <select id="hq" aria-label="Headquarters location"></select>
      <p class="slider-note">Sets the working-hours overlap each market is scored on.</p>
    </div>

    <div class="card">
      <h2>Resolution</h2>
      <div class="seg" id="view" role="group" aria-label="Resolution"></div>
      <p class="slider-note" id="view-note"></p>
    </div>
  </aside>

  <main>
    <div class="board-head">
      <h2 id="board-title"></h2>
      <p class="hint">Bar segments are each pillar's contribution to the score. Hover for detail.</p>
    </div>
    <div class="belief" id="belief"></div>
    <div class="rows" id="rows"></div>
    <div class="legend" id="legend"></div>

    <details>
      <summary>Table view — every number behind the ranking</summary>
      <table id="table"><caption></caption></table>
    </details>

    <footer>
      <p id="foot"></p>
    </footer>
  </main>
</div>
</div>
<div class="tooltip" id="tip" role="status"></div>

<script>
const DATA = __DATA__;
const $ = (s) => document.querySelector(s);

const state = {
  archetype: Object.keys(DATA.archetypes)[0],
  view: "country",
  hq: DATA.hq,
  weights: { ...DATA.archetypes[Object.keys(DATA.archetypes)[0]].weights },
};

const isDark = () => {
  const t = document.documentElement.getAttribute("data-theme");
  if (t) return t === "dark";
  return matchMedia("(prefers-color-scheme: dark)").matches;
};
const colors = () => (isDark() ? DATA.colorsDark : DATA.colors);

__SCORING__

/* ---- live stability: same idea as src/stability.py, fewer draws ---- */
function gamma(rng, k) {
  if (k < 1) return gamma(rng, k + 1) * Math.pow(rng(), 1 / k);
  const d = k - 1 / 3, c = 1 / Math.sqrt(9 * d);
  for (;;) {
    let x, v;
    do { x = normal(rng); v = 1 + c * x; } while (v <= 0);
    v = v * v * v;
    const u = rng();
    if (u < 1 - 0.0331 * x * x * x * x) return d * v;
    if (Math.log(u) < 0.5 * x * x + d * (1 - v + Math.log(v))) return d * v;
  }
}
let spare = null;
function normal(rng) {
  if (spare !== null) { const s = spare; spare = null; return s; }
  let u, v, s2;
  do { u = rng() * 2 - 1; v = rng() * 2 - 1; s2 = u * u + v * v; } while (s2 >= 1 || s2 === 0);
  const f = Math.sqrt((-2 * Math.log(s2)) / s2);
  spare = v * f; return u * f;
}
function mulberry(seed) {
  return function () {
    seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const CONCENTRATION = 40, DRAWS = 2000;

function stability(scaled, weights) {
  const rng = mulberry(20260821);
  const hits = new Map(scaled.map((it) => [it.row.id, 0]));
  const alpha = DATA.pillars.map((p) => Math.max(CONCENTRATION * weights[p], 0.05));
  const topN = DATA.topN;
  for (let d = 0; d < DRAWS; d++) {
    const g = alpha.map((a) => gamma(rng, a));
    const sum = g.reduce((a, b) => a + b, 0);
    const w = {}; DATA.pillars.forEach((p, i) => (w[p] = g[i] / sum));
    const ranked = scaled.map((it) => {
      let s = 0; for (const p of DATA.pillars) s += w[p] * it.s[p];
      return { id: it.row.id, s };
    }).sort((a, b) => b.s - a.s);
    for (let i = 0; i < topN && i < ranked.length; i++) hits.set(ranked[i].id, hits.get(ranked[i].id) + 1);
  }
  const out = new Map();
  for (const [k, v] of hits) out.set(k, v / DRAWS);
  return out;
}

function verdict(f) {
  if (f >= DATA.robustAt) return "robust";
  if (f >= 0.10) return "contingent";
  return "never";
}

/* ---- what your weighting believes ---- */
function belief(weights) {
  const entries = DATA.pillars.map((p) => [p, weights[p]]).sort((a, b) => b[1] - a[1]);
  const [topP, topW] = entries[0];
  const [lowP, lowW] = entries[entries.length - 1];
  const even = 1 / DATA.pillars.length;
  const lead = topW > even * 1.6
    ? `You are buying <b>${DATA.pillarLabels[topP].toLowerCase()}</b> above everything else`
    : `You are spreading weight fairly evenly, with <b>${DATA.pillarLabels[topP].toLowerCase()}</b> just ahead`;
  const drop = lowW < even * 0.4
    ? `, and you have effectively stopped pricing <b>${DATA.pillarLabels[lowP].toLowerCase()}</b>.`
    : `, with <b>${DATA.pillarLabels[lowP].toLowerCase()}</b> mattering least.`;
  return lead + drop;
}

/* ---- render ---- */
let lastPositions = new Map();

function render() {
  const rows = DATA.views[state.view][state.archetype];
  const items = pillarValues(rows);
  const scaled = normalise(items);
  const ranked = scoreAll(scaled, state.weights);
  const stab = stability(scaled, state.weights);
  const ref = DATA.reference[state.archetype];
  const C = colors();

  $("#board-title").textContent =
    `${DATA.archetypes[state.archetype].label} — ${ranked.length} candidates`;
  $("#belief").innerHTML = belief(state.weights);

  const host = $("#rows");
  const prev = new Map();
  host.querySelectorAll(".row").forEach((el) => prev.set(el.dataset.id, el.getBoundingClientRect().top));

  host.innerHTML = "";
  ranked.forEach((r, i) => {
    const f = stab.get(r.row.id) ?? 0;
    const v = verdict(f);
    const el = document.createElement("div");
    el.className = "row" + (i < DATA.topN ? " in-top" : "");
    el.dataset.id = r.row.id;

    const sub = r.row.isCity
      ? `${r.row.id} · ${(r.row.regionIndex).toFixed(2)}× national`
      : (ref[r.row.id] !== undefined ? `study run: ${(ref[r.row.id] * 100).toFixed(0)}%` : "");

    const segs = DATA.pillars.map((p) => {
      const pct = (r.parts[p] / (r.score || 1)) * 100;
      return `<div class="seg-fill" style="width:${pct.toFixed(2)}%;background:${C[p]}"
        data-p="${p}" data-name="${r.row.name}"></div>`;
    }).join("");

    el.innerHTML =
      `<div class="rank">${i + 1}</div>` +
      `<div class="who"><span class="nm">${r.row.name}</span><span class="sub">${sub}</span></div>` +
      `<div class="bar-cell"><div class="bar">${segs}</div></div>` +
      `<div class="stab"><span class="pct">${(f * 100).toFixed(0)}%</span>` +
      `<span class="tag ${v}">${v}</span></div>`;
    host.appendChild(el);
  });

  if (!matchMedia("(prefers-reduced-motion: reduce)").matches) {
    host.querySelectorAll(".row").forEach((el) => {
      const before = prev.get(el.dataset.id);
      if (before === undefined) return;
      const delta = before - el.getBoundingClientRect().top;
      if (!delta) return;
      el.style.transition = "none";
      el.style.transform = `translateY(${delta}px)`;
      requestAnimationFrame(() => {
        el.style.transition = "";
        el.style.transform = "";
      });
    });
  }

  $("#legend").innerHTML = DATA.pillars.map((p) =>
    `<span><i class="swatch" style="background:${C[p]}"></i>${DATA.pillarLabels[p]}</span>`).join("");

  renderTable(ranked, stab);
  renderFoot(rows);
}

function renderTable(ranked, stab) {
  const t = $("#table");
  const head = ["Market", ...DATA.pillars.map((p) => DATA.pillarLabels[p]), "Score", "Top-3"];
  t.querySelector("caption").textContent =
    "Normalised pillar scores (0–1, higher is better) under the current weights.";
  t.innerHTML = t.querySelector("caption").outerHTML +
    "<thead><tr>" + head.map((h) => `<th>${h}</th>`).join("") + "</tr></thead><tbody>" +
    ranked.map((r) =>
      `<tr><td>${r.row.name}</td>` +
      DATA.pillars.map((p) => `<td>${r.scaled[p].toFixed(2)}</td>`).join("") +
      `<td>${r.score.toFixed(3)}</td><td>${((stab.get(r.row.id) ?? 0) * 100).toFixed(0)}%</td></tr>`
    ).join("") + "</tbody>";
}

function renderFoot(rows) {
  const stale = rows.filter((r) => r.costLag > 1);
  const imputed = rows.filter((r) => r.driftMeasured === false);
  const cityNote = state.view === "city"
    ? " In city view only the cost pillar is city-resolved — governance, talent, capability and overlap are national figures wearing a city's name. Candidate counts differ by country (Poland contributes seven cities, Singapore one), so a top-three share is partly an artefact of how many candidates a country brings."
    : "";
  $("#foot").innerHTML =
    `Cost is aged to a common year at each market's own measured wage drift; ` +
    `${stale.length} market${stale.length === 1 ? "" : "s"} in this view carry an observation more than a year old` +
    (imputed.length ? `, and ${imputed.map((r) => r.name).join(", ")} ${imputed.length === 1 ? "has" : "have"} too short a series to measure a drift and use${imputed.length === 1 ? "s" : ""} the panel median.` : ".") +
    cityNote +
    ` Governance scores carry the World Bank's own 90% intervals, which overlap for several markets here. ` +
    `Full method and limitations in the <a href="https://github.com/morichtereur/gbs-location-selection">repository</a>.`;
}

/* ---- controls ---- */
function buildControls() {
  const seg = $("#archetype");
  seg.innerHTML = Object.entries(DATA.archetypes).map(([k, v]) =>
    `<button type="button" data-k="${k}" aria-pressed="${k === state.archetype}">${v.label.replace(" centre of excellence", " CoE")}</button>`).join("");
  seg.addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    state.archetype = b.dataset.k;
    state.weights = { ...DATA.archetypes[state.archetype].weights };
    seg.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x.dataset.k === state.archetype));
    syncSliders(); render(); noteArchetype();
  });

  const view = $("#view");
  view.innerHTML = `<button type="button" data-v="country" aria-pressed="true">Countries</button>
    <button type="button" data-v="city" aria-pressed="false">Cities</button>`;
  view.addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    state.view = b.dataset.v;
    view.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x.dataset.v === state.view));
    noteView(); render();
  });

  $("#sliders").innerHTML = DATA.pillars.map((p) => `
    <div class="slider-row">
      <div class="slider-head">
        <span class="slider-name"><i class="swatch" style="background:${DATA.colors[p]}"></i>${DATA.pillarLabels[p]}</span>
        <span class="slider-val" id="val-${p}"></span>
      </div>
      <input type="range" id="w-${p}" min="0" max="60" step="1" aria-label="${DATA.pillarLabels[p]} weight">
      <p class="slider-note">${DATA.pillarNotes[p]}</p>
    </div>`).join("");
  DATA.pillars.forEach((p) => {
    $(`#w-${p}`).addEventListener("input", (e) => {
      state.weights[p] = Number(e.target.value) / 100;
      syncSliders(false); render();
    });
  });

  const hq = $("#hq");
  const names = {};
  for (const list of Object.values(DATA.views.country)) for (const r of list) names[r.id] = r.name;
  hq.innerHTML = Object.keys(DATA.offsets).map((k) =>
    `<option value="${k}" ${k === state.hq ? "selected" : ""}>${names[k] || k.toUpperCase()}</option>`).join("");
  hq.addEventListener("change", (e) => { state.hq = e.target.value; render(); });

  syncSliders(); noteArchetype(); noteView();
}

function syncSliders(writeInputs = true) {
  const total = DATA.pillars.reduce((a, p) => a + state.weights[p], 0);
  DATA.pillars.forEach((p) => {
    if (writeInputs) $(`#w-${p}`).value = Math.round(state.weights[p] * 100);
    const share = total ? state.weights[p] / total : 0;
    $(`#val-${p}`).textContent = (share * 100).toFixed(0) + "%";
  });
  $("#weight-sum").innerHTML = total > 0
    ? `Weights are normalised to 100%. <strong>Reset</strong> by reselecting a centre type.`
    : `<strong>Every weight is zero.</strong> Raise at least one to rank anything.`;
}

function noteArchetype() {
  const w = DATA.archetypes[state.archetype].weights;
  const top = Object.entries(w).sort((a, b) => b[1] - a[1])[0][0];
  $("#archetype-note").textContent =
    `The study's declared weighting leads on ${DATA.pillarLabels[top].toLowerCase()}. Move any slider to depart from it.`;
}
function noteView() {
  $("#view-note").textContent = state.view === "country"
    ? "Ten national markets, every pillar measured at national level."
    : "Cost resolved to NUTS-2 regions for Poland, Germany, the Netherlands and Spain. The other six markets stay national.";
}

/* ---- tooltip ---- */
const tip = $("#tip");
document.addEventListener("mousemove", (e) => {
  const seg = e.target.closest(".seg-fill");
  if (!seg) { tip.classList.remove("on"); return; }
  const p = seg.dataset.p;
  tip.innerHTML = `${seg.dataset.name}<br>${DATA.pillarLabels[p]} · ${parseFloat(seg.style.width).toFixed(0)}% of score`;
  tip.style.left = Math.min(e.clientX + 14, innerWidth - 270) + "px";
  tip.style.top = (e.clientY + 16) + "px";
  tip.classList.add("on");
});

matchMedia("(prefers-color-scheme: dark)").addEventListener("change", render);
buildControls();
render();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
