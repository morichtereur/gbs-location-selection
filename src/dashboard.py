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
from src.baselines import load as baseline_load
from src.operators import by_city as operators_by_city, title as operator_title
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
# A glyph per pillar, stroked in the pillar's own colour: the reader gets the
# meaning and the colour key in one mark instead of an anonymous square. Drawn
# inline rather than pulled from an icon set, because the page loads nothing
# external and a 24-glyph dependency for seven marks is not worth it.
# Emoji flags fall back to letter pairs on Windows and in headless Chrome's PDF,
# which is where this has to survive. Drawn instead, at a common 3:2 so eleven of
# them stack without a ragged edge.
FLAGS = {
    "in": '<rect width="21" height="4.67" fill="#ff9933"/>'
          '<rect y="4.67" width="21" height="4.66" fill="#fff"/>'
          '<rect y="9.33" width="21" height="4.67" fill="#138808"/>'
          '<circle cx="10.5" cy="7" r="1.75" fill="none" stroke="#000080" stroke-width=".5"/>'
          '<path d="M10.5 5.25v3.5M8.75 7h3.5M9.26 5.76l2.48 2.48M11.74 5.76L9.26 8.24" '
          'stroke="#000080" stroke-width=".28"/>',
    "pl": '<rect width="21" height="7" fill="#fff"/>'
          '<rect y="7" width="21" height="7" fill="#dc143c"/>',
    "br": '<rect width="21" height="14" fill="#009c3b"/>'
          '<path d="M10.5 1.6L19.4 7l-8.9 5.4L1.6 7z" fill="#ffdf00"/>'
          '<circle cx="10.5" cy="7" r="3.1" fill="#002776"/>'
          '<path d="M7.6 5.9a9 9 0 0 1 5.9 1.9" fill="none" stroke="#fff" stroke-width=".62"/>',
    "za": '<rect width="21" height="14" fill="#002395"/>'
          '<path d="M0 0h21v5.6H0z" fill="#de3831"/>'
          '<path d="M0 4.6h21v1H0zM0 8.4h21v1H0z" fill="#fff"/>'
          '<path d="M0 0l7 7-7 7z" fill="#fff"/>'
          '<path d="M0 1.9l5.1 5.1L0 12.1z" fill="#000"/>'
          '<path d="M0 5.1h21v3.8H0z" fill="#007a4d" opacity="0"/>'
          '<path d="M8.4 5.1H21v3.8H8.4L4.5 7z" fill="#007a4d"/>',
}
FLAG_TITLES = {"in": "India", "pl": "Poland", "br": "Brazil", "za": "South Africa"}

PILLAR_ICONS = {
    # Coin.
    "cost": '<circle cx="8" cy="8" r="6"/><path d="M8 5v6M6.3 6.4h3.4M6.3 9.6h3.4"/>',
    # Three figures.
    "talent": '<circle cx="5" cy="6" r="1.8"/><circle cx="11" cy="6" r="1.8"/>'
              '<path d="M2 13c0-1.9 1.4-3.2 3-3.2s3 1.3 3 3.2M8 13c0-1.9 1.4-3.2 3-3.2s3 1.3 3 3.2"/>',
    # Shield.
    "risk": '<path d="M8 2l5 2v4.2c0 3-2.1 5.6-5 6.6-2.9-1-5-3.6-5-6.6V4z"/>',
    # Checked box.
    "capability": '<rect x="2.5" y="2.5" width="11" height="11" rx="1"/>'
                  '<path d="M5.4 8.2l1.9 1.9 3.4-3.9"/>',
    # Clock.
    "timezone": '<circle cx="8" cy="8" r="6"/><path d="M8 4.6V8l2.5 1.6"/>',
    # Hourglass. An arrow would imply a direction, and this pillar is about a
    # gap holding rather than a number rising.
    "durability": '<path d="M4 2.5h8M4 13.5h8M4.6 2.5c0 3 2.6 4.2 3.4 5.5'
                  '.8-1.3 3.4-2.5 3.4-5.5M4.6 13.5c0-3 2.6-4.2 3.4-5.5'
                  '.8 1.3 3.4 2.5 3.4 5.5"/>',
    # Three premises on a street: several employers, not one large one.
    "depth": '<path d="M1.5 13.5h13M3 13.5V7l2.5-1.6V13.5M7 13.5V4.5l2.5-1.7'
             'V13.5M11 13.5V8l2.5-1.5V13.5"/>',
}

PILLAR_NOTES = {
    # Phrased as what raising the slider does. "Wage cost per head" describes
    # the pillar; it does not tell a reader what setting it to 30% means.
    "cost": "Favours cheaper labour",
    "talent": "Favours a larger relevant workforce",
    "risk": "Favours stable, well-governed markets",
    "capability": "Favours cities already doing this work",
    "timezone": "Favours cities inside your working day",
    "durability": "Favours markets whose cost gap is closing slowly",
    "depth": "Favours markets where more employers hire",
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
    "The GBS/GCC classifier was audited five times over a hundred postings; two of the last twenty were clearly wrong. That error rate is modelled in the stability column, not just noted.",
    "One snapshot. A city hiring quietly during the fetch is under-represented; absence is weak evidence, not a verdict.",
    # The first question any GBS room asks is where Manila is. Better that the
    # exhibit answers it than that the audience finds the hole.
    "Exhibit 3 subtracts a national baseline from cities that sometimes carry a regional index, so a capital-city premium sits on one side of it and not the other. Warsaw against a UK baseline is the clearest case: it reads as dearer than the UK, which is partly Mazowieckie against a British national mean rather than a wage fact.",
    "Exhibit 3 is a wage line, not a business case. It excludes facilities, technology, management overhead, transition and severance, and holds headcount one-for-one. Read it as the upper bound on one component of the saving.",
    "Six established locations are absent because the postings feed does not reach them: Manila, Kuala Lumpur, Bucharest, Prague, Budapest and Lisbon. The ranking is therefore within the cities shown, not against every credible alternative.",
]


def _entity(m: Market, archetype: str, operators: dict | None = None) -> dict:
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
        # The raw work mix behind the capability pillar. It decides whether a
        # city suits arbitrage or value work, and was visible only as a
        # normalised score.
        "mixTransactional": m.transactional_share,
        "mixRaw": m.capability_raw,
        "costPpp": m.cost_ppp_aged or m.cost_ppp,
        "languageShare": m.language_share,
        "languages": list(m.languages or ()),
        # Who already runs a centre here, recruiters removed. The question a
        # room always asks, answered without another source.
        "operators": (operators or {}).get((m.parent, m.name), []),
        # Postings that qualified the city, before the work-family classifier
        # decided any of them. The threshold is applied to this.
        "postingsSeen": m.postings_seen,
        # The effective binomial behind the capability share: for a centre this
        # includes the shrinkage prior, so redrawing it cannot put back the
        # noise the shrinkage removed.
        "capN": m.capability_counts[1],
        "capP": getattr(m, metric),
        # What a wrongly admitted posting most likely is, for this market and
        # this archetype's metric. Needed to undo classification error.
        "contaminant": (
            m.contaminant_transactional
            if metric == "transactional_share"
            else (1.0 - m.contaminant_transactional)
        ) if m.contaminant_transactional is not None else None,
    }


