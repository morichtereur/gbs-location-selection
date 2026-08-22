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
from src.panel import Market, build, with_centres
from src.fonts import face_css
from src.score import LOG_SCALED, LOWER_IS_BETTER, PILLARS
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
    "depth": "#4a3aa7",
}
PILLAR_COLORS_DARK = {
    "cost": "#3987e5",
    "talent": "#d95926",
    "risk": "#199e70",
    "capability": "#c98500",
    "timezone": "#d55181",
    "durability": "#008300",
    "depth": "#9085e9",
}
PILLAR_LABELS = {
    "cost": "Cost",
    "talent": "Talent",
    "risk": "Governance",
    "capability": "Capability",
    "timezone": "Overlap",
    "durability": "Durability",
    "depth": "Employer depth",
}
PILLAR_NOTES = {
    "cost": "Wage cost per head",
    "talent": "Size of the relevant workforce",
    "risk": "Governance and operating stability",
    "capability": "Does the city staff this kind of work",
    "timezone": "Hours shared with headquarters",
    "durability": "How slowly the cost gap is closing",
    "depth": "How many employers hire here",
}


# Shown in the interface, not only in the repository. A reader in a review
# should be able to see where every pillar comes from without leaving the page.
ASOF = "August 2026"
SOURCES = [
    {"pillar": "Cost", "name": "ILOSTAT earnings by occupation",
     "detail": "ISCO-08 2/3/4, USD, aged to a common year", "vintage": "2020–2025"},
    {"pillar": "Talent", "name": "ILOSTAT employment by occupation",
     "detail": "same three ISCO groups", "vintage": "2025"},
    {"pillar": "Governance", "name": "World Bank Worldwide Governance Indicators",
     "detail": "five dimensions with their 90% intervals", "vintage": "2024"},
    {"pillar": "Capability", "name": "Adzuna job postings",
     "detail": "GBS/GCC roles only", "vintage": "Aug 2026"},
    {"pillar": "Overlap", "name": "computed",
     "detail": "hours shared with headquarters", "vintage": "—"},
    {"pillar": "Durability", "name": "ILOSTAT, derived",
     "detail": "wage drift, split from currency", "vintage": "2015–2025"},
    {"pillar": "Employer depth", "name": "Adzuna job postings",
     "detail": "distinct employers hiring", "vintage": "Aug 2026"},
]

# Each line has to change what a reader would do with the tool. Anything that
# only explains the tool to itself was cut.
LIMITS = [
    "Only Polish cities have city-level cost. The rest use their country's, so cities within them differ on capability alone — treat that order as undetermined.",
    "Capability comes from few postings, as low as five per city. The stability column already accounts for this; the ranking below the top few is not meaningful.",
    "The GBS/GCC classifier was audited at ~80% precision. Recall is lower — descriptions are truncated, so counts are floors.",
    "One snapshot. A city hiring quietly during the fetch is under-represented; absence is weak evidence, not a verdict.",
]


def _entity(m: Market, archetype: str) -> dict:
    metric = C.ARCHETYPES[archetype]["capability_metric"]
    return {
        "id": m.iso2,
        "name": m.name,
        "parent": m.parent,
        "isCity": m.is_city,
        "marketType": m.market_type,
        "cost": m.cost_usd_aged or m.cost_usd,
        "depth": m.depth,
        "driftLcu": m.wage_cagr_lcu,
        "fxDrift": m.fx_drift,
        "costObserved": m.cost_usd,
        "costYear": m.cost_year,
        "costLag": m.cost_lag,
        "driftMeasured": m.drift_measured,
        "drift": m.drift_used,
        "regionIndex": m.region_index,
        "regionYear": m.region_year,
        "costResolved": m.cost_resolved,
        "employers": m.employers,
        "talent": m.talent_proxy,
        "risk": m.risk_score,
        "capability": getattr(m, metric),
        "timezone": m.timezone_overlap,
        "durability": m.durability,
        "postings": m.postings_in_scope,
        # Postings that qualified the city, before the work-family classifier
        # decided any of them. The threshold is applied to this.
        "postingsSeen": m.postings_seen,
        # The effective binomial behind the capability share: for a centre this
        # includes the shrinkage prior, so redrawing it cannot put back the
        # noise the shrinkage removed.
        "capN": m.capability_counts[1],
        "capP": getattr(m, metric),
    }


