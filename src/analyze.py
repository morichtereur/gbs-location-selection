"""Run the study end to end: panel, stability, chart, RESULTS.md."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src import config as C
from src.panel import REFERENCE_YEAR, build, with_centres
from src.score import PILLARS, normalise, rank, raw_pillars, score
from src.stability import run

# The first version of this chart used the site green against a mid blue. That
# pair fails the normal-vision separation floor at deltaE 13.7 — readers with
# ordinary colour vision struggle to tell the two series apart, and no amount
# of labelling excuses that one. Blue against orange clears every gate.
TRANSACTIONAL_COLOR = "#3b6ea5"
JUDGMENT_COLOR = "#c65b2e"
ROBUST_COLOR = "#146b54"
NEVER_COLOR = "#b9b9b4"


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def chart(panel, results, path):
    """Top-three frequency per market, both archetypes on one axis.

    The comparison is the whole point, so the two archetypes share a scale and
    sit next to each other rather than in separate figures where the reader
    has to hold one in memory.
    """
    trans = results["transactional_hub"]
    judg = results["judgment_centre"]
    order = sorted(trans.frequency, key=lambda k: (-trans.frequency[k], -judg.frequency[k]))
    names = [panel[k].name for k in order]
    y = list(range(len(order)))
    height = 0.36

    fig, ax = plt.subplots(figsize=(10, 6.2))
    fig.patch.set_facecolor("white")
    fig.subplots_adjust(top=0.80, bottom=0.16, left=0.19, right=0.97)

    ax.axvspan(C.ROBUST_AT * 100, 104, color=ROBUST_COLOR, alpha=0.06, zorder=0)
    ax.axvline(C.ROBUST_AT * 100, color=ROBUST_COLOR, lw=1, ls=(0, (4, 3)), zorder=1)
    ax.axvline(C.CONTINGENT_AT * 100, color="#9a9a94", lw=1, ls=(0, (2, 3)), zorder=1)

    for i, k in zip(y, order):
        ax.barh(i - height / 2, trans.frequency[k] * 100, height=height,
                color=TRANSACTIONAL_COLOR, zorder=3)
        ax.barh(i + height / 2, judg.frequency[k] * 100, height=height,
                color=JUDGMENT_COLOR, zorder=3)

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=11)
    ax.set_ylim(len(order) - 0.4, -1.1)
    ax.set_xlim(0, 104)
    ax.set_xlabel(
        f"share of {trans.draws:,} defensible weightings placing the market in the top {C.TOP_N}",
        fontsize=10, color="#444", labelpad=8,
    )
    ax.tick_params(axis="x", labelsize=10)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#cccccc")
    ax.grid(axis="x", color="#e6e6e2", lw=0.8, zorder=0)
    ax.set_axisbelow(True)

    # Band labels sit at the top of the plot area, clear of every bar.
    ax.text(C.ROBUST_AT * 100 + 1.5, -0.95, "robust", fontsize=9.5,
            color=ROBUST_COLOR, ha="left", va="center", style="italic")
    ax.text(C.CONTINGENT_AT * 100 - 1.5, -0.95, "never shortlisted", fontsize=9.5,
            color="#8a8a84", ha="right", va="center", style="italic")

    fig.text(0.02, 0.955, "Which markets survive a change of mind",
             fontsize=16, fontweight="bold", color="#121a17", va="top")
    fig.text(
        0.02, 0.895,
        "Ten markets scored on six pillars — cost, talent, governance, demonstrated capability, hours\n"
        "shared with headquarters, and how fast the wage gap is closing — then re-scored under 10,000\n"
        "defensible weightings, with every input resampled inside its published error.",
        fontsize=10.5, color="#555", va="top", linespacing=1.45,
    )

    handles = [
        plt.Rectangle((0, 0), 1, 1, color=TRANSACTIONAL_COLOR),
        plt.Rectangle((0, 0), 1, 1, color=JUDGMENT_COLOR),
    ]
    fig.legend(handles, ["Transactional hub", "Judgment centre of excellence"],
               loc="lower center", ncol=2, frameon=False, fontsize=10.5,
               bbox_to_anchor=(0.55, 0.005))

    fig.savefig(path, dpi=170, facecolor="white")
    plt.close(fig)


def results_md(panel, results, variants) -> str:
    lines = [
        "# Results",
        "",
        f"Ten markets, {results['transactional_hub'].draws:,} draws per archetype, "
        f"panel assembled {REFERENCE_YEAR}.",
        "",
        "## The panel",
        "",
        "| market | wage basket USD/mo | obs. year | lag | talent scale proxy | WGI composite | transactional share | postings |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for k, m in sorted(panel.items(), key=lambda kv: kv[1].cost_usd):
        lines.append(
            f"| {m.name} | {m.cost_usd:,.0f} | {m.cost_year} | {m.cost_lag}y | "
            f"{m.talent_proxy:,.0f} | {m.risk_score:.1f} | {m.transactional_share:.1%} | "
            f"{m.postings_in_scope} |"
        )

    for key, st in results.items():
        arch = C.ARCHETYPES[key]
        lines += [
            "",
            f"## {arch['label']}",
            "",
            f"Declared weights: " + ", ".join(f"{p} {w:.2f}" for p, w in arch["weights"].items()) + ".",
            f"Baseline top {C.TOP_N}: **"
            + ", ".join(panel[k].name for k in st.baseline_rank[: C.TOP_N])
            + "**.",
            "",
            "| market | top-3 frequency | mean rank | rank range | verdict | what it takes |",
            "|---|---:|---:|---:|---|---|",
        ]
        for k in sorted(st.frequency, key=lambda k: -st.frequency[k]):
            need = ""
            if st.verdict(k) == "contingent" and st.weight_when_in[k]:
                wi, wo = st.weight_when_in[k], st.weight_when_out[k]
                pillar = max(PILLARS, key=lambda p: wi[p] - wo[p])
                need = f"{pillar} weight {wi[pillar]:.2f} vs {wo[pillar]:.2f} when out"
            lo, hi = st.rank_range[k]
            lines.append(
                f"| {panel[k].name} | {_pct(st.frequency[k])} | {st.mean_rank[k]:.1f} | "
                f"{lo}–{hi} | {st.verdict(k)} | {need} |"
            )

    lines += [
        "",
        "## What actually moves the ranking",
        "",
        "Largest change in any market's top-3 frequency when one thing is varied",
        "and everything else is held fixed. The first row is every published",
        "measurement error in the panel, taken together. The rest are choices a",
        "modeller makes silently.",
        "",
        "| varied | transactional hub | judgment centre |",
        "|---|---:|---:|",
    ]
    labels = {
        "measurement": "All published measurement error",
        "vintage": "Vintage: age-adjusted or as-observed",
        "transform": "Normalisation: log or linear",
        "talent": "Talent pillar: employed stock or education pipeline",
    }
    for key, label in labels.items():
        cells = []
        for arch in C.ARCHETYPES:
            name, swing = variants[arch]["swings"][key]
            cells.append(f"{name} {swing:.1f}pp")
        lines.append(f"| {label} | {cells[0]} | {cells[1]} |")

    lines += [
        "",
        "Two of those choices change the membership of the shortlist, not just the",
        "confidence in it:",
        "",
    ]
    for arch in C.ARCHETYPES:
        v = variants[arch]
        lines.append(
            f"- **{C.ARCHETYPES[arch]['label']}** — employed-stock talent gives "
            + ", ".join(panel[k].name for k in v["baseline_top"])
            + "; education-pipeline talent gives "
            + ", ".join(panel[k].name for k in v["education_top"])
            + "."
        )
    return "\n".join(lines) + "\n"


def _swing(base, other, panel):
    """Largest absolute change in any market's top-3 frequency."""
    k = max(base.frequency, key=lambda k: abs(base.frequency[k] - other.frequency[k]))
    return panel[k].name, abs(base.frequency[k] - other.frequency[k]) * 100


