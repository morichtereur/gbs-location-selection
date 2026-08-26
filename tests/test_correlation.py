"""The pillar correlation the exhibit reports.

Two things are being protected. The arithmetic — a correlation of the
normalised scores, and an effective dimensionality reached through the
Frobenius identity rather than an eigensolver, which is only worth using if it
agrees with the eigenvalues it stands in for. And the disclosure — the panel is
strongly correlated, and a refactor that quietly made it look independent would
remove the reason the limit is on the page.
"""

from __future__ import annotations

import math

import pytest

from src import config as C
from src.correlation import matrix, national_pillars, summary
from src.panel import Market
from src.score import PILLARS
from tests.test_score import make


def city(iso2: str, parent: str, cost: float, trans: float, **national) -> Market:
    """One city row, with every pillar set explicitly.

    `tests.test_score.make` derives overlap and depth from the capability share
    and pins durability flat, which is right for a scoring test and wrong here:
    this module is about which pillars co-vary, so nothing may co-vary by
    accident of the helper.
    """
    m = make(iso2, cost, national["talent"], national["risk"], trans)
    m.name = iso2
    m.parent = parent
    m.timezone_overlap = national["timezone"]
    m.durability = national["durability"]
    m.depth = national["depth"]
    return m


# Two countries of two cities. Cost and capability move inside a country;
# talent, governance, overlap, durability and depth are shared by both of its
# cities, which is the shape of the real panel.
NORTH = {"talent": 1_000_000, "risk": 50, "timezone": 6.0,
         "durability": -0.05, "depth": 40.0}
SOUTH = {"talent": 200_000, "risk": 80, "timezone": 3.0,
         "durability": -0.02, "depth": 12.0}


@pytest.fixture
def panel() -> dict[str, Market]:
    rows = [
        city("a:one", "a", 500, 0.70, **NORTH),
        city("a:two", "a", 520, 0.55, **NORTH),
        city("b:one", "b", 3000, 0.40, **SOUTH),
        city("b:two", "b", 3100, 0.35, **SOUTH),
    ]
    return {m.iso2: m for m in rows}


def test_the_matrix_is_symmetric_with_a_unit_diagonal(panel):
    r = matrix(panel, "transactional_hub")
    assert len(r) == len(PILLARS)
    for i in range(len(PILLARS)):
        assert r[i][i] == pytest.approx(1.0)
        for j in range(len(PILLARS)):
            assert r[i][j] == pytest.approx(r[j][i])


def test_every_correlation_is_inside_the_unit_interval(panel):
    for row in matrix(panel, "transactional_hub"):
        for v in row:
            assert v is None or -1.0 - 1e-12 <= v <= 1.0 + 1e-12


def test_a_pillar_that_does_not_vary_is_none_rather_than_zero(panel):
    """Imputing 0 would read as "independent" when the truth is "absent"."""
    for m in panel.values():
        m.timezone_overlap = 6.0          # identical everywhere
    r = matrix(panel, "transactional_hub")
    tz = PILLARS.index("timezone")
    assert r[tz][tz] is None
    assert all(r[tz][j] is None for j in range(len(PILLARS)))

    s = summary(r)
    assert s["pillars"] == len(PILLARS) - 1
    # A dimension nothing moves along must not be counted as one.
    assert s["n_eff"] <= s["pillars"]


def test_effective_dimensionality_matches_the_eigenvalues_it_stands_in_for(panel):
    """The page computes n_eff without an eigensolver. It has to be the same n_eff."""
    np = pytest.importorskip("numpy")
    r = matrix(panel, "transactional_hub")
    keep = [i for i in range(len(PILLARS)) if r[i][i] is not None]
    R = np.array([[r[i][j] for j in keep] for i in keep])
    ev = np.linalg.eigvalsh(R)
    by_eigenvalue = ev.sum() ** 2 / (ev**2).sum()
    assert summary(r)["n_eff"] == pytest.approx(by_eigenvalue, rel=1e-9)


