"""The page as it reads before any JavaScript runs.

Every figure on the exhibit is written by script, which left the shipped
document as a set of empty tags and half-finished sentences — "a top-three
place in 90% of 2,000 reweightings *and* at least ___ postings behind it". That
is what a crawler indexes, what a reader-mode pass extracts, and what anybody
looking at the source sees. A study whose whole argument is that a number
should be traceable cannot ship a document that says nothing until it is
executed.

So the default scenario is rendered here, in Python, and baked into the
document at build time. On load the script overwrites it with the same content,
because it is the same scenario: the declared archetype, the declared weights,
the declared headquarters and the declared cost assumptions.

This is the fourth place a piece of the page exists twice — after scoring,
correlation and loaded cost — and it is bound the same way: `tests/test_fallback.py`
runs the page's own JavaScript under a DOM shim and requires the two renderings
to name the same cities, the same bands and the same figures. Where they cannot
agree exactly they are not asserted to: the live stability meter runs 2,000
draws in the browser against this module's 10,000 in Python, so the percentages
differ in the last point or two by construction, and pretending otherwise would
make the test lie rather than the page.

Two regions are deliberately not reproduced as drawn. The composition strip
under each bar and the timezone scatter are positioned graphics; without script
they become a list of pillar shares and a list of shared hours, which is what
they say. Everything else is the page.
"""

from __future__ import annotations

import html as _html

from src.score import PILLARS, normalise, score


def esc(x) -> str:
    return _html.escape(str(x), quote=True)


def money(usd: float) -> str:
    """Mirrors the page's own formatter, including its minus sign."""
    a = abs(usd)
    sign = "−" if usd < 0 else ""
    if a >= 1e6:
        return f"{sign}${a / 1e6:.{0 if a >= 1e7 else 1}f}m"
    if a >= 1e3:
        return f"{sign}${a / 1e3:.{0 if a >= 1e4 else 1}f}k"
    return f"{sign}${round(a):,.0f}"


def num(x, digits: int = 0) -> str:
    return f"{x:,.{digits}f}"


def flag(data: dict, market: str) -> str:
    d = data["flags"].get(market)
    if not d:
        return ""
    title = esc(data["flagTitles"].get(market, market))
    return (
        f'<svg class="flag" viewBox="0 0 21 14" role="img" '
        f'aria-label="{title}">{d}</svg>'
    )


class Scenario:
    """The declared starting position, scored.

    Everything the fallback prints comes off this object, so there is one place
    where "the default scenario" is defined rather than one per region.
    """

    def __init__(self, data: dict):
        self.data = data
        self.archetype = next(iter(data["archetypes"]))
        self.arch = data["archetypes"][self.archetype]
        self.weights = dict(self.arch["weights"])
        self.rows = data["views"]["city"][self.archetype]
        self.by_id = {r["id"]: r for r in self.rows}

        raw = {r["id"]: {p: r[p] for p in PILLARS} for r in self.rows}
        self.scaled = normalise(raw)
        self.scores = score(self.scaled, self.weights)

        ref = data["defaults"][self.archetype]
        self.freq = ref["frequency"]
        self.band = ref["band"]
        self.verdicts = ref["verdict"]

        # Band first, then by how often a city survives reweighting — the order
        # the page ranks in, because the band already says the score order is
        # not established.
        self.order = sorted(
            self.rows,
            key=lambda r: (self.band.get(r["id"], 99), -self.freq.get(r["id"], 0.0)),
        )
        self.top = [r for r in self.order if self.band.get(r["id"]) == 1]
        self.bands = len(set(self.band.values()))

    def parts(self, row: dict) -> dict[str, float]:
        total = sum(self.weights.values()) or 1.0
        return {
            p: self.weights[p] * self.scaled[row["id"]][p] / total for p in PILLARS
        }

    def market(self, row: dict) -> str:
        return self.data["marketNames"].get(row["parent"], row["parent"] or "")

    def baseline(self) -> dict:
        keyed = {b["key"]: b for b in self.data["baselines"]}
        return keyed.get(self.data["baselineDefault"], self.data["baselines"][0])


# --- regions --------------------------------------------------------------
# One function per slot the script fills. Each returns the markup the script
# would have produced for this scenario.


def _headline(s: Scenario) -> str:
    if len(s.top) > 1:
        return f"{len(s.top)} cities finish level at the top."
    robust = [r for r in s.order if s.verdicts.get(r["id"]) == "robust"]
    if len(robust) == 1:
        return f"Only {esc(robust[0]['name'])} survives a change of mind."
    if robust:
        return (
            ", ".join(esc(r["name"]) for r in robust[:3])
            + " survive a change of mind."
        )
    return f"No city holds up as a {esc(s.arch['short'])}."


