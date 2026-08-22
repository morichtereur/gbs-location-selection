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
from src.dashboard import SCORING_JS, payload
from src.panel import build
from src.score import normalise, rank, raw_pillars, score

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node not available")
has_postings = C.POSTINGS_DB.exists()
needs_postings = pytest.mark.skipif(
    not has_postings, reason=f"postings snapshot not present at {C.POSTINGS_DB}"
)


def _run_js(data: dict, archetype: str, weights: dict[str, float]) -> list[str]:
    """Rank the panel using the page's own JavaScript."""
    script = f"""
const DATA = {json.dumps(data)};
const state = {{ hq: DATA.hq }};
{SCORING_JS}
const rows = DATA.views.country[{json.dumps(archetype)}];
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
    panel = build()
    expected = rank(score(normalise(raw_pillars(panel, archetype)), weights))
    assert _run_js(data, archetype, weights) == expected


@needs_node
@needs_postings
def test_javascript_agrees_under_a_lopsided_weighting():
    """Equal-weight and corner cases are where a normalisation bug hides."""
    data = payload()
    panel = build()
    for weights in (
        {p: 1 / 6 for p in data["pillars"]},
        {**{p: 0.0 for p in data["pillars"]}, "cost": 1.0},
        {**{p: 0.01 for p in data["pillars"]}, "timezone": 0.95},
    ):
        expected = rank(score(normalise(raw_pillars(panel, "judgment_centre")), weights))
        assert _run_js(data, "judgment_centre", weights) == expected


@needs_postings
def test_payload_carries_every_pillar_for_every_entity():
    data = payload()
    for view in data["views"].values():
        for archetype_rows in view.values():
            assert archetype_rows
            for row in archetype_rows:
                for pillar in data["pillars"]:
                    assert row[pillar] is not None, (row["name"], pillar)


@needs_postings
def test_centre_rows_are_evidenced_and_declare_their_parent():
    data = payload()
    centres = [r for r in data["views"]["city"]["transactional_hub"] if r["isCity"]]
    assert centres, "centre view should contain centre rows"
    for row in centres:
        assert row["parent"] in C.MARKETS
        assert row["employers"] >= C.MIN_CENTRE_EMPLOYERS
        assert row["postings"] >= C.MIN_CENTRE_POSTINGS
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
    from src.panel import build, with_centres

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
