"""How much of the shortlist was ever really in play.

A location scorecard produces one ranking from one set of weights and one set
of point estimates. Both are uncertain, and in different ways:

*The weights are opinions.* Nobody can defend 0.45 on cost against 0.38. Draws
come from a Dirichlet centred on the declared weights, so every draw is a
weighting somebody could argue for in the same room.

*The inputs are estimates.* The WGI governance scores ship with the bounds of
their own 90% confidence interval, and the wage basket rests on a declared
staffing blend. Both are resampled from what their publisher says they are
worth, rather than treated as exact.

A market that holds a top-three place across all of that is a finding. One
that holds it only in a corner of the space is a preference wearing a number.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src import config as C
from src.panel import Market
from src.score import PILLARS, normalise, rank, raw_pillars, score

# WGI confidence intervals are published at 90%, so the half-width is 1.645
# standard deviations.
Z90 = 1.6448536269514722


@dataclass
class Stability:
    archetype: str
    draws: int
    top_n: int
    frequency: dict[str, float]
    mean_rank: dict[str, float]
    rank_range: dict[str, tuple[int, int]]
    baseline_rank: list[str]
    # Mean weight on each pillar among draws where a market made the top N,
    # against draws where it did not. Says what someone would have to believe
    # for a contingent market to belong on the list.
    weight_when_in: dict[str, dict[str, float]]
    weight_when_out: dict[str, dict[str, float]]

    def verdict(self, iso2: str) -> str:
        f = self.frequency.get(iso2, 0.0)
        if f >= C.ROBUST_AT:
            return "robust"
        if f >= C.CONTINGENT_AT:
            return "contingent"
        return "never"


def _wgi_sigma(lo: float, hi: float) -> float:
    return max((hi - lo) / (2 * Z90), 0.0)


def run(
    panel: dict[str, Market],
    archetype: str,
    *,
    draws: int = C.DRAWS,
    seed: int = C.SEED,
    transform: str = "log",
    resample_inputs: bool = True,
    wgi_correlation: str = "perfect",
) -> Stability:
    """Rank stability across resampled weights and resampled inputs.

    `wgi_correlation` brackets an assumption the WGI does not publish. The six
    governance dimensions are estimated from overlapping source data and move
    together within a country, but no correlation matrix ships with them.
    Drawing them independently averages five errors down to roughly a fifth of
    one and makes the composite look far firmer than any single dimension —
    a lower bound on the real uncertainty. Drawing one shock per country and
    applying it to every dimension is the upper bound. Both are run; if the
    shortlist survives the upper bound it survives anything WGI can throw at
    it. Default is the conservative end.
    """
    rng = np.random.default_rng(seed)
    markets = [k for k, m in panel.items() if m.complete]
    declared = C.ARCHETYPES[archetype]["weights"]
    alpha = np.array([C.WEIGHT_CONCENTRATION * declared[p] for p in PILLARS])

    baseline = rank(
        score(
            normalise(raw_pillars(panel, archetype), transform=transform),
            declared,
        )
    )

    hits = {k: 0 for k in markets}
    rank_sum = {k: 0 for k in markets}
    best = {k: len(markets) for k in markets}
    worst = {k: 1 for k in markets}
    w_in = {k: {p: 0.0 for p in PILLARS} for k in markets}
    w_out = {k: {p: 0.0 for p in PILLARS} for k in markets}
    n_in = {k: 0 for k in markets}

    weight_draws = rng.dirichlet(alpha, size=draws)

    for i in range(draws):
        weights = dict(zip(PILLARS, weight_draws[i]))

        wgi_draw = None
        cost_draw = None
        if resample_inputs:
            wgi_draw = {}
            for iso2 in markets:
                m = panel[iso2]
                if wgi_correlation == "perfect":
                    z = rng.standard_normal()
                    wgi_draw[iso2] = {
                        dim: float(
                            np.clip(sc + z * _wgi_sigma(lo, hi), 0.0, 100.0)
                        )
                        for dim, (sc, lo, hi) in m.wgi.items()
                    }
                else:
                    wgi_draw[iso2] = {
                        dim: float(
                            np.clip(rng.normal(sc, _wgi_sigma(lo, hi)), 0.0, 100.0)
                        )
                        for dim, (sc, lo, hi) in m.wgi.items()
                    }
            # The staffing blend behind the wage basket is an assumption, so
            # it moves too: a centre weighted to judgment work buys more
            # ISCO-2 time than one weighted to transactional processing.
            jitter = rng.uniform(
                -C.WAGE_BLEND_JITTER, C.WAGE_BLEND_JITTER, size=len(C.ISCO_GROUPS)
            )
            blend = {
                g: max(C.WAGE_BLEND[g] + j, 0.01)
                for g, j in zip(C.ISCO_GROUPS, jitter)
            }
            total = sum(blend.values())
            blend = {g: v / total for g, v in blend.items()}
            cost_draw = {
                iso2: sum(
                    blend[g] * panel[iso2].wage_components_usd[g]
                    for g in C.ISCO_GROUPS
                )
                for iso2 in markets
            }

        raw = raw_pillars(panel, archetype, wgi_draw=wgi_draw, cost_draw=cost_draw)
        order = rank(score(normalise(raw, transform=transform), weights))

        for position, iso2 in enumerate(order, start=1):
            rank_sum[iso2] += position
            best[iso2] = min(best[iso2], position)
            worst[iso2] = max(worst[iso2], position)
            inside = position <= C.TOP_N
            target = w_in if inside else w_out
            for p in PILLARS:
                target[iso2][p] += weights[p]
            if inside:
                hits[iso2] += 1
                n_in[iso2] += 1

    return Stability(
        archetype=archetype,
        draws=draws,
        top_n=C.TOP_N,
        frequency={k: hits[k] / draws for k in markets},
        mean_rank={k: rank_sum[k] / draws for k in markets},
        rank_range={k: (best[k], worst[k]) for k in markets},
        baseline_rank=baseline,
        weight_when_in={
            k: {p: w_in[k][p] / n_in[k] for p in PILLARS} if n_in[k] else {}
            for k in markets
        },
        weight_when_out={
            k: {
                p: w_out[k][p] / (draws - n_in[k]) for p in PILLARS
            } if draws - n_in[k] else {}
            for k in markets
        },
    )
