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
from src import correlation
from src import fallback
from src import provenance
from src.panel import Market, build, with_centres
from src.fonts import face_css
from src.baselines import load as baseline_load
from src.beyond import load as beyond_load
from src.centres import survey as centres_survey
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
FLAGS.update({
    "ph": '<rect width="21" height="14" fill="#0038a8"/>'
          '<rect y="7" width="21" height="7" fill="#ce1126"/>'
          '<path d="M0 0l12.1 7L0 14z" fill="#fff"/>'
          '<circle cx="3.6" cy="7" r="1.6" fill="#fcd116"/>',
    "my": '<rect width="21" height="14" fill="#fff"/>'
          '<path d="M0 1h21v1.56H0zM0 4.1h21v1.57H0zM0 7.3h21v1.56H0zM0 10.4h21v1.57H0z" fill="#cc0001"/>'
          '<path d="M0 12.44h21V14H0z" fill="#cc0001"/>'
          '<rect width="11.7" height="7.8" fill="#010066"/>'
          '<circle cx="5.2" cy="4" r="2.4" fill="#fc0"/>'
          '<circle cx="6.2" cy="4" r="2.1" fill="#010066"/>'
          '<path d="M8.8 2.3l.4 1.2 1.2.02-1 .75.37 1.2-.97-.72-.98.72.37-1.2-1-.75 1.2-.02z" fill="#fc0"/>',
    "pt": '<rect width="21" height="14" fill="#f00"/>'
          '<rect width="8.4" height="14" fill="#060"/>'
          '<circle cx="8.4" cy="7" r="2.9" fill="none" stroke="#ff0" stroke-width="1"/>'
          '<rect x="6.9" y="5.5" width="3" height="3" fill="#fff" stroke="#f00" stroke-width=".5"/>',
    "ro": '<rect width="7" height="14" fill="#002b7f"/>'
          '<rect x="7" width="7" height="14" fill="#fcd116"/>'
          '<rect x="14" width="7" height="14" fill="#ce1126"/>',
    "cz": '<rect width="21" height="7" fill="#fff"/>'
          '<rect y="7" width="21" height="7" fill="#d7141a"/>'
          '<path d="M0 0l10.5 7L0 14z" fill="#11457e"/>',
    "hu": '<rect width="21" height="4.67" fill="#ce2939"/>'
          '<rect y="4.67" width="21" height="4.66" fill="#fff"/>'
          '<rect y="9.33" width="21" height="4.67" fill="#477050"/>',
    "do": '<rect width="21" height="14" fill="#002d62"/>'
          '<path d="M10.5 0h10.5v7H10.5zM0 7h10.5v7H0z" fill="#ce1126"/>'
          '<path d="M0 5.8h21v2.4H0zM9.3 0h2.4v14H9.3z" fill="#fff"/>',
    "cr": '<rect width="21" height="14" fill="#fff"/>'
          '<path d="M0 0h21v2.8H0zM0 11.2h21V14H0z" fill="#002b7f"/>'
          '<path d="M0 5.1h21v3.8H0z" fill="#ce1126"/>',
    "co": '<rect width="21" height="7" fill="#fcd116"/>'
          '<rect y="7" width="21" height="3.5" fill="#003893"/>'
          '<rect y="10.5" width="21" height="3.5" fill="#ce1126"/>',
    "vn": '<rect width="21" height="14" fill="#da251d"/>'
          '<path d="M10.5 3.6l1.05 3.23h3.4l-2.75 2 1.05 3.23-2.75-2-2.75 2 1.05-3.23-2.75-2h3.4z" fill="#ff0"/>',
    "eg": '<rect width="21" height="4.67" fill="#ce1126"/>'
          '<rect y="4.67" width="21" height="4.66" fill="#fff"/>'
          '<rect y="9.33" width="21" height="4.67" fill="#000"/>'
          '<path d="M10.5 5.6l.9 1.4-.9 1.4-.9-1.4z" fill="#c09300"/>',
})
FLAG_TITLES = {
    "in": "India", "pl": "Poland", "br": "Brazil", "za": "South Africa",
    "ph": "Philippines", "my": "Malaysia", "pt": "Portugal",
    "ro": "Romania", "cz": "Czechia", "hu": "Hungary",
    "do": "Dominican Republic", "cr": "Costa Rica", "co": "Colombia",
    "vn": "Vietnam", "eg": "Egypt",
}

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


TITLE = "GBS Location Selection"
OG_ALT = (
    "Exhibit 1 at the declared starting weights: eleven GBS and GCC cities ranked "
    "in bands, with the cities the evidence cannot separate sharing a band."
)

# Shown in the interface, not only in the repository. A reader in a review
# should be able to see where every pillar comes from without leaving the page.
#
# The name and the description of a source are written here because they are
# descriptions. The *vintage* is not: it is a property of the data and is read
# back out of it by `src/provenance.py`, so a refetch cannot leave the page
# claiming a year the observations no longer have. `vintage` below is the
# fallback used only when the panel carries no year to read.
SOURCES = [
    {"pillar": "Cost", "name": "ILOSTAT earnings by occupation",
     "detail": "ISCO-08 2/3/4, USD, aged to a common year", "vintage": None},
    {"pillar": "Talent", "name": "ILOSTAT employment by occupation",
     "detail": "same three ISCO groups", "vintage": None},
    {"pillar": "Governance", "name": "World Bank Worldwide Governance Indicators",
     "detail": "five dimensions with their 90% intervals", "vintage": None},
    {"pillar": "Capability", "name": "Adzuna job postings",
     "detail": "GBS/GCC roles only", "vintage": None},
    {"pillar": "Overlap", "name": "computed",
     "detail": "hours shared with headquarters", "vintage": "—"},
    {"pillar": "Durability", "name": "ILOSTAT, derived",
     "detail": "wage drift, split from currency", "vintage": None},
    {"pillar": "Employer depth", "name": "Adzuna job postings",
     "detail": "distinct employers hiring", "vintage": None},
    # Not a pillar — a modifier on cost, and the one that decides which cities
    # carry a city-level wage and which are marked national on Exhibit 3. It
    # was named in the exhibit source line and nowhere a reader would look for
    # a source.
    {"pillar": "City cost", "name": "Eurostat regional accounts",
     "detail": "NUTS-2 index against the country mean; European cities only",
     "vintage": None},
]


def _sources(panel: dict, snapshot: dict | None) -> list[dict]:
    """SOURCES with each vintage filled from the data it describes.

    A source with no recoverable year says so. Printing a remembered date
    beside an unfetched sample is the failure this replaces.
    """
    years = provenance.vintages(panel)
    unknown = "unavailable"
    sample = snapshot["dateLabel"] if snapshot else unknown
    derived = {
        "Cost": years["Cost"],
        "Talent": years["Talent"],
        "Governance": years["Governance"],
        "Capability": sample,
        "Durability": years["Durability"],
        "Employer depth": sample,
        "City cost": years["Region"],
    }
    out = []
    for s in SOURCES:
        v = derived.get(s["pillar"], s["vintage"]) or s["vintage"] or unknown
        out.append({**s, "vintage": v})
    return out

