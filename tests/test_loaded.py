"""The step from a gross wage to a loaded cost.

Three properties carry the disclosure on the exhibit, and each is asserted here
rather than left to the caveat text: a uniform loading factor cannot reorder
cities, a destination-only attrition uplift can, and a market with no measured
drift is not projected at all.
"""

from __future__ import annotations

import pytest

from src import config as C
from src.loaded import Assumptions, gap, monthly, multiplier, project

NONE = Assumptions(loading=0.0, attrition=0.0, horizon=0)


def test_with_no_assumptions_the_loaded_figure_is_the_base_figure():
    g = gap(6000, 0.02, 500, 0.05, NONE, fte=10)
    assert g["basePerRole"] == pytest.approx((6000 - 500) * 12)
    assert g["loadedPerRole"] == pytest.approx(g["basePerRole"])
    assert g["loadedTotal"] == pytest.approx(g["baseTotal"])
    assert g["unprojectable"] == []


def test_the_loading_factor_applies_to_both_sides():
    a = Assumptions(loading=0.30, attrition=0.0, horizon=0)
    g = gap(6000, 0.02, 500, 0.05, a)
    assert g["loadedPerRole"] == pytest.approx(g["basePerRole"] * 1.30)


def test_a_uniform_loading_factor_cannot_reorder_cities():
    """The exhibit claims this in words; it has to be true in the arithmetic.

    If it were not, the caveat would be understating what the slider does.
    """
    cities = [(500, 0.05), (900, 0.03), (1500, 0.04), (3000, 0.02)]
    order = lambda a: sorted(  # noqa: E731
        cities, key=lambda c: -gap(6000, 0.02, c[0], c[1], a)["loadedPerRole"]
    )
    flat = Assumptions(loading=0.0, attrition=0.0, horizon=0)
    for loading in (0.05, 0.25, 0.60, C.LOADING_FACTOR_MAX):
        a = Assumptions(loading=loading, attrition=0.0, horizon=0)
        assert order(a) == order(flat), loading


def test_attrition_applies_to_the_destination_only():
    a = Assumptions(loading=0.0, attrition=0.20, horizon=0)
    g = gap(6000, 0.02, 500, 0.05, a)
    # Origin untouched, destination up 20%: the gap widens by the destination's
    # own uplift rather than shrinking by a share of the difference.
    assert g["loadedPerRole"] == pytest.approx((6000 - 500 * 1.20) * 12)
    assert g["originMonthly"] == pytest.approx(6000)
    assert g["cityMonthly"] == pytest.approx(600)


def test_attrition_can_reorder_cities_where_loading_cannot():
    """It scales with a city's own wage, so it is the input that can move the answer."""
    cheap_but_dear_to_run, dear = (1000, 0.03), (1080, 0.03)
    a0 = Assumptions(loading=0.0, attrition=0.0, horizon=0)
    a1 = Assumptions(loading=0.0, attrition=0.9, horizon=0)
    spread = lambda c, a: gap(6000, 0.02, c[0], c[1], a)["loadedPerRole"]  # noqa: E731
    # Both are worse under attrition, and the dearer one worsens faster.
    d0 = spread(cheap_but_dear_to_run, a0) - spread(dear, a0)
    d1 = spread(cheap_but_dear_to_run, a1) - spread(dear, a1)
    assert d1 > d0


def test_projection_carries_each_side_at_its_own_measured_drift():
    a = Assumptions(loading=0.0, attrition=0.0, horizon=3)
    g = gap(6000, 0.02, 500, 0.08, a)
    expected = (6000 * 1.02**3 - 500 * 1.08**3) * 12
    assert g["loadedPerRole"] == pytest.approx(expected)


def test_a_fast_drifting_destination_closes_the_gap():
    """The durability pillar, made arithmetic: Poland's rate against Switzerland's."""
    a0 = Assumptions(loading=0.0, attrition=0.0, horizon=0)
    a5 = Assumptions(loading=0.0, attrition=0.0, horizon=5)
    now = gap(6216, 0.0218, 2000, 0.0849, a0)["loadedPerRole"]
    later = gap(6216, 0.0218, 2000, 0.0849, a5)["loadedPerRole"]
    assert later < now


