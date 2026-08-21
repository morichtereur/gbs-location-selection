"""Normalisation, direction and weighting. Synthetic panels throughout: these
assertions are about the arithmetic, not about whether three public APIs are up."""

from __future__ import annotations

import math

import pytest

from src import config as C
from src.panel import Market
from src.score import PILLARS, normalise, rank, raw_pillars, score


def make(iso2: str, cost: float, talent: float, risk: float, trans: float) -> Market:
    m = Market(iso2=iso2, name=iso2.upper(), market_type="delivery")
    m.cost_usd = cost
    m.cost_usd_aged = cost
    m.drift_used = 0.03
    m.drift_measured = True
    m.cost_year = 2025
    m.wage_components_usd = {g: cost for g in C.ISCO_GROUPS}
    m.talent_proxy = talent
    m.risk_score = risk
    m.wgi = {d: (risk, risk - 5, risk + 5) for d in C.WGI_DIMENSIONS}
    m.transactional_share = trans
    m.judgment_share = 1.0 - trans
    m.timezone_overlap = 8.0 - 3.0 * trans
    m.durability = -0.03
    m.bpo_share = 0.1
    m.employer_fragmentation = 0.5
    m.postings_in_scope = 100
    return m


@pytest.fixture
def panel() -> dict[str, Market]:
    return {
        "cheap": make("cheap", 500, 1_000_000, 50, 0.7),
        "mid": make("mid", 2_500, 500_000, 70, 0.4),
        "dear": make("dear", 8_000, 100_000, 90, 0.2),
    }


def test_cost_is_the_only_inverted_pillar(panel):
    scaled = normalise(raw_pillars(panel, "transactional_hub"))
    # Cheapest market must score best on cost, and worst on the pillars where
    # it genuinely is worst.
    assert scaled["cheap"]["cost"] == pytest.approx(1.0)
    assert scaled["dear"]["cost"] == pytest.approx(0.0)
    assert scaled["dear"]["risk"] == pytest.approx(1.0)
    assert scaled["cheap"]["risk"] == pytest.approx(0.0)


def test_every_normalised_value_is_a_unit_interval(panel):
    scaled = normalise(raw_pillars(panel, "transactional_hub"))
    for market in scaled.values():
        for pillar in PILLARS:
            assert 0.0 <= market[pillar] <= 1.0


def test_log_transform_changes_spacing_but_not_direction(panel):
    raw = raw_pillars(panel, "transactional_hub")
    log = normalise(raw, transform="log")
    linear = normalise(raw, transform="linear")
    # Direction survives the transform ...
    for tf in (log, linear):
        assert tf["cheap"]["cost"] > tf["mid"]["cost"] > tf["dear"]["cost"]
    # ... but the middle market's position does not, which is the whole reason
    # the transform is a declared choice rather than a default.
    assert log["mid"]["cost"] != pytest.approx(linear["mid"]["cost"], abs=0.05)


def test_log_transform_matches_hand_computation(panel):
    log = normalise(raw_pillars(panel, "transactional_hub"), transform="log")
    lo, hi = math.log(500), math.log(8_000)
    expected = 1.0 - (math.log(2_500) - lo) / (hi - lo)
    assert log["mid"]["cost"] == pytest.approx(expected)


def test_archetype_switches_which_capability_counts(panel):
    trans = raw_pillars(panel, "transactional_hub")
    judg = raw_pillars(panel, "judgment_centre")
    assert trans["cheap"]["capability"] == pytest.approx(0.7)
    assert judg["cheap"]["capability"] == pytest.approx(0.3)


def test_score_is_a_weighted_mean_and_weights_need_not_be_normalised(panel):
    scaled = normalise(raw_pillars(panel, "transactional_hub"))
    even = {p: 1.0 for p in PILLARS}
    scores = score(scaled, even)
    for k, v in scores.items():
        assert v == pytest.approx(sum(scaled[k][p] for p in PILLARS) / len(PILLARS))
    # Doubling every weight is the same weighting, so the same scores.
    assert score(scaled, {p: 2.0 for p in PILLARS}) == pytest.approx(scores)


def test_rank_is_deterministic_under_ties(panel):
    scaled = normalise(raw_pillars(panel, "transactional_hub"))
    tied = {k: 0.5 for k in scaled}
    assert rank(tied) == sorted(tied)


def test_incomplete_markets_are_dropped_not_imputed(panel):
    panel["gap"] = make("gap", 1_000, 200_000, 60, 0.5)
    panel["gap"].talent_proxy = None
    raw = raw_pillars(panel, "transactional_hub")
    assert "gap" not in raw
    assert panel["gap"].missing() == ["talent"]