# Each line has to change what a reader would do with the tool. Anything that
# only explains the tool to itself was cut.
LIMITS = [
    "Only Polish cities have city-level cost. The rest use their country's, so cities within them differ on capability alone — treat that order as undetermined.",
    "Capability comes from few postings, as low as five per city. The stability column already accounts for this; the ranking below the top few is not meaningful.",
    "The GBS/GCC classifier was audited five times over a hundred postings; two of the last twenty were clearly wrong. That error rate is modelled in the stability column, not just noted.",

    # The first question any GBS room asks is where Manila is. Better that the
    # exhibit answers it than that the audience finds the hole.
    "A second job board would not close the coverage gap. Employer depth counts distinct employers within one feed, so another feed\u2019s count is not comparable, and splicing one in would move Manila into the ranking on evidence unlike the rest.",
    "Exhibit 3 subtracts a national baseline from cities that sometimes carry a regional index, so a capital-city premium sits on one side of it and not the other. Warsaw against a UK baseline is the clearest case: it reads as dearer than the UK, which is partly Mazowieckie against a British national mean rather than a wage fact.",
    "Exhibit 3 is a wage line, not a business case. It excludes facilities, technology, management overhead, transition and severance, and holds headcount one-for-one. Read it as the upper bound on one component of the saving.",
    "Six established locations sit outside the ranking because the postings feed does not reach them: Manila, Kuala Lumpur, Bucharest, Prague, Budapest and Lisbon. Five pillars do reach them and are reported under 'Beyond the sample'; capability and employer depth are the two that cannot be, so these markets are never scored against the ranked cities.",
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
    beyond = beyond_load()
    # Locations the sample did see and the thresholds turned away. A reader
    # asking "what about Gdansk" deserves the count, not silence.
    _, below = centres_survey()
    # Employers is the binding threshold, so closeness is measured on it first.
    # Sorting by postings surfaced single-employer towns, which are the ones the
    # threshold exists to reject.
    near = sorted(below, key=lambda c: (-c.employers, -c.postings))[:6]
    centres = with_centres(countries)
    snapshot = provenance.postings_snapshot()
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
        # What counts as a strongly correlated pair on the exhibit. Read from
        # the module that defines it so the page and `make correlation` cannot
        # report different counts from the same matrix.
        "strongAt": correlation.STRONG_AT,
        "sources": _sources(centres, snapshot),
        # Read out of the fetch's own record, never typed: the date, what was
        # scraped to get it, and whether there is more than one point in time.
        "provenance": {
            "postings": snapshot,
            "contaminant": provenance.contaminant_sample(),
        },
        "limits": LIMITS,
        "flags": FLAGS,
        "flagTitles": FLAG_TITLES,
        "baselines": baselines,
        "beyond": beyond,
        "nearMisses": [
            {"name": c.name, "market": C.MARKETS[c.market]["name"],
             "postings": c.postings, "employers": c.employers}
            for c in near
        ],
        "nearMissTotal": len(below),
        "unpriceable": C.UNPRICEABLE,
        "baselineDefault": C.BASELINE_DEFAULT,
        "fteDefault": C.FTE_DEFAULT,
        # The three inputs that turn a gross wage into a loaded cost. Two are
        # assumptions the reader sets and the exhibit labels as such; the third
        # is a horizon over each market's own measured drift.
        "loadingDefault": C.LOADING_FACTOR_DEFAULT,
        "attritionDefault": C.ATTRITION_UPLIFT_DEFAULT,
        "horizonDefault": C.HORIZON_YEARS_DEFAULT,
        "loadingMax": C.LOADING_FACTOR_MAX,
        "attritionMax": C.ATTRITION_UPLIFT_MAX,
        "horizonMax": C.HORIZON_YEARS_MAX,
        "asOf": snapshot["dateLabel"] if snapshot else "sample not fetched",
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
        # The same run, kept whole. The pre-JS fallback needs the bands and the
        # verdicts as well as the frequencies, and re-running 10,000 draws to
        # recover what this pass already computed would be absurd.
        data.setdefault("defaults", {})[archetype] = {
            "frequency": {k: round(v, 4) for k, v in stability.frequency.items()},
            "band": dict(stability.band),
            "verdict": {k: stability.verdict(k) for k in stability.frequency},
        }
    return data


def build_html() -> str:
    data = payload()
    html = (
        TEMPLATE.replace("__FONTS__", face_css())
        .replace("__DATA__", json.dumps(data, separators=(",", ":")))
        .replace("__SCORING__", SCORING_JS)
        .replace("__SCENARIO__", SCENARIO_JS)
        .replace("__META__", _meta(data))
        .replace("__REFRESH_URL__", C.REFRESH_URL)
    )
    # The declared scenario, written into the document rather than left for the
    # script to fill. Everything the page says is then true of the file as
    # shipped, not only of the file as executed.
    return fallback.inject(html, data)


def _meta(data: dict) -> str:
    """Description and card tags, built from the run rather than written down."""
    s = fallback.Scenario(data)
    snap = data["provenance"]["postings"]
    top = [r["name"] for r in s.top]
    if len(top) > 1:
        finding = (
            f"{', '.join(top[:-1])} and {top[-1]} finish level at the top; the draws "
            f"cannot separate them."
        )
    else:
        finding = f"{s.order[0]['name']} leads outright."
    description = (
        f"{len(s.rows)} cities where GBS and GCC roles are genuinely advertised, scored "
        f"on {len(PILLARS)} pillars of public data and re-ranked across 2,000 defensible "
        f"weightings. At the {s.arch['short']}'s starting weights, {finding}"
        + (f" One snapshot, {snap['dateLabel']}." if snap else "")
    )
    esc = fallback.esc
    tags = [
        f'<meta name="description" content="{esc(description)}">',
        f'<meta property="og:title" content="{esc(TITLE)}">',
        f'<meta property="og:description" content="{esc(description)}">',
        '<meta property="og:type" content="website">',
        f'<meta property="og:url" content="{esc(C.PUBLISHED_URL)}">',
        f'<meta property="og:image" content="{esc(C.OG_IMAGE_URL)}">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        f'<meta property="og:image:alt" content="{esc(OG_ALT)}">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{esc(TITLE)}">',
        f'<meta name="twitter:description" content="{esc(description)}">',
        f'<meta name="twitter:image" content="{esc(C.OG_IMAGE_URL)}">',
    ]
    return "\n".join(tags)


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
    // A quoted wage replaces the public figure everywhere the public figure
    // would be read — the ranking included, which shifts the normalisation
    // for every city, as new evidence should.
    const ovr = (typeof state !== "undefined" && state.overrides) || {};
    if (ovr[r.id] && ovr[r.id].w) v.cost = ovr[r.id].w.v;
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

/* ---- pillar correlation: mirrors src/correlation.py exactly ----
   Recomputed on screen rather than baked into the payload, because the overlap
   pillar depends on the headquarters the reader picks: moving the clock changes
   how independent the pillars are, and a figure that stayed still while the
   matrix underneath it moved would be the sort of stale claim this study exists
   to object to. Observation order does not affect a correlation, so the array
   order here and the sorted keys in Python give the same numbers. */
function pearson(xs, ys) {
  const n = xs.length;
  if (n < 2) return null;
  let mx = 0, my = 0;
  for (let i = 0; i < n; i++) { mx += xs[i]; my += ys[i]; }
  mx /= n; my /= n;
  let sxx = 0, syy = 0, sxy = 0;
  for (let i = 0; i < n; i++) {
    const dx = xs[i] - mx, dy = ys[i] - my;
    sxx += dx * dx; syy += dy * dy; sxy += dx * dy;
  }
  // A pillar that does not vary decides nothing, and its correlation is 0/0.
  // Null keeps that visible rather than imputing an "independent" zero.
  if (sxx <= 0 || syy <= 0) return null;
  return sxy / Math.sqrt(sxx * syy);
}

function correlationMatrix(scaled) {
  const cols = {};
  for (const p of DATA.pillars) cols[p] = scaled.map((it) => it.s[p]);
  return DATA.pillars.map((a) => DATA.pillars.map((b) => pearson(cols[a], cols[b])));
}

function correlationSummary(r) {
  const P = DATA.pillars;
  const varying = P.map((_, i) => i).filter((i) => r[i][i] !== null);
  const k = varying.length;
  const pairs = [];
  for (let a = 0; a < varying.length; a++) {
    for (let b = a + 1; b < varying.length; b++) {
      const i = varying[a], j = varying[b];
      if (r[i][j] !== null) pairs.push({ r: r[i][j], a: P[i], b: P[j] });
    }
  }
  if (!pairs.length) {
    return { pillars: k, pairs: 0, meanAbs: null, maxAbs: null,
             strong: 0, nEff: k, strongest: [] };
  }
  // n_eff = k^2 / ||R||_F^2 -- the participation ratio of the eigenvalues,
  // reached without an eigensolver. See src/correlation.py.
  let frob = 0;
  for (const i of varying) {
    for (const j of varying) if (r[i][j] !== null) frob += r[i][j] * r[i][j];
  }
  return {
    pillars: k,
    pairs: pairs.length,
    meanAbs: pairs.reduce((a, x) => a + Math.abs(x.r), 0) / pairs.length,
    maxAbs: Math.max(...pairs.map((x) => Math.abs(x.r))),
    strong: pairs.filter((x) => Math.abs(x.r) >= DATA.strongAt).length,
    nEff: frob > 0 ? (k * k) / frob : k,
    strongest: pairs.slice().sort((x, y) => Math.abs(y.r) - Math.abs(x.r)).slice(0, 3),
  };
}

/* ---- fully loaded cost: mirrors src/loaded.py exactly ----
   A wage is not what a role costs. Two of the three multipliers between them
   are assumptions the reader sets; the third is a horizon over each market's
   own measured drift, which the panel already carries. */
function clampAssumptions(a) {
  return {
    loading: Math.min(Math.max(a.loading, 0), DATA.loadingMax),
    attrition: Math.min(Math.max(a.attrition, 0), DATA.attritionMax),
    horizon: Math.trunc(Math.min(Math.max(a.horizon, 0), DATA.horizonMax)),
  };
}

/* Null where the drift was never measured: a panel median carried forward and
   presented as a projection is exactly the quiet fill this study objects to. */
function projectWage(wage, drift, years) {
  if (years <= 0) return wage;
  if (drift === null || drift === undefined) return null;
  return wage * Math.pow(1 + drift, years);
}

function loadedMonthly(wage, drift, a, isDestination) {
  const carried = projectWage(wage, drift, a.horizon);
  if (carried === null) return null;
  const loaded = carried * (1 + a.loading);
  return isDestination ? loaded * (1 + a.attrition) : loaded;
}

function loadedGap(originWage, originDrift, cityWage, cityDrift, a, fte) {
  a = clampAssumptions(a);
  const basePerRole = (originWage - cityWage) * 12;
  const o = loadedMonthly(originWage, originDrift, a, false);
  const c = loadedMonthly(cityWage, cityDrift, a, true);
  const missing = [];
  if (o === null) missing.push("origin");
  if (c === null) missing.push("city");
  const loadedPerRole = missing.length ? null : (o - c) * 12;
  return {
    basePerRole, baseTotal: basePerRole * fte,
    loadedPerRole, loadedTotal: loadedPerRole === null ? null : loadedPerRole * fte,
    unprojectable: missing, originMonthly: o, cityMonthly: c,
  };
}

/* Pillars that take one value per country: the reason the matrix looks the way
   it does. A pillar in this list cannot separate two cities in the same
   country whatever weight it is given. */
function nationalPillars(items) {
  const groups = new Map();
  for (const it of items) {
    const key = it.row.parent || it.row.id;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(it);
  }
  return DATA.pillars.filter((p) => [...groups.values()].every((g) => {
    const vals = g.map((it) => it.v[p]);
    const hi = Math.max(...vals), lo = Math.min(...vals);
    return (hi - lo) <= 1e-9 * Math.max(1, Math.abs(hi));
  }));
}
"""

# The view as a string. Everything a reader can set is encoded so a link
# reproduces the exact view and a saved name restores it. Kept apart from
# SCORING_JS because it mirrors nothing in Python — it exists only in the
# browser — but it is bundled the same way so tests/test_scenario.py can run
# it under node: a shared link is untrusted input, and every field has to be
# validated on the way in, falling back field-by-field rather than taking the
# page down with it.
SCENARIO_JS = r"""/* ---- scenario codec: the view as a string ---- */
function defaultScenarioState() {
  const archetype = Object.keys(DATA.archetypes)[0];
  return {
    archetype,
    weights: { ...DATA.archetypes[archetype].weights },
    hq: DATA.hq,
    baseline: DATA.baselineDefault,
    fte: DATA.fteDefault,
    loading: DATA.loadingDefault,
    attrition: DATA.attritionDefault,
    horizon: DATA.horizonDefault,
    scenario: null,
    overrides: {},
  };
}

function encodeScenario(s, {includeName = true} = {}) {
  const p = new URLSearchParams();
  p.set("v", "1");
  p.set("a", s.archetype);
  p.set("w", DATA.pillars.map((k) => Math.round((s.weights[k] || 0) * 100)).join("-"));
  p.set("hq", s.hq);
  p.set("o", s.baseline);
  p.set("f", String(s.fte));
  p.set("l", String(Math.round(s.loading * 100)));
  p.set("t", String(Math.round(s.attrition * 100)));
  p.set("y", String(s.horizon));
  if (includeName && s.scenario) p.set("n", s.scenario);
  encodeOverrides(p, s.overrides);
  return p.toString();
}

function isDefaultScenario(s) {
  return !s.scenario
    && encodeScenario(s, {includeName: false})
       === encodeScenario(defaultScenarioState(), {includeName: false});
}

/* Returns only the fields that survived validation; the caller merges them
   onto the defaults. Weights are accepted whole or not at all — a partial
   weighting is not a weighting anyone chose. */
function decodeScenario(str) {
  const out = {};
  let p;
  try { p = new URLSearchParams(str || ""); } catch { return out; }
  if (p.get("v") !== "1") return out;

  const a = p.get("a");
  if (a && DATA.archetypes[a]) out.archetype = a;

  const w = p.get("w");
  if (w) {
    const parts = w.split("-").map((x) => parseInt(x, 10));
    const ok = parts.length === DATA.pillars.length
      && parts.every((x) => Number.isInteger(x) && x >= 0 && x <= 60)
      && parts.some((x) => x > 0);
    if (ok) {
      out.weights = {};
      DATA.pillars.forEach((k, i) => { out.weights[k] = parts[i] / 100; });
    }
  }

  const hq = p.get("hq");
  if (hq && DATA.hqOffsets[hq] !== undefined) out.hq = hq;

  const o = p.get("o");
  if (o && DATA.baselines.some((b) => b.key === o)) out.baseline = o;

  /* Below the floor is rejected, above the ceiling is clamped: a link that
     says 999 roles moved meant "a lot", a link that says minus four meant
     nothing. */
  const int = (key, lo, hi) => {
    const n = parseInt(p.get(key), 10);
    return Number.isInteger(n) && n >= lo ? Math.min(n, hi) : undefined;
  };
  const f = int("f", 1, 5000);
  if (f !== undefined) out.fte = f;
  const l = int("l", 0, Math.round(DATA.loadingMax * 100));
  if (l !== undefined) out.loading = l / 100;
  const t = int("t", 0, Math.round(DATA.attritionMax * 100));
  if (t !== undefined) out.attrition = t / 100;
  const y = int("y", 0, DATA.horizonMax);
  if (y !== undefined) out.horizon = y;

  const n = (p.get("n") || "").trim().slice(0, 60);
  if (n) out.name = n;

  /* Client-supplied figures. Each entry is id~field~value~date~source, and the
     source is REQUIRED: a figure nobody will stand behind is an assumption
     wearing a number, and this tier exists to be the opposite of that. An
     entry that fails any check is dropped alone. */
  const ids = new Set(
    DATA.views.city[Object.keys(DATA.archetypes)[0]].map((r) => r.id));
  const overrides = {};
  let kept = 0;
  for (const raw of p.getAll("x")) {
    if (kept >= 50) break;
    const parts = raw.split("~");
    if (parts.length !== 5) continue;
    const [id, field, valueStr, date, sourceRaw] = parts;
    if (!ids.has(id)) continue;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) continue;
    const source = sourceRaw.trim().slice(0, 80);
    if (!source) continue;
    const value = parseInt(valueStr, 10);
    let v;
    if (field === "w") {
      if (!Number.isInteger(value) || value < 1) continue;
      v = Math.min(value, 99999);
    } else if (field === "l" || field === "t") {
      if (!Number.isInteger(value) || value < 0) continue;
      const cap = Math.round((field === "l" ? DATA.loadingMax : DATA.attritionMax) * 100);
      v = Math.min(value, cap);
    } else continue;
    (overrides[id] = overrides[id] || {})[field] = {v, source, date};
    kept++;
  }
  if (Object.keys(overrides).length) out.overrides = overrides;
  return out;
}

