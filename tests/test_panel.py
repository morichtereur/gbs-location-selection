"""Panel assembly and the demand-side pillar.

The postings tests are skipped when the sibling snapshot is absent, so a clone
of this repository on its own still has a green suite — with the coverage gap
announced rather than hidden."""

from __future__ import annotations

import pytest

from src import config as C
from src.panel import REFERENCE_YEAR, Market, _cagr

pytestmark = pytest.mark.filterwarnings("ignore")

has_postings = C.POSTINGS_DB.exists()
needs_postings = pytest.mark.skipif(
    not has_postings, reason=f"postings snapshot not present at {C.POSTINGS_DB}"
)


def test_vintage_lag_is_measured_against_the_run_year():
    m = Market(iso2="xx", name="X", market_type="delivery")
    assert m.cost_lag is None
    m.cost_year = REFERENCE_YEAR - 4
    assert m.cost_lag == 4


def test_cagr_needs_enough_history():
    assert _cagr({2020: 100.0}, 2020) is None
    assert _cagr({2018: 100.0, 2019: 105.0, 2020: 110.0}, 2020) is None
    rate = _cagr({2020: 100.0, 2021: 110.0, 2024: 121.0}, 2024)
    assert rate == pytest.approx((121 / 100) ** (1 / 4) - 1)


def test_cagr_ignores_history_older_than_ten_years():
    hist = {2000: 1.0, 2014: 100.0, 2024: 200.0}
    # 2000 is outside the window, so the rate is measured 2014 -> 2024.
    assert _cagr(hist, 2024) == pytest.approx(2 ** (1 / 10) - 1)


@needs_postings
def test_demand_pillar_reproduces_the_published_sample_size():
    """The Agentic Shift study reports 2,110 in-scope postings. This project
    reuses that snapshot and its classifier, so it must land on the same
    number — if it does not, one of the two studies has drifted."""
    from src.sources import postings

    demand = postings.load()
    assert sum(d["postings_in_scope"] for d in demand.values()) == 2110


@needs_postings
def test_demand_shares_are_ratios_within_each_market():
    from src.sources import postings

    for iso2, d in postings.load().items():
        assert iso2 in C.MARKETS
        total = d["transactional_share"] + d["judgment_share"] + d["agent_ops_share"]
        assert total == pytest.approx(1.0)
        assert 0.0 <= d["employer_fragmentation"] <= 1.0
