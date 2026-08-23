"""The dashboard reimplements scoring in JavaScript so it can run on every
slider drag. These tests run that JavaScript under node against the real panel
and require it to agree with `src/score.py` — otherwise the page could quietly
rank markets differently from the study it is presenting."""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from src import config as C
from src import population
from src.dashboard import SCORING_JS, payload
from src.panel import build, with_centres
from src.score import normalise, rank, raw_pillars, score

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node not available")
# Two databases: this repo's GBS/GCC sample, and the sibling repo's broad one
# behind the contaminant shares. Checking only the second meant a missing local
# sample failed the suite rather than skipping it.
has_postings = population.DB_PATH.exists() and C.POSTINGS_DB.exists()
needs_postings = pytest.mark.skipif(
    not has_postings, reason=f"postings snapshot not present at {C.POSTINGS_DB}"
)


def _city_panel():
    """The cities the dashboard actually ranks — country rows are not shown."""
    return {
        k: m
        for k, m in with_centres(build()).items()
        if m.complete and m.is_city
    }


def _run_js(data: dict, archetype: str, weights: dict[str, float]) -> list[str]:
    """Rank the panel using the page's own JavaScript."""
    script = f"""
const DATA = {json.dumps(data)};
const state = {{ hq: DATA.hq }};
{SCORING_JS}
const rows = DATA.views.city[{json.dumps(archetype)}];
const ranked = scoreAll(normalise(pillarValues(rows)), {json.dumps(weights)});
console.log(JSON.stringify(ranked.map(r => r.row.id)));
"""
    out = subprocess.run(
        [node, "-e", script], capture_output=True, text=True, timeout=60
    )
    if out.returncode != 0:
        raise AssertionError(out.stderr[:2000])
    return json.loads(out.stdout.strip().splitlines()[-1])


@needs_node
@needs_postings
@pytest.mark.parametrize("archetype", list(C.ARCHETYPES))
def test_javascript_ranking_matches_python(archetype):
    data = payload()
    weights = C.ARCHETYPES[archetype]["weights"]
    panel = _city_panel()
    expected = rank(score(normalise(raw_pillars(panel, archetype)), weights))
    assert _run_js(data, archetype, weights) == expected


@needs_node
@needs_postings
def test_javascript_agrees_under_a_lopsided_weighting():
    """Equal-weight and corner cases are where a normalisation bug hides."""
    data = payload()
    panel = _city_panel()
    for weights in (
        {p: 1 / 6 for p in data["pillars"]},
        {**{p: 0.0 for p in data["pillars"]}, "cost": 1.0},
        {**{p: 0.01 for p in data["pillars"]}, "timezone": 0.95},
    ):
        expected = rank(score(normalise(raw_pillars(panel, "judgment_centre")), weights))
        assert _run_js(data, "judgment_centre", weights) == expected


@needs_postings
def test_payload_carries_what_the_monte_carlo_needs():
    """Guards a divergence the ranking parity test cannot see.

    The parity tests compare the deterministic ranking, which does not touch
    the resampling. The dashboard ran a full revision without the
    classification-error correction and showed a different leading city from
    the study it presents, because the payload simply lacked the inputs. If
    the correction is switched on, every row must carry what it needs.
    """
    data = payload()
    assert data["modelClassificationError"] is C.MODEL_CLASSIFICATION_ERROR
    if not data["modelClassificationError"]:
        return
    assert data["auditTotal"] > 0 and 0 < data["auditCorrect"] <= data["auditTotal"]
    for rows in data["views"]["city"].values():
        for row in rows:
            assert row["capN"] is not None, row["name"]
            assert row["contaminant"] is not None, row["name"]
            assert 0.0 <= row["contaminant"] <= 1.0


@needs_postings
def test_payload_carries_every_pillar_for_every_entity():
    data = payload()
    assert set(data["views"]) == {"city"}, "cities only"
    for view in data["views"].values():
        for archetype_rows in view.values():
            assert archetype_rows
            for row in archetype_rows:
                for pillar in data["pillars"]:
                    assert row[pillar] is not None, (row["name"], pillar)


