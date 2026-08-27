"""Panel assembly and the demand-side pillar.

The postings tests are skipped when the sibling snapshot is absent, so a clone
of this repository on its own still has a green suite — with the coverage gap
announced rather than hidden."""

from __future__ import annotations

import pytest

from src import config as C
from src.panel import REFERENCE_YEAR, Market, _cagr, age, median_drift

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


needs_gbs = pytest.mark.skipif(
    not (C.DATA / "gbs_postings.duckdb").exists(),
    reason="GBS/GCC sample not fetched; run `make fetch`",
)


@needs_gbs
@needs_postings
def test_capability_population_is_gbs_or_gcc_only():
    """Guards the change this project made deliberately.

    The capability pillar used to run on a broad finance-operations sample in
    which only 13% of postings carried any shared-services signal — it was
    describing retained finance nine times out of ten. Every posting reaching
    the pillar must now be classified as GBS or GCC work.
    """
    from src.population import load

    postings = load()
    assert postings, "expected a non-empty GBS/GCC population"
    assert {p.model for p in postings} <= {"gcc", "gbs"}


@needs_gbs
@needs_postings
def test_market_shares_are_proportions_over_decided_postings():
    from src.sources.postings import load_market_shares

    for iso2, d in load_market_shares().items():
        assert iso2 in C.MARKETS
        total = (
            d["transactional_share"] + d["judgment_share"] + d["agent_ops_share"]
        )
        assert total == pytest.approx(1.0)
        # Ambiguous postings are excluded from the denominator, never folded in.
        assert d["postings_in_scope"] <= d["postings_fetched"]
        assert 0.0 <= d["ambiguous_share"] < 1.0


@needs_gbs
@needs_postings
def test_sales_and_wrong_setting_postings_are_excluded():
    """A hotel cashier and a GCC sales role both matched every gate before the
    exclusion lists existed."""
    from src.delivery import _org_type, classify

    org_type = _org_type()
    assert classify(
        "Team Lead, Cashier", "hotel front desk and guest billing", "Hyatt", org_type
    ).startswith("out:")
    assert classify(
        "VP - GCC Sales", "selling to global capability centres, accounts payable",
        "ANSR", org_type,
    ).startswith("out:")
    assert classify(
        "R2R Specialist", "Finance Shared Service Centre, general ledger and reconciliation",
        "Experis", org_type,
    ) == "gbs"


def test_the_governance_pull_fails_rather_than_truncating():
    """A page cap that binds must raise, not drop the countries past it.

    per_page was 500. Adding markets took the WGI response to 572 rows, the
    API paginated, and South Africa -- which is ranked -- disappeared with no
    error anywhere. The guard turns that into a failure.
    """
    import inspect

    import requests

    from src.sources import worldbank

    src = inspect.getsource(worldbank._series)
    assert "per_page" in src and "total" in src, "the truncation guard is gone"
    try:
        data = worldbank.load()
    except requests.RequestException as e:
        pytest.skip(f"World Bank API unreachable from here: {e}")
    want = set(C.MARKETS) | set(C.BEYOND_SAMPLE)
    assert want <= set(data), f"no governance for {sorted(want - set(data))}"


def test_every_ranked_market_has_a_coherent_wage_series():
    """Professionals out-earn clerical staff in a working series.

    Egypt reported 1.06x and was excluded from the reported markets on that
    test. The same test is run here over the markets that are actually scored,
    so a refresh that breaks one of them fails rather than ranking on it.
    """
    import requests

    from src.sources import ilostat

    # The assertion is about the series, not about whether the API answers
    # today: sdmx.ilo.org started returning 403 to GitHub-hosted runners on
    # 2026-08-27, and a suite that fails on upstream availability hides real
    # failures behind expected ones. Locally the cache serves this without a
    # request, so the check still runs wherever the data exists.
    try:
        wages = ilostat.load()
    except requests.RequestException as e:
        pytest.skip(f"ILOSTAT unreachable from here: {e}")
    for key in C.MARKETS:
        w = wages.get(key)
        if not w or "usd_2" not in w or "usd_4" not in w:
            continue
        premium = w["usd_2"] / w["usd_4"]
        assert premium >= C.MIN_PROFESSIONAL_PREMIUM, (
            f"{C.MARKETS[key]['name']} reports professionals at {premium:.2f}x clerical"
        )