def test_identical_pillars_collapse_to_one_effective_dimension():
    """A panel whose pillars are all one variable has one direction, not seven.

    Built through the transforms rather than around them: cost, talent and
    depth are log-scaled and cost is inverted, so making every pillar the same
    variable *after* normalisation means setting the log-scaled ones to c and
    1/c and the linear ones to -log(c).
    """
    same = {}
    for i, c in enumerate((500.0, 900.0, 1500.0, 2400.0)):
        m = Market(iso2=f"m{i}", name=f"m{i}", market_type="delivery")
        m.cost_usd = m.cost_usd_aged = c
        m.talent_proxy = 1.0 / c
        m.depth = 1.0 / c
        flat = -math.log(c)
        m.risk_score = flat
        m.transactional_share = flat
        m.judgment_share = flat
        m.timezone_overlap = flat
        m.durability = flat
        same[m.iso2] = m
    s = summary(matrix(same, "transactional_hub"))
    assert s["n_eff"] == pytest.approx(1.0, abs=1e-9)
    assert s["mean_abs"] == pytest.approx(1.0, abs=1e-9)
    assert s["strong"] == s["pairs"]


def test_orthogonal_pillars_reach_the_full_dimensionality():
    """The counterpart: n_eff equals the pillar count only when nothing co-varies."""
    r = [[1.0 if i == j else 0.0 for j in range(len(PILLARS))] for i in range(len(PILLARS))]
    s = summary(r)
    assert s["n_eff"] == pytest.approx(len(PILLARS))
    assert s["strong"] == 0


def test_national_pillars_are_the_ones_constant_within_every_country(panel):
    """Cost and capability vary inside country 'a'; the rest are national."""
    national = national_pillars(panel, "transactional_hub")
    assert "cost" not in national
    assert "capability" not in national
    assert {"talent", "risk", "timezone", "durability", "depth"} <= set(national)


def test_summary_counts_only_pairs_above_the_declared_threshold(panel):
    r = matrix(panel, "transactional_hub")
    s = summary(r)
    n = len(PILLARS)
    assert s["pairs"] == n * (n - 1) // 2
    by_hand = sum(
        1 for i in range(n) for j in range(i + 1, n)
        if r[i][j] is not None and abs(r[i][j]) >= s["strong_at"]
    )
    assert s["strong"] == by_hand
    assert 0.0 <= s["mean_abs"] <= s["max_abs"] <= 1.0


@pytest.mark.parametrize("archetype", list(C.ARCHETYPES))
def test_switching_archetype_only_flips_the_capability_row(panel, archetype):
    """Transactional and judgment shares are mirrors, so the rest must not move."""
    base = matrix(panel, "transactional_hub")
    other = matrix(panel, archetype)
    cap = PILLARS.index("capability")
    for i in range(len(PILLARS)):
        for j in range(len(PILLARS)):
            if cap in (i, j) and i != j:
                continue
            assert base[i][j] == pytest.approx(other[i][j])


def test_the_real_panel_is_strongly_correlated():
    """The finding the disclosure exists for, asserted so it cannot vanish quietly.

    Not a tight bound — a data refresh moves these figures. It fails if the
    panel ever becomes something like independent, which would mean the limit
    on the page had stopped being true and should be rewritten rather than
    left standing.
    """
    from src import population
    from src.panel import build, with_centres

    if not (population.DB_PATH.exists() and C.POSTINGS_DB.exists()):
        pytest.skip("postings snapshot not present")

    cities = {
        k: m for k, m in with_centres(build()).items() if m.complete and m.is_city
    }
    s = summary(matrix(cities, "transactional_hub"))
    assert s["mean_abs"] > 0.4, s
    assert s["n_eff"] < 4.0, s
    assert len(national_pillars(cities, "transactional_hub")) >= 4
    assert not math.isnan(s["n_eff"])