def main() -> None:
    panel = build()
    results = {a: run(panel, a) for a in C.ARCHETYPES}

    # The education-pipeline talent pillar, run on the same panel. Swapping the
    # field rather than rebuilding avoids refetching four sources.
    education = {}
    for m in panel.values():
        m.talent_proxy = m.talent_education
    original_source, C.TALENT_SOURCE = C.TALENT_SOURCE, "education"
    for a in C.ARCHETYPES:
        education[a] = run(panel, a)
    C.TALENT_SOURCE = original_source
    for m in panel.values():
        m.talent_proxy = m.talent_employed

    original_age, C.AGE_ADJUST = C.AGE_ADJUST, False
    as_observed = {a: run(panel, a) for a in C.ARCHETYPES}
    C.AGE_ADJUST = original_age

    variants = {}
    for a in C.ARCHETYPES:
        st = results[a]
        linear = run(panel, a, transform="linear")
        weights_only = run(panel, a, resample_inputs=False)
        variants[a] = {
            "order": sorted(st.frequency, key=lambda k: -st.frequency[k]),
            "baseline_top": st.baseline_rank[: C.TOP_N],
            "education_top": sorted(
                education[a].frequency, key=lambda k: -education[a].frequency[k]
            )[: C.TOP_N],
            "swings": {
                "measurement": _swing(st, weights_only, panel),
                "vintage": _swing(st, as_observed[a], panel),
                "transform": _swing(st, linear, panel),
                "talent": _swing(st, education[a], panel),
            },
        }
    C.DATA.mkdir(exist_ok=True)
    chart(panel, results, C.DATA / "chart_stability.png")
    centres_chart(with_centres(panel), C.DATA / "chart_centres.png")
    (C.ROOT / "RESULTS.md").write_text(results_md(panel, results, variants))
    print("wrote data/chart_stability.png and RESULTS.md")
    for a, st in results.items():
        robust = [panel[k].name for k in st.frequency if st.verdict(k) == "robust"]
        print(f"  {C.ARCHETYPES[a]['label']}: robust = {robust or 'none'}")



