"""The order the page makes its case in.

An exhibit that has to be configured before it says anything is a tool, not an
exhibit. These assert the running order rather than the styling: the finding
first, one control in the open, and everything else behind a disclosure. They
are string assertions on the built document because that is what ships — a
reordering in the template is exactly the change that should fail here.
"""

from __future__ import annotations

import pytest

from src import config as C
from src import population
from src.dashboard import build_html

pytestmark = pytest.mark.skipif(
    not (population.DB_PATH.exists() and C.POSTINGS_DB.exists()),
    reason="postings snapshot not present",
)


@pytest.fixture(scope="module")
def html() -> str:
    """Built once: the payload runs two 10,000-draw stability passes."""
    return build_html()


def _disclosure(html: str) -> str:
    start = html.index('<details class="adjust" id="adjust">')
    return html[start:html.index("</details>", start)]


def _own_figures(html: str) -> str:
    start = html.index('<details class="adjust" id="own-figures">')
    return html[start:html.index("</details>", start)]


def test_the_finding_is_rendered_before_any_control(html):
    """The whole point of the change: say something, then offer the controls."""
    finding = html.index('id="takeaway"')
    assert finding < html.index('id="archetype"'), "centre type precedes the finding"
    assert finding < html.index('class="layout"'), "the control rail precedes the finding"
    assert html.index('id="headline"') < finding


def test_one_control_stays_in_the_open_and_it_is_the_centre_type(html):
    assert 'id="archetype"' not in _disclosure(html)


def test_every_other_input_is_behind_the_disclosure(html):
    inside = _disclosure(html)
    for control in (
        'id="sliders"',     # the seven weights
        'id="hq"',          # headquarters
        'id="baseline"',    # cost comparison origin
        'id="fte"',         # roles moved
        'id="loading"',     # employer loading
        'id="attrition"',   # attrition backfill
        'id="horizon"',     # years forward
    ):
        assert control in inside, control


def test_the_disclosures_start_closed(html):
    """Open by default would put the wall of controls straight back."""
    for anchor in ('<details class="adjust" id="adjust">',
                   '<details class="adjust" id="own-figures">'):
        assert anchor in html, anchor
        assert " open" not in anchor


def test_client_figures_have_their_own_disclosure(html):
    """Evidence entry is not an assumption: it gets its own fold, with the
    entry points inside it and the tier named in its summary."""
    inside = _own_figures(html)
    for control in ('id="ovr-city"', 'id="ovr-wage"', 'id="ovr-source"',
                    'id="ovr-date"', 'id="ovr-add"', 'id="ovr-list"'):
        assert control in inside, control
    assert 'id="ovr-city"' not in _disclosure(html)


def test_the_disclosure_reports_what_it_is_hiding(html):
    """A collapsed panel concealing a changed setting is worse than one hiding a default."""
    assert 'id="adjust-state"' in html
    assert "renderAdjustState" in html
    # And the label is derived from the state rather than written down.
    assert "function moved()" in html


def test_provenance_stays_visible_rather_than_being_folded_away(html):
    """Item 3 put the sample's date and terms on the page; they must not hide here."""
    assert 'id="provenance"' not in _disclosure(html)
    assert 'id="sources"' not in _disclosure(html)


def test_the_sources_card_is_reordered_below_the_exhibit_when_stacked(html):
    """Stacked, it sat between the finding and Exhibit 1 and cost two screens."""
    assert 'class="card sources-card"' in html
    assert ".rail > .sources-card { order: 3; }" in html
    # The rule has to fall after the base .rail declarations or the cascade
    # never reaches it — media queries carry no extra specificity.
    assert html.index(".rail { gap: 22px; }") < html.index(".rail { display: contents; }")


def test_scenario_controls_stay_outside_the_disclosure(html):
    """Naming or sharing a view is not an assumption — it must not hide with them."""
    inside = _disclosure(html)
    assert 'id="scenario-list"' not in inside
    assert 'id="scenario-list"' in html
    assert 'id="copy-link"' in html


def test_the_headline_names_whose_weighting_it_is_reporting(html):
    """Unqualified, the finding reads as the study's after a reader has moved a slider."""
    assert "weightingLabel" in html
    assert "At your weighting" in html
    assert "starting weights" in html
