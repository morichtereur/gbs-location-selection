"""Talent scale from the UNESCO Institute for Statistics.

UIS publishes no count of business graduates. It publishes total tertiary
enrolment and the share of graduates coming out of Business, Administration and
Law. Their product is a *scale proxy* — it says how large the relevant
education system is, not how many accountants graduate. Called a proxy
everywhere in this codebase for that reason.
"""

from __future__ import annotations

import json

from src import config as C
from src.sources._http import fetch

BASE = "https://api.uis.unesco.org/api/public/data/indicators"


def _url() -> str:
    units = "&".join(f"geoUnit={m['iso3']}" for m in C.MARKETS.values())
    inds = f"indicator={C.UIS_ENROLMENT}&indicator={C.UIS_BUSINESS_SHARE}"
    return f"{BASE}?{inds}&{units}&start=2015&end=2026"


def load() -> dict[str, dict]:
    records = json.loads(fetch(_url(), suffix=".json"))["records"]
    latest: dict[tuple[str, str], tuple[int, float]] = {}
    for r in records:
        if r["value"] is None:
            continue
        iso2 = C.ISO3_TO_ISO2.get(r["geoUnit"])
        if not iso2:
            continue
        key = (r["indicatorId"], iso2)
        year = int(r["year"])
        if key not in latest or year > latest[key][0]:
            latest[key] = (year, float(r["value"]))

    out: dict[str, dict] = {}
    for iso2 in C.MARKETS:
        enrol = latest.get((C.UIS_ENROLMENT, iso2))
        share = latest.get((C.UIS_BUSINESS_SHARE, iso2))
        if not enrol or not share:
            continue
        out[iso2] = {
            # The two components carry different years often enough that
            # reporting one "year" for the pillar would be a small lie.
            "enrolment_year": enrol[0],
            "share_year": share[0],
            "year": min(enrol[0], share[0]),
            "tertiary_enrolment": enrol[1],
            "business_share_pct": share[1],
            "business_scale_proxy": enrol[1] * share[1] / 100.0,
            "source": "UNESCO UIS",
        }
    return out