def _takeaway(s: Scenario) -> str:
    label = f"At the {esc(s.arch['short'])}’s starting weights"
    if len(s.top) > 1:
        names = [esc(r["name"]) for r in s.top]
        last = names.pop()
        return (
            f"{label}, <strong>{', '.join(names)} and {last}</strong> finish level "
            f"at the top: the draws cannot separate them, so the order within that "
            f"group is not a finding."
        )
    lead = s.order[0]
    pct = f"{s.freq.get(lead['id'], 0.0) * 100:.0f}"
    return (
        f"{label}, <strong>{esc(lead['name'])}</strong> ({esc(s.market(lead))}) leads "
        f"outright, holding a top-three place in {pct}% of 2,000 nearby weightings."
    )


def _belief(s: Scenario) -> str:
    entries = sorted(s.weights.items(), key=lambda kv: -kv[1])
    (top_p, top_w), (low_p, low_w) = entries[0], entries[-1]
    even = 1 / len(PILLARS)
    labels = s.data["pillarLabels"]
    lead = (
        f"You are buying <b>{esc(labels[top_p].lower())}</b> above everything else"
        if top_w > even * 1.6
        else "You are spreading weight fairly evenly, with "
             f"<b>{esc(labels[top_p].lower())}</b> just ahead"
    )
    drop = (
        f", and you have effectively stopped pricing <b>{esc(labels[low_p].lower())}</b>."
        if low_w < even * 0.4
        else f", with <b>{esc(labels[low_p].lower())}</b> mattering least."
    )
    return lead + drop


def _rows(s: Scenario) -> str:
    best = max(s.scores.values()) or 1.0
    out = []
    seen_bands: set[int] = set()
    for r in s.order:
        b = s.band.get(r["id"], 1)
        opens = b not in seen_bands
        seen_bands.add(b)
        f = s.freq.get(r["id"], 0.0)
        v = s.verdicts.get(r["id"], "never")
        width = (s.scores[r["id"]] / best) * 100
        # `lead`, not `in-top`: the row carries in-top, the bar carries lead,
        # and giving the bar the row's class left it correctly sized and
        # invisible, because only .bar.lead and .bar.rest paint.
        tone = "lead" if b == 1 else "rest"
        n = r["postings"]
        thin = n is not None and n < s.data["evidenceFloor"]

        cost_note = (
            f"{r['regionIndex']:.2f}× national cost"
            if r["costResolved"] else "national cost"
        )
        langs = (
            " · " + ", ".join(esc(x) for x in (r["languages"] or [])[:2])
            if r["languages"] else ""
        )
        mix = (
            f"{round(r['mixTransactional'] * 100)}% processing"
            if r["mixTransactional"] is not None else ""
        )
        sub = " · ".join(
            x for x in (esc(s.market(r)), mix,
                        f"{r['employers']} employers" if r["employers"] else "",
                        cost_note) if x
        ) + langs

        # The composition strip is drawn too: the exhibit's own caption points at
        # it ("the strip beneath it is the composition") and the legend names
        # its colours, so leaving it out would leave both referring to nothing.
        parts = s.parts(r)
        total = s.scores[r["id"]] or 1.0
        segs = "".join(
            f'<i class="seg-fill" style="width:{parts[p] / total * 100:.2f}%;'
            f'background:{s.data["colors"][p]}" data-p="{p}" '
            f'data-name="{esc(r["name"])}"></i>'
            for p in PILLARS
        )
        composition = ", ".join(
            f"{esc(s.data['pillarLabels'][p])} {v2 * 100:.0f}%"
            for p, v2 in sorted(parts.items(), key=lambda kv: -kv[1])
            if v2 > 0.005
        )
        out.append(
            f'<div class="row{" in-top" if b == 1 else ""}'
            f'{" band-start" if opens else ""}" data-id="{esc(r["id"])}">'
            f'<div class="rank">{b if opens else ""}</div>'
            f'<div class="who"><span class="nm">{flag(s.data, r["parent"])}'
            f'{esc(r["name"])}</span><span class="sub">{sub}</span></div>'
            f'<div class="bar-cell"><div class="bar-wrap" title="{esc(composition)}">'
            f'<div class="bar {tone}" style="width:{width:.2f}%"></div>'
            f'<div class="mix" style="width:{width:.2f}%">{segs}</div></div></div>'
            f'<div class="evidence" title="{esc(r["name"])}: {n} postings the '
            f'work-family classifier could decide, out of {r["postingsSeen"]} that '
            f'qualified the city.">'
            f'<span class="{"thin" if thin else ""}">{"—" if n is None else n}</span>'
            f'</div>'
            f'<div class="stab"><span class="pct">{f * 100:.0f}%</span>'
            f'<span class="tag {v}">{v}</span></div></div>'
        )
    return "".join(out)