def centres_chart(panel, path):
    """Every evidenced GBS centre, grouped by country, on one score axis.

    Two things have to read at once: which locations are genuinely GBS centres,
    and how much choosing between them inside one country actually matters. A
    dot plot does both — the spread of a country's dots is the value of the
    city decision, and the fill says whether that spread rests on measured
    city-level cost or only on residual capability noise.
    """
    import collections

    archetype = "transactional_hub"
    scores = score(
        normalise(raw_pillars(panel, archetype)),
        C.ARCHETYPES[archetype]["weights"],
    )
    grouped = collections.defaultdict(list)
    for key, m in panel.items():
        if m.is_city:
            grouped[m.parent].append((m, scores[key]))
    order = sorted(
        grouped,
        key=lambda k: max(v for _, v in grouped[k]) - min(v for _, v in grouped[k]),
        reverse=True,
    )

    fig, ax = plt.subplots(figsize=(10, 5.4))
    fig.patch.set_facecolor("white")
    fig.subplots_adjust(top=0.80, bottom=0.14, left=0.16, right=0.97)

    for row, market in enumerate(order):
        entries = sorted(grouped[market], key=lambda kv: kv[1])
        xs = [v for _, v in entries]
        ax.plot([min(xs), max(xs)], [row, row], color="#c9cbc2", lw=1.5, zorder=1,
                solid_capstyle="round")
        for m, value in entries:
            resolved = m.cost_resolved
            ax.scatter(
                value, row, s=58, zorder=3,
                facecolor=TRANSACTIONAL_COLOR if resolved else "white",
                edgecolor=TRANSACTIONAL_COLOR, linewidth=1.6,
            )
        # Name the extremes only; labelling every dot turns the row into soup.
        lo, hi = entries[0], entries[-1]
        ax.annotate(lo[0].name, (lo[1], row), textcoords="offset points",
                    xytext=(-9, 0), ha="right", va="center", fontsize=9, color="#4d554f")
        if len(entries) > 1:
            ax.annotate(hi[0].name, (hi[1], row), textcoords="offset points",
                        xytext=(9, 0), ha="left", va="center", fontsize=9, color="#4d554f")

    # Extreme labels sit outside their dots, so the axis needs room for them
    # or the leftmost one collides with the country names.
    values = [v for entries in grouped.values() for _, v in entries]
    lo, hi = min(values), max(values)
    pad = (hi - lo) * 0.22
    ax.set_xlim(lo - pad, hi + pad * 0.6)

    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([C.MARKETS[m]["name"] for m in order], fontsize=11)
    ax.set_ylim(len(order) - 0.4, -0.8)
    ax.set_xlabel("score as a transactional hub (higher is better)", fontsize=10,
                  color="#444", labelpad=8)
    ax.tick_params(axis="x", labelsize=10)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#cccccc")
    ax.grid(axis="x", color="#e6e6e2", lw=0.8)
    ax.set_axisbelow(True)

    fig.text(0.02, 0.955, "Choosing a city matters where you can measure it",
             fontsize=16, fontweight="bold", color="#121a17", va="top")
    fig.text(
        0.02, 0.893,
        f"{sum(len(v) for v in grouped.values())} locations where GBS roles are actually advertised by four or more employers.\n"
        "Filled dots have city-level labour cost from Eurostat; hollow dots carry their country's figure, so\n"
        "the spread between them is residual noise rather than measured difference.",
        fontsize=10.5, color="#555", va="top", linespacing=1.45,
    )
    fig.savefig(path, dpi=170, facecolor="white")
    plt.close(fig)

if __name__ == "__main__":
    main()
