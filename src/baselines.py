"""Origin markets for the wage-gap exhibit.

Exhibit 3 subtracts an origin's wage from each candidate city's. The origin
does not need seven pillars, a postings sample or a stability run — it needs
one number — so requiring it to be a scored market was a restriction with no
reason behind it, and it left the tool unable to answer "out of France".

These carry the same treatment as the panel's own cost pillar: the same three
ISCO groups blended in the same proportions, in USD, aged to the reference
year on the market's own measured wage trend where ILOSTAT has enough history
for one. They are never scored and never ranked.
"""

from __future__ import annotations

from src import config as C
from src.panel import REFERENCE_YEAR, _blend, _cagr, age, build, median_drift
from src.sources import ilostat


def load() -> list[dict]:
    """Every offerable origin, dearest first, each with a wage the exhibit can subtract."""
    wages = ilostat.load()
    history = ilostat.series()
    panel = build()
    fallback = median_drift(panel)

    out: list[dict] = []
    for key in C.BASELINE_MARKETS:
        m = panel.get(key)
        monthly = m and (m.cost_usd_aged or m.cost_usd)
        if monthly:
            out.append({
                "key": key, "label": C.MARKETS[key]["name"],
                "monthly": monthly, "year": m.cost_year, "scored": True,
                # Carried so Exhibit 3 can project the origin forward at its own
                # rate rather than at the destination's. `driftMeasured` is what
                # lets the exhibit refuse to project rather than fall back to a
                # median and call it a forecast.
                "drift": m.wage_cagr,
                "driftMeasured": m.wage_cagr is not None,
            })

    for key, meta in C.BASELINE_EXTRA.items():
        w = wages.get(key)
        if not w:
            continue
        components = {
            g: w[f"usd_{g[-1]}"] for g in C.ISCO_GROUPS if f"usd_{g[-1]}" in w
        }
        if len(components) != len(C.ISCO_GROUPS):
            continue
        blended = _blend(components, C.WAGE_BLEND)
        drift = _cagr(history[key], w["year"]) if key in history else None
        lag = REFERENCE_YEAR - w["year"]
        out.append({
            "key": key, "label": meta["name"],
            "monthly": age(blended, lag, drift if drift is not None else fallback)
                       if C.AGE_ADJUST else blended,
            "year": w["year"], "scored": False,
            "drift": drift,
            "driftMeasured": drift is not None,
        })

    return sorted(out, key=lambda b: -b["monthly"])


def main() -> None:
    for b in load():
        mark = "" if b["scored"] else "  (origin only)"
        print(f"{b['label']:16}{b['monthly']:8.0f} USD/month   {b['year']}{mark}")


if __name__ == "__main__":
    main()