def _legend(s: Scenario) -> str:
    return '<span class="legend-lede">Composition:</span>' + "".join(
        f'<span><i class="swatch" style="background:{s.data["colors"][p]}"></i>'
        f'{esc(s.data["pillarLabels"][p])}</span>' for p in PILLARS
    )


def _strip(s: Scenario) -> str:
    """Exhibit 2 without positioning: the shared hours, per market, as a list."""
    seen: dict[str, dict] = {}
    for r in s.order:
        key = r["parent"]
        m = seen.setdefault(key, {
            "name": s.market(r), "offset": s.data["offsets"].get(key, 0),
            "hours": r["timezone"], "cities": [], "lead": False,
        })
        m["cities"].append(r["name"])
        if s.band.get(r["id"]) == 1:
            m["lead"] = True
    markets = sorted(seen.values(), key=lambda m: m["offset"])
    return '<ul class="tz-static">' + "".join(
        f'<li><b>{esc(m["name"])}</b> (UTC{"+" if m["offset"] >= 0 else "−"}'
        f'{abs(m["offset"]):g}) — {m["hours"]:g}h shared · '
        f'{esc(", ".join(m["cities"]))}</li>' for m in markets
    ) + "</ul>"


def _case(s: Scenario) -> str:
    from src.loaded import Assumptions, gap

    base = s.baseline()
    a = Assumptions()
    fte = s.data["fteDefault"]
    items = []
    for r in s.order:
        if r["cost"] is None:
            continue
        drift = r["drift"] if r["driftMeasured"] else None
        g = gap(base["monthly"], base["drift"], r["cost"], drift, a, fte=fte)
        items.append((r, g))
    items.sort(key=lambda t: -(t[1]["loadedTotal"] or t[1]["baseTotal"]))

    reach = [v for _, g in items for v in (g["baseTotal"], g["loadedTotal"]) if v is not None]
    span = max((abs(v) for v in reach), default=1.0) or 1.0
    worst = min(reach + [0.0])
    full = span + abs(worst)
    zero = (abs(worst) / full) * 100

    def bar(v: float, cls: str) -> str:
        w = (abs(v) / full) * 100
        if v < 0:
            return (f'<div class="case-bar over {cls}" style="right:{100 - zero:.2f}%;'
                    f'width:{w:.2f}%"></div>')
        return f'<div class="case-bar {cls}" style="left:{zero:.2f}%;width:{w:.2f}%"></div>'

    out = []
    for r, g in items:
        bars = (bar(g["loadedTotal"], "loaded") if g["loadedTotal"] is not None else "")
        bars += bar(g["baseTotal"], "base")
        national = "" if r["costResolved"] else '<span class="natl">national</span>'
        loaded = (
            '<span class="na">not projectable</span>' if g["loadedTotal"] is None
            else f'{money(g["loadedTotal"])}'
                 f'<span class="per">{money(g["loadedPerRole"])} per role</span>'
        )
        out.append(
            f'<div class="case-row"><span class="cn">{flag(s.data, r["parent"])}'
            f'{esc(r["name"])}{national}</span>'
            f'<div class="case-track"><div class="case-zero" style="left:{zero:.2f}%">'
            f'</div>{bars}</div>'
            f'<span class="case-val base-val">{money(g["baseTotal"])}</span>'
            f'<span class="case-val">{loaded}</span></div>'
        )
    return "".join(out)


def _settles(s: Scenario) -> tuple[str, str]:
    postings = sum(r["postings"] or 0 for r in s.rows)
    named = sum(1 for r in s.rows if r["operators"])
    decisive = s.data["pillarLabels"][
        max(s.weights.items(), key=lambda kv: kv[1])[0]
    ].lower()
    yes = [
        f'Which cities genuinely advertise this work: <b>{len(s.rows)}</b> clear the '
        f'evidence threshold, on <b>{num(postings)}</b> GBS and GCC postings.',
        (f'That <b>{len(s.top)} cities finish level</b> at the top. The draws cannot '
         f'separate them, so their order is not a finding.') if len(s.top) > 1 else
        (f'That <b>{esc(s.order[0]["name"])}</b> leads alone, and the draws keep it there.'),
        f'That the answer turns on <b>{esc(decisive)}</b> at your weighting, and how far '
        f'it moves when you price something else.',
        f'Who already operates in <b>{named}</b> of them, by name.' if named else "",
        f'How far the evidence separates them: <b>{s.bands} bands</b>, not '
        f'{len(s.rows)} ranks.',
    ]
    no = [
        'Whether GBS work is actually <b>advertised</b> in Manila, Kuala Lumpur, Lisbon, '
        'Bucharest, Prague or Budapest. They are priced above on the five pillars that '
        'reach them; the two built from postings do not.',
        f'<b>What employer charges and attrition actually cost, per market.</b> Exhibit 3 '
        f'loads the wage with both, but at a rate you set — no free source gives '
        f'comparable employer-charge schedules or attrition rates for all {len(s.rows)} '
        f'cities, so the factor is uniform where reality is not.',
        '<b>Incentives, property and transition cost.</b> None are in this study. '
        'Exhibit 3 loads the wage line and stops there, so it remains one line of a '
        'run-cost rather than a business case.',
        'Whether a city suits <b>your</b> mandate. Nothing here is a recommendation.',
    ]
    li = lambda xs: "".join(f"<li>{x}</li>" for x in xs if x)  # noqa: E731
    return li(yes), li(no)


