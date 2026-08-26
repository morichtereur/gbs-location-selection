"""Where every figure came from and when it was observed.

The page carried an as-of date as a hand-typed string — `ASOF = "August 2026"`
— beside vintages that were also typed by hand. Both were right when they were
written, and neither had any connection to the data underneath them: a refetch
would move the evidence and leave the date saying whatever it said last. A
provenance line that cannot go stale is worth more than one that is merely
accurate today, so this reads the dates back out of the sources.

Three things are recovered, and each answers a question a reviewer asks:

*When was this seen?* The fetch records a `snapshots` row per run — the date,
the markets it covered, how many search terms and how deep it paged. One row
means one snapshot, and a study resting on one snapshot has to say so rather
than let a reader assume a series.

*What was scraped?* The board, the terms, the page depth and the markets. The
terms in particular decide the sample: this study's population is what those
five phrases returned, not "GBS postings" in the abstract.

*How old is each statistical series?* The observation year is already carried
per market on the panel for the vintage adjustment. Reporting the span from
those values means a market with a 2020 wage cannot hide inside a sentence
that says 2025.

Everything degrades to None rather than raising. A fresh clone has no postings
database, and the honest output there is "unavailable", not a traceback or a
remembered date.
"""

from __future__ import annotations

from datetime import date

import duckdb

from src import config as C
from src.gbs_fetch import DB_PATH, LOCAL_TERMS, MAX_PAGES, SEARCH_TERMS

MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def _pretty(d: date | str | None) -> str | None:
    if d is None:
        return None
    if isinstance(d, str):
        try:
            d = date.fromisoformat(d[:10])
        except ValueError:
            return d
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def postings_snapshot() -> dict | None:
    """The fetch's own record of what it collected, and when.

    Returns None where no database has been fetched yet, so the caller can say
    the sample is unavailable rather than print a date nothing supports.
    """
    if not DB_PATH.exists():
        return None
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        snaps = con.execute(
            "SELECT CAST(snapshot AS VARCHAR), markets, max_pages, terms "
            "FROM main.snapshots ORDER BY snapshot"
        ).fetchall()
        total = con.execute("SELECT count(*) FROM main.postings").fetchone()[0]
    except duckdb.CatalogException:
        return None
    finally:
        con.close()
    if not snaps:
        return None

    latest = snaps[-1]
    markets = [m for m in (latest[1] or "").split(",") if m]
    return {
        "date": latest[0],
        "dateLabel": _pretty(latest[0]),
        # One row is one point in time. The distinction decides whether the
        # study may speak about direction at all, so it is carried explicitly
        # rather than inferred from a list length at the call site.
        "count": len(snaps),
        "isSnapshot": len(snaps) == 1,
        "all": [s[0] for s in snaps],
        "markets": markets,
        "marketCount": len(markets),
        "maxPages": latest[2] if latest[2] is not None else MAX_PAGES,
        "termCount": latest[3] if latest[3] is not None else len(SEARCH_TERMS),
        "postingsFetched": total,
        "board": "Adzuna",
        # The terms are the sample definition, not a detail of it.
        "terms": list(SEARCH_TERMS),
        "localTerms": {k: list(v) for k, v in LOCAL_TERMS.items()},
    }


def contaminant_sample() -> dict | None:
    """The sibling study's broad finance sample, used to model classifier error.

    A second database, fetched on its own date. It never enters the ranking,
    but it does enter the stability column through the contaminant shares, so a
    reader tracing a number should be able to find it.
    """
    if not C.POSTINGS_DB.exists():
        return None
    con = duckdb.connect(str(C.POSTINGS_DB), read_only=True)
    try:
        row = con.execute(
            "SELECT max(fetched_at), count(*) FROM main.postings"
        ).fetchone()
    except duckdb.CatalogException:
        return None
    finally:
        con.close()
    if not row or not row[0]:
        return None
    return {
        "date": row[0][:10],
        "dateLabel": _pretty(row[0][:10]),
        "postings": row[1],
        "repo": "gbs-agentic-shift",
    }


def _span(years: list[int]) -> str | None:
    """A vintage span from observation years, or None where nothing carries one."""
    seen = sorted({y for y in years if y})
    if not seen:
        return None
    return str(seen[0]) if seen[0] == seen[-1] else f"{seen[0]}–{seen[-1]}"


def vintages(panel: dict) -> dict[str, str | None]:
    """Observation-year spans read off the panel rather than typed by hand.

    Keyed by the pillar labels the sources card uses, so a source whose year
    moves after a refetch moves on the page too.
    """
    rows = list(panel.values())
    return {
        "Cost": _span([m.cost_year for m in rows]),
        "Talent": _span([m.talent_employed_year for m in rows]),
        "Governance": _span([m.risk_year for m in rows]),
        # Measured across a window reaching up to ten years back, not just the
        # cost observation year, so it is read off the window itself.
        "Durability": _span([
            y for m in rows if m.drift_window for y in m.drift_window
        ]),
        # Eurostat's regional index carries its own year, and only the cities
        # it resolves have one.
        "Region": _span([
            int(m.region_year) for m in rows
            if m.region_year and str(m.region_year).isdigit()
        ]),
    }


def as_of() -> str:
    """The date the page leads with: the postings snapshot, or a stated absence."""
    snap = postings_snapshot()
    return snap["dateLabel"] if snap else "sample not fetched"


def main() -> None:
    snap = postings_snapshot()
    if not snap:
        print(f"no postings snapshot at {DB_PATH}")
    else:
        print(f"postings snapshot   {snap['dateLabel']}")
        print(f"  snapshots held    {snap['count']}"
              f"{'  (one point in time)' if snap['isSnapshot'] else ''}")
        print(f"  board             {snap['board']}")
        print(f"  markets           {snap['marketCount']}: {','.join(snap['markets'])}")
        print(f"  search terms      {snap['termCount']} "
              f"({', '.join(snap['terms'])})")
        for market, terms in snap["localTerms"].items():
            print(f"                    +{market}: {', '.join(terms)}")
        print(f"  page depth        {snap['maxPages']}")
        print(f"  postings fetched  {snap['postingsFetched']:,}")

    other = contaminant_sample()
    if other:
        print(f"\ncontaminant sample  {other['dateLabel']} "
              f"({other['postings']:,} postings, {other['repo']})")

    from src.panel import build, with_centres

    # The city panel, not the country one: Eurostat's regional index only
    # exists on the rows that carry a region, so reporting off country rows
    # would call it unavailable when the page is showing it.
    print("\nstatistical series")
    for name, span in vintages(with_centres(build())).items():
        print(f"  {name:<16}  {span or 'unavailable'}")


if __name__ == "__main__":
    main()
