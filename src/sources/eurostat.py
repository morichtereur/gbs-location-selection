"""City-level labour cost, for the four markets where it exists.

The national panel compares Poland to Spain. A site selection does not choose
Poland; it chooses Wrocław or Katowice or Warsaw, and those are not the same
number. Eurostat's regional national accounts resolve that for EU markets:
compensation of employees divided by the number of employees, in the
professional-and-administrative-services sector, by NUTS-2 region.

Hours worked would have been the better denominator — it nets out regional
differences in part-time working — but Germany does not publish regional hours
in this collection. Using hours for three countries and heads for Germany would
have made the four indices incomparable, so all four use heads.

Three limits define what this layer can be used for.

*It covers four of ten markets.* Poland, Germany, the Netherlands and Spain.
Switzerland is absent from Eurostat's regional accounts entirely, the UK left
the collection, and India, Mexico, South Africa and Singapore were never in it.
Pune cannot be placed beside Wrocław on this evidence, and is not.

*It is a different measure from the national panel.* Annual compensation per
employee including employer contributions is not gross monthly earnings by
occupation.
Splicing the two would compare unlike things, so this layer is only ever used
as an **index against its own country mean** — how far a region sits from the
national figure the panel already uses.

*A NUTS-2 region is not a city.* Dolnośląskie is not Wrocław. The region is
named for the city a GBS programme would actually be considering, but it
carries that city's whole hinterland with it.
"""

from __future__ import annotations

import json

from src import config as C
from src.sources._http import fetch

BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
# Professional, scientific and technical activities plus administrative and
# support service activities — the closest published aggregate to the work a
# shared-service centre does. Eurostat resolves no finer at NUTS-2.
SECTOR = "M_N"
YEARS = tuple(str(y) for y in range(2018, 2025))


def _url(dataset: str, extra: str) -> str:
    geos = "&".join(f"geo={g}" for g in _all_geos())
    times = "&".join(f"time={y}" for y in YEARS)
    return f"{BASE}/{dataset}?format=JSON&lang=en&{extra}&{geos}&{times}"


def _all_geos() -> list[str]:
    """Every NUTS-2 code an evidenced centre maps to, plus its country.

    Driven by `CENTRE_NUTS` rather than a separate region list, so a centre can
    never be scored against a region this module did not fetch.
    """
    out: set[str] = set()
    for nuts in C.CENTRE_NUTS.values():
        out.add(nuts)
        out.add(nuts[:2])
    return sorted(out)


def _series(payload: dict) -> dict[tuple[str, str], float]:
    """Flatten a Eurostat JSON-stat response to {(geo, year): value}."""
    dims = payload["id"]
    sizes = payload["size"]
    index = {d: payload["dimension"][d]["category"]["index"] for d in dims}
    rev = {d: {v: k for k, v in index[d].items()} for d in dims}

    strides = [1] * len(sizes)
    for i in range(len(sizes) - 2, -1, -1):
        strides[i] = strides[i + 1] * sizes[i + 1]

    out: dict[tuple[str, str], float] = {}
    for flat, value in payload["value"].items():
        if value is None:
            continue
        rest = int(flat)
        coords = {}
        for d, stride in zip(dims, strides):
            coords[d] = rev[d][rest // stride]
            rest %= stride
        out[(coords["geo"], coords["time"])] = float(value)
    return out


def load() -> dict[str, dict]:
    """Per region: hourly labour cost and its index against the country mean."""
    comp = _series(json.loads(fetch(
        _url("nama_10r_2coe", f"currency=MIO_EUR&nace_r2={SECTOR}"), suffix=".json"
    )))
    staff = _series(json.loads(fetch(
        _url("nama_10r_3empers", f"wstatus=SAL&unit=THS&nace_r2={SECTOR}"),
        suffix=".json",
    )))

    def rate(geo: str) -> tuple[str, float] | None:
        """Latest year where both numerator and denominator exist."""
        for year in sorted(YEARS, reverse=True):
            c, n = comp.get((geo, year)), staff.get((geo, year))
            if c and n:
                # MIO_EUR over thousand employees, to euro per employee.
                return year, (c * 1e6) / (n * 1e3)
        return None

    out: dict[str, dict] = {}
    for name, geo in C.CENTRE_NUTS.items():
        national = rate(geo[:2])
        if not national:
            continue
        base_year, base_rate = national
        got = rate(geo)
        if got:
            year, value = got
            out[geo] = {
                "market": geo[:2].lower(),
                "name": name,
                "nuts2": geo,
                "year": year,
                "eur_per_employee": value,
                "national_eur_per_employee": base_rate,
                "national_year": base_year,
                # The only number the scoring layer uses. A ratio inside one
                # country and one measure, so the concept mismatch with the
                # national panel cancels.
                "index_vs_country": value / base_rate,
                "source": f"Eurostat nama_10r_2coe / nama_10r_2emhrw, NACE {SECTOR}",
            }
    return out