def payload() -> dict:
    operators = {
        key: [operator_title(n) for n, _ in ops]
        for key, ops in operators_by_city().items()
    }
    countries = build()
    baselines = baseline_load()
    centres = with_centres(countries)
    data = {
        "pillars": list(PILLARS),
        "pillarLabels": PILLAR_LABELS,
        "pillarNotes": PILLAR_NOTES,
        "colors": PILLAR_COLORS,
        "icons": PILLAR_ICONS,
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
                "short": v["label"].lower(),
            "blurb": v["blurb"],
            "why": v["why"],
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
        "separableAt": C.SEPARABLE_AT,
        "auditCorrect": C.AUDIT_CORRECT,
        "auditTotal": C.AUDIT_TOTAL,
        "modelClassificationError": C.MODEL_CLASSIFICATION_ERROR,
        "sources": SOURCES,
        "limits": LIMITS,
        "flags": FLAGS,
        "flagTitles": FLAG_TITLES,
        "baselines": baselines,
        "baselineDefault": C.BASELINE_DEFAULT,
        "fteDefault": C.FTE_DEFAULT,
        "asOf": ASOF,
        "evidenceFloor": C.EVIDENCE_FLOOR,
        "separableAt": C.SEPARABLE_AT,
        "auditCorrect": C.AUDIT_CORRECT,
        "auditTotal": C.AUDIT_TOTAL,
        "modelClassificationError": C.MODEL_CLASSIFICATION_ERROR,
        "views": {},
        "reference": {},
    }
    for archetype in C.ARCHETYPES:
        # Cities only. A location decision picks a city, not a country, and a
        # ranking that mixes the two compares Kraków against Germany.
        data["views"].setdefault("city", {})[archetype] = [
            _entity(m, archetype, operators)
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
/* A title block: the finding on the left, changing as weights move; what the
   tool is on the right, fixed. The header was a narrow column against half a
   page of empty space. */
.title-block {
  display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr);
  gap: 44px; align-items: start;
}
@media (max-width: 900px) { .title-block { grid-template-columns: minmax(0,1fr); gap: 16px; } }
.deck { border-left: 1px solid var(--rule-strong); padding-left: 20px; }
.deck p {
  margin: 0 0 8px; font-size: 13px; line-height: 1.55; color: var(--ink-3);
  max-width: 52ch;
}
.deck p:last-child { margin-bottom: 0; }

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

.blurb {
  font-size: 12px; line-height: 1.45; color: var(--ink-2);
  border-left: 2px solid var(--rule-strong); padding: 1px 0 1px 10px;
  margin: 10px 0 4px;
}
.panel-note {
  font-size: 11.5px; line-height: 1.4; color: var(--ink-3);
  margin: -4px 0 14px;
}
.slider-row { margin-bottom: 14px; }
.slider-head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; margin-bottom: 3px; }
.slider-name { display: flex; align-items: center; gap: 7px; font-size: 13.5px; }
.swatch { width: 10px; height: 10px; flex: none; border-radius: 2px; }
.ico {
  width: 15px; height: 15px; flex: none; fill: none;
  stroke-width: 1.4; stroke-linecap: round; stroke-linejoin: round;
}
.slider-val { font-family: var(--mono); font-size: 12.5px; color: var(--ink-2); font-variant-numeric: tabular-nums; }
.slider-note { font-size: 11.5px; color: var(--ink-3); margin: 2px 0 0; line-height: 1.35; }
.track { position: relative; }
input[type=range] { width: 100%; accent-color: var(--accent); margin: 2px 0 0; display: block; }
/* Where the chosen centre type put this weight, so departure is visible. */
.preset {
  position: absolute; top: 1px; width: 1px; height: 13px;
  background: var(--ink-3); opacity: .55; pointer-events: none;
}
.slider-val .was { color: var(--ink-3); font-size: 11px; }

select {
  width: 100%; padding: 6px 8px; font: inherit; font-size: 13px;
  background: var(--panel-2); color: var(--ink); border: 1px solid var(--rule-strong);
}

.reads { margin: 0; font-size: 12px; color: var(--ink-3); }
#reset-weights {
  font: inherit; font-size: 12px; padding: 4px 10px; cursor: pointer;
  background: var(--panel-2); color: var(--ink); border: 1px solid var(--rule-strong);
}
#reset-weights:hover { border-color: var(--accent); color: var(--accent); }
#reset-weights:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
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
/* The overlap pillar is geographic and was invisible: a number in a column.
   Placing the cities on a clock relative to the headquarters shows why India is
   a handover and Poland is a shared day — which is the pillar, drawn. */
.strip-wrap { margin-top: 26px; border-top: 1px solid var(--rule-strong); padding-top: 10px; }
.strip-title {
  margin: 0 0 12px; font-size: 14px; font-weight: 600; letter-spacing: -.01em;
}
/* The ranking answers "where"; this answers "what it is worth", which is the
   question that follows it in every room. One hue for a saving, the warn tone
   for a city above the baseline — a magnitude chart that can go negative. */
.case-row {
  display: grid; grid-template-columns: 8.5rem 1fr 7.5rem;
  align-items: center; gap: 10px; padding: 3px 0;
}
.case-row .cn { font-size: 12.5px; color: var(--ink-2); }
.flag {
  width: 15px; height: 10px; margin-right: 7px; vertical-align: -1px;
  border: .5px solid rgba(0,0,0,.22); border-radius: 1px; flex: none;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}
:root[data-theme="dark"] .flag { border-color: rgba(255,255,255,.28); }
.case-track { position: relative; height: 15px; }
.case-bar { position: absolute; top: 0; bottom: 0; background: var(--accent); border-radius: 0 3px 3px 0; }
.case-bar.over { background: var(--warn); border-radius: 3px 0 0 3px; }
.case-zero { position: absolute; top: -3px; bottom: -3px; width: 1px; background: var(--rule-strong); }
.case-val {
  font-family: var(--mono); font-size: 11.5px; text-align: right;
  font-variant-numeric: tabular-nums; color: var(--ink);
}
.case-val .per { display: block; font-size: 10px; color: var(--ink-3); }
/* The limitations sat behind a disclosure triangle at the foot of the page,
   which is where a reader looks last and a sceptic looks first. Public evidence
   running out is the finding here, so it is set beside the exhibits, in their
   register, rather than confessed at the bottom. */
.settles { margin-top: 26px; border-top: 1px solid var(--rule-strong); padding-top: 10px; }
.settles-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 26px; margin-top: 10px; }
.settles h4 {
  margin: 0 0 7px; font-size: 11px; font-weight: 600; letter-spacing: .05em;
  text-transform: uppercase; color: var(--ink-2);
}
.settles .not h4 { color: var(--warn); }
.settles ul { margin: 0; padding: 0; list-style: none; }
.settles li {
  font-size: 12.5px; line-height: 1.45; color: var(--ink-2);
  padding: 0 0 7px 15px; position: relative;
}
.settles li::before {
  content: ""; position: absolute; left: 0; top: 7px;
  width: 6px; height: 6px; border-radius: 50%; background: var(--accent);
}
.settles .not li::before {
  background: none; border-top: 1.5px solid var(--warn); height: 0; top: 9px;
}
.settles b { color: var(--ink); font-weight: 600; }
@media (max-width: 700px) { .settles-cols { grid-template-columns: 1fr; gap: 16px; } }

.case-caveat {
  margin: 10px 0 0; font-size: 11.5px; line-height: 1.5; color: var(--ink-3); max-width: 70ch;
}
.fld {
  display: block; font-size: 11px; letter-spacing: .04em; text-transform: uppercase;
  color: var(--ink-3); margin: 9px 0 3px;
}
.card .fld:first-of-type { margin-top: 0; }
#fte {
  width: 100%; font: inherit; font-family: var(--mono); font-size: 12.5px;
  padding: 5px 7px; color: var(--ink);
  background: var(--panel-2); border: 1px solid var(--rule-strong); border-radius: 4px;
}
.tz { position: relative; height: 122px; }
/* A vertical rule at the headquarters rather than a shaded window: the window
   covered almost the whole axis and shaded nothing meaningful. */
