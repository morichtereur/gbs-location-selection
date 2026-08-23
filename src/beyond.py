"""The six established locations the postings feed cannot reach.

Manila is the first name a GBS room says, and the study could not price it at
all. That was a gap in the tool, not a fact about Manila: five of the seven
pillars come from sources that cover every country alike, and only the two
built from job postings stop at Adzuna's country list.

So those five are reported here — wage, employed stock in the relevant
occupations, governance with its published interval, and hours shared with
the headquarters — and the two that are missing are named as missing.

Nothing here is scored, normalised or ranked. A score over five of seven
pillars would render beside the ranked cities' scores and would not mean the
same thing, and no weighting makes a market with no capability evidence
comparable to one with it. The row says what is known and stops.
"""

from __future__ import annotations

from src import config as C
from src.panel import REFERENCE_YEAR, _blend, _cagr, age, build, median_drift
from src.proximity import hq_offset
from src.sources import ilostat, worldbank


def load(hq: str | None = None) -> list[dict]:
    """One row per unreachable market, dearest first."""
    wages = ilostat.load()
    history = ilostat.series()
    employment = ilostat.employment()
    risk = worldbank.load()
    fallback = median_drift(build())
    shift_base = hq_offset(hq or C.HQ)

    out: list[dict] = []
    for key, meta in C.BEYOND_SAMPLE.items():
        w = wages.get(key)
        if not w:
            continue
        parts = {g: w[f"usd_{g[-1]}"] for g in C.ISCO_GROUPS if f"usd_{g[-1]}" in w}
        if len(parts) != len(C.ISCO_GROUPS):
            continue
        drift = _cagr(history[key], w["year"]) if key in history else None
        lag = REFERENCE_YEAR - w["year"]

        emp = employment.get(key) or {}
        # The loader keys the stock by the ISCO group code itself.
        stock = sum(emp[g] for g in C.ISCO_GROUPS if g in emp) or None

        r = risk.get(key) or {}
        dims = [r[f"{d}_score"] for d in C.WGI_IN_COMPOSITE if f"{d}_score" in r]

        # Overlap is arithmetic on a UTC offset, so it needs no source at all.
        shift = abs(meta["utc"] - shift_base)
        lo, hi = C.WORKING_DAY
        overlap = max(0.0, (hi - lo) - shift)

        out.append({
            "key": key,
            "market": meta["name"],
            "city": meta["city"],
            "cost": age(_blend(parts, C.WAGE_BLEND), lag,
                        drift if drift is not None else fallback)
                    if C.AGE_ADJUST else _blend(parts, C.WAGE_BLEND),
            "costYear": w["year"],
            "talent": stock,
            "talentYear": (emp or {}).get("year"),
            "risk": sum(dims) / len(dims) if dims else None,
            "riskYear": r.get("year"),
            "overlap": overlap,
            "driftMeasured": drift is not None,
        })

    return sorted(out, key=lambda x: -(x["cost"] or 0))


def main() -> None:
    rows = load()
    print(f"{'City':16}{'Market':14}{'USD/mo':>9}{'Talent':>12}{'Gov':>7}{'Overlap':>9}")
    for r in rows:
        talent = f"{r['talent']/1e6:.1f}m" if r["talent"] else "—"
        print(f"{r['city']:16}{r['market']:14}{r['cost']:9.0f}{talent:>12}"
              f"{(r['risk'] or 0):7.0f}{r['overlap']:8.1f}h")
    print("\nCapability and employer depth are not available for any of these:")
    print("Adzuna has no endpoint, and another feed's counts would not be comparable.")


if __name__ == "__main__":
    main()