def _table(s: Scenario) -> str:
    labels = s.data["pillarLabels"]
    head = (["City"] + [labels[p] for p in PILLARS]
            + ["Score", "Top-3", "Processing", "Judgment", "Cost USD", "Cost PPP",
               "Languages", "Operators already there"])
    caption = (
        "Normalised pillar scores (0–1, higher is better) under the current weights. "
        "Processing and judgment are the work mix the city advertises, shrunk toward "
        "its country's where the sample is thin. Cost is monthly, per head: USD is what "
        "you pay, PPP what it buys locally. "
        "Languages are those the city's postings ask for. Operators are the employers "
        "advertising this work there, with staffing firms removed and one company's "
        "several spellings merged. Both reported, neither scored."
    )
    body = []
    for r in s.order:
        mix = r["mixTransactional"]
        body.append(
            f'<tr><td>{esc(r["name"])}</td>'
            + "".join(f'<td>{s.scaled[r["id"]][p]:.2f}</td>' for p in PILLARS)
            + f'<td>{s.scores[r["id"]]:.3f}</td>'
            + f'<td>{s.freq.get(r["id"], 0.0) * 100:.0f}%</td>'
            + f'<td>{f"{round(mix * 100)}%" if mix is not None else "—"}</td>'
            + f'<td>{f"{round((1 - mix) * 100)}%" if mix is not None else "—"}</td>'
            + f'<td>{num(round(r["cost"]))}</td>'
            + f'<td>{num(round(r["costPpp"])) if r["costPpp"] else "—"}</td>'
            + f'<td>{esc(", ".join(r["languages"])) or "—"}</td>'
            + f'<td class="ops">{esc(", ".join(r["operators"])) or "—"}</td></tr>'
        )
    return (
        f"<caption>{caption}</caption><thead><tr>"
        + "".join(f"<th>{esc(h)}</th>" for h in head)
        + "</tr></thead><tbody>" + "".join(body) + "</tbody>"
    )


def _correlation(s: Scenario) -> tuple[str, str, str]:
    from src.correlation import STRONG_AT

    keys = sorted(s.scaled)
    cols = {p: [s.scaled[k][p] for k in keys] for p in PILLARS}

    from src.correlation import _pearson
    r = [[_pearson(cols[a], cols[b]) for b in PILLARS] for a in PILLARS]

    def fmt(v: float) -> str:
        return f"{v:.2f}".replace("-", "−")

    labels = s.data["pillarLabels"]
    head = ("<thead><tr><th></th>"
            + "".join(f"<th>{j + 1}</th>" for j in range(len(PILLARS) - 1))
            + "</tr></thead>")
    body = []
    for i, p in enumerate(PILLARS):
        cells = []
        for j in range(len(PILLARS) - 1):
            if j >= i:
                cells.append('<td class="blank"></td>')
                continue
            v = r[i][j]
            if v is None:
                cells.append('<td title="does not vary">—</td>')
                continue
            hue = "--corr-pos" if v >= 0 else "--corr-neg"
            tint = f"background:rgb(var({hue}) / {abs(v) * 0.32:.3f})"
            cells.append(
                f'<td style="{tint}" title="{esc(labels[p])} and '
                f'{esc(labels[PILLARS[j]])}: {fmt(v)}">{fmt(v)}</td>'
            )
        body.append(
            f'<tr><th>{i + 1} {esc(labels[p])}</th>{"".join(cells)}</tr>'
        )

    from src.correlation import summary
    summ = summary(r)
    read = (
        f'<strong>{summ["strong"]} of the {summ["pairs"]} pairs</strong> correlate at '
        f'{STRONG_AT} or above, and the average pair sits at {fmt(summ["mean_abs"])}. '
        f'These {summ["pillars"]} pillars therefore carry about '
        f'<strong>{summ["n_eff"]:.1f} independent directions</strong> between them, so the '
        f'2,000 reweightings explore correspondingly less of the decision space than '
        f'their count suggests.'
    )
    return head + f"<tbody>{''.join(body)}</tbody>", read, summ