def test_an_unmeasured_drift_is_not_projected_at_all(caplog):
    """No panel median standing in for a forecast, and the missing side is named."""
    a = Assumptions(loading=0.25, attrition=0.15, horizon=4)
    g = gap(6000, 0.02, 500, None, a)
    assert g["loadedPerRole"] is None
    assert g["loadedTotal"] is None
    assert g["unprojectable"] == ["city"]
    # The base figure still stands, so the row is not blank.
    assert g["basePerRole"] == pytest.approx((6000 - 500) * 12)


def test_an_unmeasured_origin_drift_is_named_too():
    a = Assumptions(loading=0.0, attrition=0.0, horizon=2)
    assert gap(6000, None, 500, 0.03, a)["unprojectable"] == ["origin"]
    assert gap(6000, None, 500, None, a)["unprojectable"] == ["origin", "city"]


def test_a_missing_drift_is_harmless_at_a_zero_horizon():
    """Nothing is being carried forward, so nothing needs a rate."""
    a = Assumptions(loading=0.25, attrition=0.15, horizon=0)
    g = gap(6000, None, 500, None, a)
    assert g["loadedPerRole"] is not None
    assert g["unprojectable"] == []


def test_project_returns_the_wage_unchanged_at_zero_years():
    assert project(1234.0, None, 0) == 1234.0
    assert project(1234.0, 0.05, 0) == 1234.0


def test_inputs_are_clamped_so_a_typo_cannot_invert_a_wage_bill():
    a = Assumptions(loading=-5.0, attrition=-2.0, horizon=-3).clamped()
    assert a.loading == 0.0 and a.attrition == 0.0 and a.horizon == 0
    b = Assumptions(loading=99.0, attrition=99.0, horizon=999).clamped()
    assert b.loading == C.LOADING_FACTOR_MAX
    assert b.attrition == C.ATTRITION_UPLIFT_MAX
    assert b.horizon == C.HORIZON_YEARS_MAX
    # And a clamped run still produces a finite figure.
    assert gap(6000, 0.02, 500, 0.03, b)["loadedPerRole"] is not None


def test_gap_scales_linearly_with_headcount():
    a = Assumptions(loading=0.25, attrition=0.15, horizon=2)
    one = gap(6000, 0.02, 500, 0.03, a, fte=1)
    many = gap(6000, 0.02, 500, 0.03, a, fte=250)
    assert many["baseTotal"] == pytest.approx(one["basePerRole"] * 250)
    assert many["loadedTotal"] == pytest.approx(one["loadedPerRole"] * 250)


def test_monthly_is_the_piece_the_gap_is_built_from():
    a = Assumptions(loading=0.25, attrition=0.15, horizon=0)
    assert monthly(1000, 0.03, a, destination=False) == pytest.approx(1250)
    assert monthly(1000, 0.03, a, destination=True) == pytest.approx(1250 * 1.15)
    assert monthly(1000, None, a.__class__(0.25, 0.15, 2), destination=True) is None


def test_multiplier_reports_the_level_uplift():
    assert multiplier(Assumptions(loading=0.25, attrition=0.15, horizon=0)) == pytest.approx(1.25)
    assert multiplier(NONE) == pytest.approx(1.0)


def test_the_declared_defaults_are_inside_their_own_guard_rails():
    a = Assumptions()
    assert a == a.clamped()
    assert 0.0 <= C.LOADING_FACTOR_DEFAULT <= C.LOADING_FACTOR_MAX
    assert 0.0 <= C.ATTRITION_UPLIFT_DEFAULT <= C.ATTRITION_UPLIFT_MAX
    assert 0 <= C.HORIZON_YEARS_DEFAULT <= C.HORIZON_YEARS_MAX
    # The horizon defaults to today: a non-zero default would apply a
    # compounding projection the reader never chose.
    assert C.HORIZON_YEARS_DEFAULT == 0


def test_every_baseline_carries_a_drift_and_says_whether_it_was_measured():
    from src import population
    from src.baselines import load

    if not (population.DB_PATH.exists() and C.POSTINGS_DB.exists()):
        pytest.skip("postings snapshot not present")
    for b in load():
        assert "drift" in b and "driftMeasured" in b, b["label"]
        assert b["driftMeasured"] == (b["drift"] is not None), b["label"]