.tz .hqmark {
  position: absolute; top: 18px; bottom: 24px; width: 1px;
  background: var(--accent); opacity: .45;
}
.tz .axis {
  position: absolute; left: 0; right: 0; bottom: 24px; height: 1px; background: var(--rule-strong);
}
.tz .tick {
  position: absolute; bottom: 6px; transform: translateX(-50%);
  font-family: var(--mono); font-size: 9.5px; color: var(--ink-3);
}
.tz .city {
  position: absolute; transform: translateX(-50%); text-align: center; white-space: nowrap;
}
.tz .dot { width: 9px; height: 9px; border-radius: 50%; margin: 0 auto 3px; }
.tz .dot.lead { background: var(--accent); }
.tz .dot.rest { background: var(--rule-strong); }
.tz .nm { font-size: 10.5px; color: var(--ink-2); }
.tz .nm .n {
  font-family: var(--mono); font-size: 8.5px; color: var(--ink-3);
  border: 1px solid var(--rule-strong); border-radius: 6px; padding: 0 4px; margin-left: 3px;
}
.tz .hrs { font-family: var(--mono); font-size: 9px; color: var(--ink-3); }
/* The headquarters gets its own row at the top: it frequently shares an offset
   with a market — Zurich and Poland are both UTC+1 — and the two labels landed
   on the same point. */
.tz .hq {
  position: absolute; top: 0; transform: translateX(-50%);
  font-weight: 600;
  font-family: var(--mono); font-size: 9.5px; color: var(--accent); white-space: nowrap;
}
.tz .hq::after {
  content: ""; display: block; width: 1px; height: 6px; margin: 2px auto 0;
  background: var(--accent); opacity: .5;
}

.exhibit-source {
  font-family: var(--mono); font-size: 10.5px; line-height: 1.5; color: var(--ink-3);
  margin: 12px 0 0; padding-top: 9px; border-top: 1px solid var(--rule);
  max-width: 92ch;
}