def _sliders(s: Scenario) -> str:
    labels, notes, icons = (
        s.data["pillarLabels"], s.data["pillarNotes"], s.data["icons"]
    )
    out = []
    for p in PILLARS:
        pct = round(s.weights[p] * 100)
        ico = (
            f'<svg class="ico" viewBox="0 0 16 16" aria-hidden="true" '
            f'style="stroke:{s.data["colors"][p]}">{icons[p]}</svg>'
        )
        out.append(
            f'<div class="slider-row"><div class="slider-head">'
            f'<span class="slider-name">{ico}{esc(labels[p])}</span>'
            f'<span class="slider-val" id="val-{p}">{pct}%</span></div>'
            f'<div class="track"><input type="range" id="w-{p}" min="0" max="60" step="1" '
            f'value="{pct}" aria-label="{esc(labels[p])} weight">'
            f'<i class="preset" id="preset-{p}" style="left:{pct / 60 * 100:.2f}%"></i>'
            f'</div><p class="slider-note">{esc(notes[p])}</p></div>'
        )
    return "".join(out)


# --- assembly -------------------------------------------------------------

def slots(data: dict) -> dict[str, str]:
    """Every element the script fills, rendered for the declared scenario."""
    s = Scenario(data)
    snap = data["provenance"]["postings"]
    base = s.baseline()
    corr_table, corr_read, summ = _correlation(s)
    settles_yes, settles_no = _settles(s)
    next_items, next_note = _next(s)

    resolved = sum(1 for r in s.rows if r["costResolved"])
    thin = sum(
        1 for r in s.rows
        if r["postings"] is not None and r["postings"] < data["evidenceFloor"]
    )
    national = _national_pillars(s)

    fte = data["fteDefault"]
    horizon = data["horizonDefault"]

    out = {
        "scope": f"{len(s.rows)} GBS and GCC cities",
        "asof": (
            f"{len(PILLARS)} pillars · "
            + (f"{'one snapshot' if snap['isSnapshot'] else str(snap['count']) + ' snapshots'}"
               f", {esc(snap['dateLabel'])}" if snap else "sample not fetched")
        ),
        "headline": _headline(s),
        "takeaway": _takeaway(s),
        "archetype": "".join(
            f'<button type="button" data-k="{esc(k)}" '
            f'aria-pressed="{"true" if k == s.archetype else "false"}">'
            f'{esc(v["label"])}</button>'
            for k, v in data["archetypes"].items()
        ),
        "archetype-blurb": esc(s.arch["blurb"]),
        "weights-why": f"<strong>Starting position:</strong> {esc(s.arch['why'])} "
                       f"A starting position, not a recommendation — move it and see "
                       f"what survives.",
        "sliders": _sliders(s),
        "weight-sum": "Tick marks show this centre type’s starting position.",
        "adjust-state": "weights · headquarters · cost",
        "assume-note": "Employer charges and backfill are <b>assumptions you set</b>, "
                       "not measured here. Years forward carries each market at its own "
                       "measured wage drift.",
        "hq": "".join(
            f'<optgroup label="{esc(region)}">'
            + "".join(
                f'<option value="{esc(x["key"])}"'
                f'{" selected" if x["key"] == data["hq"] else ""}>{esc(x["label"])} '
                f'(UTC{"+" if x["offset"] >= 0 else "−"}{abs(x["offset"]):g})</option>'
                for x in places)
            + "</optgroup>"
            for region, places in data["hqGroups"].items()
        ),
        "baseline": (
            '<optgroup label="Also scored in this study">'
            + "".join(
                f'<option value="{esc(b["key"])}"'
                f'{" selected" if b["key"] == data["baselineDefault"] else ""}>'
                f'{esc(b["label"])}</option>'
                for b in data["baselines"] if b["scored"])
            + '</optgroup><optgroup label="Origin only">'
            + "".join(
                f'<option value="{esc(b["key"])}">{esc(b["label"])}</option>'
                for b in data["baselines"] if not b["scored"])
            + "</optgroup>"
        ),
        "board-title": f"{s.arch['label']}: {len(s.rows)} cities ranked on your weighting",
        "belief": _belief(s),
        "rows": _rows(s),
        "legend": _legend(s),
        "strip-title": f"Working hours shared with {esc(_hq_label(data))}",
        "tzstrip": _strip(s),
        "case-title": (
            f"Annual wage gap for <strong>{num(fte)} role{'' if fte == 1 else 's'}</strong> "
            f"leaving <strong>{esc(base['label'])}</strong>"
            + (f" in <strong>{horizon} year{'' if horizon == 1 else 's'}</strong>"
               if horizon > 0 else "")
        ),
        "case": _case(s),
        "case-caveat": _case_caveat(s, base),
        "exhibit-source": (
            "Source: ILOSTAT earnings and employment by occupation; World Bank Worldwide "
            "Governance Indicators; Eurostat regional accounts; "
            f"{len(s.rows)} cities from a GBS/GCC job-posting sample, {esc(data['asOf'])}. "
            f"Note: {resolved} of {len(s.rows)} cities carry city-level cost, the remainder "
            f"their country's; {thin} rest on fewer than {data['evidenceFloor']} postings "
            f"and cannot be called robust."
        ),
        "beyond": _beyond(data),
        "beyond-note": _beyond_note(data),
        "beyond-more": _beyond_more(data),
        "settles-yes": settles_yes,
        "settles-no": settles_no,
        "next": next_items,
        "next-note": next_note,
        "table": _table(s),
        "floor-n": str(data["evidenceFloor"]),
        "sep-n": f"{round(data['separableAt'] * 100)}%",
        "corr": corr_table,
        "corr-n": str(len(s.rows)),
        "corr-read": corr_read,
        "corr-why": _corr_why(s, national),
        "limits": _limits(data, summ, national, snap),
        "sources": "".join(
            f'<div><dt>{esc(x["pillar"])}</dt><dd>{esc(x["name"])}<br>'
            f'<span class="vint">{esc(x["detail"])} · {esc(x["vintage"])}</span></dd></div>'
            for x in data["sources"]
        ),
        "provenance": _provenance(data),
        "foot": (
            "A city qualifies only where four or more employers advertise this work. "
            f"{resolved} of {len(s.rows)} carry city-level cost. "
            '<a href="https://github.com/morichtereur/gbs-location-selection">'
            "Method and code</a>."
        ),
    }
    return out


