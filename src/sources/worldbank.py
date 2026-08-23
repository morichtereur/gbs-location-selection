"""Operating risk from the World Bank's Worldwide Governance Indicators.

WGI publishes each governance dimension as a 0-100 score *and* the bounds of
its own 90% confidence interval. The interval is the part a scorecard normally
throws away, and it is the part that says how much of a gap between two
countries is real. Both are pulled.

Indicator IDs were renamed in the 2025 methodology revision (PV.EST became
GOV_WGI_PV.SC and friends); the old codes now return "indicator not found".
"""

from __future__ import annotations

import json

from src import config as C
from src.sources._http import fetch

BASE = "https://api.worldbank.org/v2"


def _series(indicator: str) -> dict[str, tuple[int, float]]:
    iso3 = ";".join(
        [m["iso3"] for m in C.MARKETS.values()]
        + [m["iso3"] for m in C.BEYOND_SAMPLE.values()]
    )
    url = (
        f"{BASE}/country/{iso3}/indicator/{indicator}"
        f"?format=json&source=3&per_page=500"
    )
    payload = json.loads(fetch(url, suffix=".json"))
    if len(payload) < 2 or not payload[1]:
        raise RuntimeError(f"no data returned for {indicator}")
    latest: dict[str, tuple[int, float]] = {}
    for row in payload[1]:
        if row["value"] is None:
            continue
        iso2 = C.ISO3_TO_ISO2.get(row["countryiso3code"])
        if not iso2:
            continue
        year = int(row["date"])
        if iso2 not in latest or year > latest[iso2][0]:
            latest[iso2] = (year, float(row["value"]))
    return latest


def load() -> dict[str, dict]:
    """Per market: each dimension's score and the width of its 90% interval."""
    out: dict[str, dict] = {}
    for dim in C.WGI_DIMENSIONS:
        score = _series(f"GOV_WGI_{dim}.SC")
        lower = _series(f"GOV_WGI_{dim}.SC_LB")
        upper = _series(f"GOV_WGI_{dim}.SC_UB")
        for iso2, (year, value) in score.items():
            rec = out.setdefault(iso2, {"year": year, "source": "World Bank WGI"})
            rec[f"{dim}_score"] = value
            if iso2 in lower and iso2 in upper:
                rec[f"{dim}_lo"] = lower[iso2][1]
                rec[f"{dim}_hi"] = upper[iso2][1]
    return out