def payload() -> dict:
    countries = build()
    centres = with_centres(countries)
    data = {
        "pillars": list(PILLARS),
        "pillarLabels": PILLAR_LABELS,
        "pillarNotes": PILLAR_NOTES,
        "colors": PILLAR_COLORS,
        "colorsDark": PILLAR_COLORS_DARK,
        # Derived, never restated. These were hand-written lists and drifted the
        # moment a log-scaled pillar was added: Python scaled depth and the page
        # did not, so the two ranked differently.
        "lowerIsBetter": sorted(LOWER_IS_BETTER),
        "logScaled": sorted(LOG_SCALED),
        "archetypes": {
            k: {
                "label": v["label"],
                # A headline states a finding and has to stay short; the full
                # label is the control's job, not the sentence's.
                "short": v["label"].replace(" centre of excellence", " centre"),
                "weights": v["weights"],
            }
            for k, v in C.ARCHETYPES.items()
        },
        "offsets": C.UTC_OFFSET,
        # Headquarters options are independent of the scored markets: the HQ is
        # the clock, not a candidate.
        "hqGroups": {
            region: [
                {"key": k, "label": label, "offset": offset}
                for k, (label, offset) in places.items()
            ]
            for region, places in C.HQ_LOCATIONS.items()
        },
        "hqOffsets": {k: v[1] for k, v in C.HQ_BY_KEY.items()},
        # The headquarters selector needs market names, which city rows no
        # longer carry. Supplied directly rather than scraped from a view.
        "marketNames": {k: v["name"] for k, v in C.MARKETS.items()},
        "workingDay": list(C.WORKING_DAY),
        "hq": C.HQ,
        "topN": C.TOP_N,
        "robustAt": C.ROBUST_AT,
        "evidenceFloor": C.EVIDENCE_FLOOR,
        "sources": SOURCES,
        "limits": LIMITS,
        "asOf": ASOF,
        "evidenceFloor": C.EVIDENCE_FLOOR,
        "views": {},
        "reference": {},
    }
    for archetype in C.ARCHETYPES:
        # Cities only. A location decision picks a city, not a country, and a
        # ranking that mixes the two compares Kraków against Germany.
        data["views"].setdefault("city", {})[archetype] = [
            _entity(m, archetype)
            for m in centres.values()
            if m.complete and m.is_city
        ]
        # The 10,000-draw run at the declared weights, so the page can show what
        # the study concluded next to whatever the reader is now proposing.
        stability = run(
            {k: m for k, m in centres.items() if m.complete and m.is_city},
            archetype,
        )
        data["reference"][archetype] = {
            k: round(v, 4) for k, v in stability.frequency.items()
        }
    return data


def build_html() -> str:
    data = json.dumps(payload(), separators=(",", ":"))
    return (
        TEMPLATE.replace("__FONTS__", face_css())
        .replace("__DATA__", data)
        .replace("__SCORING__", SCORING_JS)
    )


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
  const shift = market - (DATA.hqOffsets[hq] ?? DATA.offsets[hq] ?? 0);
  const [s, e] = DATA.workingDay;
  return Math.max(0, Math.min(e, e - shift) - Math.max(s, s - shift));
}

