"""Run the study end to end: panel, stability, chart, RESULTS.md."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src import config as C
from src.panel import REFERENCE_YEAR, build
from src.score import PILLARS, normalise, rank, raw_pillars, score
from src.stability import run

ROBUST_COLOR = "#146b54"
CONTINGENT_COLOR = "#3b6ea5"
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
                color=ROBUST_COLOR, zorder=3)
        ax.barh(i + height / 2, judg.frequency[k] * 100, height=height,
                color=CONTINGENT_COLOR, zorder=3)

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
        "Ten markets scored on cost, talent scale, governance risk and demonstrated capability, then\n"
        "re-scored under 10,000 defensible weightings with inputs resampled inside their published error.",
        fontsize=10.5, color="#555", va="top", linespacing=1.45,
    )

    handles = [
        plt.Rectangle((0, 0), 1, 1, color=ROBUST_COLOR),
        plt.Rectangle((0, 0), 1, 1, color=CONTINGENT_COLOR),
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
    (C.ROOT / "RESULTS.md").write_text(results_md(panel, results, variants))
    print("wrote data/chart_stability.png and RESULTS.md")
    for a, st in results.items():
        robust = [panel[k].name for k in st.frequency if st.verdict(k) == "robust"]
        print(f"  {C.ARCHETYPES[a]['label']}: robust = {robust or 'none'}")


if __name__ == "__main__":
    main()
