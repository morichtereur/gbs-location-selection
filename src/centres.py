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
# Every spelling a feed uses for a whole country, including the local one. The
# Portuguese "Brasil" was missing and produced a GBS centre called Brasil.
COUNTRY_ONLY = {
    "polska", "poland", "india", "bhārat", "deutschland", "germany",
    "méxico", "mexico", "south africa", "singapore", "singapur",
    "nederland", "netherlands", "españa", "spain", "united kingdom", "uk",
    "schweiz", "switzerland", "suisse", "svizzera",
    "brasil", "brazil", "grande são paulo", "grande sao paulo",
}


@dataclass
class Centre:
    market: str
    name: str
    postings: int
    decided: int
    employers: int
    transactional_share: float
    judgment_share: float
    gcc_share: float
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
    """Return (centres that clear both thresholds, those that do not).

    Surveys the GBS/GCC population, not the broad finance-operations sample.
    That is the whole point of the filter: Warsaw led the broad sample with 76
    postings because it is Poland's largest finance job market, while Kraków
    leads the GBS/GCC one because it is Poland's largest *shared-services*
    market. The two questions have different answers.
    """
    from src.population import load, shares

    postings = load()
    grouped: dict[tuple[str, str], list] = {}
    for posting in postings:
        if posting.country not in C.MARKETS or not posting.city:
            continue
        grouped.setdefault((posting.country, posting.city), []).append(posting)

    kept: list[Centre] = []
    dropped: list[Centre] = []
    for (market, city), rows in grouped.items():
        stats = shares(rows)
        if stats["n"] == 0:
            continue
        # Qualifying as a GBS city and measuring its work mix are two different
        # questions and were wrongly answered by one number. A location is a
        # centre if GBS roles are advertised there by several employers — that
        # is the delivery classifier's job. Whether the *work-family* classifier
        # could also read a posting is irrelevant to whether the city exists,
        # and coupling them hid São Paulo, Johannesburg, Chennai and Łódź.
        centre = Centre(
            market=market,
            name=city,
            postings=len(rows),
            decided=stats["n"],
            employers=len({r.company for r in rows}),
            transactional_share=stats["transactional_share"],
            judgment_share=stats["judgment_share"],
            gcc_share=stats["gcc_share"],
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