function encodeOverrides(p, overrides) {
  for (const id of Object.keys(overrides || {}).sort()) {
    for (const field of ["w", "l", "t"]) {
      const o = overrides[id][field];
      if (!o) continue;
      const source = String(o.source).replace(/~/g, " ").trim().slice(0, 80);
      p.append("x", `${id}~${field}~${o.v}~${o.date}~${source}`);
    }
  }
}
"""

TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GBS Location Selection</title>
__META__
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
  /* White, and precise. The ground was a sage grey (#e9eae4) that put a cast
     over every colour on the page and held --ink-3 at 3.14:1, under the floor
     for the 10.5px mono this page labels everything in. A consulting exhibit
     is set on white: the structure has to come from alignment and hairlines,
     which means the rules get lighter and the ink gets darker, not the reverse.
     Every ink here clears 4.5:1 on all three light surfaces. */
  --bg: #ffffff;
  /* One step of grey, used for grouping and hover only — never for decoration.
     A second, fainter step exists for the inputs that sit on the grey. */
  --panel: #f7f8f7;
  --panel-2: #fbfcfb;
  --ink: #0d1211;
  --ink-2: #414a46;
  --ink-3: #666f6a;
  /* Hairlines. The whole grid of the page is these two weights: --rule between
     rows of the same kind, --rule-strong where one kind of thing ends. */
  --rule: #e6e8e5;
  --rule-strong: #cdd2ce;
  --accent: #0f7a5c;
  /* The accent at low saturation, for the band a finding rests on. */
  --accent-soft: #eaf3ef;
  /* Bars below the leading band were a sage grey that read as dirt next to
     seven saturated pillar hues. In the accent's own hue instead, so the
     exhibit is one colour story, and light enough to sit on white. */
  --bar-rest: #a9cfc2;
  --warn: #b0374a;
  --shadow: 0 1px 2px rgba(13,18,17,.05);
  --flag-edge: rgba(18,26,23,.22);
  /* Correlation matrix tint: hue carries the sign, alpha the magnitude.
     Kept as raw channels so the cell can scale its own alpha inline. */
  --corr-pos: 20 107 84;
  --corr-neg: 176 55 74;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --bg: #14171a;
    --panel: #1c2024;
    --panel-2: #232830;
    --ink: #eef1ee;
    --ink-2: #b3bab4;
    --ink-3: #949d96;
    --rule: #2e343a;
    --rule-strong: #454d54;
    --accent: #3fa585;
    --accent-soft: #17302a;
    --bar-rest: #255045;
    --warn: #d97186;
    --shadow: none;
    --flag-edge: rgba(238,241,238,.30);
    --corr-pos: 63 165 133;
    --corr-neg: 217 113 134;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --bg: #14171a; --panel: #1c2024; --panel-2: #232830;
  --ink: #eef1ee; --ink-2: #b3bab4; --ink-3: #949d96;
  --rule: #2e343a; --rule-strong: #454d54;
  --accent: #3fa585; --accent-soft: #17302a; --bar-rest: #255045;
  --warn: #d97186; --shadow: none;
  --flag-edge: rgba(238,241,238,.30);
  --corr-pos: 63 165 133; --corr-neg: 217 113 134;
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
.deck .deck-lede { color: var(--ink-2); }
.deck .fold { margin-top: 10px; }

.layout { display: grid; grid-template-columns: 310px minmax(0,1fr); gap: 32px; align-items: start; }

.rail { position: sticky; top: 20px; display: flex; flex-direction: column; gap: 20px; }
@media (max-width: 940px) { .rail { position: static; } }
.card { background: transparent; border: 0; border-top: 1px solid var(--rule-strong); padding: 14px 0 0; box-shadow: none; }
.card h2 {
  font-family: var(--mono);
  font-size: 10.5px; letter-spacing: .14em; text-transform: uppercase;
  color: var(--ink-3); margin: 0 0 12px; font-weight: 500;
}
.rail { gap: 22px; }

/* Stacked, the rail sits between the finding and the exhibit. Centre type and
   the disclosure are short and belong there; the sources card is neither, and
   pushed Exhibit 1 two screens down a phone. `display: contents` dissolves the
   rail so its children can be ordered against main directly, which moves
   provenance below the exhibit without hiding it. */
@media (max-width: 940px) {
  .layout { display: flex; flex-direction: column; gap: 26px; }
  .rail { display: contents; }
  .rail > .card, .rail > .adjust { order: 1; }
  main { order: 2; }
  .rail > .sources-card { order: 3; }
}

/* One question is asked in the open — what kind of centre — and every other
   input waits behind this. The page used to present five cards of controls
   before it had said anything, which is the wrong order for an exhibit: a
   reader should be given the finding and then offered the means to attack it. */
.adjust { margin: 0; border-top: 1px solid var(--rule-strong); padding-top: 13px; }
/* Two lines, not one row: at rail width a title, a state and a marker on one
   baseline wrapped into each other. */
.adjust > summary {
  cursor: pointer; list-style: none; display: block; position: relative;
  padding-right: 16px;
  font-family: var(--mono); font-size: 10.5px; letter-spacing: .14em;
  text-transform: uppercase; color: var(--ink-3); font-weight: 500;
}
.adjust > summary::-webkit-details-marker { display: none; }
.adjust > summary::after {
  content: "+"; position: absolute; right: 0; top: -1px;
  font-size: 14px; line-height: 1; color: var(--ink-3);
}
.adjust[open] > summary::after { content: "\2212"; }
.adjust > summary:hover, .adjust[open] > summary { color: var(--ink-2); }
.adjust > summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
.adjust-title { display: block; }
/* What is behind the fold when it is shut, and what has been moved when it is
   not at its starting position. A disclosure that hides a changed setting is
   worse than one that hides a default. */
.adjust-state {
  display: block; margin-top: 5px; letter-spacing: .04em;
  text-transform: none; font-size: 10.5px; line-height: 1.4;
}
.adjust-state b { color: var(--accent); font-weight: 500; }
.adjust-body { display: flex; flex-direction: column; gap: 22px; margin-top: 18px; }
.adjust-body > .card:first-child { border-top: 0; padding-top: 0; }

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

/* Scenario controls: a name box and two quiet verbs. The card must not read
   as a feature — it is a filing drawer for the controls that already exist. */
.scn-row { display: grid; grid-template-columns: 1fr auto auto; gap: 7px; margin-top: 7px; }
.scn-row input {
  min-width: 0; font: inherit; font-size: 12.5px; padding: 5px 7px; color: var(--ink);
  background: var(--panel-2); border: 1px solid var(--rule-strong); border-radius: 4px;
}
.scn-row button {
  font: inherit; font-size: 12px; padding: 5px 10px; cursor: pointer;
  background: var(--panel); color: var(--ink); border: 1px solid var(--rule-strong);
}
.scn-row button:hover { border-color: var(--accent); color: var(--accent); }
.scn-row button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
/* The scenario's name rides in the eyebrow — and therefore onto the one-pager,
   which is where "which stand was this" actually gets asked. */
.scn-tag { color: var(--ink-2); }

/* Client figures: the middle tier between a measurement and an assumption,
   marked in the accent so the exhibit shows where private evidence entered. */
.ovr-actions { grid-template-columns: auto; justify-content: start; }
#ovr-source, #ovr-date {
  width: 100%; font: inherit; font-size: 12.5px; padding: 5px 7px; color: var(--ink);
  background: var(--panel-2); border: 1px solid var(--rule-strong); border-radius: 4px;
}
.ovr-list { margin: 10px 0 0; padding: 0; list-style: none; display: grid; gap: 6px; }
.ovr-list li {
  font-size: 11.5px; line-height: 1.4; color: var(--ink-2);
  display: flex; align-items: baseline; gap: 7px;
}
.ovr-list .src { color: var(--ink-3); }
.ovr-list button {
  font: inherit; font-size: 10.5px; padding: 1px 6px; cursor: pointer; margin-left: auto;
  background: transparent; color: var(--ink-3); border: 1px solid var(--rule-strong);
}
.ovr-list button:hover { border-color: var(--warn); color: var(--warn); }
.natl.ovr, .ovr-mark { color: var(--accent); border: 0; font-style: normal; }
.ovr-sources { columns: 1; max-width: 78ch; }
.ovr-sources b { color: var(--accent); }
.ovr-sources:empty { display: none; margin: 0; padding: 0; }
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
/* The line that states what you are buying is also the way to change it. The
   weights live behind a disclosure on purpose — an exhibit should say something
   before it offers five cards of controls — but the reader who has just been
   told what they are buying is exactly the one looking for that control. */
.belief-row .belief-edit {
  font-family: var(--mono); font-size: 10px; letter-spacing: .1em;
  text-transform: uppercase; color: var(--ink-3);
  background: none; border: 0; padding: 0; cursor: pointer;
  margin: 6px 0 0 16px; white-space: nowrap;
}
.belief-row .belief-edit:hover { color: var(--accent); }
.belief-row .belief-edit:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
@media print { .belief-row .belief-edit { display: none; } }

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
  display: grid; grid-template-columns: 9.6rem 1fr 5.4rem 7.3rem;
  align-items: center; gap: 10px; padding: 3px 0;
}
.case-row .cn { font-size: 12.5px; color: var(--ink-2); }
/* The base column is the reference, not the answer, so it is set back a step. */
.case-val.base-val { color: var(--ink-3); font-size: 11px; }
.case-head {
  display: grid; grid-template-columns: 9.6rem 1fr 5.4rem 7.3rem;
  gap: 10px; padding-bottom: 4px; margin-bottom: 2px;
  border-bottom: 1px solid var(--rule);
  font-family: var(--mono); font-size: 9.5px; text-transform: uppercase;
  letter-spacing: .08em; color: var(--ink-3);
}
.case-head .r { text-align: right; }
/* Said once per row, quietly: this city has no city-level wage. Seven of the
   eleven cities carry it, so a boxed chip made the common case look like the
   exception and wrapped the longer names; muted text states it without
   competing with the figures. */
.natl, .na {
  font-family: var(--mono); font-size: 9px; color: var(--ink-3);
  margin-left: 5px; white-space: nowrap; cursor: help;
}
.na { font-size: 10px; font-style: italic; }
.flag {
  width: 15px; height: 10px; margin-right: 7px; vertical-align: -1px;
  border: .5px solid var(--flag-edge); border-radius: 1px; flex: none;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}
/* Through a token, not an attribute override: the attribute is absent in the
   default "system" setting, so a literal here kept a black edge on dark ground. */
.case-track { position: relative; height: 15px; }
.case-bar { position: absolute; top: 0; bottom: 0; background: var(--accent); border-radius: 0 3px 3px 0; }
.case-bar.over { background: var(--warn); border-radius: 3px 0 0 3px; }
/* Two bars in one track: the loaded gap behind, the wage line in front. The
   overhang is what the loading assumptions added, which is the comparison the
   column pair exists to make. */
.case-bar.loaded { opacity: .34; }
.case-bar.base { opacity: 1; }
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
/* Reported, never ranked: no bar, no band, no rank number, and a rule above
   that separates it from the exhibit rather than continuing it. Five of seven
   pillars scored beside seven would read as the same measurement. */
.beyond { margin-top: 26px; border-top: 1px solid var(--rule-strong); padding-top: 10px; }
/* Wide content scrolls in its own box; the page never scrolls sideways. Head
   and rows share the scroller so a scrolled column keeps its label. */
.beyond-scroll { overflow-x: auto; }
.beyond-head, .beyond-row { min-width: 468px; }
.beyond-head {
  display: grid; grid-template-columns: minmax(0,1fr) 7rem repeat(4, 5.4rem);
  gap: 8px; margin-top: 16px; padding-bottom: 5px;
  border-bottom: 1px solid var(--rule-strong);
}
.beyond-head span {
  font-family: var(--mono); font-size: 10px; text-transform: uppercase;
  letter-spacing: .04em; color: var(--ink-3); text-align: right; line-height: 1.25;
}
.beyond-row {
  display: grid; grid-template-columns: minmax(0,1fr) 7rem repeat(4, 5.4rem);
  align-items: baseline; gap: 8px; padding: 6px 0; border-bottom: 1px solid var(--rule);
}
.beyond-row:hover { background: var(--panel); }
.beyond-row .cty { font-size: 13.5px; font-weight: 600; color: var(--ink); }
.beyond-row .mkt { font-family: var(--mono); font-size: 10.5px; color: var(--ink-3); }
.beyond-row .fig {
  text-align: right; font-family: var(--mono); font-size: 12px;
  font-variant-numeric: tabular-nums; color: var(--ink-2);
}
.beyond-row .fig.none { color: var(--ink-3); }

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
/* A tick and a cross. The markers were a dot and a dash, which needed the
   column heading to be read first to mean anything; these two say settled and
   not settled on their own, which is what a reader skimming one column needs. */
.settles li { padding-left: 19px; }
.settles li::before {
  content: ""; position: absolute; left: 1px; top: 4px;
  width: 5px; height: 9px; border-radius: 0; background: none;
  border: solid var(--accent); border-width: 0 1.7px 1.7px 0;
  transform: rotate(42deg);
}
.settles .not li::before {
  left: 0; top: 6px; width: 10px; height: 10px; border: 0; transform: rotate(45deg);
  background:
    linear-gradient(var(--warn), var(--warn)) 50% 50%/10px 1.7px no-repeat,
    linear-gradient(var(--warn), var(--warn)) 50% 50%/1.7px 10px no-repeat;
}
/* The two columns are a claim and its limit, so the limit is set off rather
   than merely placed beside it. */
.settles .not { border-left: 1px solid var(--rule); padding-left: 24px; }
@media (max-width: 700px) { .settles .not { border-left: 0; padding-left: 0; } }
.settles b { color: var(--ink); font-weight: 600; }
@media (max-width: 700px) { .settles-cols { grid-template-columns: 1fr; gap: 16px; } }

/* The close: not more analysis, the checks that would replace it. Numbered
   because they are a sequence a phase 2 would actually schedule, not a list
   of caveats to skim. */
.next { margin-top: 26px; border-top: 1px solid var(--rule-strong); padding-top: 10px; }
.next ol { margin: 12px 0 0; padding: 0 0 0 22px; display: grid; gap: 10px; }
.next li {
  font-size: 12.5px; line-height: 1.5; color: var(--ink-2); padding-left: 4px;
}
.next li::marker { font-family: var(--mono); font-size: 11px; color: var(--ink-3); }
.next b { color: var(--ink); font-weight: 600; }
/* Two sentences do not need the caveat's two-column flow; a break lands
   mid-sentence and reads as a layout fault. */
.next .case-caveat { columns: 1; max-width: 78ch; }

/* 70ch left a third of the measure blank beside a table that used all of it.
   Dropping the cap alone would give a 105-character line, so the width is
   filled with two columns rather than one long one. */
.case-caveat {
  margin: 10px 0 0; font-size: 11.5px; line-height: 1.5; color: var(--ink-3);
  columns: 2; column-gap: 32px;
}
.case-caveat b { color: var(--ink-2); }
@media (max-width: 860px) { .case-caveat { columns: 1; } }
.fld {
  display: block; font-size: 11px; letter-spacing: .04em; text-transform: uppercase;
  color: var(--ink-3); margin: 9px 0 3px;
}
.card .fld:first-of-type { margin-top: 0; }
.num {
  width: 100%; font: inherit; font-family: var(--mono); font-size: 12.5px;
  padding: 5px 7px; color: var(--ink);
  background: var(--panel-2); border: 1px solid var(--rule-strong); border-radius: 4px;
}
/* Three narrow boxes on one line: they are read together, and stacking them
   made the card look like it held three unrelated decisions. */
.assume { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 7px; }
.assume .fld { margin-top: 0; font-size: 9.5px; letter-spacing: .03em; }
.assume .num { padding: 5px 4px; text-align: center; }
/* Named as assumptions in the control itself, not only in the caveat below the
   exhibit — this is where a reader decides how much to trust the number. */
.assume-head {
  margin: 14px 0 5px; padding-top: 10px; border-top: 1px solid var(--rule);
  color: var(--ink-2);
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
  columns: 2; column-gap: 32px;
}
@media (max-width: 860px) { .exhibit-source { columns: 1; } }

/* The header stays while eleven rows scroll under it: at the foot of the list
   the two right-hand columns are a bare number and a word, and a reader who has
   scrolled past the header has no way to know which is which. */
.col-head {
  display: grid; grid-template-columns: 26px minmax(150px, 215px) minmax(0,1fr) 58px 88px;
  gap: 12px; margin-top: 18px; padding: 0 0 5px;
  border-bottom: 1px solid var(--rule-strong);
  position: sticky; top: 0; z-index: 4; background: var(--bg);
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
.bar { height: 15px; border-radius: 0 3px 3px 0; }
.bar.lead { background: var(--accent); }
.bar.rest { background: var(--bar-rest); }
/* Secondary: composition. It sat at 4px and 50% opacity, which put the one
   validated categorical palette on the page below the threshold of being read
   at all — and half-opacity is also what pushed three of the seven hues under
   3:1 against the surface. At 6px and .92 the strip is legible enough to aim a
   cursor at, which is what the click target needs it to be. */
.mix { display: flex; height: 6px; margin-top: 2px; opacity: .92; }
/* A surface gap, not a hairline: the separator is the ground showing through,
   so segments read as separate fills. 1px rather than the 2px the spec prefers
   because a pillar at a low weight can be a couple of pixels wide, and a 2px
   border on a 2px segment is not a segment. */
.mix .seg-fill { height: 100%; border-right: 1px solid var(--bg); }
.mix .seg-fill:last-child { border-right: 0; }

/* ---- the row as a control ---------------------------------------------
   Every figure behind a bar is in the payload already; until now the only way
   to reach it was the table at the foot of the page, which costs the reader
   the comparison they were looking at. The row opens in place instead. */
.rows .row { cursor: pointer; }
.row:hover, .row.open { background: var(--panel); }
/* The disclosure marker earns its place by pointing at the thing it opens. */
.who .nm .caret {
  display: inline-block; margin-left: 7px; font-family: var(--mono);
  font-size: 9px; color: var(--ink-3); vertical-align: 1px;
  opacity: 0; transition: opacity .12s;
}
.row:hover .caret, .row.open .caret, .row:focus-visible .caret { opacity: 1; }
.row.open .caret { color: var(--accent); }
.row:focus-visible { outline: 2px solid var(--ink); outline-offset: -2px; }

/* ---- the opened detail ------------------------------------------------ */
/* A sibling of the row, not a child: the row carries role="button", and a
   button with a button inside it is not a thing a screen reader can offer. */
.detail {
  background: var(--panel); border-bottom: 1px solid var(--rule);
  box-shadow: inset 3px 0 0 var(--accent);
  padding: 14px 18px 16px; margin-bottom: 0; cursor: default;
}
.detail-head {
  display: flex; flex-wrap: wrap; gap: 6px 18px; align-items: baseline;
  margin-bottom: 12px;
}
.detail-head .dh-t {
  font-family: var(--mono); font-size: 10px; letter-spacing: .14em;
  text-transform: uppercase; color: var(--ink-3);
}
.detail-head .dh-v { font-family: var(--mono); font-size: 11.5px; color: var(--ink-2); }
/* The contribution ledger. Seven rows that add to the score, so a reader can
   see which pillar actually put the city where it is — the question the bar
   raises and could not answer. */
/* Six columns of mono numbers have a floor a phone is under. The table
   scrolls inside its own box rather than pushing the page sideways. */
.ledger-scroll { overflow-x: auto; }
.ledger { width: 100%; min-width: 380px; border-collapse: collapse; font-variant-numeric: tabular-nums; }
.ledger th {
  font-family: var(--mono); font-size: 9.5px; letter-spacing: .07em;
  text-transform: uppercase; color: var(--ink-3); font-weight: 500;
  text-align: right; padding: 0 0 5px; border-bottom: 1px solid var(--rule);
}
.ledger th.l, .ledger td.l { text-align: left; }
.ledger td {
  font-family: var(--mono); font-size: 11.5px; color: var(--ink-2);
  text-align: right; padding: 4px 0; border-bottom: 1px solid var(--rule);
}
.ledger td.l { color: var(--ink); }
.ledger tr:last-child td { border-bottom: 0; }
.ledger td.l { white-space: nowrap; }
.ledger td.l .ico { width: 13px; height: 13px; margin-right: 7px; vertical-align: -2px; }
.ledger td.off { color: var(--ink-3); }
/* The contribution column, drawn as well as numbered: the whole point is which
   pillar is carrying the score, and a bar answers that faster than seven
   decimals do. Shares the row's own colour key. */
.ledger .contrib { width: 96px; padding-left: 12px; }
.ledger .cbar { height: 7px; border-radius: 0 2px 2px 0; min-width: 1px; }
.ledger tfoot td {
  border-top: 1px solid var(--rule-strong); border-bottom: 0;
  padding-top: 6px; color: var(--ink); font-weight: 600;
}
/* Facts a weighting cannot change, and that the ledger has no column for. */
.detail-notes {
  margin: 12px 0 0; display: grid; gap: 10px 26px;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
}
.detail-notes div { min-width: 0; }
.detail-notes dt {
  font-family: var(--mono); font-size: 9.5px; letter-spacing: .09em;
  text-transform: uppercase; color: var(--ink-3); margin-bottom: 2px;
}
.detail-notes dd { margin: 0; font-size: 12.5px; line-height: 1.45; color: var(--ink-2); }
.detail-notes dd .warnmark { color: var(--warn); }
.detail-close {
  margin-top: 12px; background: none; border: 0; padding: 0; cursor: pointer;
  font-family: var(--mono); font-size: 10px; letter-spacing: .1em;
  text-transform: uppercase; color: var(--ink-3);
}
.detail-close:hover { color: var(--accent); }
@media (max-width: 560px) {
  .detail { padding: 12px 12px 14px; }
  /* The bar restates the contribution column it sits beside. On a narrow
     screen the number is the one that has to survive. */
  .ledger .contrib { display: none; }
  .ledger { min-width: 300px; }
  .detail-head { gap: 4px 14px; }
}
@media (prefers-reduced-motion: no-preference) {
  .detail { animation: detail-in .18s ease-out; }
  @keyframes detail-in { from { opacity: 0; transform: translateY(-3px); } }
}
.stab { text-align: right; font-family: var(--mono); font-size: 12px; font-variant-numeric: tabular-nums; }
.stab .pct { display: block; }
.stab .tag { display: block; font-size: 10px; letter-spacing: .06em; text-transform: uppercase; }
.tag.robust { color: var(--accent); }
.tag.contingent { color: var(--ink-3); }
.tag.never { color: var(--warn); }
/* The band the finding rests on, tinted rather than edged. An exhibit marks
   the group it is making a claim about; the 3px inset rule it had before was a
   marker a reader has to be told how to read. */
.in-top { background: var(--accent-soft); box-shadow: inset 2px 0 0 var(--accent); }
.rows .in-top:hover, .rows .in-top.open { background: var(--accent-soft); filter: brightness(.985); }
/* A band is a group the draws cannot separate; the rule marks where one ends. */
.row.band-start { border-top: 1px solid var(--rule-strong); }
.row.band-start:first-child { border-top: 0; }

.prov {
  margin: 12px 0 0; padding-top: 10px; border-top: 1px solid var(--rule);
  font-size: 11px; line-height: 1.55; color: var(--ink-3);
}
.prov b { color: var(--ink-2); }
.sources { margin: 0; display: grid; gap: 9px; }
.sources div { display: grid; gap: 1px; }
.sources dt {
  font-family: var(--mono); font-size: 10px; text-transform: uppercase;
  letter-spacing: .07em; color: var(--ink-3);
}
.sources dd { margin: 0; font-size: 12.5px; line-height: 1.35; }
.sources .vint { color: var(--ink-3); font-size: 11.5px; }

.legend {
  display: flex; flex-wrap: wrap; align-items: center; gap: 6px 16px;
  margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--rule);
  font-size: 11.5px; color: var(--ink-2);
}
.legend span { display: inline-flex; align-items: center; gap: 5px; cursor: help; }
.legend .ico { width: 13px; height: 13px; }
.legend-lede {
  color: var(--ink-3); font-family: var(--mono); font-size: 9.5px;
  text-transform: uppercase; letter-spacing: .14em; margin-right: 2px;
}
/* The fill the strip actually uses, next to the glyph that names it: the glyph
   is stroked, and a stroke and a fill of one hue do not read as the same key
   until they are side by side once. */
.chip { width: 8px; height: 8px; flex: none; border-radius: 1px; }

.table-actions { display: flex; align-items: center; gap: 12px; margin-top: 12px; }
.table-actions button {
  font: inherit; font-size: 12.5px; padding: 5px 11px; cursor: pointer;
  background: var(--panel); color: var(--ink); border: 1px solid var(--rule-strong);
}
.table-actions button:hover { border-color: var(--accent); color: var(--accent); }
.table-actions button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.copy-status { font-size: 12px; color: var(--ink-3); }
.table-scroll { overflow-x: auto; }

/* ---- fold ---------------------------------------------------------------
   This page argues by qualification: nine tenths of its prose is the reasons a
   figure should not be trusted further than it goes. Deleting that would make
   the tool cheaper to read and worthless to rely on, so none of it is deleted —
   it is folded. What stays open is the one line a reader needs to know the
   qualification exists; the rest opens on request, and prints regardless. */
.fold { margin: 10px 0 0; border-top: 1px solid var(--rule); padding-top: 8px; }
.fold > summary {
  cursor: pointer; list-style: none; display: flex; align-items: baseline; gap: 8px;
  font-family: var(--mono); font-size: 10px; letter-spacing: .1em;
  text-transform: uppercase; color: var(--ink-3);
}
.fold > summary::-webkit-details-marker { display: none; }
.fold > summary:hover { color: var(--accent); }
.fold > summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
/* A caret that turns, drawn rather than typed so it sits on the baseline at any
   size. It is the only ornament in the component. */
.fold > summary::before {
  content: ""; flex: none; width: 0; height: 0; margin-bottom: 1px;
  border-left: 4px solid currentColor;
  border-top: 3.5px solid transparent; border-bottom: 3.5px solid transparent;
  transition: transform .15s;
}
.fold[open] > summary::before { transform: rotate(90deg); }
@media (prefers-reduced-motion: reduce) { .fold > summary::before { transition: none; } }
.fold > summary .fold-count {
  margin-left: auto; font-size: 9.5px; letter-spacing: .08em; opacity: .8;
}
.fold > :not(summary) { margin-top: 9px; }
/* The printed brief carries every source, so a fold is a screen affordance
   only: in print it is open and its handle is gone. */
@media print {
  .fold { display: block !important; border-top: 0; padding-top: 0; }
  .fold > summary { display: none !important; }
  .fold > :not(summary) { display: block !important; margin-top: 6px; }
}

.method { font-size: 13.5px; line-height: 1.55; max-width: 90ch; }
.method h3 {
  font-family: var(--mono); font-size: 10.5px; text-transform: uppercase;
  letter-spacing: .09em; color: var(--ink-3); margin: 16px 0 6px; font-weight: 600;
}
.method ol, .method ul { margin: 0; padding-left: 18px; display: grid; gap: 7px; }
.method li { color: var(--ink-2); }
.method-note { color: var(--ink-3); margin: 0 0 2px; max-width: 74ch; }

/* Lower triangle only: the matrix is symmetric, and printing both halves
   doubles the ink without adding a number. */
.corr-wrap { overflow-x: auto; margin: 9px 0 8px; }
table.corr { border-collapse: collapse; font-family: var(--mono); font-size: 11px; }
table.corr th {
  font-weight: 500; color: var(--ink-3); font-size: 10px; letter-spacing: .04em;
  padding: 3px 7px; white-space: nowrap; text-align: right;
}
table.corr thead th { text-align: center; padding-bottom: 5px; }
table.corr td {
  min-width: 44px; height: 24px; text-align: center; color: var(--ink);
  border: 1px solid var(--panel); font-variant-numeric: tabular-nums;
}
table.corr td.blank { border-color: transparent; }
.corr-read { color: var(--ink); margin: 0 0 4px; max-width: 74ch; }

.page-actions { display: flex; align-items: center; gap: 12px; margin-top: 18px; }
.page-actions button {
  font: inherit; font-size: 12.5px; padding: 6px 12px; cursor: pointer;
  display: inline-flex; align-items: center; gap: 7px; white-space: nowrap;
  background: var(--panel); color: var(--ink); border: 1px solid var(--rule-strong);
}
/* The row wraps as a whole on a narrow screen; a button does not wrap inside
   itself, which turned "Copy link to this view" into two ragged lines. */
.page-actions { flex-wrap: wrap; }
.page-actions .hint { flex: 1 1 14ch; }
/* The action glyphs carry no data, so they take the ink colour rather than a
   pillar's — a coloured icon here would imply a key that does not exist. */
.ico.act { width: 14px; height: 14px; flex: none; stroke: currentColor; }
/* Matches the buttons beside it: the row is one set of controls, and which of
   them happen to be links is not a distinction the reader has to care about. */
.page-actions .act-link {
  font-size: 12.5px; padding: 6px 12px; text-decoration: none;
  display: inline-flex; align-items: center; gap: 7px; white-space: nowrap;
  background: var(--panel); color: var(--ink); border: 1px solid var(--rule-strong);
}
.page-actions button:hover, .page-actions .act-link:hover {
  border-color: var(--accent); color: var(--accent);
}
.page-actions button:focus-visible, .page-actions .act-link:focus-visible {
  outline: 2px solid var(--accent); outline-offset: 2px;
}

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
  .case-row { padding: 0; grid-template-columns: 6.6rem 1fr 4.6rem 8.2rem; gap: 8px; }
  .case-head { display: none; }
  .case-val .per { display: inline; }
  .case-val .per::before { content: "\00a0\00b7\00a0"; }
  .case-row .cn { font-size: 8.5pt; }
  .case-track { height: 9px; }
  .case-row { line-height: 1.15; }
  .case-val { font-size: 7.5pt; }
  .case-val .per { font-size: 6.5pt; }
  .case-caveat {
    font-size: 6.7pt; line-height: 1.35; margin-top: 4px; max-width: none; columns: 1;
  }
  /* Print drops the long forms: the column header clipped to "REWEIGHTIN", and
     the caveat's last clause repeats the source note beneath it. */
  .screen-only, .settles, .beyond { display: none !important; }
  .col-head { margin-bottom: 2px; }
  .case-bar { background: #0f7a5c !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
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
  .bar.lead { background: #0f7a5c !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .bar.rest { background: #96c1b2 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .mix { display: none; }
  /* The brief is two pages of finding, not of one city's ledger: whatever the
     reader had open on screen is a detour in print. */
  .detail { display: none !important; }
  .row.open, .row:hover { background: none !important; }
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
.exhibit-source {
  font-size: 6.3pt; line-height: 1.3; margin-top: 4px; padding-top: 3px; columns: 1;
}
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
/* The hover says what it knows and then hands over: a tooltip cannot hold a
   seven-row ledger, so it names the way to one. */
.tooltip .tip-cta {
  display: block; margin-top: 5px; padding-top: 5px;
  border-top: 1px solid rgba(255,255,255,.2);
  font-size: 10px; letter-spacing: .06em; text-transform: uppercase; opacity: .75;
}

@media (prefers-reduced-motion: no-preference) {
  .row { transition: transform .42s cubic-bezier(.22,.61,.36,1); }
}
</style>
</head>
<body>
<div class="wrap">
<header>
  <p class="eyebrow"><span id="scope"></span> · <span id="asof"></span><span class="scn-tag" id="scenario-tag"></span></p>
  <div class="title-block">
    <div>
      <h1 id="headline">Which city, and how sure can you be?</h1>
      <p class="standfirst" id="takeaway"></p>
    </div>
    <div class="deck">
      <p class="deck-lede">Cities where GBS and GCC roles are genuinely advertised, scored on
         seven pillars of public data and re-ranked across 2,000 defensible weightings.</p>
      <details class="fold">
        <summary>How to read it</summary>
        <p>The finding is stated first, at the weighting the study declares. Change what you
           are buying, or open <em>adjust assumptions</em>, and the exhibit re-ranks: what
           survives is the answer, and cities the evidence cannot separate share a band
           rather than a rank. Click any city for the figures behind its score.</p>
      </details>
    </div>
  </div>
</header>

<div class="layout">
  <aside class="rail">
    <div class="card">
      <h2>Centre type</h2>
      <p class="panel-note">What you move sets where the weighting starts.</p>
      <div class="seg" id="archetype" role="group" aria-label="Centre type"></div>
      <p class="blurb" id="archetype-blurb"></p>
    </div>

    <div class="card">
      <h2>Scenarios</h2>
      <p class="panel-note">Save the whole view under a name.</p>
      <select id="scenario-list" aria-label="Saved scenarios"></select>
      <div class="scn-row">
        <input id="scenario-name" type="text" maxlength="60"
               placeholder="Name this view" aria-label="Scenario name">
        <button type="button" id="scenario-save">Save</button>
        <button type="button" id="scenario-delete">Delete</button>
      </div>
      <p class="slider-note" id="scenario-note"></p>
    </div>

    <details class="adjust" id="own-figures">
      <summary>
        <span class="adjust-title">Your figures</span>
        <span class="adjust-state" id="ovr-state"></span>
      </summary>
      <div class="adjust-body">
        <div class="card">
          <p class="panel-note">A figure you can stand behind replaces the public one and is
            marked as yours — on the exhibit, the one-pager and in the link. The wage enters
            the ranking; loading and attrition enter Exhibit 3 for that city.</p>
          <label class="fld" for="ovr-city">City</label>
          <select id="ovr-city" aria-label="City the figure is for"></select>
          <div class="assume">
            <div>
              <label class="fld" for="ovr-wage">Wage USD/mo</label>
              <input id="ovr-wage" class="num" type="number" min="1" max="99999"
                     aria-label="Quoted monthly wage in USD">
            </div>
            <div>
              <label class="fld" for="ovr-loading">Loading %</label>
              <input id="ovr-loading" class="num" type="number" min="0" max="100"
                     aria-label="Employer loading for this city, percent">
            </div>
            <div>
              <label class="fld" for="ovr-attrition">Attrition %</label>
              <input id="ovr-attrition" class="num" type="number" min="0" max="100"
                     aria-label="Attrition backfill for this city, percent">
            </div>
          </div>
          <label class="fld" for="ovr-source">Source — required</label>
          <input id="ovr-source" type="text" maxlength="80"
                 placeholder="e.g. recruiter quote, provider RFI" aria-label="Source of the figure">
          <label class="fld" for="ovr-date">As of</label>
          <input id="ovr-date" type="date" aria-label="Date of the figure">
          <div class="scn-row ovr-actions"><button type="button" id="ovr-add">Add figure</button></div>
          <ul class="ovr-list" id="ovr-list"></ul>
          <p class="slider-note" id="ovr-note"></p>
        </div>
      </div>
    </details>

    <details class="adjust" id="adjust">
      <summary>
        <span class="adjust-title">Adjust assumptions</span>
        <span class="adjust-state" id="adjust-state"></span>
      </summary>
      <div class="adjust-body">

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
      <input id="fte" class="num" type="number" min="1" max="5000" step="10" aria-label="Roles moved">
      <p class="slider-note">Sets Exhibit 3. Origins are markets ILOSTAT prices;
        most are not candidates and are never ranked.</p>

      <p class="fld assume-head">On top of the wage — your assumptions</p>
      <div class="assume">
        <div>
          <label class="fld" for="loading">Employer loading %</label>
          <input id="loading" class="num" type="number" min="0" max="100" step="1"
                 aria-label="Employer loading, percent of gross wage">
        </div>
        <div>
          <label class="fld" for="attrition">Attrition backfill %</label>
          <input id="attrition" class="num" type="number" min="0" max="100" step="1"
                 aria-label="Attrition and backfill uplift, percent">
        </div>
        <div>
          <label class="fld" for="horizon">Years forward</label>
          <input id="horizon" class="num" type="number" min="0" max="10" step="1"
                 aria-label="Years to project forward">
        </div>
      </div>
      <p class="slider-note" id="assume-note"></p>
    </div>

      </div>
    </details>

    <div class="card sources-card">
      <h2>Sources</h2>
      <dl class="sources" id="sources"></dl>
      <p class="prov" id="provenance"></p>
    </div>
  </aside>

  <main>
    <div class="exhibit-head">
      <p class="exhibit-label">Exhibit 1</p>
      <h2 id="board-title"></h2>
      <p class="hint">Bar length is the score; the strip beneath it is the composition.</p>
    </div>
    <div class="belief-row"><div class="belief" id="belief"></div></div>
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
      <div class="case-head">
        <span></span><span></span>
        <span class="r">base</span><span class="r">fully loaded</span>
      </div>
      <div id="case"></div>
      <p class="case-caveat ovr-sources" id="override-note"></p>
      <details class="fold">
        <summary>How base and loaded are built<span class="fold-count">2 figures you set</span></summary>
        <p class="case-caveat" id="case-caveat"></p>
      </details>
    </div>

    <details class="fold">
      <summary>Sources and coverage<span class="fold-count">ILOSTAT · World Bank · Eurostat · postings</span></summary>
      <p class="exhibit-source" id="exhibit-source"></p>
    </details>

    <div class="beyond">
      <p class="exhibit-label">Beyond the sample</p>
      <h3 class="strip-title">Established locations the postings feed cannot reach</h3>
      <div class="beyond-scroll">
        <div class="beyond-head">
          <span></span><span></span>
          <span class="ch-num">cost USD/mo</span><span class="ch-num">relevant workforce</span>
          <span class="ch-num">governance</span><span class="ch-num">hours shared</span>
        </div>
        <div id="beyond"></div>
      </div>
      <details class="fold">
        <summary>Why these are reported, not ranked<span class="fold-count">and what is absent entirely</span></summary>
        <p class="case-caveat" id="beyond-note"></p>
        <p class="case-caveat" id="beyond-more"></p>
      </details>
    </div>

    <div class="settles">
      <p class="exhibit-label">The boundary of this evidence</p>
      <div class="settles-cols">
        <div><h4>What it settles</h4><ul id="settles-yes"></ul></div>
        <div class="not"><h4>What it does not</h4><ul id="settles-no"></ul></div>
      </div>
    </div>

    <div class="next">
      <p class="exhibit-label">What would change this</p>
      <h3 class="strip-title">Three checks a shortlist validation would run</h3>
      <ol id="next"></ol>
      <details class="fold">
        <summary>Why these three, and not a phase 2</summary>
        <p class="case-caveat" id="next-note"></p>
      </details>
    </div>

    <div class="page-actions">
      <button type="button" id="one-pager"><svg class="ico act" viewBox="0 0 16 16"
        aria-hidden="true"><path d="M4.5 6V2.5h7V6M4.5 12.5h7v-3h-7zM3 6h10v4.5h-1.5"/>
        <path d="M4.5 10.5H3V6"/></svg>Print the brief</button>
      <span class="hint">Finding, both exhibits and every source — two pages.</span>
      <button type="button" id="copy-link"><svg class="ico act" viewBox="0 0 16 16"
        aria-hidden="true"><path d="M6.8 9.2a2.6 2.6 0 003.8 0l2-2a2.7 2.7 0 00-3.8-3.8l-.9.9"/>
        <path d="M9.2 6.8a2.6 2.6 0 00-3.8 0l-2 2a2.7 2.7 0 003.8 3.8l.9-.9"/></svg>Copy link to this view</button>
      <span class="copy-status" id="link-status" role="status"></span>
      <!-- A link, not a button, and it says where it goes: the refresh runs on
           GitHub because the fetch needs credentials a public page cannot
           carry. Naming it "Run the refresh on GitHub" rather than "Refresh"
           keeps the label honest about what pressing it does. -->
      <a class="act-link" href="__REFRESH_URL__" target="_blank" rel="noopener">
        <svg class="ico act" viewBox="0 0 16 16" aria-hidden="true">
        <path d="M13.5 8a5.5 5.5 0 01-9.4 3.9M2.5 8a5.5 5.5 0 019.4-3.9"/>
        <path d="M11.9 1.6v2.5h-2.5M4.1 14.4v-2.5h2.5"/></svg>Run the refresh on GitHub</a>
      <span class="hint">Refetches the postings and rebuilds this page. About
        fifteen minutes, and it needs repository access.</span>
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
        <h3>How independent the pillars are</h3>
        <p class="method-note">Pearson correlation of the normalised pillar scores across
          the <span id="corr-n"></span> cities on screen — the same values the weighting
          takes its mean over, so a weight acts on exactly this. Positive means the two
          pillars favour the same cities.</p>
        <div class="corr-wrap"><table class="corr" id="corr"></table></div>
        <p class="corr-read" id="corr-read"></p>
        <p class="method-note" id="corr-why"></p>
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
  loading: DATA.loadingDefault,
  attrition: DATA.attritionDefault,
  horizon: DATA.horizonDefault,
  // Client-supplied figures, keyed by city id then field (w/l/t). Each carries
  // its value, its source and its date — the middle tier between a public
  // measurement and an assumption.
  overrides: {},
  // Which city has its figures open, by id. Deliberately not part of the
  // scenario codec: it is where the reader is looking, not what they believe,
  // so it does not belong in a shared link. Held across renders so that
  // dragging a weight moves the open ledger under the cursor — watching one
  // city's contributions change is the point of opening it.
  open: null,
};

const isDark = () => {
  const t = document.documentElement.getAttribute("data-theme");
  if (t) return t === "dark";
  return matchMedia("(prefers-color-scheme: dark)").matches;
};
const colors = () => (isDark() ? DATA.colorsDark : DATA.colors);

__SCORING__
__SCENARIO__

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
      `${weightingLabel()}, <strong>${names.join(", ")} and ${last}</strong> finish level `
      + `at the top: the draws cannot separate them, so the order within that group is `
      + `not a finding.`;
  } else {
    const pct = ((stab.get(lead.row.id) ?? 0) * 100).toFixed(0);
    const where = DATA.marketNames[lead.row.parent] || "";
    $("#takeaway").innerHTML =
      `${weightingLabel()}, <strong>${lead.row.name}</strong> (${where}) leads outright, `
      + `holding a top-three place in ${pct}% of 2,000 nearby weightings.`;
  }
}

/* Which inputs the reader has moved off the study's declared starting point.
   Two callers want different subsets: the headline cares only about what can
   change the ranking (weights and the headquarters clock), while the
   disclosure label reports everything it hides. */
function moved() {
  const declared = DATA.archetypes[state.archetype].weights;
  return {
    weights: DATA.pillars.some(
      (p) => Math.abs(state.weights[p] - declared[p]) > 1e-9),
    hq: state.hq !== DATA.hq,
    cost: state.baseline !== DATA.baselineDefault
      || state.fte !== DATA.fteDefault
      || state.loading !== DATA.loadingDefault
      || state.attrition !== DATA.attritionDefault
      || state.horizon !== DATA.horizonDefault,
  };
}

/* The finding at the top has to say whose weighting it is the finding for.
   Unqualified, it reads as the study's conclusion even after a reader has
   dialled cost to sixty per cent. */
function weightingLabel() {
  const m = moved();
  if (m.weights || m.hq) return "At your weighting";
  return `At the ${DATA.archetypes[state.archetype].short}\u2019s starting weights`;
}

function renderAdjustState() {
  const m = moved();
  const changed = [
    m.weights && "weights", m.hq && "headquarters", m.cost && "cost inputs",
  ].filter(Boolean);
  $("#adjust-state").innerHTML = changed.length
    ? `<b>${changed.join(", ")} changed</b>`
    : `weights \u00b7 headquarters \u00b7 cost`;
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
  // Created once, and only when a script is running to make it work: without
  // JS the control would be a button that does nothing.
  if (!$("#belief-edit")) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "belief-edit";
    b.id = "belief-edit";
    b.textContent = "Change weights";
    $(".belief-row").appendChild(b);
  }

  const host = $("#rows");
  const prev = new Map();
  host.querySelectorAll(".row").forEach((el) => prev.set(el.dataset.id, el.getBoundingClientRect().top));

  host.innerHTML = "";
  const maxScore = Math.max(...ranked.map((x) => x.score), 1e-9);
  // The measured value behind each normalised score, and which pillars take one
  // value per country. Both are needed by an opened row and neither survives
  // normalisation, so they are carried across from the items the scoring saw.
  const rawById = new Map(items.map((it) => [it.row.id, it.v]));
  const natlSet = new Set(nationalPillars(items));
  // A city can only be open if it is still on the board.
  if (state.open && !ranked.some((r) => r.row.id === state.open)) state.open = null;
  ranked.forEach((r, i) => {
    const f = stab.get(r.row.id) ?? 0;
    const v = verdict(f, r.row);
    const b = band.get(r.row.id);
    const opensBand = i === 0 || band.get(ranked[i - 1].row.id) !== b;
    const isOpen = state.open === r.row.id;
    const el = document.createElement("div");
    el.className = "row" + (b === 1 ? " in-top" : "") + (opensBand ? " band-start" : "")
      + (isOpen ? " open" : "");
    el.dataset.id = r.row.id;
    // The row is the control. Announced as one, reachable by keyboard, and it
    // says what it opens — a reader on a screen reader gets the same offer a
    // cursor does.
    el.setAttribute("role", "button");
    el.tabIndex = 0;
    el.setAttribute("aria-expanded", isOpen ? "true" : "false");
    el.setAttribute("aria-controls", `d-${r.row.id}`);

    // The country first: a reader should not have to know where Poznań is to
    // read the ranking.
    const where = DATA.marketNames[r.row.parent] || "";
    const ovrW = (state.overrides[r.row.id] || {}).w;
    const costNote = ovrW
      ? `<span class="ovr-mark" title="${escHtml(ovrW.source)}, ${ovrW.date}">client wage</span>`
      : r.row.costResolved
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
        `<div class="bar ${tone}" style="width:${width.toFixed(2)}%"` +
          ` data-name="${escHtml(r.row.name)}" data-score="${r.score.toFixed(3)}"` +
          ` data-band="${b}"></div>` +
        `<div class="mix" style="width:${width.toFixed(2)}%">${segs}</div>` +
      `</div>`;

    const n = r.row.postings;
    const thin = r.row.isCity && n != null && n < DATA.evidenceFloor;
    const evidence = n == null ? "—"
      : `<span class="${thin ? "thin" : ""}">${n}</span>`;

    el.innerHTML =
      `<div class="rank">${opensBand ? b : ""}</div>` +
      `<div class="who"><span class="nm">${flag(r.row.parent)}${r.row.name}`
      + `<span class="caret">${isOpen ? "\u25B2" : "\u25BC"}</span></span>`
      + `<span class="sub">${sub}</span></div>` +
      `<div class="bar-cell">${bar}</div>` +
      `<div class="evidence" title="${n == null ? "No postings sample for this city."
          : `${r.row.name}: ${n} posting${n === 1 ? "" : "s"} the work-family classifier `
            + `could decide, out of ${r.row.postingsSeen} that qualified the city. The `
            + `capability pillar rests on those ${n}` + (thin
              ? `, below the floor of ${DATA.evidenceFloor} needed to call a place robust.`
              : `.`)}">${evidence}</div>` +
      `<div class="stab"><span class="pct">${(f * 100).toFixed(0)}%</span>` +
      `<span class="tag ${v}">${v}</span></div>`;
    host.appendChild(el);
    if (isOpen) {
      const d = document.createElement("div");
      d.className = "detail";
      d.id = `d-${r.row.id}`;
      d.setAttribute("role", "region");
      d.setAttribute("aria-label", `${r.row.name}: the figures behind the score`);
      d.innerHTML = detailHtml(r, rawById.get(r.row.id) || {}, f, b, C, natlSet);
      host.appendChild(d);
    }
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

  // The glyph, not a square: it carries the pillar's meaning and its colour in
  // one mark. Three of the seven hues sit under 3:1 against white, which the
  // validator allows only with a secondary encoding — this is that encoding,
  // and it doubles as the key for the strip and the ledger.
  $("#legend").innerHTML = `<span class="legend-lede">Composition</span>` + DATA.pillars.map((p) =>
    `<span title="${escHtml(DATA.pillarNotes[p] || "")}">${icon(p)}`
    + `<i class="chip" style="background:${C[p]}"></i>${DATA.pillarLabels[p]}</span>`).join("");

  renderStrip(ranked, band);
  renderTable(ranked, stab);
  renderCase(ranked);
  renderBeyond();
  renderNotShown();
  renderSettles(ranked, band, rows);
  renderNext(ranked, band);
  renderCorrelation(items, scaled);
  renderAdjustState();
  renderOverrideNote();
  renderSource(rows);
  renderFoot(rows);
  syncUrl();
  updateScenarioTag();
}

/* ---- how independent the pillars are ----
   The robustness column is worth what the independence of the pillars is
   worth, so the page measures it rather than leaving the reader to assume it.
   Columns are numbered rather than labelled: at this width a header row of
   seven pillar names is unreadable, and the row labels already carry them. */
function renderCorrelation(items, scaled) {
  const P = DATA.pillars;
  const r = correlationMatrix(scaled);
  const s = correlationSummary(r);
  const num = (v) => v.toFixed(2).replace("-", "−");

  $("#corr-n").textContent = scaled.length;

  const head = `<thead><tr><th></th>${
    P.slice(0, -1).map((_, j) => `<th>${j + 1}</th>`).join("")
  }</tr></thead>`;
  const body = P.map((p, i) => {
    const cells = P.slice(0, -1).map((_, j) => {
      if (j >= i) return `<td class="blank"></td>`;
      const v = r[i][j];
      if (v === null) return `<td title="does not vary">—</td>`;
      const hue = v >= 0 ? "--corr-pos" : "--corr-neg";
      const tint = `background:rgb(var(${hue}) / ${(Math.abs(v) * 0.32).toFixed(3)})`;
      return `<td style="${tint}" title="${DATA.pillarLabels[p]} and `
        + `${DATA.pillarLabels[P[j]]}: ${num(v)}">${num(v)}</td>`;
    }).join("");
    return `<tr><th>${i + 1} ${DATA.pillarLabels[p]}</th>${cells}</tr>`;
  }).join("");
  $("#corr").innerHTML = head + `<tbody>${body}</tbody>`;

  if (s.pairs) {
    $("#corr-read").innerHTML =
      `<strong>${s.strong} of the ${s.pairs} pairs</strong> correlate at `
      + `${DATA.strongAt} or above, and the average pair sits at ${num(s.meanAbs)}. `
      + `These ${s.pillars} pillars therefore carry about `
      + `<strong>${s.nEff.toFixed(1)} independent directions</strong> between them, so the `
      + `${DRAWS.toLocaleString("en-US")} reweightings explore correspondingly less of the `
      + `decision space than their count suggests.`;
  } else {
    $("#corr-read").textContent =
      "Too few varying pillars on screen to measure a correlation.";
  }

  // The limits list leads with this rather than mentioning it, because it
  // qualifies the robustness column the whole exhibit is read through. Written
  // on every render, not once at startup: the overlap pillar moves with the
  // headquarters, and so does the figure.
  const limit = s.pairs
    ? `The ${P.length} pillars are <strong>not independent</strong>: the average pair `
      + `correlates at ${num(s.meanAbs)} and they carry about ${s.nEff.toFixed(1)} `
      + `independent directions between them, because ${nationalPillars(items).length} `
      + `of the ${P.length} are national series shared by every city in a country. `
      + `The ${DRAWS.toLocaleString("en-US")} reweightings therefore explore substantially `
      + `less of the decision space than their count suggests — a top-three place that `
      + `survives them has survived less than the number sounds like. The matrix is above.`
    : null;
  // Counted, not asserted: a second fetch has to change this sentence rather
  // than leave it claiming a single point in time the data no longer is.
  const snap = DATA.provenance.postings;
  const sample = snap
    ? (snap.isSnapshot
        ? `<b>One snapshot, ${snap.dateLabel}.</b> A city hiring quietly during the fetch `
          + `is under-represented; absence is weak evidence, not a verdict. Nothing here `
          + `can show a trend, because there is only one point in time to compare.`
        : `<b>${snap.count} snapshots</b>, the most recent ${snap.dateLabel}. A city hiring `
          + `quietly during a fetch is under-represented; absence is weak evidence, not a `
          + `verdict.`)
    : `<b>No postings sample has been fetched</b>, so capability and employer depth are `
      + `unavailable and no city can be ranked.`;
  $("#limits").innerHTML = [limit, sample, ...DATA.limits]
    .filter(Boolean).map((x) => `<li>${x}</li>`).join("");

  const national = nationalPillars(items);
  const names = national.map((p) => DATA.pillarLabels[p].toLowerCase());
  const last = names.pop();
  $("#corr-why").innerHTML = national.length
    ? `Why: ${national.length} of the ${P.length} pillars — `
      + `${names.length ? names.join(", ") + " and " : ""}${last} — are national series `
      + `that take one value per country across these cities. They cannot separate two `
      + `cities in the same country whatever weight they are given, and the countries `
      + `themselves line up on close to one axis.`
    : `Every pillar varies within at least one country here.`;
}

/* ---- one city, opened ------------------------------------------------
   A bar answers "which city", and raises "why". Everything needed to answer
   the second is already in the payload; the only route to it was the table at
   the foot of the page, which costs the reader the comparison they were
   looking at. This is that table for one city, in the gap the row leaves.

   The ledger's columns are the four steps the score actually takes: what was
   measured, what that became once every city was put on 0–1, what the reader
   weighted it, and what it therefore contributed. Read across a row and the
   arithmetic is checkable; read down the last column and the answer to "why
   is this city here" is the longest bar. */
function pillarMeasured(p, v) {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  switch (p) {
    case "cost": return "$" + Math.round(v).toLocaleString("en-US");
    case "talent": return v >= 1e5 ? (v / 1e6).toFixed(1) + "m"
      : Math.round(v).toLocaleString("en-US");
    case "risk": return v.toFixed(0);
    case "capability": return (v * 100).toFixed(0) + "%";
    case "timezone": return v.toFixed(1) + "h";
    // Stored as the negative of measured wage drift, so that more is better
    // like every other pillar. Shown as the drift itself, which is the figure
    // a reader recognises.
    case "durability": return (-v >= 0 ? "+" : "") + (-v * 100).toFixed(1) + "%";
    case "depth": return v.toFixed(0);
    default: return String(v);
  }
}
const PILLAR_UNITS = {
  cost: "USD per head, month",
  talent: "relevant workforce",
  risk: "governance, 0–100",
  capability: "share of postings",
  timezone: "hours with your HQ",
  durability: "wage drift a year",
  depth: "employers in market",
};

function detailHtml(r, raw, freq, b, C, natlSet) {
  const P = DATA.pillars;
  const wTotal = P.reduce((a, p) => a + state.weights[p], 0) || 1;
  const maxPart = Math.max(...P.map((p) => r.parts[p]), 1e-9);
  const row = r.row;

  const head =
    `<div class="detail-head">`
    + `<span><span class="dh-t">Band</span> <span class="dh-v">${b}</span></span>`
    + `<span><span class="dh-t">Score</span> <span class="dh-v">${r.score.toFixed(3)}</span></span>`
    + `<span><span class="dh-t">Top-3 across reweightings</span> `
    + `<span class="dh-v">${(freq * 100).toFixed(0)}%</span></span>`
    + `</div>`;

  const body = P.map((p) => {
    const off = state.weights[p] <= 0;
    const isNatl = natlSet.has(p);
    return `<tr>`
      + `<td class="l${off ? " off" : ""}">`
      + `${icon(p)}${DATA.pillarLabels[p]}`
      // "country-wide", not "national": the cost basis below already uses
      // "national average" for a different fact — that Mumbai has no city wage —
      // and two senses of the same word in one panel is one too many.
      + (isNatl ? `<span class="natl" title="One value for the whole country, so `
          + `this pillar cannot separate two cities in `
          + `${escHtml(DATA.marketNames[row.parent] || "the same country")}.">`
          + `country-wide</span>` : "")
      + `</td>`
      + `<td class="${off ? "off" : ""}" title="${escHtml(PILLAR_UNITS[p] || "")}">`
      + `${pillarMeasured(p, raw[p])}</td>`
      + `<td class="${off ? "off" : ""}">${r.scaled[p].toFixed(2)}</td>`
      + `<td class="${off ? "off" : ""}">${(state.weights[p] / wTotal * 100).toFixed(0)}%</td>`
      + `<td class="${off ? "off" : ""}">${r.parts[p].toFixed(3)}</td>`
      + `<td class="contrib"><div class="cbar" style="width:${(r.parts[p] / maxPart * 100).toFixed(1)}%;`
      + `background:${C[p]}"></div></td>`
      + `</tr>`;
  }).join("");

  const ledger =
    `<div class="ledger-scroll"><table class="ledger">`
    + `<thead><tr><th class="l">Pillar</th><th>Measured</th><th>Score</th>`
    + `<th>Weight</th><th>Contribution</th><th class="contrib"></th></tr></thead>`
    + `<tbody>${body}</tbody>`
    + `<tfoot><tr><td class="l">Total</td><td></td><td></td>`
    + `<td>100%</td><td>${r.score.toFixed(3)}</td><td class="contrib"></td></tr></tfoot>`
    + `</table></div>`;

  // The facts a weighting cannot move, and that the ledger has no column for.
  const n = row.postings;
  const thin = row.isCity && n != null && n < DATA.evidenceFloor;
  const evidence = n == null
    ? "No postings sample for this city."
    : `${n} of ${row.postingsSeen} postings classified`
      + (thin ? `<span class="warnmark"> — below the floor of ${DATA.evidenceFloor}, `
          + `so this city cannot be called robust</span>` : "")
      + ` · ${row.employers} employers`;

  const ovrW = (state.overrides[row.id] || {}).w;
  const costBasis = ovrW
    ? `Your figure: $${Math.round(ovrW.v).toLocaleString("en-US")} — `
      + `${escHtml(ovrW.source)}, ${escHtml(String(ovrW.date))}`
    : row.costResolved
      ? `City level: ${row.regionIndex.toFixed(2)}× the national wage, `
        + `${row.regionYear || row.costYear}`
      : `National average, ${row.costYear} — no city-level wage is published for `
        + `${escHtml(row.name)}, so no city premium sits on either side of it`;

  const notes =
    `<dl class="detail-notes">`
    + `<div><dt>Evidence behind capability</dt><dd>${evidence}</dd></div>`
    + `<div><dt>Cost basis</dt><dd>${costBasis}`
    + (row.costPpp ? ` · $${Math.round(row.costPpp).toLocaleString("en-US")} at PPP` : "")
    + `</dd></div>`
    + `<div><dt>Languages in its postings</dt><dd>`
    + `${(row.languages || []).map(escHtml).join(", ") || "None asked for"}</dd></div>`
    + `<div><dt>Already operating there</dt><dd>`
    + `${(row.operators || []).map(escHtml).join(", ") || "None named in the sample"}</dd></div>`
    + `</dl>`;

  return head + ledger + notes
    + `<button type="button" class="detail-close">Close ${escHtml(row.name)}</button>`;
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
  const a = { loading: state.loading, attrition: state.attrition, horizon: state.horizon };

  const items = ranked
    .filter((r) => r.row.cost != null)
    .map((r) => {
      // The row's drift falls back to the panel median where a market's series
      // is too short to measure one, which is right for ageing a stale
      // observation by a year and wrong for projecting a decade. Only a
      // measured rate is offered to the projection; the rest report as
      // unavailable, which is what they are.
      const drift = r.row.driftMeasured ? r.row.drift : null;
      // Client figures replace their public counterparts for this city only:
      // the quoted wage stands in for ILOSTAT, and a quoted loading or
      // attrition replaces the uniform assumption on the destination side.
      const ovr = state.overrides[r.row.id] || {};
      const wage = ovr.w ? ovr.w.v : r.row.cost;
      const ca = {
        loading: ovr.l ? ovr.l.v / 100 : a.loading,
        attrition: ovr.t ? ovr.t.v / 100 : a.attrition,
        horizon: a.horizon,
      };
      const g = loadedGap(base.monthly, base.drift, wage, drift, ca, fte);
      return {
        name: r.row.name, market: r.row.parent, row: r.row, ovr,
        base: g.baseTotal, basePerRole: g.basePerRole,
        loaded: g.loadedTotal, loadedPerRole: g.loadedPerRole,
        unprojectable: g.unprojectable,
      };
    })
    // Ordered on the loaded figure where there is one, since that is the column
    // the exhibit now leads with; cities that cannot be projected keep their
    // base position rather than being dropped to the bottom.
    .sort((x, y) => (y.loaded ?? y.base) - (x.loaded ?? x.base));

  // The track holds both bars, so it has to span whichever reaches furthest.
  const reach = items.flatMap((i) => [i.base, i.loaded].filter((v) => v != null));
  const span = Math.max(...reach.map(Math.abs), 1);
  // Zero sits inside the track only when something lands above the baseline.
  const worst = Math.min(...reach, 0);
  const full = span + Math.abs(worst);
  const zero = (Math.abs(worst) / full) * 100;
  const bar = (v, cls) => {
    const w = (Math.abs(v) / full) * 100;
    return v < 0
      ? `<div class="case-bar over ${cls}" style="right:${(100 - zero).toFixed(2)}%;width:${w.toFixed(2)}%"></div>`
      : `<div class="case-bar ${cls}" style="left:${zero.toFixed(2)}%;width:${w.toFixed(2)}%"></div>`;
  };

  const horizonLabel = a.horizon > 0
    ? ` in <strong>${a.horizon} year${a.horizon === 1 ? "" : "s"}</strong>` : ``;
  $("#case-title").innerHTML =
    `Annual wage gap for <strong>${fte.toLocaleString("en-US")} `
    + `role${fte === 1 ? "" : "s"}</strong> leaving <strong>${base.label}</strong>${horizonLabel}`;

  $("#case").innerHTML = items.map((i) => {
    // The loaded bar is drawn behind the base one, so the base reads as the
    // part of the gap that is wage and the overhang as what loading added.
    const bars = (i.loaded == null ? `` : bar(i.loaded, "loaded")) + bar(i.base, "base");
    // A city whose cost is its country's carries no city premium, and saying so
    // per row is the difference between a missing figure and a silent one.
    const ovrFields = Object.keys(i.ovr || {});
    const national = ovrFields.length
      ? `<span class="natl ovr" title="${escHtml(overrideTitle(i.row.id))}">client figure</span>`
      : i.row.costResolved
        ? ``
        : `<span class="natl" title="No city-level wage for ${i.name}: this is `
          + `${DATA.marketNames[i.market] || "its country"}'s national figure, so the gap `
          + `carries no city premium either way.">national</span>`;
    const loadedCell = i.loaded == null
      ? `<span class="na" title="${DATA.marketNames[i.market] || "This market"} has too `
        + `short a wage series to measure a drift, so it cannot be projected forward. `
        + `The base figure stands.">not projectable</span>`
      : `${money(i.loaded)}<span class="per">${money(i.loadedPerRole)} per role</span>`;
    return `<div class="case-row"><span class="cn">${flag(i.market)}${i.name}${national}</span>`
      + `<div class="case-track"><div class="case-zero" style="left:${zero.toFixed(2)}%"></div>${bars}</div>`
      + `<span class="case-val base-val">${money(i.base)}</span>`
      + `<span class="case-val">${loadedCell}</span></div>`;
  }).join("");

  const unresolved = items.filter((i) => !i.row.costResolved).length;
  const cannot = items.filter((i) => i.loaded == null);

  // Print keeps the bounds that change how the number is read and drops the
  // elaborations, because the page is decided by three lines here.
  // A baseline is always a national average; some cities carry a regional index.
  // That puts a capital premium on one side of the subtraction and not the other,
  // which is what makes Warsaw look dearer than a UK national mean.
  const tilted = ranked
    .filter((r) => r.row.regionIndex && r.row.regionIndex > 1)
    .sort((a2, b2) => b2.row.regionIndex - a2.row.regionIndex);
  const tilt = tilted.length
    ? `The baseline is a national average, while `
      + tilted.slice(0, 2).map((r) =>
          `${r.row.name} carries ${r.row.regionIndex.toFixed(2)}×`).join(" and ")
      + ` its own country mean, so a capital-city premium sits on one side of the `
      + `subtraction and not the other. `
    : ``;

  // What the loaded column is and is not. The uniform-factor point is the one
  // that matters: a reader who sees a "fully loaded" column will assume it
  // prices the difference between Brazilian and Indian employer charges, and it
  // does not.
  const loadPct = (x) => `${Math.round(x * 100)}%`;
  const loadedNote =
    `<b>Base</b> is the gross wage line. <b>Loaded</b> adds `
    + `${loadPct(state.loading)} employer charges to both sides and `
    + `${loadPct(state.attrition)} attrition backfill to the destination only, since the `
    + `origin is not being stood up`
    + (a.horizon > 0
        ? `, then carries each market forward ${a.horizon} year${a.horizon === 1 ? "" : "s"} `
          + `at its own measured wage drift`
        : ``)
    + `. Those first two are <b>assumptions you set, not measured here</b>: no free source `
    + `gives comparable employer-charge schedules for all eleven markets, so the factor is `
    + `uniform, which scales every gap and cannot reorder them — real charges differ sharply `
    + `by country and pricing that difference is precisely what this cannot do. `
    + (unresolved
        ? `<span class="screen-only">${unresolved} of ${items.length} cities are marked `
          + `<b>national</b>: no city-level wage exists for them, so neither side of their `
          + `gap carries a city premium. </span>`
        : ``)
    + (cannot.length
        ? `<span class="screen-only">${cannot.map((i) => i.name).join(", ")} `
          + `cannot be projected forward — too short a wage series to measure a drift — so `
          + `${cannot.length === 1 ? "it keeps its base figure" : "they keep their base figures"} `
          + `rather than being carried at a panel median. </span>`
        : ``);

  $("#case-caveat").innerHTML =
    loadedNote
    + `Wage line only, at ${base.label}’s blended rate for professional and clerical `
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
function renderBeyond() {
  // One column, one unit: 722,616 beside 2.4m made the reader convert.
  const n = (x, d) => x == null ? "\u2014"
    : x >= 1e5 ? `${(x / 1e6).toFixed(1)}m`
    : x.toLocaleString("en-US", { maximumFractionDigits: d ?? 0 });

  $("#beyond").innerHTML = DATA.beyond.map((r) =>
    `<div class="beyond-row">`
    + `<span class="cty">${flag(r.key)}${r.city}</span>`
    + `<span class="mkt">${r.market}</span>`
    + `<span class="fig">${n(r.cost)}</span>`
    + `<span class="fig">${n(r.talent)}</span>`
    + `<span class="fig">${n(r.risk)}</span>`
    + `<span class="fig">${r.overlap.toFixed(1)}h</span></div>`).join("");

  const years = [...new Set(DATA.beyond.map((r) => r.costYear))].sort();
  $("#beyond-note").innerHTML =
    `Reported, not ranked. Five pillars reach these markets because ILOSTAT and the World `
    + `Bank cover every country alike; <b>capability and employer depth do not</b>, and those `
    + `are the two the postings carry. Cost is national, observed `
    + `${years[0] === years[years.length - 1] ? years[0] : `${years[0]}\u2013${years[years.length - 1]}`}; `
    + `the city named is the one a programme would consider, not a measured city figure.`;
}

/* Three ways a location can be missing, and they are not the same thing.
   A reader who asks about one of them should not be told about another. */
function renderNotShown() {
  // Six locations with two figures each is a list, not a finding. Three carry it.
  const near = DATA.nearMisses.slice(0, 3).map((m) =>
    `<b>${m.name}</b> (${m.postings} postings, ${m.employers} employer`
    + `${m.employers === 1 ? "" : "s"})`).join(", ");
  const un = Object.entries(DATA.unpriceable)
    .map(([c, cities]) => `<b>${c}</b> (${cities})`).join(" and ");

  $("#beyond-more").innerHTML =
    `Two other kinds of absence. <b>Seen but too thin:</b> ${DATA.nearMissTotal} locations `
    + `appear in the sample and clear neither threshold \u2014 ${near} come closest. The `
    + `employer count is usually what stops them, and one employer hiring is an office, not `
    + `a centre. <b>Not priceable at all:</b> ${un} \u2014 ILOSTAT publishes no earnings by `
    + `occupation for either, so there is no cost figure on the basis every market here uses, `
    + `and two pillars without the decisive one would be worse than no row. Egypt was dropped `
    + `for a third reason: its professionals report 1.06\u00d7 clerical pay against 1.3\u2013`
    + `2.9\u00d7 everywhere else, which is a broken series rather than a cheap country.`;
}

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
    `Whether GBS work is actually <b>advertised</b> in Manila, Kuala Lumpur, Lisbon, `
      + `Bucharest, Prague or Budapest. They are priced above on the five pillars that reach `
      + `them; the two built from postings do not.`,
    `<b>What employer charges and attrition actually cost, per market.</b> Exhibit 3 loads `
      + `the wage with both, but at a rate you set — no free source gives comparable `
      + `employer-charge schedules or attrition rates for all ${rows.length} cities, so the `
      + `factor is uniform where reality is not.`,
    `<b>Incentives, property and transition cost.</b> None are in this study. Exhibit 3 loads `
      + `the wage line and stops there, so it remains one line of a run-cost rather than a `
      + `business case.`,
    `Whether a city suits <b>your</b> mandate. Nothing here is a recommendation.`,
  ].map((x) => `<li>${x}</li>`).join("");
}

/* What was scraped, when, and whether there is more than one point in time.
   Every figure here is read out of the fetch's own record rather than written
   down, so a refetch moves the page instead of leaving it confidently wrong. */
function renderProvenance() {
  const p = DATA.provenance.postings;
  const c = DATA.provenance.contaminant;
  const el = $("#provenance");
  if (!p) {
    el.innerHTML =
      `<b>No postings sample has been fetched.</b> Capability and employer depth `
      + `cannot be computed without one, so no city is ranked.`;
    return;
  }
  const terms = p.terms.map((t) => `\u201c${t}\u201d`).join(", ");
  const local = Object.entries(p.localTerms || {})
    .map(([m, ts]) => `${DATA.marketNames[m] || m} (${ts.length})`).join(", ");
  el.innerHTML =
    `<b>${p.isSnapshot ? "One snapshot" : `${p.count} snapshots`}, ${p.dateLabel}.</b> `
    + `${p.postingsFetched.toLocaleString("en-US")} postings from ${p.board} across `
    + `${p.marketCount} markets, ${p.termCount} search terms paged to ${p.maxPages}: `
    + `${terms}`
    + (local ? `, plus local-language terms in ${local}` : ``)
    + `. The terms are the sample: this is what those phrases returned, not GBS `
    + `hiring in the abstract. `
    + (p.isSnapshot
        ? `A single point in time — a city hiring quietly during the fetch is `
          + `under-represented, and nothing here can show a trend. `
        : ``)
    + (c
        ? `Classification error is modelled against a broader finance sample of `
          + `${c.postings.toLocaleString("en-US")} postings fetched ${c.dateLabel} `
          + `(${c.repo}).`
        : ``);
}

/* ---- what would change this ----
   The page ends on the checks a phase-2 validation would actually run, framed
   as what this analysis cannot settle: each one replaces an input no public
   source supplies. Written from the run on screen — the band, the operators
   and the assumption rates are the current ones, so the close stays true when
   the reader moves something. */
function renderNext(ranked, band) {
  const top = ranked.filter((r) => band.get(r.row.id) === 1);
  const names = top.map((r) => r.row.name);
  const last = names.length > 1 ? names.pop() : null;
  const bandLabel = last ? `${names.join(", ")} and ${last}` : names[0];
  const national = top.filter((r) => !r.row.costResolved).length;
  const minN = Math.min(...top.map((r) => r.row.postings ?? Infinity));
  const ops = [...new Set(top.flatMap((r) => r.row.operators || []))];
  const pct = (x) => `${Math.round(x * 100)}%`;

  const wage = national > 0
    ? `${national} of the ${top.length} carry ILOSTAT\u2019s national wage, and the `
      + `${pct(state.loading)} employer loading is a uniform assumption where real `
      + `schedules differ by country.`
    : `Every city here carries a measured city wage, but the ${pct(state.loading)} `
      + `employer loading is a uniform assumption where real schedules differ by country.`;
  // A count, not a shortlist of names: the per-city lists lead with whoever
  // posted most in a small sample, and opening the close of the page with an
  // employer nobody recognises reads as noise. The table below already names
  // every one of them, per city.
  const attrition = ops.length
    ? `The ${ops.length} employers named in this band\u2019s postings already run `
      + `centres there<span class="screen-only"> \u2014 the table below lists them `
      + `per city</span>. Their attrition, time-to-fill and ramp curves would replace `
      + `the ${pct(state.attrition)} backfill assumption`
    : `No operator is named in this band\u2019s postings, so provider benchmarks would `
      + `have to replace the ${pct(state.attrition)} backfill assumption`;

  const ovrTail = overrideCount()
    ? `today ${overrideCount()} client figure${overrideCount() === 1 ? " has" : "s have"} `
      + `been entered under \u201cYour figures\u201d`
    : `until one is entered under \u201cYour figures\u201d, it is a slider`;
  $("#next").innerHTML = [
    `<b>Live wage and employer-charge quotes for ${bandLabel}.</b> ${wage} `
      + `A recruiter\u2019s per-role quote and a payroll provider\u2019s charge schedule `
      + `replace both \u2014 the two figures on Exhibit 3 no public source supplies.`,
    `<b>Site visits against the advertised capability.</b> The capability pillar is job `
      + `postings \u2014 as few as ${minN} behind a city in this band. Postings say who is `
      + `hiring; they cannot say whether the advertised work is the work done, or whether `
      + `a centre could hire at programme rate. A provider RFI and days on the ground `
      + `settle what postings cannot.`,
    `<b>Attrition and ramp data from the operators already there.</b> ${attrition}, `
      + `which is the one Exhibit 3 input that can reorder cities \u2014 and ${ovrTail}.`,
  ].map((x) => `<li>${x}</li>`).join("");

  $("#next-note").innerHTML =
    `Checks, not refinements: each replaces an input this analysis cannot source from `
    + `public data, which is why they close the page rather than extend it. A phase 2 `
    + `that skips them is trusting a slider.`;
}

function renderSource(rows) {
  const resolved = rows.filter((r) => r.costResolved).length;
  const thin = rows.filter((r) => r.postings != null && r.postings < DATA.evidenceFloor).length;
  $("#exhibit-source").innerHTML =
    `Source: ILOSTAT earnings and employment by occupation; World Bank Worldwide Governance ` +
    `Indicators; Eurostat regional accounts; ${rows.length} cities from a GBS/GCC job-posting ` +
    `sample, ${DATA.asOf}. ` +
    `Note: ${resolved} of ${rows.length} cities carry city-level cost, the remainder their ` +
    `country's; ${thin} rest on fewer than ${DATA.evidenceFloor} postings and cannot be called robust.` +
    (overrideCount()
      ? ` ${overrideCount()} figure${overrideCount() === 1 ? " is" : "s are"} client-supplied — `
        + `sources under Exhibit 3.`
      : ``);
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

  // Percentages are typed as percentages and held as fractions: a reader thinks
  // in "25", and every formula downstream wants 0.25.
  const assume = (id, key, {pct = true, min = 0, max = 100} = {}) => {
    const el = $(`#${id}`);
    el.value = pct ? Math.round(state[key] * 100) : state[key];
    el.addEventListener("input", (e) => {
      const n = parseFloat(e.target.value);
      if (!Number.isFinite(n) || n < min || n > max) return;
      state[key] = pct ? n / 100 : n;
      render();
    });
  };
  assume("loading", "loading", {max: DATA.loadingMax * 100});
  assume("attrition", "attrition", {max: DATA.attritionMax * 100});
  assume("horizon", "horizon", {pct: false, max: DATA.horizonMax});
  $("#assume-note").innerHTML =
    `Employer charges and backfill are <b>assumptions you set</b>, not measured here. `
    + `Years forward carries each market at its own measured wage drift.`;

  writeArchetypeCopy();
  $("#sources").innerHTML = DATA.sources.map((x) => `
    <div>
      <dt>${x.pillar}</dt>
      <dd>${x.name}<br><span class="vint">${x.detail} · ${x.vintage}</span></dd>
    </div>`).join("");
  const snap = DATA.provenance.postings;
  $("#asof").textContent =
    `${DATA.pillars.length} pillars · `
    + (snap
        ? `${snap.isSnapshot ? "one snapshot" : `${snap.count} snapshots`}, ${snap.dateLabel}`
        : `sample not fetched`);
  renderProvenance();
  $("#floor-n").textContent = DATA.evidenceFloor;
  $("#sep-n").textContent = Math.round(DATA.separableAt * 100) + "%";

  $("#copy").addEventListener("click", copyTable);
  $("#one-pager").addEventListener("click", () => window.print());
  $("#copy-link").addEventListener("click", copyLink);

  syncSliders();
}

/* ---- scenarios: a name for the view, and a link that reproduces it ----
   The state is the scenario; this only files it. Names live in this browser's
   storage — the tool has no server and gains none here — while the URL carries
   the full view to anyone, storage or not. */
const SCENARIO_STORE = "gbs-location-scenarios-v1";

function scenarioStore() {
  try {
    const raw = localStorage.getItem(SCENARIO_STORE);
    return raw ? JSON.parse(raw) : {};
  } catch { return null; }  // storage blocked: saving is off, links still work
}

function writeScenarioStore(map) {
  try { localStorage.setItem(SCENARIO_STORE, JSON.stringify(map)); return true; }
  catch { return false; }
}

const escHtml = (x) => String(x).replace(/[&<>"]/g,
  (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));

/* The address bar always holds the current view; at the defaults it holds
   nothing, so an untouched page keeps a clean URL. replaceState, not pushState:
   every slider drag as a history entry would bury the back button. */
function syncUrl() {
  const enc = isDefaultScenario(state) ? "" : encodeScenario(state);
  history.replaceState(null, "", location.pathname + location.search + (enc ? "#" + enc : ""));
}

/* A view that drifted from its saved name says so: a one-pager stamped
   "Steering" that no longer shows the Steering stand is the quiet lie this
   page keeps refusing elsewhere. */
function updateScenarioTag() {
  const el = $("#scenario-tag");
  if (!state.scenario) { el.textContent = ""; return; }
  const map = scenarioStore();
  const saved = map && map[state.scenario];
  const edited = saved && saved.s !== encodeScenario(state, {includeName: false});
  el.textContent = ` · scenario “${state.scenario}”${edited ? " (edited)" : ""}`;
}

function refreshScenarioList() {
  const map = scenarioStore() || {};
  const names = Object.keys(map).sort(
    (a, b) => (map[b].at || "").localeCompare(map[a].at || ""));
  $("#scenario-list").innerHTML =
    `<option value="">${names.length
      ? "— load a saved view —"
      : "— nothing saved on this device —"}</option>`
    + names.map((n) => `<option value="${escHtml(n)}">${escHtml(n)}</option>`).join("");
}

function reflectControls() {
  $("#archetype").querySelectorAll("button").forEach((x) =>
    x.setAttribute("aria-pressed", String(x.dataset.k === state.archetype)));
  syncSliders();
  $("#hq").value = state.hq;
  $("#baseline").value = state.baseline;
  $("#fte").value = state.fte;
  $("#loading").value = Math.round(state.loading * 100);
  $("#attrition").value = Math.round(state.attrition * 100);
  $("#horizon").value = state.horizon;
}

function applyScenario(dec, name) {
  const base = defaultScenarioState();
  state.archetype = dec.archetype || base.archetype;
  state.weights = dec.weights || { ...DATA.archetypes[state.archetype].weights };
  state.hq = dec.hq ?? base.hq;
  state.baseline = dec.baseline ?? base.baseline;
  state.fte = dec.fte ?? base.fte;
  state.loading = dec.loading ?? base.loading;
  state.attrition = dec.attrition ?? base.attrition;
  state.horizon = dec.horizon ?? base.horizon;
  state.overrides = dec.overrides ?? {};
  state.scenario = name ?? dec.name ?? null;
  reflectControls();
  refreshOverrideList();
  render();
}

function buildScenarioControls() {
  const sel = $("#scenario-list");
  const note = $("#scenario-note");
  if (scenarioStore() === null) {
    sel.style.display = "none";
    sel.closest(".card").querySelector(".scn-row").style.display = "none";
    note.textContent =
      "This browser blocks site storage, so views cannot be saved here. "
      + "“Copy link” under the exhibits still carries the current view.";
    return;
  }
  refreshScenarioList();
  note.textContent = "This browser only. Use “Copy link” to share a view.";

  sel.addEventListener("change", () => {
    const name = sel.value;
    if (!name) return;
    const rec = (scenarioStore() || {})[name];
    if (!rec) { refreshScenarioList(); return; }
    applyScenario(decodeScenario(rec.s), name);
    $("#scenario-name").value = name;
    sel.value = name;
  });

  $("#scenario-save").addEventListener("click", () => {
    const name = $("#scenario-name").value.trim().slice(0, 60);
    if (!name) { $("#scenario-name").focus(); return; }
    const map = scenarioStore() || {};
    map[name] = {
      s: encodeScenario(state, {includeName: false}),
      at: new Date().toISOString(),
    };
    if (!writeScenarioStore(map)) return;
    state.scenario = name;
    refreshScenarioList();
    sel.value = name;
    render();
  });

  $("#scenario-delete").addEventListener("click", () => {
    const name = sel.value;
    if (!name) return;
    const map = scenarioStore() || {};
    delete map[name];
    writeScenarioStore(map);
    if (state.scenario === name) state.scenario = null;
    $("#scenario-name").value = "";
    refreshScenarioList();
    render();
  });
}

/* ---- client figures: the middle tier ----
   A reader with a real quote should not have to argue with a slider. Each
   figure carries a mandatory source and date, is marked on the exhibit and the
   one-pager, and rides in the link and in saved scenarios — so a shared view
   carries its evidence with it. */
const OVR_FIELDS = {
  w: {label: "wage", fmt: (v) => `$${v.toLocaleString("en-US")}/mo`},
  l: {label: "loading", fmt: (v) => `${v}%`},
  t: {label: "attrition", fmt: (v) => `${v}%`},
};

function overrideCount() {
  return Object.values(state.overrides)
    .reduce((n, m) => n + Object.keys(m).length, 0);
}

function cityName(id) {
  const r = DATA.views.city[state.archetype].find((x) => x.id === id);
  return r ? r.name : id;
}

function overrideTitle(id) {
  const m = state.overrides[id] || {};
  return Object.keys(OVR_FIELDS).filter((f) => m[f]).map((f) =>
    `${OVR_FIELDS[f].label} ${OVR_FIELDS[f].fmt(m[f].v)} — ${m[f].source}, ${m[f].date}`
  ).join("; ");
}

/* The sources print. Tooltips do not survive paper, and a client figure whose
   source is only a hover away from missing would be a quiet downgrade of the
   one thing that makes this tier different from an assumption. */
function renderOverrideNote() {
  const lines = [];
  for (const id of Object.keys(state.overrides).sort()) {
    const m = state.overrides[id];
    for (const f of Object.keys(OVR_FIELDS)) {
      if (!m[f]) continue;
      lines.push(`${escHtml(cityName(id))} ${OVR_FIELDS[f].label} `
        + `${OVR_FIELDS[f].fmt(m[f].v)} (${escHtml(m[f].source)}, ${m[f].date})`);
    }
  }
  $("#override-note").innerHTML = lines.length
    ? `<b>Client figures:</b> ${lines.join("; ")}. Each replaces its public `
      + `counterpart for that city only; everything unmarked is public data or `
      + `a stated assumption.`
    : "";
  $("#ovr-state").textContent = overrideCount()
    ? `${overrideCount()} figure${overrideCount() === 1 ? "" : "s"}`
    : "none yet";
}

function refreshOverrideList() {
  const host = $("#ovr-list");
  const rows = [];
  for (const id of Object.keys(state.overrides).sort()) {
    const m = state.overrides[id];
    for (const f of Object.keys(OVR_FIELDS)) {
      if (!m[f]) continue;
      rows.push(`<li><b>${escHtml(cityName(id))}</b> ${OVR_FIELDS[f].label} `
        + `${OVR_FIELDS[f].fmt(m[f].v)}<span class="src"> — ${escHtml(m[f].source)}, `
        + `${m[f].date}</span><button type="button" data-id="${escHtml(id)}" `
        + `data-f="${f}">remove</button></li>`);
    }
  }
  host.innerHTML = rows.join("");
}

function buildOverrideControls() {
  const sel = $("#ovr-city");
  sel.innerHTML = DATA.views.city[state.archetype]
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((r) => `<option value="${escHtml(r.id)}">${escHtml(r.name)}</option>`)
    .join("");
  $("#ovr-date").value = new Date().toISOString().slice(0, 10);
  $("#ovr-note").textContent =
    "At least one figure and a source. A quoted wage enters the ranking as "
    + "given — a quote is current and role-specific, so it is not aged and "
    + "not resampled.";
  refreshOverrideList();

  $("#ovr-add").addEventListener("click", () => {
    const source = $("#ovr-source").value.replace(/~/g, " ").trim().slice(0, 80);
    if (!source) { $("#ovr-source").focus(); return; }
    const date = $("#ovr-date").value;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) { $("#ovr-date").focus(); return; }
    const id = sel.value;
    const entries = [];
    const wage = parseInt($("#ovr-wage").value, 10);
    if (Number.isInteger(wage) && wage >= 1) entries.push(["w", Math.min(wage, 99999)]);
    const l = parseInt($("#ovr-loading").value, 10);
    if (Number.isInteger(l) && l >= 0)
      entries.push(["l", Math.min(l, Math.round(DATA.loadingMax * 100))]);
    const t = parseInt($("#ovr-attrition").value, 10);
    if (Number.isInteger(t) && t >= 0)
      entries.push(["t", Math.min(t, Math.round(DATA.attritionMax * 100))]);
    if (!entries.length) { $("#ovr-wage").focus(); return; }
    if (overrideCount() + entries.length > 50) return;
    const m = state.overrides[id] = state.overrides[id] || {};
    for (const [f, v] of entries) m[f] = {v, source, date};
    for (const el of ["#ovr-wage", "#ovr-loading", "#ovr-attrition"]) $(el).value = "";
    refreshOverrideList();
    render();
  });

  $("#ovr-list").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    const m = state.overrides[b.dataset.id];
    if (m) {
      delete m[b.dataset.f];
      if (!Object.keys(m).length) delete state.overrides[b.dataset.id];
    }
    refreshOverrideList();
    render();
  });
}

async function copyLink() {
  syncUrl();
  const url = location.href;
  const status = $("#link-status");
  try {
    await navigator.clipboard.writeText(url);
    status.textContent = "Link copied — it reproduces exactly this view.";
  } catch {
    const area = document.createElement("textarea");
    area.value = url;
    document.body.appendChild(area);
    area.select();
    const ok = document.execCommand("copy");
    area.remove();
    status.textContent = ok
      ? "Link copied — it reproduces exactly this view."
      : url;
  }
  setTimeout(() => (status.textContent = ""), 6000);
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
  // The strip answers "which pillar"; the bar answers "which city, how far".
  // Both then point at the click, because a hover cannot hold a ledger.
  const seg = e.target.closest(".seg-fill");
  const bar = seg ? null : e.target.closest(".bar");
  if (!seg && !bar) { tip.classList.remove("on"); return; }
  if (seg) {
    const p = seg.dataset.p;
    tip.innerHTML = `${escHtml(seg.dataset.name)}<br>${DATA.pillarLabels[p]} · `
      + `${parseFloat(seg.style.width).toFixed(0)}% of score`
      + `<span class="tip-cta">Click the row for every figure</span>`;
  } else {
    const open = state.open === (bar.closest(".row") || {}).dataset?.id;
    tip.innerHTML = `${escHtml(bar.dataset.name)}<br>Score ${bar.dataset.score} · `
      + `band ${bar.dataset.band}`
      + `<span class="tip-cta">${open ? "Click to close" : "Click for every figure"}</span>`;
  }
  tip.style.left = Math.min(e.clientX + 14, innerWidth - 270) + "px";
  tip.style.top = (e.clientY + 16) + "px";
  tip.classList.add("on");
});

/* ---- folds in print ------------------------------------------------------
   The printed brief carries every source, and a fold is a screen affordance
   only. CSS cannot be trusted to reopen a closed <details>: the content of one
   is hidden by the element's own rendering, not by a display rule a stylesheet
   can outrank. So the attribute is set for the duration of the print and put
   back afterwards, which is the only method that holds in every engine. */
let foldsForcedOpen = [];
window.addEventListener("beforeprint", () => {
  foldsForcedOpen = [...document.querySelectorAll(".fold:not([open])")];
  foldsForcedOpen.forEach((d) => { d.open = true; });
});
window.addEventListener("afterprint", () => {
  foldsForcedOpen.forEach((d) => { d.open = false; });
  foldsForcedOpen = [];
});

/* ---- opening a row --------------------------------------------------------
   Delegated, because the rows are rebuilt on every weight change. */
function toggleRow(id) {
  state.open = state.open === id ? null : id;
  render();
  if (state.open) {
    const el = document.querySelector(`.row[data-id="${state.open}"]`);
    if (el) el.focus({ preventScroll: true });
  }
}
$("#rows").addEventListener("click", (e) => {
  if (e.target.closest(".detail-close")) {
    const d = e.target.closest(".detail");
    state.open = null;
    render();
    // Focus goes back to the row that opened it, not to the top of the page.
    const el = d && document.querySelector(`.row[data-id="${d.id.slice(2)}"]`);
    if (el) el.focus({ preventScroll: true });
    return;
  }
  // A click inside the opened panel is a reader selecting a figure, not a
  // request to close it.
  if (e.target.closest(".detail")) return;
  const row = e.target.closest(".row");
  if (row) toggleRow(row.dataset.id);
});
document.addEventListener("click", (e) => {
  if (!e.target.closest("#belief-edit")) return;
  const d = $("#adjust");
  d.open = true;
  d.scrollIntoView({ block: "nearest" });
  const first = d.querySelector('input[type="range"]');
  if (first) first.focus({ preventScroll: true });
});
$("#rows").addEventListener("keydown", (e) => {
  const row = e.target.closest(".row");
  if (!row) return;
  if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggleRow(row.dataset.id); }
});
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape" || !state.open) return;
  const id = state.open;
  state.open = null;
  render();
  const el = document.querySelector(`.row[data-id="${id}"]`);
  if (el) el.focus({ preventScroll: true });
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
/* A shared link is the whole view. Decoded before anything renders, field by
   field, so an invalid fragment costs that field its default and nothing else. */
{
  const dec = decodeScenario(location.hash.replace(/^#/, ""));
  if (dec.archetype) {
    state.archetype = dec.archetype;
    state.weights = { ...DATA.archetypes[dec.archetype].weights };
  }
  if (dec.weights) state.weights = dec.weights;
  if (dec.hq !== undefined) state.hq = dec.hq;
  if (dec.baseline !== undefined) state.baseline = dec.baseline;
  if (dec.fte !== undefined) state.fte = dec.fte;
  if (dec.loading !== undefined) state.loading = dec.loading;
  if (dec.attrition !== undefined) state.attrition = dec.attrition;
  if (dec.horizon !== undefined) state.horizon = dec.horizon;
  if (dec.overrides) state.overrides = dec.overrides;
  state.scenario = dec.name || null;
}

buildControls();
buildScenarioControls();
buildOverrideControls();
render();

/* A pasted link must work on a page that is already open: the browser treats a
   fragment-only change as navigation without a reload, so it has to be caught
   here. syncUrl uses replaceState, which fires no hashchange — no feedback
   loop. An emptied hash reads as "back to the defaults", which is what
   deleting the fragment means. */
window.addEventListener("hashchange", (e) => {
  // The event's own URL, not location.hash: a render between the change and
  // this handler replaceStates the old fragment back, and reading location
  // would apply the state the paste was meant to replace.
  const frag = (e.newURL || "").split("#")[1] || "";
  const dec = decodeScenario(frag);
  applyScenario(dec, dec.name ?? null);
});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