function pillarValues(rows) {
  return rows.map((r) => {
    const parentId = r.parent || r.id;
    const tz = overlapHours(parentId, state.hq);
    // Built from DATA.pillars rather than a hand-written list: the last time
    // this was spelled out by hand, adding a pillar left it undefined here and
    // the page ranked on NaN while the study ranked correctly.
    const v = {};
    for (const p of DATA.pillars) v[p] = r[p];
    v.timezone = tz === null ? r.timezone : tz;
    return { row: r, v };
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
__FONTS__

/* Three families, three jobs, taken from the portfolio site so the tool and the
   work it belongs to read as one thing.
   Archivo — headings and interface. Tight, and it holds a tabular number.
   Source Serif — the argument. The standfirst and the weighting readout are
     prose making a case, and they are set as prose rather than as UI text.
   IBM Plex Mono — every measured value, label and eyebrow, so a number always
     looks like a number and never like a sentence. */
:root {
  color-scheme: light;
  --sans: Archivo, "Helvetica Neue", Arial, sans-serif;
  --serif: "Source Serif 4", Georgia, "Times New Roman", serif;
  --mono: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
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
  font-family: var(--sans);
  font-size: 15px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}
.mono { font-family: var(--mono); }
.wrap { max-width: 1240px; margin: 0 auto; padding: 32px 24px 72px; }

header { border-bottom: 1px solid var(--rule-strong); padding-bottom: 20px; margin-bottom: 28px; }
.eyebrow {
  font-family: var(--mono);
  font-size: 11px; letter-spacing: .14em; text-transform: uppercase;
  color: var(--ink-3); margin: 0 0 10px;
}
h1 {
  font-family: var(--sans); font-weight: 700;
  font-size: clamp(27px, 3.6vw, 40px); line-height: 1.08;
  letter-spacing: -.026em; margin: 0 0 12px; text-wrap: balance; max-width: 24ch;
}
.standfirst {
  font-family: var(--serif); margin: 0; max-width: 58ch;
  color: var(--ink-2); font-size: 16.5px; line-height: 1.5; text-wrap: pretty;
}

.layout { display: grid; grid-template-columns: 310px minmax(0,1fr); gap: 32px; align-items: start; }
@media (max-width: 940px) { .layout { grid-template-columns: minmax(0,1fr); } }

.rail { position: sticky; top: 20px; display: flex; flex-direction: column; gap: 20px; }
@media (max-width: 940px) { .rail { position: static; } }
.card { background: transparent; border: 0; border-top: 1px solid var(--rule-strong); padding: 14px 0 0; box-shadow: none; }
.card h2 {
  font-family: var(--mono);
  font-size: 10.5px; letter-spacing: .14em; text-transform: uppercase;
  color: var(--ink-3); margin: 0 0 12px; font-weight: 500;
}
.rail { gap: 22px; }

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
.slider-val { font-family: var(--mono); font-size: 12.5px; color: var(--ink-2); font-variant-numeric: tabular-nums; }
.slider-note { font-size: 11.5px; color: var(--ink-3); margin: 2px 0 0; line-height: 1.35; }
input[type=range] { width: 100%; accent-color: var(--accent); margin: 2px 0 0; }

select {
  width: 100%; padding: 6px 8px; font: inherit; font-size: 13px;
  background: var(--panel-2); color: var(--ink); border: 1px solid var(--rule-strong);
}

.reads { margin: 0; font-size: 13px; color: var(--ink-2); }
.reads strong { color: var(--ink); font-weight: 600; }

.belief {
  font-family: var(--serif); border-left: 2px solid var(--accent);
  padding: 2px 0 2px 14px; margin-top: 4px;
  font-size: 15.5px; line-height: 1.5; color: var(--ink-2);
}
.belief b { font-weight: 600; color: var(--ink); }

/* Exhibit framing: a label, a title that states the reading rather than naming
   the chart, and a source line under the body. */
.exhibit-head { border-top: 2px solid var(--ink); padding-top: 10px; margin-bottom: 4px; }
.exhibit-label {
  font-family: var(--mono); font-size: 10px; letter-spacing: .16em;
  text-transform: uppercase; color: var(--ink-3); margin: 0 0 6px;
}
.exhibit-head h2 {
  margin: 0; font-size: 19.5px; font-weight: 600; letter-spacing: -.014em;
  line-height: 1.25; text-wrap: balance; max-width: 54ch;
}
.hint { font-size: 12px; color: var(--ink-3); margin: 6px 0 0; }
.exhibit-source {
  font-family: var(--mono); font-size: 10.5px; line-height: 1.5; color: var(--ink-3);
  margin: 12px 0 0; padding-top: 9px; border-top: 1px solid var(--rule);
  max-width: 92ch;
}

.col-head {
  display: grid; grid-template-columns: 26px minmax(112px, 180px) minmax(0,1fr) 62px 92px;
  gap: 12px; margin-top: 18px; padding-bottom: 5px;
  border-bottom: 1px solid var(--rule-strong);
}
.ch-num {
  text-align: right; font-family: var(--mono); font-size: 10px;
  text-transform: uppercase; letter-spacing: .07em; color: var(--ink-3);
}
@media (max-width: 780px) { .col-head { display: none; } }
.rows { position: relative; margin-top: 0; }
.row {
  display: grid; grid-template-columns: 26px minmax(112px, 180px) minmax(0,1fr) 62px 92px;
  gap: 14px; align-items: center; padding: 11px 0; border-bottom: 1px solid var(--rule);
}
@media (max-width: 780px) {
  .row { grid-template-columns: 22px 1fr auto; row-gap: 6px; }
  .row .bar-cell { grid-column: 1 / -1; }
}
.evidence { text-align: right; font-family: var(--mono); font-size: 12px;
  color: var(--ink-3); font-variant-numeric: tabular-nums; }
.evidence .thin { color: var(--warn); }
.rank { font-family: var(--mono); font-size: 12px; color: var(--ink-3); text-align: right; font-variant-numeric: tabular-nums; }
.who { min-width: 0; }
.who .nm {
  display: block; font-size: 15.5px; font-weight: 600; letter-spacing: -.008em;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.who .sub { display: block; font-size: 10.5px; color: var(--ink-3); font-family: var(--mono); }
.bar { display: flex; height: 22px; width: 100%; background: var(--panel-2); border: 1px solid var(--rule); }
.seg-fill { height: 100%; border-right: 2px solid var(--panel); position: relative; }
.seg-fill:last-child { border-right: 0; }
.stab { text-align: right; font-family: var(--mono); font-size: 12px; font-variant-numeric: tabular-nums; }
.stab .pct { display: block; }
.stab .tag { display: block; font-size: 10px; letter-spacing: .06em; text-transform: uppercase; }
.tag.robust { color: var(--accent); }
.tag.contingent { color: var(--ink-3); }
.tag.never { color: var(--warn); }
.in-top { box-shadow: inset 3px 0 0 var(--accent); }

.sources { margin: 0; display: grid; gap: 9px; }
.sources div { display: grid; gap: 1px; }
.sources dt {
  font-family: var(--mono); font-size: 10px; text-transform: uppercase;
  letter-spacing: .07em; color: var(--ink-3);
}
.sources dd { margin: 0; font-size: 12.5px; line-height: 1.35; }
.sources .vint { color: var(--ink-3); font-size: 11.5px; }

.legend { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 14px; font-size: 12px; color: var(--ink-2); }
.legend span { display: inline-flex; align-items: center; gap: 6px; }

.table-actions { display: flex; align-items: center; gap: 12px; margin-top: 12px; }
.table-actions button {
  font: inherit; font-size: 12.5px; padding: 5px 11px; cursor: pointer;
  background: var(--panel); color: var(--ink); border: 1px solid var(--rule-strong);
}
.table-actions button:hover { border-color: var(--accent); color: var(--accent); }
.table-actions button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.copy-status { font-size: 12px; color: var(--ink-3); }
.table-scroll { overflow-x: auto; }

.method { font-size: 13.5px; line-height: 1.55; max-width: 78ch; }
.method h3 {
  font-family: var(--mono); font-size: 10.5px; text-transform: uppercase;
  letter-spacing: .09em; color: var(--ink-3); margin: 16px 0 6px; font-weight: 600;
}
.method ol, .method ul { margin: 0; padding-left: 18px; display: grid; gap: 7px; }
.method li { color: var(--ink-2); }

@media print {
  .rail, .table-actions, .hint { display: none; }
  .layout { grid-template-columns: minmax(0,1fr); }
  details { break-inside: avoid; }
  details > summary { display: none; }
  details > * { display: revert; }
  body { background: #fff; }
}

details { margin-top: 26px; border-top: 1px solid var(--rule-strong); padding-top: 14px; }
summary { cursor: pointer; font-size: 13.5px; color: var(--ink-2); }
table { border-collapse: collapse; width: 100%; margin-top: 12px; font-size: 12.5px; }
th, td { text-align: right; padding: 5px 8px; border-bottom: 1px solid var(--rule); font-variant-numeric: tabular-nums; }
th:first-child, td:first-child { text-align: left; font-variant-numeric: normal; }
th { font-family: var(--mono); font-size: 10.5px; text-transform: uppercase; letter-spacing: .07em; color: var(--ink-3); font-weight: 600; }
caption { caption-side: top; text-align: left; font-size: 12px; color: var(--ink-3); padding-bottom: 8px; }

footer { margin-top: 40px; border-top: 1px solid var(--rule-strong); padding-top: 16px; font-size: 12.5px; color: var(--ink-3); }
footer a { color: var(--accent); }
footer p { max-width: 78ch; }

.tooltip {
  position: fixed; pointer-events: none; z-index: 9; background: var(--ink); color: var(--bg);
  padding: 7px 9px; font-size: 12px; line-height: 1.4; max-width: 260px; opacity: 0;
  transition: opacity .1s; font-family: var(--mono);
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
  <p class="eyebrow"><span id="scope"></span> · <span id="asof"></span></p>
  <h1 id="headline">Which city, and how sure can you be?</h1>
  <p class="standfirst" id="takeaway"></p>
</header>

<div class="layout">
  <aside class="rail">
    <div class="card">
      <h2>Centre type</h2>
      <div class="seg" id="archetype" role="group" aria-label="Centre type"></div>
    </div>

    <div class="card">
      <h2>Weights</h2>
      <div id="sliders"></div>
      <p class="reads" id="weight-sum"></p>
    </div>

    <div class="card">
      <h2>Headquarters</h2>
      <select id="hq" aria-label="Headquarters location"></select>
      <p class="slider-note">Sets the hours each city is scored on sharing with you.</p>
    </div>

    <div class="card">
      <h2>Where the numbers come from</h2>
      <dl class="sources" id="sources"></dl>
    </div>
  </aside>

  <main>
    <div class="exhibit-head">
      <p class="exhibit-label">Exhibit 1</p>
      <h2 id="board-title"></h2>
      <p class="hint">Bar segments are pillar contributions. Hover for detail.</p>
    </div>
    <div class="belief" id="belief"></div>
    <div class="col-head">
      <span></span><span></span><span></span>
      <span class="ch-num">postings</span><span class="ch-num">top-3 across reweightings</span>
    </div>
    <div class="rows" id="rows"></div>
    <div class="legend" id="legend"></div>

    <p class="exhibit-source" id="exhibit-source"></p>

    <details>
      <summary>Table view — every number behind the ranking</summary>
      <div class="table-actions">
        <button type="button" id="copy">Copy table</button>
        <span class="copy-status" id="copy-status" role="status"></span>
      </div>
      <div class="table-scroll"><table id="table"><caption></caption></table></div>
    </details>

    <details>
      <summary>Method, and what this cannot tell you</summary>
      <div class="method">
        <ul>
          <li>Scores are relative to the cities on screen, not absolute ratings.</li>
          <li><strong>Robust</strong> means a top-three place in 90% of 2,000 reweightings
              <em>and</em> at least <span id="floor-n"></span> postings behind it.</li>
        </ul>
        <h3>Limits</h3>
        <ul id="limits"></ul>
      </div>
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
  view: "city",
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

/* Weights are not the only thing that is uncertain, and on the centre view they
   are not even the important one: centres inside one country share every pillar
   except capability, so a run that varies only the weights can never reorder
   them and reports a hard 100%/0% split the study does not support. Each draw
   therefore also redraws every capability share from its own binomial and
   re-normalises that pillar, matching src/stability.py.

   The redraw uses a normal approximation to the binomial rather than summing
   Bernoulli trials — with the shrinkage prior every effective n is at least 35,
   where the approximation is close, and the exact version would cost seventeen
   million draws per slider move. */
function stability(base, weights) {
  const rng = mulberry(20260821);
  const hits = new Map(base.map((it) => [it.row.id, 0]));
  const alpha = DATA.pillars.map((p) => Math.max(CONCENTRATION * weights[p], 0.05));
  const topN = DATA.topN;
  const others = DATA.pillars.filter((p) => p !== "capability");
  const caps = new Float64Array(base.length);

  for (let d = 0; d < DRAWS; d++) {
    const g = alpha.map((a) => gamma(rng, a));
    const gsum = g.reduce((a, b) => a + b, 0);
    const w = {}; DATA.pillars.forEach((p, i) => (w[p] = g[i] / gsum));

    let lo = Infinity, hi = -Infinity;
    for (let i = 0; i < base.length; i++) {
      const row = base[i].row;
      const n = row.capN || 0, pHat = row.capP ?? 0;
      let draw = pHat;
      if (n > 0) {
        const sd = Math.sqrt(Math.max(pHat * (1 - pHat), 0) / n);
        draw = Math.min(1, Math.max(0, pHat + normal(rng) * sd));
      }
      caps[i] = draw;
      if (draw < lo) lo = draw;
      if (draw > hi) hi = draw;
    }
    const span = hi - lo;

    const ranked = base.map((it, i) => {
      let s = w.capability * (span === 0 ? 0.5 : (caps[i] - lo) / span);
      for (const p of others) s += w[p] * it.s[p];
      return { id: it.row.id, s };
    }).sort((a, b) => b.s - a.s);
    for (let i = 0; i < topN && i < ranked.length; i++) {
      hits.set(ranked[i].id, hits.get(ranked[i].id) + 1);
    }
  }
  const out = new Map();
  for (const [k, v] of hits) out.set(k, v / DRAWS);
  return out;
}

/* "Robust" is a claim about evidence, not just arithmetic: Mumbai reached 90% of
   weightings on six postings, edging a centre with twenty by two points of a
   shrunk share. A candidate below the evidence floor is capped at contingent
   however often it survives. Mirrors Stability.verdict in src/stability.py. */
function verdict(f, row) {
  const thin = row && row.isCity && row.postings != null
    && row.postings < DATA.evidenceFloor;
  if (f >= DATA.robustAt && !thin) return "robust";
  if (f >= 0.10) return "contingent";
  return "never";
}

/* ---- answer first ----
   A consulting exhibit leads with the finding, not the subject, and the finding
   here changes every time a weight moves. The headline is therefore written
   from the current result rather than fixed in the markup: what survives, and
   what it would take to believe otherwise. */
function writeHeadline(ranked, stab) {
  const robust = ranked.filter((r) => verdict(stab.get(r.row.id) ?? 0, r.row) === "robust");
  const lead = ranked[0];
  const arch = DATA.archetypes[state.archetype].short.toLowerCase();

  let headline;
  if (robust.length === 1) {
    headline = `Only ${robust[0].row.name} survives a change of mind.`;
  } else if (robust.length > 1) {
    const names = robust.slice(0, 3).map((r) => r.row.name);
    headline = `${names.join(", ")} survive a change of mind.`;
  } else {
    headline = `No city holds up as a ${arch}.`;
  }
  $("#headline").textContent = headline;

  const pct = ((stab.get(lead.row.id) ?? 0) * 100).toFixed(0);
  const where = DATA.marketNames[lead.row.parent] || "";
  $("#takeaway").innerHTML = robust.length
    ? `<strong>${lead.row.name}</strong> (${where}) leads and holds a top-three place in `
      + `${pct}% of 2,000 nearby weightings.`
    : `<strong>${lead.row.name}</strong> (${where}) leads on your weighting but holds a `
      + `top-three place in only ${pct}% of 2,000 nearby ones — the ranking is yours, not the evidence's.`;
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
  const rows = DATA.views.city[state.archetype];
  const items = pillarValues(rows);
  const scaled = normalise(items);
  const ranked = scoreAll(scaled, state.weights);
  const stab = stability(scaled, state.weights);
  const ref = DATA.reference[state.archetype];
  const C = colors();

  writeHeadline(ranked, stab);
  $("#board-title").textContent =
    `${DATA.archetypes[state.archetype].label}: ${ranked.length} cities ranked on your weighting`;
  $("#scope").textContent = `${rows.length} GBS and GCC cities`;
  $("#belief").innerHTML = belief(state.weights);

  const host = $("#rows");
  const prev = new Map();
  host.querySelectorAll(".row").forEach((el) => prev.set(el.dataset.id, el.getBoundingClientRect().top));

  host.innerHTML = "";
  ranked.forEach((r, i) => {
    const f = stab.get(r.row.id) ?? 0;
    const v = verdict(f, r.row);
    const el = document.createElement("div");
    el.className = "row" + (i < DATA.topN ? " in-top" : "");
    el.dataset.id = r.row.id;

    // The country first: a reader should not have to know where Poznań is to
    // read the ranking.
    const where = DATA.marketNames[r.row.parent] || "";
    const costNote = r.row.costResolved
      ? `cost ${(r.row.regionIndex).toFixed(2)}× national`
      : "country cost";
    const sub = `${where} · ${r.row.employers} employers · ${costNote}`;

    const segs = DATA.pillars.map((p) => {
      const pct = (r.parts[p] / (r.score || 1)) * 100;
      return `<div class="seg-fill" style="width:${pct.toFixed(2)}%;background:${C[p]}"
        data-p="${p}" data-name="${r.row.name}"></div>`;
    }).join("");

    const n = r.row.postings;
    const thin = r.row.isCity && n != null && n < DATA.evidenceFloor;
    const evidence = n == null ? "—"
      : `<span class="${thin ? "thin" : ""}">${n}</span>`;

    el.innerHTML =
      `<div class="rank">${i + 1}</div>` +
      `<div class="who"><span class="nm">${r.row.name}</span><span class="sub">${sub}</span></div>` +
      `<div class="bar-cell"><div class="bar">${segs}</div></div>` +
      `<div class="evidence" title="postings behind the capability pillar">${evidence}</div>` +
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
  renderSource(rows);
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

/* Every exhibit carries its own source. A reader should not have to open a
   panel to learn what the numbers are made of. */
function renderSource(rows) {
  const resolved = rows.filter((r) => r.costResolved).length;
  const thin = rows.filter((r) => r.postings != null && r.postings < DATA.evidenceFloor).length;
  $("#exhibit-source").innerHTML =
    `Source: ILOSTAT earnings and employment by occupation; World Bank Worldwide Governance ` +
    `Indicators; Eurostat regional accounts; ${rows.length} cities from a GBS/GCC job-posting ` +
    `sample, ${DATA.asOf}. ` +
    `Note: ${resolved} of ${rows.length} cities have city-level cost, the rest their country's; ` +
    `${thin} rest on fewer than ${DATA.evidenceFloor} postings and cannot be called robust.`;
}

function renderFoot(rows) {
  const resolved = rows.filter((r) => r.costResolved).length;
  $("#foot").innerHTML =
    `${resolved} of ${rows.length} cities have city-level cost; the rest use their country's. ` +
    `<a href="https://github.com/morichtereur/gbs-location-selection">Method and code</a>.`;
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
    syncSliders(); render();
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

  // Grouped by region and labelled with the offset, because the whole point of
  // the control is the time difference it implies.
  const hq = $("#hq");
  hq.innerHTML = Object.entries(DATA.hqGroups).map(([region, places]) =>
    `<optgroup label="${region}">` + places.map((x) => {
      const sign = x.offset < 0 ? "\u2212" : "+";
      const abs = Math.abs(x.offset);
      const off = Number.isInteger(abs) ? abs : abs.toFixed(1);
      return `<option value="${x.key}" ${x.key === state.hq ? "selected" : ""}>`
           + `${x.label} (UTC${sign}${off})</option>`;
    }).join("") + `</optgroup>`).join("");
  hq.addEventListener("change", (e) => { state.hq = e.target.value; render(); });

  $("#sources").innerHTML = DATA.sources.map((x) => `
    <div>
      <dt>${x.pillar}</dt>
      <dd>${x.name}<br><span class="vint">${x.detail} · ${x.vintage}</span></dd>
    </div>`).join("");
  $("#limits").innerHTML = DATA.limits.map((x) => `<li>${x}</li>`).join("");
  $("#asof").textContent = `${DATA.pillars.length} pillars · ${DATA.asOf}`;
  $("#floor-n").textContent = DATA.evidenceFloor;

  $("#copy").addEventListener("click", copyTable);

  syncSliders();
}

/* Viewers cannot be handed a file — a download started by the page is blocked
   in the contexts this is published to — so the table leaves as text on the
   clipboard, which pastes straight into a document or a spreadsheet. */
async function copyTable() {
  const table = $("#table");
  const rows = [...table.querySelectorAll("tr")].map((tr) =>
    [...tr.querySelectorAll("th,td")].map((c) => c.textContent.trim()).join("\t")
  ).join("\n");
  const status = $("#copy-status");
  try {
    await navigator.clipboard.writeText(rows);
    status.textContent = "Copied — paste into a document or spreadsheet.";
  } catch {
    const area = document.createElement("textarea");
    area.value = rows;
    document.body.appendChild(area);
    area.select();
    const ok = document.execCommand("copy");
    area.remove();
    status.textContent = ok
      ? "Copied — paste into a document or spreadsheet."
      : "Copying is blocked here. Select the table and press Ctrl-C.";
  }
  setTimeout(() => (status.textContent = ""), 4000);
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

/* Series colours are chosen in JavaScript, so they only change when the page
   re-renders. Watching the media query alone covers the operating system
   changing theme and misses the other route: a viewer flipping the host's own
   toggle, which stamps data-theme on the root element. Both are watched, or the
   bars keep the previous theme's ramp against the new background. */
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", render);
new MutationObserver(render).observe(document.documentElement, {
  attributes: true, attributeFilter: ["data-theme"],
});
buildControls();
render();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
