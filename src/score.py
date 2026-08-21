"""Normalise the panel and score it under a declared weighting.

Two choices here decide more than they look like they do, so both are stated
rather than defaulted quietly:

*Transform.* Cost spans 24x across this panel and the talent proxy spans 160x.
Min-max normalising either one on a linear scale collapses eight markets into
a rounding error against India's education system, which answers a question
nobody asked — a location decision cares about the order of magnitude of a
labour pool, not its linear headcount. Both are therefore log-scaled first.
Risk is already a bounded 0-100 index and capability is already a share, so
both are normalised linearly. `transform="linear"` runs the alternative, and
the difference is reported rather than argued about.

*Direction.* Cost is the only pillar where less is better. Encoded once, here.
"""

from __future__ import annotations

import math

from src import config as C
from src.panel import Market

PILLARS = ("cost", "talent", "risk", "capability")
LOWER_IS_BETTER = {"cost"}
LOG_SCALED = {"cost", "talent"}


def raw_pillars(
    panel: dict[str, Market],
    archetype: str,
    *,
    wgi_draw: dict[str, dict[str, float]] | None = None,
    cost_draw: dict[str, float] | None = None,
) -> dict[str, dict[str, float]]:
    """Pillar values per market, before normalisation.

    `wgi_draw` and `cost_draw` let a Monte Carlo pass in resampled inputs
    without this module knowing anything about how they were drawn.
    """
    metric = C.ARCHETYPES[archetype]["capability_metric"]
    out: dict[str, dict[str, float]] = {}
    for iso2, m in panel.items():
        if not m.complete:
            continue
        if wgi_draw and iso2 in wgi_draw:
            drawn = wgi_draw[iso2]
            risk = sum(drawn[d] for d in C.WGI_IN_COMPOSITE if d in drawn) / len(
                [d for d in C.WGI_IN_COMPOSITE if d in drawn]
            )
        else:
            risk = m.risk_score
        out[iso2] = {
            "cost": (cost_draw or {}).get(iso2, m.cost_usd),
            "talent": m.talent_proxy,
            "risk": risk,
            "capability": getattr(m, metric),
        }
    return out


def normalise(
    raw: dict[str, dict[str, float]], *, transform: str = "log"
) -> dict[str, dict[str, float]]:
    """Min-max each pillar to 0-1, higher always meaning more attractive."""
    scaled: dict[str, dict[str, float]] = {k: {} for k in raw}
    for pillar in PILLARS:
        values = {k: v[pillar] for k, v in raw.items()}
        if transform == "log" and pillar in LOG_SCALED:
            values = {k: math.log(v) for k, v in values.items() if v > 0}
        lo, hi = min(values.values()), max(values.values())
        span = hi - lo
        for k, v in values.items():
            unit = 0.5 if span == 0 else (v - lo) / span
            scaled[k][pillar] = 1.0 - unit if pillar in LOWER_IS_BETTER else unit
    return scaled


def score(
    scaled: dict[str, dict[str, float]], weights: dict[str, float]
) -> dict[str, float]:
    total = sum(weights.values())
    return {
        k: sum(weights[p] * v[p] for p in PILLARS) / total for k, v in scaled.items()
    }


def rank(scores: dict[str, float]) -> list[str]:
    """Markets best first. Ties broken by name so a run is reproducible."""
    return [k for k, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))]