def _national_pillars(s: Scenario) -> list[str]:
    groups: dict[str, list[dict]] = {}
    for r in s.rows:
        groups.setdefault(r["parent"] or r["id"], []).append(r)
    out = []
    for p in PILLARS:
        if all(
            (max(x[p] for x in g) - min(x[p] for x in g))
            <= 1e-9 * max(1.0, abs(max(x[p] for x in g)))
            for g in groups.values()
        ):
            out.append(p)
    return out


def _hq_label(data: dict) -> str:
    for places in data["hqGroups"].values():
        for x in places:
            if x["key"] == data["hq"]:
                return x["label"]
    return data["hq"]


def _corr_why(s: Scenario, national: list[str]) -> str:
    if not national:
        return "Every pillar varies within at least one country here."
    names = [s.data["pillarLabels"][p].lower() for p in national]
    last = names.pop()
    joined = (", ".join(names) + " and " if names else "") + last
    return (
        f"Why: {len(national)} of the {len(PILLARS)} pillars — {esc(joined)} — are "
        f"national series that take one value per country across these cities. They "
        f"cannot separate two cities in the same country whatever weight they are given, "
        f"and the countries themselves line up on close to one axis."
    )


def _limits(data: dict, summ: dict, national: list[str], snap: dict | None) -> str:
    correlation = (
        f"The {len(PILLARS)} pillars are <strong>not independent</strong>: the average "
        f"pair correlates at {summ['mean_abs']:.2f} and they carry about "
        f"{summ['n_eff']:.1f} independent directions between them, because "
        f"{len(national)} of the {len(PILLARS)} are national series shared by every city "
        f"in a country. The 2,000 reweightings therefore explore substantially less of "
        f"the decision space than their count suggests — a top-three place that survives "
        f"them has survived less than the number sounds like. The matrix is above."
    )
    if snap and snap["isSnapshot"]:
        sample = (
            f"<b>One snapshot, {esc(snap['dateLabel'])}.</b> A city hiring quietly during "
            f"the fetch is under-represented; absence is weak evidence, not a verdict. "
            f"Nothing here can show a trend, because there is only one point in time to "
            f"compare."
        )
    elif snap:
        sample = (
            f"<b>{snap['count']} snapshots</b>, the most recent {esc(snap['dateLabel'])}. "
            f"A city hiring quietly during a fetch is under-represented; absence is weak "
            f"evidence, not a verdict."
        )
    else:
        sample = ("<b>No postings sample has been fetched</b>, so capability and employer "
                  "depth are unavailable and no city can be ranked.")
    return "".join(f"<li>{x}</li>" for x in [correlation, sample, *data["limits"]])