.col-head {
  display: grid; grid-template-columns: 26px minmax(150px, 215px) minmax(0,1fr) 58px 88px;
  gap: 12px; margin-top: 18px; padding-bottom: 5px;
  border-bottom: 1px solid var(--rule-strong);
}
.ch-band {
  font-family: var(--mono); font-size: 10px; text-transform: uppercase;
  letter-spacing: .07em; color: var(--ink-3); text-align: right;
}
.ch-num {
  text-align: right; font-family: var(--mono); font-size: 10px;
  text-transform: uppercase; letter-spacing: .07em; color: var(--ink-3);
}
@media (max-width: 780px) { .col-head { display: none; } }
.rows { position: relative; margin-top: 0; }
.row {
  display: grid; grid-template-columns: 26px minmax(150px, 215px) minmax(0,1fr) 58px 88px;
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
/* Primary mark: one solid bar whose length is the score. The leading band is
   the accent, everything below it recedes to a neutral — so the answer the
   headline states is visible in the exhibit without reading a number. */
.bar-wrap { width: 100%; }
.bar { height: 15px; border-radius: 0 1px 1px 0; }
.bar.lead { background: var(--accent); }
.bar.rest { background: var(--rule-strong); }
/* Secondary: composition, at a third the height and muted, so it informs on
   inspection instead of competing for the first glance. */
.mix { display: flex; height: 4px; margin-top: 2px; opacity: .5; }
.mix .seg-fill { height: 100%; border-right: 1px solid var(--panel); }
.mix .seg-fill:last-child { border-right: 0; }
.row:hover .mix { opacity: 1; }
.stab { text-align: right; font-family: var(--mono); font-size: 12px; font-variant-numeric: tabular-nums; }
.stab .pct { display: block; }
.stab .tag { display: block; font-size: 10px; letter-spacing: .06em; text-transform: uppercase; }
.tag.robust { color: var(--accent); }
.tag.contingent { color: var(--ink-3); }
.tag.never { color: var(--warn); }
.in-top { box-shadow: inset 3px 0 0 var(--accent); }
/* A band is a group the draws cannot separate; the rule marks where one ends. */
.row.band-start { border-top: 1px solid var(--rule-strong); }
.row.band-start:first-child { border-top: 0; }

.sources { margin: 0; display: grid; gap: 9px; }
.sources div { display: grid; gap: 1px; }
.sources dt {
  font-family: var(--mono); font-size: 10px; text-transform: uppercase;
  letter-spacing: .07em; color: var(--ink-3);
}
.sources dd { margin: 0; font-size: 12.5px; line-height: 1.35; }
.sources .vint { color: var(--ink-3); font-size: 11.5px; }

.legend { display: flex; flex-wrap: wrap; gap: 11px; margin-top: 14px; font-size: 11px; color: var(--ink-3); }
.legend .swatch { opacity: .5; }
.legend span { display: inline-flex; align-items: center; gap: 5px; }
.legend-lede { color: var(--ink-3); font-family: var(--mono); font-size: 10px;
  text-transform: uppercase; letter-spacing: .07em; }

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

.page-actions { display: flex; align-items: center; gap: 12px; margin-top: 18px; }
.page-actions button {
  font: inherit; font-size: 12.5px; padding: 5px 11px; cursor: pointer;
  background: var(--panel); color: var(--ink); border: 1px solid var(--rule-strong);
}
.page-actions button:hover { border-color: var(--accent); color: var(--accent); }
.page-actions button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

/* One-pager: the finding, the exhibit, and where the numbers came from. The
   controls are the instrument and do not belong in a document; the appendices
   would push it past a page. */
@media print {
  @page { size: A4 portrait; margin: 14mm 12mm; }
  .rail, .table-actions, .page-actions, .legend, details, footer, .strip-wrap { display: none !important; }
  /* Exhibit 2 explains a pillar; Exhibit 3 answers the question that follows the
     ranking, so it earns the page while the timezone strip does not. */
  .case-wrap { display: block !important; break-inside: avoid; margin-top: 2px; padding-top: 3px; }
  .case-wrap .exhibit-label { margin-bottom: 2px; }
  .case-wrap .strip-title { margin-bottom: 5px; }
  /* On screen the per-role figure sits under the total; in print that doubles
     every row and costs the page. Inline, it costs a column's width instead. */
  .case-row { padding: 0; grid-template-columns: 6.6rem 1fr 10.4rem; gap: 8px; }
  .case-val .per { display: inline; }
  .case-val .per::before { content: "\00a0\00b7\00a0"; }
  .case-row .cn { font-size: 8.5pt; }
  .case-track { height: 9px; }
  .case-row { line-height: 1.15; }
  .case-val { font-size: 7.5pt; }
  .case-val .per { font-size: 6.5pt; }
  .case-caveat { font-size: 6.7pt; line-height: 1.35; margin-top: 4px; max-width: none; }
  /* Print drops the long forms: the column header clipped to "REWEIGHTIN", and
     the caveat's last clause repeats the source note beneath it. */
  .screen-only, .settles { display: none !important; }
  .col-head { margin-bottom: 2px; }
  .case-bar { background: #146b54 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .case-bar.over { background: #b0374a !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .layout { grid-template-columns: minmax(0,1fr); gap: 0; }
  .wrap { max-width: none; padding: 0; }
  body { background: #fff; color: #000; font-size: 9pt; }
  header { margin-bottom: 9px; padding-bottom: 8px; }
  h1 { font-size: 17pt; margin-bottom: 6px; max-width: none; }
  .standfirst { font-size: 9.5pt; max-width: none; }
  .title-block { grid-template-columns: minmax(0,1.2fr) minmax(0,1fr) !important; gap: 18px !important; }
  .deck { padding-left: 12px; }
  .deck p { font-size: 7.5pt; margin-bottom: 4px; }
  .eyebrow { margin-bottom: 5px; }
  .exhibit-head { padding-top: 6px; margin-bottom: 2px; }
  .exhibit-head h2 { font-size: 11pt; }
  .belief { font-size: 9.5pt; margin-top: 2px; }
  .col-head { margin-top: 8px; }
  .row { padding: 2px 0; break-inside: avoid; }
  .who .nm { font-size: 9.5pt; }
  /* On screen the detail line wraps to two or three lines; eleven cities of
     that is most of a page. In print it gets one line and clips. */
  .who .sub {
    font-size: 7pt; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  /* A4 portrait is about 794px, which is inside the mobile breakpoint, so the
     row grid was collapsing to a stacked single column and the page ran to two.
     The print layout has to override that explicitly. */
  .row, .col-head {
    display: grid !important;
    /* 62px clipped "CONTINGENT" against the page edge; the bar column absorbs
       the difference without losing any comparison. */
    grid-template-columns: 18px minmax(140px, 200px) minmax(0,1fr) 40px 78px !important;
    gap: 9px !important;
  }
  .row .bar-cell, .row .stab, .row .evidence { grid-column: auto !important; }
  .col-head { display: grid !important; }
  .bar { height: 11px; }
  .rank, .evidence, .stab { font-size: 8pt; }
  /* The overlap pillar is geographic and was invisible: a number in a column.
   Placing the cities on a clock relative to the headquarters shows why India is
   a handover and Poland is a shared day — which is the pillar, drawn. */
.strip-wrap { margin-top: 26px; border-top: 1px solid var(--rule-strong); padding-top: 10px; }
.strip-title {
  margin: 0 0 12px; font-size: 14px; font-weight: 600; letter-spacing: -.01em;
}
.tz { position: relative; height: 122px; }
/* A vertical rule at the headquarters rather than a shaded window: the window
   covered almost the whole axis and shaded nothing meaningful. */
.tz .hqmark {
  position: absolute; top: 18px; bottom: 24px; width: 1px;
  background: var(--accent); opacity: .45;
}
.tz .axis {
  position: absolute; left: 0; right: 0; bottom: 24px; height: 1px; background: var(--rule-strong);
}
.tz .tick {
  position: absolute; bottom: 6px; transform: translateX(-50%);
  font-family: var(--mono); font-size: 9.5px; color: var(--ink-3);
}
.tz .city {
  position: absolute; transform: translateX(-50%); text-align: center; white-space: nowrap;
}
.tz .dot { width: 9px; height: 9px; border-radius: 50%; margin: 0 auto 3px; }
.tz .dot.lead { background: var(--accent); }
.tz .dot.rest { background: var(--rule-strong); }
.tz .nm { font-size: 10.5px; color: var(--ink-2); }
.tz .nm .n {
  font-family: var(--mono); font-size: 8.5px; color: var(--ink-3);
  border: 1px solid var(--rule-strong); border-radius: 6px; padding: 0 4px; margin-left: 3px;
}
.tz .hrs { font-family: var(--mono); font-size: 9px; color: var(--ink-3); }
/* The headquarters gets its own row at the top: it frequently shares an offset
   with a market — Zurich and Poland are both UTC+1 — and the two labels landed
   on the same point. */
.tz .hq {
  position: absolute; top: 0; transform: translateX(-50%);
  font-weight: 600;
  font-family: var(--mono); font-size: 9.5px; color: var(--accent); white-space: nowrap;
}
.tz .hq::after {
  content: ""; display: block; width: 1px; height: 6px; margin: 2px auto 0;
  background: var(--accent); opacity: .5;
}

.exhibit-source { margin-top: 8px; padding-top: 6px; }
  .bar.lead { background: #146b54 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .bar.rest { background: #b6b9ae !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .mix { display: none; }
  /* The overlap pillar is geographic and was invisible: a number in a column.
   Placing the cities on a clock relative to the headquarters shows why India is
   a handover and Poland is a shared day — which is the pillar, drawn. */
.strip-wrap { margin-top: 26px; border-top: 1px solid var(--rule-strong); padding-top: 10px; }
.strip-title {
  margin: 0 0 12px; font-size: 14px; font-weight: 600; letter-spacing: -.01em;
}
.tz { position: relative; height: 122px; }
/* A vertical rule at the headquarters rather than a shaded window: the window
   covered almost the whole axis and shaded nothing meaningful. */
.tz .hqmark {
  position: absolute; top: 18px; bottom: 24px; width: 1px;
  background: var(--accent); opacity: .45;
}
.tz .axis {
  position: absolute; left: 0; right: 0; bottom: 24px; height: 1px; background: var(--rule-strong);
}
.tz .tick {
  position: absolute; bottom: 6px; transform: translateX(-50%);
  font-family: var(--mono); font-size: 9.5px; color: var(--ink-3);
}
.tz .city {
  position: absolute; transform: translateX(-50%); text-align: center; white-space: nowrap;
}
.tz .dot { width: 9px; height: 9px; border-radius: 50%; margin: 0 auto 3px; }
.tz .dot.lead { background: var(--accent); }
.tz .dot.rest { background: var(--rule-strong); }
.tz .nm { font-size: 10.5px; color: var(--ink-2); }
.tz .nm .n {
  font-family: var(--mono); font-size: 8.5px; color: var(--ink-3);
  border: 1px solid var(--rule-strong); border-radius: 6px; padding: 0 4px; margin-left: 3px;
}
.tz .hrs { font-family: var(--mono); font-size: 9px; color: var(--ink-3); }
/* The headquarters gets its own row at the top: it frequently shares an offset
   with a market — Zurich and Poland are both UTC+1 — and the two labels landed
   on the same point. */
.tz .hq {
  position: absolute; top: 0; transform: translateX(-50%);
  font-weight: 600;
  font-family: var(--mono); font-size: 9.5px; color: var(--accent); white-space: nowrap;
}
.tz .hq::after {
  content: ""; display: block; width: 1px; height: 6px; margin: 2px auto 0;
  background: var(--accent); opacity: .5;
}

/* Four lines of source note is what decided the second page. At this size it is
   three, and still comfortably legible in print. */
.exhibit-source { font-size: 6.3pt; line-height: 1.3; margin-top: 4px; padding-top: 3px; }
}

details { margin-top: 26px; border-top: 1px solid var(--rule-strong); padding-top: 14px; }
summary { cursor: pointer; font-size: 13.5px; color: var(--ink-2); }
table { border-collapse: collapse; width: 100%; margin-top: 12px; font-size: 12.5px; }
th, td { text-align: right; padding: 5px 8px; border-bottom: 1px solid var(--rule); font-variant-numeric: tabular-nums; }
th:first-child, td:first-child { text-align: left; font-variant-numeric: normal; }
td.ops { text-align: left; font-variant-numeric: normal; max-width: 30ch; }
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
  <div class="title-block">
    <div>
      <h1 id="headline">Which city, and how sure can you be?</h1>
      <p class="standfirst" id="takeaway"></p>
    </div>
    <div class="deck">
      <p>Cities where GBS and GCC roles are genuinely advertised, scored on seven pillars of
         public data and re-ranked across 2,000 defensible weightings.</p>
      <p>Set what you are buying. The exhibit shows what survives the change — and groups the
         cities the evidence cannot separate rather than ranking them.</p>
    </div>
  </div>
</header>

<div class="layout">
  <aside class="rail">
    <div class="card">
      <h2>Centre type</h2>
      <p class="panel-note">Which work moves determines what you are buying,
        and therefore where each weighting starts.</p>
      <div class="seg" id="archetype" role="group" aria-label="Centre type"></div>
      <p class="blurb" id="archetype-blurb"></p>
    </div>

    <div class="card">
      <h2>Weights</h2>
      <p class="panel-note">
        Each figure is that pillar's share of the decision. Shares total 100%, so
        raising one lowers the rest.
      </p>
      <p class="blurb" id="weights-why"></p>
      <div id="sliders"></div>
      <p class="reads" id="weight-sum"></p>
    </div>

    <div class="card">
      <h2>Headquarters</h2>
      <select id="hq" aria-label="Headquarters location"></select>
      <p class="slider-note">Sets the working hours each city shares with you.</p>
    </div>

    <div class="card">
      <h2>Cost comparison</h2>
      <label class="fld" for="baseline">Origin</label>
      <select id="baseline" aria-label="Market the work leaves"></select>
      <label class="fld" for="fte">Roles moved</label>
      <input id="fte" type="number" min="1" max="5000" step="10" aria-label="Roles moved">
      <p class="slider-note">Sets Exhibit 3. Origins are markets ILOSTAT prices;
        most are not candidates and are never ranked.</p>
    </div>

    <div class="card">
      <h2>Sources</h2>
      <dl class="sources" id="sources"></dl>
    </div>
  </aside>

  <main>
    <div class="exhibit-head">
      <p class="exhibit-label">Exhibit 1</p>
      <h2 id="board-title"></h2>
      <p class="hint">Bar length is the score; the strip beneath it is the composition.</p>
    </div>
    <div class="belief" id="belief"></div>
    <div class="col-head">
      <span class="ch-band">band</span><span></span><span></span>
      <span class="ch-num">postings</span><span class="ch-num">top-3<span class="screen-only"> across reweightings</span></span>
    </div>
    <div class="rows" id="rows"></div>
    <div class="legend" id="legend"></div>

    <div class="strip-wrap">
      <p class="exhibit-label">Exhibit 2</p>
      <h3 class="strip-title" id="strip-title"></h3>
      <div id="tzstrip"></div>
    </div>

    <div class="strip-wrap case-wrap">
      <p class="exhibit-label">Exhibit 3</p>
      <h3 class="strip-title" id="case-title"></h3>
      <div id="case"></div>
      <p class="case-caveat" id="case-caveat"></p>
    </div>

    <p class="exhibit-source" id="exhibit-source"></p>

    <div class="settles">
      <p class="exhibit-label">The boundary of this evidence</p>
      <div class="settles-cols">
        <div><h4>What it settles</h4><ul id="settles-yes"></ul></div>
        <div class="not"><h4>What it does not</h4><ul id="settles-no"></ul></div>
      </div>
    </div>

    <div class="page-actions">
      <button type="button" id="one-pager">Print one-pager</button>
      <span class="hint">Finding, exhibit and sources on one page.</span>
    </div>

    <details>
      <summary>Table — every figure behind the ranking</summary>
      <div class="table-actions">
        <button type="button" id="copy">Copy table</button>
        <span class="copy-status" id="copy-status" role="status"></span>
      </div>
      <div class="table-scroll"><table id="table"><caption></caption></table></div>
    </details>

    <details>
      <summary>Method and limitations</summary>
      <div class="method">
        <ul>
          <li>Scores are relative to the cities on screen, not absolute ratings.</li>
          <li><strong>Robust</strong> means a top-three place in 90% of 2,000 reweightings
              <em>and</em> at least <span id="floor-n"></span> postings behind it.</li>
          <li>Setting a pillar's weight to zero shows whether it decides anything. For a
              transactional hub the top band survives losing any pillar except <em>cost</em>;
              for a judgment centre five of seven move it.</li>
          <li><strong>Bands</strong> group cities the draws cannot tell apart. A city opens a new
              band only when every city above it finishes ahead in at least
              <span id="sep-n"></span> of runs — so cities sharing a band have no established
              order between them.</li>
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
  baseline: DATA.baselineDefault,
  fte: DATA.fteDefault,
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

/* Beta via two Gammas — needed to draw the classifier's precision per
   iteration, exactly as src/stability.py does. */
function beta(rng, a, b) {
  const x = gamma(rng, a), y = gamma(rng, b);
  return x / (x + y);
}

/* An observed capability share is a mixture of correctly and wrongly admitted
   postings; this recovers the former. Mirrors _correct_for_precision in
   src/stability.py — the dashboard ran without it for one revision and showed a
   different leader from the study it presents. */
function correctForPrecision(observed, precision, row) {
  if (!DATA.modelClassificationError || precision <= 0.05) return observed;
  if (row.contaminant == null) return observed;
  const t = (observed - (1 - precision) * row.contaminant) / precision;
  return Math.min(1, Math.max(0, t));
}

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
  // Who finishes ahead of whom, so the ranking can be grouped into bands the
  // draws actually support rather than printed as N distinct positions.
  const ids = base.map((it) => it.row.id);
  const beats = new Map(ids.map((a) => [a, new Map(ids.map((b) => [b, 0]))]));
  const meanRank = new Map(ids.map((a) => [a, 0]));
  const alpha = DATA.pillars.map((p) => Math.max(CONCENTRATION * weights[p], 0.05));
  const topN = DATA.topN;
  const others = DATA.pillars.filter((p) => p !== "capability");
  const caps = new Float64Array(base.length);

  for (let d = 0; d < DRAWS; d++) {
    const g = alpha.map((a) => gamma(rng, a));
    const gsum = g.reduce((a, b) => a + b, 0);
    const w = {}; DATA.pillars.forEach((p, i) => (w[p] = g[i] / gsum));

    // One precision per draw: the classifier is a single instrument and its
    // accuracy does not vary by city.
    const precision = DATA.modelClassificationError
      ? beta(rng, DATA.auditCorrect + 1, DATA.auditTotal - DATA.auditCorrect + 1)
      : 1;

    let lo = Infinity, hi = -Infinity;
    for (let i = 0; i < base.length; i++) {
      const row = base[i].row;
      const n = row.capN || 0, pHat = row.capP ?? 0;
      let draw = pHat;
      if (n > 0) {
        const sd = Math.sqrt(Math.max(pHat * (1 - pHat), 0) / n);
        draw = Math.min(1, Math.max(0, pHat + normal(rng) * sd));
      }
      draw = correctForPrecision(draw, precision, row);
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
    for (let i = 0; i < ranked.length; i++) {
      meanRank.set(ranked[i].id, meanRank.get(ranked[i].id) + i + 1);
      const row = beats.get(ranked[i].id);
      for (let j = i + 1; j < ranked.length; j++) row.set(ranked[j].id, row.get(ranked[j].id) + 1);
    }
  }
  const out = new Map();
  for (const [k, v] of hits) out.set(k, v / DRAWS);
  const order = [...ids].sort((a, b) => meanRank.get(a) - meanRank.get(b));
  return { frequency: out, band: bandsFrom(order, beats), order };
}

/* A city opens a new band only when every current member of the band clearly
   outranks it. Comparing against all members, not just the previous city, keeps
   the grouping transitive — a chain of close neighbours cannot merge into one
   band spanning a gap the draws do separate. Mirrors _bands in stability.py. */
function bandsFrom(order, beats) {
  const band = new Map();
  let current = 1, members = [];
  for (const key of order) {
    if (members.length && members.every((m) => (beats.get(m).get(key) / DRAWS) >= DATA.separableAt)) {
      current += 1; members = [];
    }
    band.set(key, current);
    members.push(key);
  }
  return band;
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

function icon(p) {
  return `<svg class="ico" viewBox="0 0 16 16" aria-hidden="true" `
       + `style="stroke:${colors()[p]}">${DATA.icons[p]}</svg>`;
}

/* ---- answer first ----
   A consulting exhibit leads with the finding, not the subject, and the finding
   here changes every time a weight moves. The headline is therefore written
   from the current result rather than fixed in the markup: what survives, and
   what it would take to believe otherwise. */
function writeHeadline(ranked, stab, band) {
  const robust = ranked.filter((r) => verdict(stab.get(r.row.id) ?? 0, r.row) === "robust");
  const lead = ranked[0];
  const top = ranked.filter((r) => band.get(r.row.id) === 1);
  const arch = DATA.archetypes[state.archetype].short.toLowerCase();

  let headline;
  if (top.length > 1) {
    headline = `${top.length} cities finish level at the top.`;
  } else if (robust.length === 1) {
    headline = `Only ${robust[0].row.name} survives a change of mind.`;
  } else if (robust.length > 1) {
    const names = robust.slice(0, 3).map((r) => r.row.name);
    headline = `${names.join(", ")} survive a change of mind.`;
  } else {
    headline = `No city holds up as a ${arch}.`;
  }
  $("#headline").textContent = headline;

  // The leading band, not the leading city: naming one city as first when the
  // draws cannot separate it from four others is the error this tool argues
  // against.
  if (top.length > 1) {
    const names = top.map((r) => r.row.name);
    const last = names.pop();
    $("#takeaway").innerHTML =
      `<strong>${names.join(", ")} and ${last}</strong> finish level. The draws `
      + `cannot separate them; treat the order within that group as undetermined.`;
  } else {
    const pct = ((stab.get(lead.row.id) ?? 0) * 100).toFixed(0);
    const where = DATA.marketNames[lead.row.parent] || "";
    $("#takeaway").innerHTML =
      `<strong>${lead.row.name}</strong> (${where}) leads outright, holding a top-three `
      + `place in ${pct}% of 2,000 nearby weightings.`;
  }
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
  let ranked = scoreAll(scaled, state.weights);
  const result = stability(scaled, state.weights);
  const stab = result.frequency;
  const band = result.band;
  const ref = DATA.reference[state.archetype];
  const C = colors();

  // Order by band first: a ranking that prints positions the draws cannot
  // support is the thing this tool exists to argue against.
  // Band first; within a band by how often the city survives reweighting,
  // since the band already says the score order is not established.
  ranked = ranked.slice().sort((a, b) =>
    (band.get(a.row.id) - band.get(b.row.id))
    || ((stab.get(b.row.id) ?? 0) - (stab.get(a.row.id) ?? 0)));
  writeHeadline(ranked, stab, band);
  $("#board-title").textContent =
    `${DATA.archetypes[state.archetype].label}: ${ranked.length} cities ranked on your weighting`;
  $("#scope").textContent = `${rows.length} GBS and GCC cities`;
  $("#belief").innerHTML = belief(state.weights);

  const host = $("#rows");
  const prev = new Map();
  host.querySelectorAll(".row").forEach((el) => prev.set(el.dataset.id, el.getBoundingClientRect().top));

  host.innerHTML = "";
  const maxScore = Math.max(...ranked.map((x) => x.score), 1e-9);
  ranked.forEach((r, i) => {
    const f = stab.get(r.row.id) ?? 0;
    const v = verdict(f, r.row);
    const b = band.get(r.row.id);
    const opensBand = i === 0 || band.get(ranked[i - 1].row.id) !== b;
    const el = document.createElement("div");
    el.className = "row" + (b === 1 ? " in-top" : "") + (opensBand ? " band-start" : "");
    el.dataset.id = r.row.id;

    // The country first: a reader should not have to know where Poznań is to
    // read the ranking.
    const where = DATA.marketNames[r.row.parent] || "";
    const costNote = r.row.costResolved
      ? `${(r.row.regionIndex).toFixed(2)}× national cost`
      : "national cost";
    // Languages and local purchasing power are facts a reader asks for and
    // neither is scored: more languages helps only if you need them, and PPP
    // does not reorder anything because the cheapest market is cheapest on
    // both bases. Shown, not weighted.
    const langs = (r.row.languages || []).length
      ? ` · ${r.row.languages.slice(0, 2).join(", ")}`
      : "";
    // Lead with the work mix: which side of arbitrage-versus-value a city sits
    // on is the thing the chosen centre type is actually asking about.
    const mix = r.row.mixTransactional != null
      ? `${Math.round(r.row.mixTransactional * 100)}% processing`
      : "";
    const sub = `${where} · ${mix} · ${r.row.employers} employers · ${costNote}${langs}`;

    // Length carries the score, which is the comparative fact. Composition
    // moves to a thin strip beneath: still there, no longer shouting. Eleven
    // equal-length rainbows told the reader nothing and dominated the page.
    const width = (r.score / maxScore) * 100;
    const tone = b === 1 ? "lead" : "rest";
    const segs = DATA.pillars.map((p) => {
      const pct = (r.parts[p] / (r.score || 1)) * 100;
      return `<i class="seg-fill" style="width:${pct.toFixed(2)}%;background:${C[p]}"
        data-p="${p}" data-name="${r.row.name}"></i>`;
    }).join("");
    const bar =
      `<div class="bar-wrap">` +
        `<div class="bar ${tone}" style="width:${width.toFixed(2)}%"></div>` +
        `<div class="mix" style="width:${width.toFixed(2)}%">${segs}</div>` +
      `</div>`;

    const n = r.row.postings;
    const thin = r.row.isCity && n != null && n < DATA.evidenceFloor;
    const evidence = n == null ? "—"
      : `<span class="${thin ? "thin" : ""}">${n}</span>`;

    el.innerHTML =
      `<div class="rank">${opensBand ? b : ""}</div>` +
      `<div class="who"><span class="nm">${flag(r.row.parent)}${r.row.name}</span>`
      + `<span class="sub">${sub}</span></div>` +
      `<div class="bar-cell">${bar}</div>` +
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

  $("#legend").innerHTML = `<span class="legend-lede">Composition:</span>` + DATA.pillars.map((p) =>
    `<span><i class="swatch" style="background:${C[p]}"></i>${DATA.pillarLabels[p]}</span>`).join("");

  renderStrip(ranked, band);
  renderTable(ranked, stab);
  renderCase(ranked);
  renderSettles(ranked, band, rows);
  renderSource(rows);
  renderFoot(rows);
}

function renderTable(ranked, stab) {
  const t = $("#table");
  const head = ["City", ...DATA.pillars.map((p) => DATA.pillarLabels[p]),
                "Score", "Top-3", "Processing", "Judgment", "Cost USD", "Cost PPP",
                "Languages", "Operators already there"];
  t.querySelector("caption").textContent =
    "Normalised pillar scores (0–1, higher is better) under the current weights. "
    + "Processing and judgment are the work mix the city advertises, shrunk toward "
    + "its country's where the sample is thin. Cost is monthly, per head: USD is what "
    + "you pay, PPP what it buys locally. "
    + "Languages are those the city's postings ask for. Operators are the employers "
    + "advertising this work there, with staffing firms removed and one company's "
    + "several spellings merged. Both reported, neither scored.";
  t.innerHTML = t.querySelector("caption").outerHTML +
    "<thead><tr>" + head.map((h) => `<th>${h}</th>`).join("") + "</tr></thead><tbody>" +
    ranked.map((r) =>
      `<tr><td>${r.row.name}</td>` +
      DATA.pillars.map((p) => `<td>${r.scaled[p].toFixed(2)}</td>`).join("") +
      `<td>${r.score.toFixed(3)}</td><td>${((stab.get(r.row.id) ?? 0) * 100).toFixed(0)}%</td>`
      + `<td>${r.row.mixTransactional != null ? Math.round(r.row.mixTransactional * 100) + "%" : "—"}</td>`
      + `<td>${r.row.mixTransactional != null ? Math.round((1 - r.row.mixTransactional) * 100) + "%" : "—"}</td>`
      + `<td>${Math.round(r.row.cost).toLocaleString()}</td>`
      + `<td>${r.row.costPpp ? Math.round(r.row.costPpp).toLocaleString() : "—"}</td>`
      + `<td>${(r.row.languages || []).join(", ") || "—"}</td>`
      + `<td class="ops">${(r.row.operators || []).join(", ") || "—"}</td></tr>`
    ).join("") + "</tbody>";
}

/* Every exhibit carries its own source. A reader should not have to open a
   panel to learn what the numbers are made of. */
/* Overlap is a market fact, not a city one: every Indian city sits at UTC+5.5.
   Plotting cities individually piled five labels on one point and read as
   noise, so the strip works at the grain the pillar actually has — one mark per
   market, carrying its cities and its shared hours. */
function renderStrip(ranked, band) {
  const hq = DATA.hqOffsets[state.hq] ?? 0;

  const byMarket = new Map();
  for (const r of ranked) {
    const key = r.row.parent;
    if (!byMarket.has(key)) {
      byMarket.set(key, {
        name: DATA.marketNames[key] || key,
        offset: DATA.offsets[key] ?? 0,
        hours: overlapHours(key, state.hq),
        cities: [],
        lead: false,
      });
    }
    const m = byMarket.get(key);
    m.cities.push(r.row.name);
    if (band.get(r.row.id) === 1) m.lead = true;
  }

  const markets = [...byMarket.values()].sort((a, b) => a.offset - b.offset);
  const offsets = markets.map((m) => m.offset);
  const lo = Math.min(...offsets, hq) - 1.5;
  const hi = Math.max(...offsets, hq) + 1.5;
  const pos = (o) => ((o - lo) / (hi - lo)) * 100;

  const marks = markets.map((m, i) => {
    const label = m.cities.length > 1
      ? `${m.name} <span class="n">${m.cities.length}</span>`
      : m.cities[0];
    return `<div class="city" style="left:${pos(m.offset).toFixed(2)}%;top:${22 + (i % 2) * 30}px">`
         + `<div class="dot ${m.lead ? "lead" : "rest"}"></div>`
         + `<div class="nm">${label}</div>`
         + `<div class="hrs">${m.hours}h shared</div></div>`;
  }).join("");

  const ticks = [];
  for (let o = Math.ceil(lo); o <= Math.floor(hi); o += 2) {
    const sign = o < 0 ? "\u2212" : "+";
    ticks.push(`<div class="tick" style="left:${pos(o).toFixed(2)}%">UTC${sign}${Math.abs(o)}</div>`);
  }

  $("#strip-title").innerHTML =
    `Working hours shared with <strong>${hqLabel()}</strong>`;
  $("#tzstrip").innerHTML =
    `<div class="tz"><div class="axis"></div>${ticks.join("")}${marks}`
    + `<div class="hqmark" style="left:${pos(hq).toFixed(2)}%"></div>`
    + `<div class="hq" style="left:${pos(hq).toFixed(2)}%">${hqLabel()}</div></div>`;
}

function flag(market) {
  const d = DATA.flags[market];
  if (!d) return "";
  return `<svg class="flag" viewBox="0 0 21 14" role="img" `
       + `aria-label="${DATA.flagTitles[market] || market}">${d}</svg>`;
}

function baselineRow() {
  return DATA.baselines.find((b) => b.key === state.baseline) || DATA.baselines[0];
}

function money(usd) {
  const a = Math.abs(usd);
  if (a >= 1e6) return `${usd < 0 ? "\u2212" : ""}$${(a / 1e6).toFixed(a >= 1e7 ? 0 : 1)}m`;
  // A per-role figure of 9,417 read as "$9k" loses the part a reader is checking.
  if (a >= 1e3) return `${usd < 0 ? "\u2212" : ""}$${(a / 1e3).toFixed(a >= 1e4 ? 0 : 1)}k`;
  return `${usd < 0 ? "\u2212" : ""}$${Math.round(a)}`;
}

/* Exhibit 3 — the wage gap, annualised. Deliberately not called a saving: it is
   one line of a run-cost, and the caveat under it carries the rest. */
function renderCase(ranked) {
  const base = baselineRow();
  const fte = state.fte;
  const items = ranked
    .filter((r) => r.row.cost != null)
    .map((r) => {
      const perFte = (base.monthly - r.row.cost) * 12;
      return { name: r.row.name, market: r.row.parent, perFte, total: perFte * fte };
    })
    .sort((a, b) => b.total - a.total);

  const span = Math.max(...items.map((i) => Math.abs(i.total)), 1);
  // Zero sits inside the track only when something lands above the baseline.
  const worst = Math.min(...items.map((i) => i.total), 0);
  const zero = (Math.abs(worst) / (span + Math.abs(worst))) * 100;

  $("#case-title").innerHTML =
    `Annual wage gap for <strong>${fte.toLocaleString("en-US")} `
    + `role${fte === 1 ? "" : "s"}</strong> leaving <strong>${base.label}</strong>`;

  $("#case").innerHTML = items.map((i) => {
    const w = (Math.abs(i.total) / (span + Math.abs(worst))) * 100;
    const over = i.total < 0;
    const bar = over
      ? `<div class="case-bar over" style="right:${(100 - zero).toFixed(2)}%;width:${w.toFixed(2)}%"></div>`
      : `<div class="case-bar" style="left:${zero.toFixed(2)}%;width:${w.toFixed(2)}%"></div>`;
    return `<div class="case-row"><span class="cn">${flag(i.market)}${i.name}</span>`
      + `<div class="case-track"><div class="case-zero" style="left:${zero.toFixed(2)}%"></div>${bar}</div>`
      + `<span class="case-val">${money(i.total)}`
      + `<span class="per">${money(i.perFte)} per role</span></span></div>`;
  }).join("");

  // Print keeps the bounds that change how the number is read and drops the
  // elaborations, because the page is decided by three lines here.
  // A baseline is always a national average; some cities carry a regional index.
  // That puts a capital premium on one side of the subtraction and not the other,
  // which is what makes Warsaw look dearer than a UK national mean.
  const tilted = ranked
    .filter((r) => r.row.regionIndex && r.row.regionIndex > 1)
    .sort((a, b) => b.row.regionIndex - a.row.regionIndex);
  const tilt = tilted.length
    ? `The baseline is a national average, while `
      + tilted.slice(0, 2).map((r) =>
          `${r.row.name} carries ${r.row.regionIndex.toFixed(2)}\u00d7`).join(" and ")
      + ` its own country mean, so a capital-city premium sits on one side of the `
      + `subtraction and not the other. `
    : ``;

  $("#case-caveat").innerHTML =
    `Wage line only, at ${base.label}\u2019s blended rate for professional and clerical `
    + `occupations. It excludes facilities, technology, management overhead, transition and `
    + `severance, so it is an upper bound on the wage component and not a savings case. `
    + tilt
    + `Headcount is held one-for-one<span class="screen-only">; a centre that is still ramping `
    + `needs more heads for the same volume, which moves this number further than the wage gap `
    + `itself does</span>.`;
}

function hqLabel() {
  for (const places of Object.values(DATA.hqGroups)) {
    const hit = places.find((x) => x.key === state.hq);
    if (hit) return hit.label;
  }
  return state.hq;
}

/* Both columns are built from the run on screen rather than written down once:
   a reader who moves a slider must see the boundary move with it, or it reads
   as boilerplate and gets skipped. */
function renderSettles(ranked, band, rows) {
  const lead = ranked.filter((r) => band.get(r.row.id) === 1);
  const bands = new Set([...band.values()]).size;
  const postings = rows.reduce((a, r) => a + (r.postings || 0), 0);
  const named = ranked.filter((r) => (r.row.operators || []).length).length;
  const decisive = DATA.pillarLabels[
    Object.entries(state.weights).sort((a, b) => b[1] - a[1])[0][0]
  ].toLowerCase();

  $("#settles-yes").innerHTML = [
    `Which cities genuinely advertise this work: <b>${rows.length}</b> clear the evidence `
      + `threshold, on <b>${postings.toLocaleString("en-US")}</b> GBS and GCC postings.`,
    lead.length > 1
      ? `That <b>${lead.length} cities finish level</b> at the top. The draws cannot separate `
        + `them, so their order is not a finding.`
      : `That <b>${lead[0] ? lead[0].row.name : "one city"}</b> leads alone, and the draws `
        + `keep it there.`,
    `That the answer turns on <b>${decisive}</b> at your weighting, and how far it moves when `
      + `you price something else.`,
    named ? `Who already operates in <b>${named}</b> of them, by name.` : "",
    `How far the evidence separates them: <b>${bands} bands</b>, not ${rows.length} ranks.`,
  ].filter(Boolean).map((x) => `<li>${x}</li>`).join("");

  $("#settles-no").innerHTML = [
    `Anything about <b>Manila, Kuala Lumpur, Bucharest, Prague, Budapest or Lisbon</b>. The `
      + `postings feed does not reach them, so they are absent, not rejected.`,
    `<b>Attrition, incentives, property and transition cost.</b> None are in this study, and `
      + `the first is the driver a GBS case usually turns on.`,
    `The <b>fully loaded</b> saving. Exhibit 3 is one line of a run-cost, and an upper bound `
      + `on that line.`,
    `Whether a city suits <b>your</b> mandate. Nothing here is a recommendation.`,
  ].map((x) => `<li>${x}</li>`).join("");
}

function renderSource(rows) {
  const resolved = rows.filter((r) => r.costResolved).length;
  const thin = rows.filter((r) => r.postings != null && r.postings < DATA.evidenceFloor).length;
  $("#exhibit-source").innerHTML =
    `Source: ILOSTAT earnings and employment by occupation; World Bank Worldwide Governance ` +
    `Indicators; Eurostat regional accounts; ${rows.length} cities from a GBS/GCC job-posting ` +
    `sample, ${DATA.asOf}. ` +
    `Note: ${resolved} of ${rows.length} cities carry city-level cost, the remainder their ` +
    `country's; ${thin} rest on fewer than ${DATA.evidenceFloor} postings and cannot be called robust.`;
}

function renderFoot(rows) {
  const resolved = rows.filter((r) => r.costResolved).length;
  $("#foot").innerHTML =
    `A city qualifies only where four or more employers advertise this work. ` +
    `${resolved} of ${rows.length} carry city-level cost. ` +
    `<a href="https://github.com/morichtereur/gbs-location-selection">Method and code</a>.`;
}

/* ---- controls ---- */
function buildControls() {
  const seg = $("#archetype");
  seg.innerHTML = Object.entries(DATA.archetypes).map(([k, v]) =>
    `<button type="button" data-k="${k}" aria-pressed="${k === state.archetype}">${v.label}</button>`).join("");
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
        <span class="slider-name">${icon(p)}${DATA.pillarLabels[p]}</span>
        <span class="slider-val" id="val-${p}"></span>
      </div>
      <div class="track"><input type="range" id="w-${p}" min="0" max="60" step="1"
        aria-label="${DATA.pillarLabels[p]} weight"><i class="preset" id="preset-${p}"></i></div>
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

  const bl = $("#baseline");
  const opt = (b) =>
    `<option value="${b.key}"${b.key === state.baseline ? " selected" : ""}>${b.label}</option>`;
  const scored = DATA.baselines.filter((b) => b.scored);
  const origins = DATA.baselines.filter((b) => !b.scored);
  bl.innerHTML =
    `<optgroup label="Also scored in this study">${scored.map(opt).join("")}</optgroup>`
    + `<optgroup label="Origin only">${origins.map(opt).join("")}</optgroup>`;
  bl.addEventListener("change", (e) => { state.baseline = e.target.value; render(); });

  const fte = $("#fte");
  fte.value = state.fte;
  // A blank or nonsense box should leave the exhibit alone rather than blank it.
  fte.addEventListener("input", (e) => {
    const n = parseInt(e.target.value, 10);
    if (!Number.isFinite(n) || n < 1) return;
    state.fte = Math.min(n, 5000);
    render();
  });

  writeArchetypeCopy();
  $("#sources").innerHTML = DATA.sources.map((x) => `
    <div>
      <dt>${x.pillar}</dt>
      <dd>${x.name}<br><span class="vint">${x.detail} · ${x.vintage}</span></dd>
    </div>`).join("");
  $("#limits").innerHTML = DATA.limits.map((x) => `<li>${x}</li>`).join("");
  $("#asof").textContent = `${DATA.pillars.length} pillars · ${DATA.asOf}`;
  $("#floor-n").textContent = DATA.evidenceFloor;
  $("#sep-n").textContent = Math.round(DATA.separableAt * 100) + "%";

  $("#copy").addEventListener("click", copyTable);
  $("#one-pager").addEventListener("click", () => window.print());

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

/* The starting weights are a declared judgement, not a recommendation, and the
   whole point of the tool is that the answer moves with them. Saying where they
   come from is the difference between a control someone trusts and one they
   assume is authoritative. */
function writeArchetypeCopy() {
  const a = DATA.archetypes[state.archetype];
  $("#archetype-blurb").textContent = a.blurb;
  $("#weights-why").innerHTML =
    `<strong>Starting position:</strong> ${a.why} A starting position, not a `
    + `recommendation \u2014 move it and see what survives.`;
}

function syncSliders(writeInputs = true) {
  const total = DATA.pillars.reduce((a, p) => a + state.weights[p], 0);
  DATA.pillars.forEach((p) => {
    if (writeInputs) $(`#w-${p}`).value = Math.round(state.weights[p] * 100);
    const share = total ? state.weights[p] / total : 0;
    const shown = Math.round(share * 100);
    const preset = DATA.archetypes[state.archetype].weights[p];
    const presetPct = Math.round(preset * 100);
    // Only flag a real departure, not a rounding wobble from renormalising.
    $(`#val-${p}`).innerHTML = Math.abs(shown - presetPct) > 1
      ? `${shown}% <span class="was">was ${presetPct}%</span>`
      : `${shown}%`;
    const mark = $(`#preset-${p}`);
    if (mark) mark.style.left = `calc(${(preset / 0.60) * 100}% )`;
  });
  const moved = DATA.pillars.some((p) => {
    const share = total ? state.weights[p] / total : 0;
    const preset = DATA.archetypes[state.archetype].weights[p];
    return Math.abs(Math.round(share * 100) - Math.round(preset * 100)) > 1;
  });
  $("#weight-sum").innerHTML = total <= 0
    ? `<strong>Every weight is zero.</strong> Raise at least one to rank anything.`
    : moved
      ? `<button type="button" id="reset-weights">Reset to ${DATA.archetypes[state.archetype].short}</button>`
      : `Tick marks show this centre type\u2019s starting position.`;
  const reset = $("#reset-weights");
  if (reset) {
    reset.addEventListener("click", () => {
      state.weights = { ...DATA.archetypes[state.archetype].weights };
      syncSliders(); render();
    });
  }
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
