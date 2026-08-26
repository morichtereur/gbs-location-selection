"""What a role costs beyond the wage on the payslip.

Exhibit 3 subtracted one ILOSTAT wage from another and called the difference
what the move is worth. That is a defensible upper bound on one line of a run
cost, and it was already labelled as one — but a reader quotes the number, and
the number a reader quotes should be the one they would defend in a business
case. Three things sit between a gross wage and a loaded cost:

    loaded_origin = wage_origin x (1 + loading) x (1 + drift_origin) ^ years
    loaded_city   = wage_city   x (1 + loading) x (1 + attrition)
                                x (1 + drift_city) ^ years

    annual gap per role = (loaded_origin - loaded_city) x 12

Two of the three multipliers are assumptions the reader sets, and this module
does not pretend otherwise; they are declared in `src/config.py` and adjustable
on the exhibit. The third is not an assumption at all — the drift is already
measured per market for the vintage adjustment and is what the durability
pillar scores, so projecting forward costs no new data and no new judgement.

Three properties of the arithmetic are worth stating, because each is the kind
of thing a scorecard usually leaves for the reader to discover:

*The loading factor cannot reorder anything.* It multiplies both sides, so it
scales every gap by the same amount. Real employer charges differ sharply by
country and would reorder plenty; the panel carries no comparable per-country
schedule, so this factor is uniform and the exhibit says so rather than letting
a uniform number look like a priced one.

*The attrition uplift can.* It applies to the destination only, so it costs
more where the wage is higher, and it can close a gap between two cities that
the base wage separated.

*A market with no measured drift cannot be projected honestly.* South Africa
has too short a series to measure a rate. Rather than carry it forward at the
panel median and let that pass as a projection, the horizon is reported as
unavailable for that market, per city, and the base figure stands.
"""

from __future__ import annotations

from dataclasses import dataclass

from src import config as C


@dataclass(frozen=True)
class Assumptions:
    """The three inputs, with the declared defaults."""

    loading: float = C.LOADING_FACTOR_DEFAULT
    attrition: float = C.ATTRITION_UPLIFT_DEFAULT
    horizon: int = C.HORIZON_YEARS_DEFAULT

    def clamped(self) -> "Assumptions":
        """Inside the guard rails, so a typed input cannot invert a wage bill."""
        return Assumptions(
            loading=min(max(self.loading, 0.0), C.LOADING_FACTOR_MAX),
            attrition=min(max(self.attrition, 0.0), C.ATTRITION_UPLIFT_MAX),
            horizon=int(min(max(self.horizon, 0), C.HORIZON_YEARS_MAX)),
        )


def project(wage: float, drift: float | None, years: int) -> float | None:
    """Carry a wage forward at its own measured drift.

    Returns None where the drift was never measured. The caller reports that as
    unavailable rather than substituting a panel median: a median dressed as a
    projection is the sort of quiet fill this study exists to expose, and the
    vintage adjustment already has one place where it is unavoidable without
    adding a second.
    """
    if years <= 0:
        return wage
    if drift is None:
        return None
    return wage * (1.0 + drift) ** years


def monthly(
    wage: float,
    drift: float | None,
    a: Assumptions,
    *,
    destination: bool,
) -> float | None:
    """One market's loaded monthly cost per role, or None if it cannot be projected.

    `destination` decides whether the attrition uplift applies: the origin is
    not being stood up, so it does not carry a ramp cost.
    """
    carried = project(wage, drift, a.horizon)
    if carried is None:
        return None
    loaded = carried * (1.0 + a.loading)
    return loaded * (1.0 + a.attrition) if destination else loaded


def gap(
    origin_wage: float,
    origin_drift: float | None,
    city_wage: float,
    city_drift: float | None,
    a: Assumptions | None = None,
    *,
    fte: int = 1,
) -> dict:
    """Base and loaded annual wage gap for `fte` roles.

    `loaded` is None when either side has no measured drift and a horizon was
    asked for; `unprojectable` then names which side, so the exhibit can say
    which figure is missing and why instead of printing a dash.
    """
    a = (a or Assumptions()).clamped()
    base_per_role = (origin_wage - city_wage) * 12.0

    o = monthly(origin_wage, origin_drift, a, destination=False)
    c = monthly(city_wage, city_drift, a, destination=True)
    missing = [
        side for side, v in (("origin", o), ("city", c)) if v is None
    ]
    loaded_per_role = None if missing else (o - c) * 12.0

    return {
        "basePerRole": base_per_role,
        "baseTotal": base_per_role * fte,
        "loadedPerRole": loaded_per_role,
        "loadedTotal": None if loaded_per_role is None else loaded_per_role * fte,
        "unprojectable": missing,
        "originMonthly": o,
        "cityMonthly": c,
    }


def multiplier(a: Assumptions | None = None) -> float:
    """The level uplift applied to a single wage before attrition and drift.

    Reported on the exhibit so a reader can see what the loading factor did to
    a figure without re-deriving it.
    """
    return 1.0 + (a or Assumptions()).clamped().loading