def _case_caveat(s: Scenario, base: dict) -> str:
    from src.loaded import Assumptions

    a = Assumptions()
    items = [r for r in s.order if r["cost"] is not None]
    unresolved = sum(1 for r in items if not r["costResolved"])
    cannot = [r for r in items if a.horizon > 0 and not r["driftMeasured"]]
    tilted = sorted(
        (r for r in items if r["regionIndex"] and r["regionIndex"] > 1),
        key=lambda r: -r["regionIndex"],
    )
    tilt = (
        "The baseline is a national average, while "
        + " and ".join(f"{esc(r['name'])} carries {r['regionIndex']:.2f}×"
                       for r in tilted[:2])
        + " its own country mean, so a capital-city premium sits on one side of the "
          "subtraction and not the other. "
    ) if tilted else ""

    pct = lambda x: f"{round(x * 100)}%"  # noqa: E731
    note = (
        f"<b>Base</b> is the gross wage line. <b>Loaded</b> adds {pct(a.loading)} employer "
        f"charges to both sides and {pct(a.attrition)} attrition backfill to the "
        f"destination only, since the origin is not being stood up"
        + (f", then carries each market forward {a.horizon} "
           f"year{'' if a.horizon == 1 else 's'} at its own measured wage drift"
           if a.horizon > 0 else "")
        + ". Those first two are <b>assumptions you set, not measured here</b>: no free "
          "source gives comparable employer-charge schedules for all eleven markets, so "
          "the factor is uniform, which scales every gap and cannot reorder them — real "
          "charges differ sharply by country and pricing that difference is precisely "
          "what this cannot do. "
    )
    if unresolved:
        note += (
            f'<span class="screen-only">{unresolved} of {len(items)} cities are marked '
            f'<b>national</b>: no city-level wage exists for them, so neither side of '
            f'their gap carries a city premium. </span>'
        )
    if cannot:
        note += (
            f'<span class="screen-only">{esc(", ".join(r["name"] for r in cannot))} '
            f'cannot be projected forward — too short a wage series to measure a drift — '
            f'so {"it keeps its base figure" if len(cannot) == 1 else "they keep their base figures"} '
            f'rather than being carried at a panel median. </span>'
        )
    return (
        note
        + f"Wage line only, at {esc(base['label'])}’s blended rate for professional and "
          "clerical occupations. It excludes facilities, technology, management overhead, "
          "transition and severance, so it is an upper bound on the wage component and "
          "not a savings case. "
        + tilt
        + 'Headcount is held one-for-one<span class="screen-only">; a centre that is '
          "still ramping needs more heads for the same volume, which moves this number "
          "further than the wage gap itself does</span>."
    )


def _beyond(data: dict) -> str:
    def n(x, d=0):
        if x is None:
            return "—"
        if x >= 1e5:
            return f"{x / 1e6:.1f}m"
        return f"{x:,.{d}f}"

    return "".join(
        f'<div class="beyond-row">'
        f'<span class="cty">{flag(data, r["key"])}{esc(r["city"])}</span>'
        f'<span class="mkt">{esc(r["market"])}</span>'
        f'<span class="fig">{n(r["cost"])}</span>'
        f'<span class="fig">{n(r["talent"])}</span>'
        f'<span class="fig">{n(r["risk"])}</span>'
        f'<span class="fig">{r["overlap"]:.1f}h</span></div>'
        for r in data["beyond"]
    )


def _beyond_note(data: dict) -> str:
    years = sorted({r["costYear"] for r in data["beyond"] if r.get("costYear")})
    observed = "" if not years else (
        str(years[0]) if years[0] == years[-1] else f"{years[0]}–{years[-1]}"
    )
    return (
        "Reported, not ranked. Five pillars reach these markets because ILOSTAT and the "
        "World Bank cover every country alike; <b>capability and employer depth do not</b>, "
        f"and those are the two the postings carry. Cost is national, observed {observed}; "
        "the city named is the one a programme would consider, not a measured city figure."
    )


def _beyond_more(data: dict) -> str:
    near = ", ".join(
        f'<b>{esc(m["name"])}</b> ({m["postings"]} postings, {m["employers"]} '
        f'employer{"" if m["employers"] == 1 else "s"})'
        for m in data["nearMisses"][:3]
    )
    un = " and ".join(
        f"<b>{esc(c)}</b> ({esc(cities)})"
        for c, cities in data["unpriceable"].items()
    )
    return (
        f"Two other kinds of absence. <b>Seen but too thin:</b> {data['nearMissTotal']} "
        f"locations appear in the sample and clear neither threshold — {near} come "
        f"closest. The employer count is usually what stops them, and one employer hiring "
        f"is an office, not a centre. <b>Not priceable at all:</b> {un} — ILOSTAT "
        f"publishes no earnings by occupation for either, so there is no cost figure on "
        f"the basis every market here uses, and two pillars without the decisive one "
        f"would be worse than no row. Egypt was dropped for a third reason: its "
        f"professionals report 1.06× clerical pay against 1.3–2.9× everywhere else, "
        f"which is a broken series rather than a cheap country."
    )


