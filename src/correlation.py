"""How independent the seven pillars actually are.

The robustness claim on the exhibit — a top-three place that survives 2,000
reweightings — is only worth what the independence of the pillars is worth. Two
thousand draws over seven weights sound like two thousand different decisions.
They are two thousand different decisions only if moving weight from one pillar
to another moves the score somewhere new, and that is a property of the panel
rather than of the sampler.

It is not true here, and by a wide margin. Five of the seven pillars take one
value per country across the ranked cities — talent, governance, overlap,
durability and employer depth are national series, and only capability and
(for the Polish cities) cost resolve any finer. The four countries in the panel
then line up on a single axis: the cheaper markets sit further from a European
working day, score lower on governance, and have had flatter dollar wage drift.
So a weighting that buys cost is very close to a weighting that buys distance,
and the sampler cannot tell them apart.

This module measures that rather than asserting it. The correlation is taken on
the *normalised* pillar scores — log-transformed and direction-corrected, the
same basis `src/score.py` takes the weighted mean over — because that is the
basis a weight actually acts on. A sign is therefore readable directly: a
positive entry means the two pillars favour the same cities.

Effective dimensionality is the participation ratio of the correlation matrix's
eigenvalues, which needs no eigensolver:

    n_eff = (sum L)^2 / sum L^2 = k^2 / sum_ij R_ij^2

since the eigenvalues of a k x k correlation matrix sum to k, and the sum of
their squares is the matrix's own squared Frobenius norm. It reads as "the
number of pillars this panel behaves as if it had". The identity is what lets
the page recompute the figure live when the reader moves the headquarters,
without shipping a linear-algebra routine to do it.
"""

from __future__ import annotations

import math

from src import config as C
from src.panel import Market
from src.score import PILLARS, normalise, raw_pillars

# What counts as a pair worth naming on the exhibit. Not a test of anything —
# a reporting threshold, stated here so the count on the page is reproducible.
STRONG_AT = 0.7


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    """Correlation, or None where a series does not vary.

    A pillar that is constant across the panel decides nothing, and its
    correlation with anything else is 0/0. Returning None keeps that visible
    instead of imputing a zero, which would read as "independent" when the
    truth is "absent".
    """
    n = len(xs)
    if n < 2:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0.0 or syy <= 0.0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / math.sqrt(sxx * syy)


def matrix(
    panel: dict[str, Market], archetype: str, *, transform: str = "log"
) -> list[list[float | None]]:
    """Pairwise correlation of the normalised pillar scores across the panel.

    Row and column order is `src.score.PILLARS`. The diagonal is 1.0 where the
    pillar varies and None where it does not.
    """
    scaled = normalise(raw_pillars(panel, archetype), transform=transform)
    keys = sorted(scaled)
    columns = {p: [scaled[k][p] for k in keys] for p in PILLARS}
    return [
        [_pearson(columns[a], columns[b]) for b in PILLARS] for a in PILLARS
    ]


def summary(r: list[list[float | None]]) -> dict:
    """What the matrix implies, reduced to the figures the page states.

    `n_eff` counts only the pillars that vary: a constant pillar carries no
    direction of its own, and including it would inflate the count with a
    dimension nothing moves along.
    """
    varying = [i for i, p in enumerate(PILLARS) if r[i][i] is not None]
    k = len(varying)
    pairs = [
        (r[i][j], PILLARS[i], PILLARS[j])
        for ai, i in enumerate(varying)
        for j in varying[ai + 1:]
        if r[i][j] is not None
    ]
    if not pairs:
        return {
            "pillars": k, "pairs": 0, "mean_abs": None, "max_abs": None,
            "strong": 0, "strong_at": STRONG_AT, "n_eff": float(k),
            "strongest": [],
        }
    frobenius = sum(
        r[i][j] ** 2 for i in varying for j in varying if r[i][j] is not None
    )
    strongest = sorted(pairs, key=lambda t: -abs(t[0]))
    return {
        "pillars": k,
        "pairs": len(pairs),
        "mean_abs": sum(abs(v) for v, _, _ in pairs) / len(pairs),
        "max_abs": max(abs(v) for v, _, _ in pairs),
        "strong": sum(1 for v, _, _ in pairs if abs(v) >= STRONG_AT),
        "strong_at": STRONG_AT,
        # k^2 / ||R||_F^2 -- see the module docstring.
        "n_eff": (k * k) / frobenius if frobenius > 0 else float(k),
        "strongest": [
            {"a": a, "b": b, "r": v} for v, a, b in strongest[:3]
        ],
    }


def national_pillars(
    panel: dict[str, Market], archetype: str
) -> list[str]:
    """Pillars that take one value per country across the panel.

    This is the reason the correlation is as high as it is, and it is a fact
    about the sources rather than an opinion, so the page counts it rather
    than asserting it. A pillar in this list cannot separate two cities in the
    same country at all: whatever weight it is given, it moves them together.
    """
    raw = raw_pillars(panel, archetype)
    by_parent: dict[str, list[str]] = {}
    for k, m in panel.items():
        by_parent.setdefault(m.parent or k, []).append(k)
    out = []
    for p in PILLARS:
        if all(_constant([raw[k][p] for k in ks]) for ks in by_parent.values()):
            out.append(p)
    return out


def _constant(values: list[float]) -> bool:
    """Whether a group of observations is one value, to floating-point noise."""
    hi, lo = max(values), min(values)
    return (hi - lo) <= 1e-9 * max(1.0, abs(hi))


def main() -> None:
    from src.panel import build, with_centres

    cities = {
        k: m for k, m in with_centres(build()).items() if m.complete and m.is_city
    }
    print(f"{len(cities)} cities\n")
    for archetype in C.ARCHETYPES:
        r = matrix(cities, archetype)
        s = summary(r)
        print(C.ARCHETYPES[archetype]["label"])
        print("        " + "".join(f"{p[:6]:>7}" for p in PILLARS))
        for i, p in enumerate(PILLARS):
            cells = "".join(
                "      -" if r[i][j] is None else f"{r[i][j]:7.2f}"
                for j in range(len(PILLARS))
            )
            print(f"{p[:7]:<8}{cells}")
        print(
            f"  mean |r| {s['mean_abs']:.2f} · "
            f"{s['strong']} of {s['pairs']} pairs at or above {s['strong_at']} · "
            f"effective dimensionality {s['n_eff']:.1f} of {s['pillars']}"
        )
        print(
            "  strongest: "
            + ", ".join(
                f"{x['a']}~{x['b']} {x['r']:+.2f}" for x in s["strongest"]
            )
        )
        national = national_pillars(cities, archetype)
        print(
            f"  one value per country: {len(national)} of {len(PILLARS)} — "
            + ", ".join(national)
            + "\n"
        )


if __name__ == "__main__":
    main()
