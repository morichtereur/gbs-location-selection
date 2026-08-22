"""How much of the shortlist was ever really in play.

A location scorecard produces one ranking from one set of weights and one set
of point estimates. Both are uncertain, and in different ways:

*The weights are opinions.* Nobody can defend 0.45 on cost against 0.38. Draws
come from a Dirichlet centred on the declared weights, so every draw is a
weighting somebody could argue for in the same room.

*The classifier is wrong two times in five.* The capability shares are measured
on postings a classifier selected, and it is about 55% precise. An observed
share is therefore a mixture of real service-centre work and ordinary finance
work that got through, and each draw recovers the former from the latter using a
precision drawn from the audit itself. This was a caveat before it was a model,
which was one revision too long.

*The inputs are estimates.* The WGI governance scores ship with the bounds of
their own 90% confidence interval. The wage and talent baskets rest on a
declared staffing blend, and the same blend is applied to both so cost and
talent keep describing the same workforce. The capability shares are estimates
from finite postings samples — 88 of them in Switzerland — and carry a binomial
standard error like anyone else's number. All three are resampled rather than
treated as exact.

A market that holds a top-three place across all of that is a finding. One
that holds it only in a corner of the space is a preference wearing a number.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src import config as C
from src.panel import Market, age, median_drift
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

    # Set by `run` so a verdict can weigh how much evidence sits behind it.
    evidence: dict[str, int] | None = None

    def verdict(self, iso2: str) -> str:
        f = self.frequency.get(iso2, 0.0)
        thin = (
            self.evidence is not None
            and self.evidence.get(iso2) is not None
            and self.evidence[iso2] < C.EVIDENCE_FLOOR
        )
        if f >= C.ROBUST_AT and not thin:
            return "robust"
        if f >= C.CONTINGENT_AT:
            return "contingent"
        return "never"


def _wgi_sigma(lo: float, hi: float) -> float:
    return max((hi - lo) / (2 * Z90), 0.0)


def _correct_for_precision(observed: float, precision: float, market, metric: str) -> float:
    """Recover the true share from one contaminated by classification error.

    An observed share is a mixture of the postings the classifier got right and
    the ones it should not have admitted:

        observed = precision · true + (1 − precision) · contaminant

    so the true share is that relation rearranged. The contaminant is the broad
    finance sample's mix for this market — what an intruding posting most likely
    is — measured rather than assumed.

    The result can fall outside [0, 1] when the observed share is extreme and the
    drawn precision is low, and those draws are clipped. Clipping biases the
    correction slightly toward the middle, which is worth knowing and is the sort
    of quiet step this study exists to expose.
    """
    if not C.MODEL_CLASSIFICATION_ERROR or precision <= 0.05:
        return observed
    contaminant = market.contaminant_transactional
    if contaminant is None:
        return observed
    if metric != "transactional_share":
        # The mirror share, since the taxonomy's two families partition the
        # postings it could decide.
        contaminant = 1.0 - contaminant
    true = (observed - (1.0 - precision) * contaminant) / precision
    return min(1.0, max(0.0, true))


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
    fallback_drift = median_drift(panel)
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
        talent_draw = None
        capability_draw = None
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
            cost_draw = {}
            for iso2 in markets:
                m = panel[iso2]
                basket = sum(
                    blend[g] * m.wage_components_usd[g] for g in C.ISCO_GROUPS
                )
                if C.AGE_ADJUST and m.cost_lag:
                    # A stale observation is uncertain in proportion to how
                    # stale it is, so the drift is drawn rather than assumed.
                    scale = C.DRIFT_SIGMA * (
                        1.0 if m.drift_measured
                        else C.DRIFT_SIGMA_UNMEASURED_MULTIPLE
                    )
                    centre = m.drift_used if m.drift_used is not None else fallback_drift
                    basket = age(basket, m.cost_lag, rng.normal(centre, scale))
                cost_draw[iso2] = basket
            # Same blend on the talent basket. Drawing a separate one would
            # let the model buy a transactional wage bill for a judgment-heavy
            # labour pool, which is not a workforce anyone could hire.
            if C.TALENT_SOURCE == "employment":
                talent_draw = {
                    iso2: sum(
                        blend[g] * panel[iso2].employment_components[g]
                        for g in C.ISCO_GROUPS
                    )
                    for iso2 in markets
                    if panel[iso2].employment_components
                }
            # The capability share is a sample proportion. Resampling it from
            # the binomial that produced it is the difference between taking
            # this project's own measurement error seriously and taking only
            # everybody else's.
            capability_draw = {}
            # One precision per draw, not one per market: the classifier is a
            # single instrument and its accuracy does not vary by country.
            precision = (
                rng.beta(C.AUDIT_CORRECT + 1, C.AUDIT_TOTAL - C.AUDIT_CORRECT + 1)
                if C.MODEL_CLASSIFICATION_ERROR
                else 1.0
            )
            metric = C.ARCHETYPES[archetype]["capability_metric"]
            for iso2 in markets:
                m = panel[iso2]
                successes, n = m.capability_counts
                if n <= 0:
                    continue
                p_hat = getattr(m, metric)
                observed = float(rng.binomial(n, p_hat)) / n
                capability_draw[iso2] = _correct_for_precision(
                    observed, precision, m, metric
                )

        raw = raw_pillars(
            panel, archetype, wgi_draw=wgi_draw, cost_draw=cost_draw,
            talent_draw=talent_draw, capability_draw=capability_draw,
        )
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
        evidence={
            k: panel[k].postings_in_scope
            for k in markets
            if panel[k].is_city and panel[k].postings_in_scope is not None
        },
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
