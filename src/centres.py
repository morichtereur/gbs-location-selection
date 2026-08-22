"""Which locations are actually GBS centres, read off the hiring market.

The alternative was a list of cities somebody believes are GBS hubs. That is an
assertion, and this project does not run on assertions. A location qualifies
here if GBS and finance-operations roles are genuinely advertised there by
several distinct employers — the same postings snapshot the capability pillar
already uses, asked a different question.

What the evidence cannot do:

*Two markets have no location data at all.* The sources for the United Kingdom
and South Africa return no location string, so neither market can be resolved
below national level. That is a gap in the feed, not a finding about those
markets, and they stay national.

*Singapore is a city already*, so the question does not arise there.

*Counts are small.* Pune is eleven postings. The city-level capability shares
that come out of this carry a wide binomial error, which is why the Monte Carlo
resamples them rather than treating them as exact.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass

import duckdb

from src import config as C

# Location strings that name a country rather than a place inside it.
COUNTRY_ONLY = {
    "polska", "poland", "india", "bhārat", "deutschland", "germany",
    "méxico", "mexico", "south africa", "singapore", "singapur",
    "nederland", "netherlands", "españa", "spain", "united kingdom", "uk",
    "schweiz", "switzerland", "suisse", "svizzera",
}


@dataclass
class Centre:
    market: str
    name: str
    postings: int
    employers: int
    transactional_share: float
    judgment_share: float
    bpo_share: float
    nuts2: str | None

    @property
    def cost_resolved(self) -> bool:
        return self.nuts2 is not None


def _org_type():
    path = C.POSTINGS_DB.parent.parent / "src" / "orgtype.py"
    spec = importlib.util.spec_from_file_location("shift_orgtype", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.org_type


def _clean(location: str | None) -> str | None:
    if not location:
        return None
    city = location.split(",")[0].strip()
    if len(city) < 2 or city.lower() in COUNTRY_ONLY:
        return None
    return C.CITY_ALIASES.get(city.lower(), city)


def survey() -> tuple[list[Centre], list[Centre]]:
    """Return (centres that clear both thresholds, those that do not)."""
    org_type = _org_type()
    con = duckdb.connect(str(C.POSTINGS_DB), read_only=True)
    rows = con.execute(
        """
        SELECT p.country, p.location, p.company, l.label
        FROM postings p JOIN labels l USING (id)
        WHERE l.label IN ('transactional', 'judgment', 'agent_ops')
        """
    ).fetchall()
    con.close()

    agg: dict[tuple[str, str], dict] = {}
    for country, location, company, label in rows:
        if country not in C.MARKETS:
            continue
        if org_type(company) == "advisory":
            continue
        city = _clean(location)
        if not city:
            continue
        rec = agg.setdefault(
            (country, city),
            {"n": 0, "transactional": 0, "judgment": 0, "bpo": 0, "firms": set()},
        )
        rec["n"] += 1
        if label in ("transactional", "judgment"):
            rec[label] += 1
        rec["bpo"] += org_type(company) == "bpo"
        rec["firms"].add((company or "").strip().lower())

    kept: list[Centre] = []
    dropped: list[Centre] = []
    for (market, city), rec in agg.items():
        centre = Centre(
            market=market,
            name=city,
            postings=rec["n"],
            employers=len(rec["firms"]),
            transactional_share=rec["transactional"] / rec["n"],
            judgment_share=rec["judgment"] / rec["n"],
            bpo_share=rec["bpo"] / rec["n"],
            nuts2=C.CENTRE_NUTS.get(city),
        )
        target = (
            kept
            if centre.postings >= C.MIN_CENTRE_POSTINGS
            and centre.employers >= C.MIN_CENTRE_EMPLOYERS
            else dropped
        )
        target.append(centre)

    kept.sort(key=lambda c: (c.market, -c.postings))
    dropped.sort(key=lambda c: -c.postings)
    return kept, dropped


def main() -> None:
    kept, dropped = survey()
    print(f"Evidenced GBS centres (>= {C.MIN_CENTRE_POSTINGS} postings, "
          f">= {C.MIN_CENTRE_EMPLOYERS} employers): {len(kept)}\n")
    print(f"{'mkt':5}{'centre':20}{'posts':>6}{'firms':>7}{'trans':>8}{'cost':>16}")
    for c in kept:
        cost = c.nuts2 if c.nuts2 else "national"
        print(f"{c.market:5}{c.name[:19]:20}{c.postings:6}{c.employers:7}"
              f"{c.transactional_share:8.0%}{cost:>16}")
    near = [d for d in dropped if d.postings >= C.MIN_CENTRE_POSTINGS]
    print(f"\nExcluded despite volume — too few employers to be a labour market: {len(near)}")
    for d in near:
        print(f"  {d.market}  {d.name[:26]:28}{d.postings:3} postings from "
              f"{d.employers} employer{'s' if d.employers != 1 else ''}")


if __name__ == "__main__":
    main()
