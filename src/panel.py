"""Assemble the four pillars into one panel, carrying provenance per cell.

Nothing is imputed. Where a source has no observation the cell stays empty and
the market is reported as incomplete, because a location study that quietly
fills a gap with a regional average is making up the number that decides it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src import config as C
from src.sources import ilostat, postings, unesco, worldbank

# The panel is a point-in-time read. Vintage lag is measured against the year
# the analysis is run, not against the freshest market, so a uniformly stale
# panel still reports itself as stale.
REFERENCE_YEAR = 2026


@dataclass
class Market:
    iso2: str
    name: str
    market_type: str
    cost_usd: float | None = None
    cost_ppp: float | None = None
    cost_year: int | None = None
    wage_components_usd: dict[str, float] = field(default_factory=dict)
    wage_cagr: float | None = None
    talent_proxy: float | None = None
    talent_year: int | None = None
    tertiary_enrolment: float | None = None
    business_share_pct: float | None = None
    risk_score: float | None = None
    risk_year: int | None = None
    wgi: dict[str, tuple[float, float, float]] = field(default_factory=dict)
    transactional_share: float | None = None
    judgment_share: float | None = None
    bpo_share: float | None = None
    employer_fragmentation: float | None = None
    postings_in_scope: int | None = None

    @property
    def cost_lag(self) -> int | None:
        return None if self.cost_year is None else REFERENCE_YEAR - self.cost_year

    @property
    def complete(self) -> bool:
        return all(
            v is not None
            for v in (
                self.cost_usd, self.talent_proxy, self.risk_score,
                self.transactional_share,
            )
        )

    def missing(self) -> list[str]:
        names = {
            "cost": self.cost_usd, "talent": self.talent_proxy,
            "risk": self.risk_score, "capability": self.transactional_share,
        }
        return [k for k, v in names.items() if v is None]


def _blend(components: dict[str, float], blend: dict[str, float]) -> float:
    total = sum(blend.values())
    return sum(blend[g] * components[g] for g in blend) / total


def _cagr(hist: dict[int, float], base_year: int) -> float | None:
    """Compound annual growth in the market's own blended USD wage.

    Measured over the longest window ending at the latest observation, capped
    at ten years so a single currency crisis two decades back does not set the
    rate. Returns None when there is not enough history to measure one.
    """
    years = sorted(hist)
    if len(years) < 3:
        return None
    end = max(years)
    candidates = [y for y in years if end - y >= 3 and end - y <= 10]
    if not candidates:
        return None
    start = min(candidates)
    span = end - start
    if hist[start] <= 0 or span <= 0:
        return None
    return (hist[end] / hist[start]) ** (1 / span) - 1


def build() -> dict[str, Market]:
    wages = ilostat.load()
    history = ilostat.series()
    talent = unesco.load()
    risk = worldbank.load()
    demand = postings.load()

    panel: dict[str, Market] = {}
    for iso2, meta in C.MARKETS.items():
        m = Market(iso2=iso2, name=meta["name"], market_type=meta["type"])

        if iso2 in wages:
            w = wages[iso2]
            m.cost_year = w["year"]
            m.wage_components_usd = {g: w[f"usd_{g[-1]}"] for g in C.ISCO_GROUPS}
            m.cost_usd = _blend(m.wage_components_usd, C.WAGE_BLEND)
            m.cost_ppp = _blend(
                {g: w[f"ppp_{g[-1]}"] for g in C.ISCO_GROUPS}, C.WAGE_BLEND
            )
            if iso2 in history:
                m.wage_cagr = _cagr(history[iso2], w["year"])

        if iso2 in talent:
            t = talent[iso2]
            m.talent_proxy = t["business_scale_proxy"]
            m.talent_year = t["year"]
            m.tertiary_enrolment = t["tertiary_enrolment"]
            m.business_share_pct = t["business_share_pct"]

        if iso2 in risk:
            r = risk[iso2]
            m.risk_year = r["year"]
            m.wgi = {
                d: (r[f"{d}_score"], r.get(f"{d}_lo", r[f"{d}_score"]),
                    r.get(f"{d}_hi", r[f"{d}_score"]))
                for d in C.WGI_DIMENSIONS
                if f"{d}_score" in r
            }
            in_composite = [m.wgi[d][0] for d in C.WGI_IN_COMPOSITE if d in m.wgi]
            if in_composite:
                m.risk_score = sum(in_composite) / len(in_composite)

        if iso2 in demand:
            d = demand[iso2]
            m.transactional_share = d["transactional_share"]
            m.judgment_share = d["judgment_share"]
            m.bpo_share = d["bpo_share"]
            m.employer_fragmentation = d["employer_fragmentation"]
            m.postings_in_scope = d["postings_in_scope"]

        panel[iso2] = m
    return panel