def _next(s: Scenario) -> tuple[str, str]:
    """The closing block: the checks a phase-2 validation would run."""
    top = s.top or s.order[:1]
    names = [esc(r["name"]) for r in top]
    last = names.pop() if len(names) > 1 else None
    band_label = f"{', '.join(names)} and {last}" if last else names[0]
    national = sum(1 for r in top if not r["costResolved"])
    min_n = min(
        (r["postings"] for r in top if r["postings"] is not None), default=0
    )
    ops = list(dict.fromkeys(o for r in top for o in (r["operators"] or [])))
    pct = lambda x: f"{round(x * 100)}%"  # noqa: E731
    loading = pct(s.data["loadingDefault"])
    attr = pct(s.data["attritionDefault"])

    wage = (
        f"{national} of the {len(top)} carry ILOSTAT’s national wage, and the "
        f"{loading} employer loading is a uniform assumption where real schedules "
        f"differ by country."
        if national > 0 else
        f"Every city here carries a measured city wage, but the {loading} employer "
        f"loading is a uniform assumption where real schedules differ by country."
    )
    attrition = (
        f"The {len(ops)} employers named in this band’s postings already run centres "
        f'there<span class="screen-only"> — the table below lists them per city</span>. '
        f"Their attrition, time-to-fill and ramp curves would replace the {attr} "
        f"backfill assumption"
        if ops else
        f"No operator is named in this band’s postings, so provider benchmarks would "
        f"have to replace the {attr} backfill assumption"
    )

    items = [
        f"<b>Live wage and employer-charge quotes for {band_label}.</b> {wage} "
        f"A recruiter’s per-role quote and a payroll provider’s charge schedule "
        f"replace both — the two figures on Exhibit 3 no public source supplies.",
        f"<b>Site visits against the advertised capability.</b> The capability pillar "
        f"is job postings — as few as {min_n} behind a city in this band. Postings say "
        f"who is hiring; they cannot say whether the advertised work is the work done, "
        f"or whether a centre could hire at programme rate. A provider RFI and days on "
        f"the ground settle what postings cannot.",
        f"<b>Attrition and ramp data from the operators already there.</b> {attrition}, "
        f"which is the one Exhibit 3 input that can reorder cities — and today it is "
        f"a slider.",
    ]
    note = (
        "Checks, not refinements: each replaces an input this analysis cannot source "
        "from public data, which is why they close the page rather than extend it. "
        "A phase 2 that skips them is trusting a slider."
    )
    return "".join(f"<li>{x}</li>" for x in items), note


def _provenance(data: dict) -> str:
    p = data["provenance"]["postings"]
    c = data["provenance"]["contaminant"]
    if not p:
        return ("<b>No postings sample has been fetched.</b> Capability and employer "
                "depth cannot be computed without one, so no city is ranked.")
    terms = ", ".join(f"“{esc(t)}”" for t in p["terms"])
    local = ", ".join(
        f'{esc(data["marketNames"].get(m, m))} ({len(ts)})'
        for m, ts in (p.get("localTerms") or {}).items()
    )
    out = (
        f"<b>{'One snapshot' if p['isSnapshot'] else str(p['count']) + ' snapshots'}, "
        f"{esc(p['dateLabel'])}.</b> {num(p['postingsFetched'])} postings from "
        f"{esc(p['board'])} across {p['marketCount']} markets, {p['termCount']} search "
        f"terms paged to {p['maxPages']}: {terms}"
    )
    if local:
        out += f", plus local-language terms in {local}"
    out += (". The terms are the sample: this is what those phrases returned, not GBS "
            "hiring in the abstract. ")
    if p["isSnapshot"]:
        out += ("A single point in time — a city hiring quietly during the fetch is "
                "under-represented, and nothing here can show a trend. ")
    if c:
        out += (f"Classification error is modelled against a broader finance sample of "
                f"{num(c['postings'])} postings fetched {esc(c['dateLabel'])} "
                f"({esc(c['repo'])}).")
    return out


def values(data: dict) -> dict[str, str]:
    """Defaults for the void inputs, which have no innards to fill.

    A number box that renders blank reads as broken even when nothing can be
    typed into it, and these are the four the script sets on load.
    """
    return {
        "fte": str(data["fteDefault"]),
        "loading": str(round(data["loadingDefault"] * 100)),
        "attrition": str(round(data["attritionDefault"] * 100)),
        "horizon": str(int(data["horizonDefault"])),
    }


def inject(html: str, data: dict) -> str:
    """Write each region into the empty element the script would have filled.

    Replaces whatever sits between an element's tags, so a slot that already
    carries placeholder markup is replaced rather than appended to.
    """
    for element_id, content in slots(data).items():
        marker = f'id="{element_id}"'
        try:
            i = html.index(marker)
        except ValueError:  # pragma: no cover - a slot removed from the template
            raise AssertionError(f"no element with id {element_id!r} to fill")
        tag_start = html.rindex("<", 0, i)
        tag_name = html[tag_start + 1:].split(">")[0].split()[0]
        open_end = html.index(">", i) + 1
        close = f"</{tag_name}>"
        close_at = html.index(close, open_end)
        html = html[:open_end] + content + html[close_at:]

    for element_id, value in values(data).items():
        marker = f'id="{element_id}"'
        i = html.index(marker)
        end = html.index(">", i)
        assert f'value="' not in html[i:end], f"{element_id} already carries a value"
        html = html[:end] + f' value="{esc(value)}"' + html[end:]
    return html
