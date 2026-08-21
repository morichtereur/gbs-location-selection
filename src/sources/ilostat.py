"""Wage cost from ILOSTAT, via the SDMX API.

The bulk-download paths in ILOSTAT's own documentation 404 as of this writing;
the SDMX service at sdmx.ilo.org is the route that works. Recorded here because
the next person to try the documented path will lose an hour to it.
"""

from __future__ import annotations

import csv
import io

from src import config as C
from src.sources._http import fetch

BASE = "https://sdmx.ilo.org/rest/data/ILO"
ACCEPT = {"Accept": "application/vnd.sdmx.data+csv;version=1.0.0"}


def _url() -> str:
    key = "+".join(m["iso3"] for m in C.MARKETS.values())
    # Six dimensions: REF_AREA.FREQ.MEASURE.SEX.OCU.CUR — the trailing dots
    # are wildcards, filtered down after the pull.
    return f"{BASE},{C.ILO_DATAFLOW}/{key}....."


def load() -> dict[str, dict]:
    """Latest available earnings per market, per ISCO group, per currency.

    Returns one record per market carrying the observation year, so a stale
    market is visible as stale rather than blended into a ranking as if it
    were current.
    """
    body = fetch(_url(), ACCEPT, suffix=".csv")
    rows = [
        r for r in csv.DictReader(io.StringIO(body))
        if r["SEX"] == "SEX_T"
        and r["OCU"] in C.ISCO_GROUPS
        and r["CUR"] in C.CURRENCIES
        and r["OBS_VALUE"]
    ]

    # Group by market, then take the most recent year for which the whole
    # basket is present. Taking the latest year per ISCO group independently
    # would silently mix vintages inside a single market's wage basket.
    by_market: dict[str, dict[tuple[str, str, int], float]] = {}
    for r in rows:
        iso2 = C.ISO3_TO_ISO2.get(r["REF_AREA"])
        if not iso2:
            continue
        key = (r["OCU"], r["CUR"], int(r["TIME_PERIOD"]))
        by_market.setdefault(iso2, {})[key] = float(r["OBS_VALUE"])

    out: dict[str, dict] = {}
    for iso2, obs in by_market.items():
        years = sorted({y for _, _, y in obs}, reverse=True)
        for year in years:
            complete = all(
                (g, cur, year) in obs
                for g in C.ISCO_GROUPS
                for cur in C.CURRENCIES
            )
            if complete:
                out[iso2] = {
                    "year": year,
                    "source": "ILOSTAT SDMX / " + C.ILO_DATAFLOW,
                    **{
                        f"{cur.replace('CUR_TYPE_', '').lower()}_{g[-1]}": obs[(g, cur, year)]
                        for g in C.ISCO_GROUPS
                        for cur in C.CURRENCIES
                    },
                }
                break
    return out


def series() -> dict[str, dict[int, float]]:
    """Blended USD wage basket per market per year, for measuring wage drift.

    Three of the ten markets have earnings observations several years old. The
    honest way to age them is each market's own measured trend rather than an
    assumed inflation number, so the history is pulled from the same response.
    """
    body = fetch(_url(), ACCEPT, suffix=".csv")
    obs: dict[str, dict[tuple[int, str], float]] = {}
    for r in csv.DictReader(io.StringIO(body)):
        if (
            r["SEX"] != "SEX_T"
            or r["CUR"] != "CUR_TYPE_USD"
            or r["OCU"] not in C.ISCO_GROUPS
            or not r["OBS_VALUE"]
        ):
            continue
        iso2 = C.ISO3_TO_ISO2.get(r["REF_AREA"])
        if not iso2:
            continue
        obs.setdefault(iso2, {})[(int(r["TIME_PERIOD"]), r["OCU"])] = float(r["OBS_VALUE"])

    out: dict[str, dict[int, float]] = {}
    for iso2, o in obs.items():
        years = sorted({y for y, _ in o})
        for year in years:
            if all((year, g) in o for g in C.ISCO_GROUPS):
                out.setdefault(iso2, {})[year] = sum(
                    C.WAGE_BLEND[g] * o[(year, g)] for g in C.ISCO_GROUPS
                )
    return out
