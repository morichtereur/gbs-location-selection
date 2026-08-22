"""Assemble the four pillars into one panel, carrying provenance per cell.

Nothing is imputed. Where a source has no observation the cell stays empty and
the market is reported as incomplete, because a location study that quietly
fills a gap with a regional average is making up the number that decides it.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from src import config as C
from src.proximity import overlap_hours
from src import centres, population
from src.sources import eurostat, ilostat, postings, unesco, worldbank

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
    wage_cagr_lcu: float | None = None
    fx_drift: float | None = None
    depth: float | None = None
    cost_usd_aged: float | None = None
    cost_ppp_aged: float | None = None
    drift_used: float | None = None
    drift_measured: bool = False
    talent_proxy: float | None = None
    talent_year: int | None = None
    talent_employed: float | None = None
    talent_employed_year: int | None = None
    employment_components: dict[str, float] = field(default_factory=dict)
    talent_education: float | None = None
    tertiary_enrolment: float | None = None
    business_share_pct: float | None = None
    risk_score: float | None = None
    risk_year: int | None = None
    wgi: dict[str, tuple[float, float, float]] = field(default_factory=dict)
    timezone_overlap: float | None = None
    durability: float | None = None
    # Set only on city rows: which country row they were derived from, and the
    # regional cost index applied to it.
    parent: str | None = None
    region_index: float | None = None
    region_year: str | None = None
    employers: int | None = None
    postings_seen: int | None = None
    language_share: float | None = None
    languages: tuple = ()
    capability_raw: float | None = None
    capability_shrunk_from: float | None = None
    transactional_share: float | None = None
    judgment_share: float | None = None
    gcc_share: float | None = None
    ambiguous_share: float | None = None
    # Transactional share of the broad finance sample for this market: what a
    # posting the classifier admitted in error most likely is.
    contaminant_transactional: float | None = None
    contaminant_measured: bool = False
    employer_fragmentation: float | None = None
    postings_in_scope: int | None = None

    @property
    def cost_lag(self) -> int | None:
        return None if self.cost_year is None else REFERENCE_YEAR - self.cost_year

    @property
    def capability_counts(self) -> tuple[int, int]:
        """Successes and sample size behind the capability share.

        The share is an estimate from a finite sample — 88 postings in
        Switzerland — and carries a binomial standard error like any other.
        Returned so the Monte Carlo can resample it instead of treating this
        project's own measurement as exact while resampling everyone else's.
        """
        n = self.postings_in_scope or 0
        if self.is_city:
            # The shrunk share carries the weight of both samples, so the
            # binomial that generated it has the combined size. Redrawing at
            # the centre's own n would put back exactly the noise the
            # shrinkage removed.
            n = n + C.CAPABILITY_PRIOR_STRENGTH
        return round((self.transactional_share or 0.0) * n), n

    @property
    def is_city(self) -> bool:
        return self.parent is not None

    @property
    def cost_resolved(self) -> bool:
        """Whether cost is city-level or inherited from the country."""
        return self.region_index is not None

    @property
    def complete(self) -> bool:
        return all(
            v is not None
            for v in (
                self.cost_usd, self.talent_proxy, self.risk_score,
                self.transactional_share, self.timezone_overlap, self.durability,
                self.depth,
            )
        )

    def missing(self) -> list[str]:
        names = {
            "cost": self.cost_usd, "talent": self.talent_proxy,
            "risk": self.risk_score, "capability": self.transactional_share,
            "timezone": self.timezone_overlap, "durability": self.durability,
            "depth": self.depth,
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


def median_drift(panel: dict[str, Market]) -> float:
    """Median measured wage drift across markets that have enough history."""
    rates = sorted(m.wage_cagr for m in panel.values() if m.wage_cagr is not None)
    if not rates:
        return 0.0
    mid = len(rates) // 2
    return rates[mid] if len(rates) % 2 else (rates[mid - 1] + rates[mid]) / 2


def age(cost: float, lag: int | None, drift: float) -> float:
    """Carry an observation forward `lag` years at `drift` a year."""
    if not lag or lag <= 0:
        return cost
    return cost * (1.0 + drift) ** lag


def build() -> dict[str, Market]:
    wages = ilostat.load()
    history = ilostat.series()
    history_lcu = ilostat.series("CUR_TYPE_LCU")
    employment = ilostat.employment()
    talent = unesco.load()
    risk = worldbank.load()
    demand = postings.load_market_shares()
    contaminants = population.contaminant_shares()
    fallback_contaminant = (
        sorted(contaminants.values())[len(contaminants) // 2] if contaminants else 0.5
    )

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
            if iso2 in history_lcu:
                m.wage_cagr_lcu = _cagr(history_lcu[iso2], w["year"])
            if m.wage_cagr is not None and m.wage_cagr_lcu is not None:
                # What the dollar buyer saw, minus what local wages actually
                # did. A positive figure means the currency worked against the
                # buyer; a negative one means it cushioned local wage growth.
                m.fx_drift = m.wage_cagr - m.wage_cagr_lcu

        if iso2 in employment:
            e = employment[iso2]
            m.employment_components = {g: e[g] for g in C.ISCO_GROUPS}
            m.talent_employed = _blend(m.employment_components, C.WAGE_BLEND)
            m.talent_employed_year = e["year"]

        if iso2 in talent:
            t = talent[iso2]
            m.talent_education = t["business_scale_proxy"]
            m.talent_year = t["year"]
            m.tertiary_enrolment = t["tertiary_enrolment"]
            m.business_share_pct = t["business_share_pct"]

        # The pillar the score actually reads. Both constructions stay on the
        # record so the alternative can be run without refetching anything.
        m.talent_proxy = (
            m.talent_employed if C.TALENT_SOURCE == "employment" else m.talent_education
        )

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
            m.gcc_share = d["gcc_share"]
            m.language_share = d["language_share"]
            m.languages = tuple(d["languages"])
            m.contaminant_measured = iso2 in contaminants
            m.contaminant_transactional = contaminants.get(iso2, fallback_contaminant)
            m.ambiguous_share = d["ambiguous_share"]
            m.employer_fragmentation = d["employers"] / d["postings_in_scope"]
            m.depth = float(d["employers"])
            m.postings_in_scope = d["postings_in_scope"]

        m.timezone_overlap = overlap_hours(iso2)
        panel[iso2] = m

    # Point-adjusted cost for the baseline ranking. The Monte Carlo draws its
    # own drift rather than reusing this, so the uncertainty is not lost.
    fallback = median_drift(panel)
    for m in panel.values():
        if m.cost_usd is None:
            continue
        m.drift_used = m.wage_cagr if m.wage_cagr is not None else fallback
        m.drift_measured = m.wage_cagr is not None
        m.cost_usd_aged = (
            age(m.cost_usd, m.cost_lag, m.drift_used) if C.AGE_ADJUST else m.cost_usd
        )
        if m.cost_ppp is not None:
            m.cost_ppp_aged = (
                age(m.cost_ppp, m.cost_lag, m.drift_used) if C.AGE_ADJUST else m.cost_ppp
            )
        # Durability is the inverse of drift: a market whose wages have been
        # climbing fast is one whose arbitrage is closing. Stored as the
        # negative rate so that, like every other pillar, higher is better.
        m.durability = -m.drift_used
    return panel


def with_centres(panel: dict[str, Market]) -> dict[str, Market]:
    """Replace a country row with its evidenced GBS centres, where there are any.

    A centre row differs from its country on two pillars, not one:

    *Cost*, where Eurostat resolves the region — the national wage basket scaled
    by the region's cost index. Centres outside that coverage keep the national
    figure and are marked as unresolved.

    *Capability*, always — each centre carries its own transactional and judgment
    mix from the postings advertised there, rather than its country's average.
    These are small samples, down to five postings, so the shares are noisy; the
    Monte Carlo redraws them from their own binomial rather than pretending
    otherwise.

    Governance, talent, overlap and durability remain national. A centre row is
    a country row with two pillars sharpened, and should be read that way.
    """
    kept, _ = centres.survey()
    regions = eurostat.load()
    index_by_nuts = {r["nuts2"]: r for r in regions.values()}

    by_market: dict[str, list] = {}
    for centre in kept:
        by_market.setdefault(centre.market, []).append(centre)

    out: dict[str, Market] = {}
    for iso2, m in panel.items():
        if iso2 not in by_market:
            # No evidenced centre — either the feed carries no location for this
            # market, or it is a city already. Stays national, and says so.
            out[iso2] = m
            continue
        for centre in by_market[iso2]:
            row = replace(
                m,
                iso2=f"{iso2}:{centre.name}",
                name=centre.name,
                parent=iso2,
            )
            region = index_by_nuts.get(centre.nuts2) if centre.nuts2 else None
            if region:
                factor = region["index_vs_country"]
                row.region_index = factor
                row.region_year = region["year"]
                row.cost_usd = m.cost_usd * factor
                row.cost_usd_aged = (m.cost_usd_aged or m.cost_usd) * factor
                row.wage_components_usd = {
                    g: v * factor for g, v in m.wage_components_usd.items()
                }
            # Shrink toward the country, in proportion to how thin the
            # centre's own evidence is. See CAPABILITY_PRIOR_STRENGTH.
            k = C.CAPABILITY_PRIOR_STRENGTH
            n = centre.decided
            row.transactional_share = (
                n * centre.transactional_share + k * m.transactional_share
            ) / (n + k)
            row.judgment_share = (
                n * centre.judgment_share + k * m.judgment_share
            ) / (n + k)
            row.capability_raw = centre.transactional_share
            row.capability_shrunk_from = m.transactional_share
            row.gcc_share = centre.gcc_share
            row.language_share = centre.language_share
            row.languages = centre.languages
            row.postings_in_scope = centre.decided
            row.postings_seen = centre.postings
            row.employers = centre.employers
            out[row.iso2] = row
    return out