@needs_postings
def test_centre_rows_are_evidenced_and_declare_their_parent():
    data = payload()
    centres = data["views"]["city"]["transactional_hub"]
    assert centres, "the city view should contain cities"
    assert all(r["isCity"] for r in centres), "no country rows in a city ranking"
    for row in centres:
        assert row["parent"] in C.MARKETS
        assert row["employers"] >= C.MIN_CENTRE_EMPLOYERS
        # The threshold qualifies a city on GBS postings seen, not on how many
        # the work-family classifier could also read.
        assert row["postingsSeen"] >= C.MIN_CENTRE_POSTINGS
        # Cost is either city-resolved with an index, or inherited and marked.
        assert row["costResolved"] == (row["regionIndex"] is not None)


@needs_postings
def test_single_employer_locations_are_excluded():
    """Rheda-Wiedenbruck had 17 postings from two employers. Volume alone would
    have admitted it as a GBS centre; it is one company's office."""
    from src.centres import survey

    kept, dropped = survey()
    names = {c.name for c in kept}
    assert "Rheda-Wiedenbrück" not in names
    assert "Oberkochen" not in names
    for centre in kept:
        assert centre.employers >= C.MIN_CENTRE_EMPLOYERS


@needs_postings
def test_capability_is_shrunk_toward_the_country():
    """A thin centre sample must not carry its raw share into the score."""
    from src.panel import build, with_centres, with_centres

    countries = build()
    for m in with_centres(countries).values():
        if not m.is_city or m.capability_raw is None:
            continue
        national = m.capability_shrunk_from
        # The shrunk value lies between the centre's own estimate and its
        # country's, and never outside them.
        assert min(m.capability_raw, national) - 1e-9 <= m.transactional_share
        assert m.transactional_share <= max(m.capability_raw, national) + 1e-9
        # A thin sample sits closer to the country than to its own estimate.
        if m.postings_in_scope and m.postings_in_scope < C.CAPABILITY_PRIOR_STRENGTH:
            assert abs(m.transactional_share - national) < abs(
                m.transactional_share - m.capability_raw
            ) or m.capability_raw == pytest.approx(national, abs=0.02)


@needs_postings
def test_every_baseline_carries_a_wage_the_exhibit_can_subtract():
    """Exhibit 3 subtracts the baseline's wage from each city's.

    A baseline market whose wage failed to load would render the whole exhibit
    as NaN rather than as an error, so the payload must not offer one. This
    also catches a market being added to BASELINE_MARKETS before ILOSTAT
    covers it.
    """
    data = payload()
    offered = {b["key"] for b in data["baselines"]}
    scored = {b["key"] for b in data["baselines"] if b["scored"]}
    origins = {b["key"] for b in data["baselines"] if not b["scored"]}
    assert scored == set(C.BASELINE_MARKETS), (
        f"scored origins {scored}, config declares {set(C.BASELINE_MARKETS)}"
    )
    assert origins <= set(C.BASELINE_EXTRA), (
        f"unscored origins {origins - set(C.BASELINE_EXTRA)} are in neither list"
    )
    # An origin-only market must never reach the ranking; it carries one pillar.
    assert not (origins & set(data["marketNames"])), (
        "an origin-only market appears among the scored markets"
    )
    for b in data["baselines"]:
        assert b["monthly"] and b["monthly"] > 0, b
        assert b["label"], b
    assert data["baselineDefault"] in offered
    assert data["fteDefault"] > 0


@needs_postings
def test_the_default_baseline_is_dearer_than_every_city_it_is_compared_with():
    """Not a law of the tool, but true of Switzerland, and the headline rests on it.

    A negative delta renders as "above baseline" and is handled, but if the
    default ever produced one the one-pager would open on a mixed exhibit
    without anyone deciding that it should.
    """
    data = payload()
    base = next(b for b in data["baselines"] if b["key"] == data["baselineDefault"])
    for rows in data["views"]["city"].values():
        for row in rows:
            if row["cost"] is None:
                continue
            assert row["cost"] < base["monthly"], (row["name"], row["cost"])
