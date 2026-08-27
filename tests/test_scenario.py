"""The scenario codec: a URL fragment that reproduces the exact view.

A shared link is untrusted input, so most of these tests are about the way in:
every field validated, invalid pieces costing their own default and nothing
else, floors rejected and ceilings clamped. The codec mirrors nothing in
Python — it exists only in the browser — so the tests run the page's own
JavaScript under node against the real payload.
"""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from src import config as C
from src import population
from src.dashboard import SCENARIO_JS, build_html, payload
from src.score import PILLARS

node = shutil.which("node")
pytestmark = [
    pytest.mark.skipif(node is None, reason="node not available"),
    pytest.mark.skipif(
        not (population.DB_PATH.exists() and C.POSTINGS_DB.exists()),
        reason="postings snapshot not present",
    ),
]


@pytest.fixture(scope="module")
def data() -> dict:
    return payload()


def run_js(data: dict, body: str):
    script = f"""
const DATA = {json.dumps(data)};
{SCENARIO_JS}
{body}
"""
    out = subprocess.run(
        [node, "-e", script], capture_output=True, text=True, timeout=60
    )
    if out.returncode != 0:
        raise AssertionError(out.stderr[:2000])
    return json.loads(out.stdout.strip().splitlines()[-1])


def decode(data: dict, fragment: str) -> dict:
    return run_js(data, f"console.log(JSON.stringify(decodeScenario({json.dumps(fragment)})));")


def test_a_full_view_survives_the_round_trip(data):
    """Encode, decode, and every field including a unicode name comes back."""
    got = run_js(data, """
const s = {
  archetype: Object.keys(DATA.archetypes)[1],
  weights: Object.fromEntries(DATA.pillars.map((p, i) => [p, (i + 2) / 100])),
  hq: "new-york", baseline: "gb", fte: 250,
  loading: 0.30, attrition: 0.20, horizon: 5,
  scenario: "Steering – 3 Sep „Basisfall”",
};
console.log(JSON.stringify(decodeScenario(encodeScenario(s))));
""")
    assert got["archetype"] == list(data["archetypes"])[1]
    assert got["weights"] == {p: (i + 2) / 100 for i, p in enumerate(PILLARS)}
    assert got["hq"] == "new-york" and got["baseline"] == "gb"
    assert got["fte"] == 250 and got["horizon"] == 5
    assert got["loading"] == pytest.approx(0.30)
    assert got["attrition"] == pytest.approx(0.20)
    assert got["name"] == "Steering – 3 Sep „Basisfall”"


def test_the_untouched_page_keeps_a_clean_url(data):
    """The default state encodes as default, so the address bar stays empty."""
    got = run_js(data, """
const d = defaultScenarioState();
console.log(JSON.stringify({
  isDefault: isDefaultScenario(d),
  named: isDefaultScenario({...d, scenario: "x"}),
  moved: isDefaultScenario({...d, fte: 101}),
}));
""")
    assert got["isDefault"] is True
    # A name or a moved control is a view worth a URL.
    assert got["named"] is False
    assert got["moved"] is False


def test_garbage_and_wrong_versions_decode_to_nothing(data):
    assert decode(data, "") == {}
    assert decode(data, "not&even=parseable%%%") == {}
    assert decode(data, "v=2&a=transactional_hub&f=200") == {}, "future version ignored whole"


def test_each_invalid_field_costs_only_itself(data):
    frag = "v=1&a=no_such_archetype&hq=atlantis&o=xx&f=250"
    got = decode(data, frag)
    assert "archetype" not in got and "hq" not in got and "baseline" not in got
    assert got["fte"] == 250, "the one valid field survives its invalid neighbours"


def test_weights_are_whole_or_not_at_all(data):
    n = len(PILLARS)
    ok = "-".join(["10"] * n)
    assert "weights" in decode(data, f"v=1&w={ok}")
    assert "weights" not in decode(data, "v=1&w=10-10-10"), "wrong length"
    assert "weights" not in decode(data, f"v=1&w={'-'.join(['70'] * n)}"), "over the slider max"
    assert "weights" not in decode(data, f"v=1&w={'-'.join(['0'] * n)}"), "all zero is no weighting"
    assert "weights" not in decode(data, "v=1&w=" + "-".join(["x"] * n)), "not numbers"


def test_floors_reject_and_ceilings_clamp(data):
    """A link saying 999,999 roles meant a lot; one saying minus four meant nothing."""
    got = decode(data, "v=1&f=999999&l=999&t=999&y=99")
    assert got["fte"] == 5000
    assert got["loading"] == pytest.approx(C.LOADING_FACTOR_MAX)
    assert got["attrition"] == pytest.approx(C.ATTRITION_UPLIFT_MAX)
    assert got["horizon"] == C.HORIZON_YEARS_MAX
    bad = decode(data, "v=1&f=0&l=-5&y=-1")
    assert "fte" not in bad and "loading" not in bad and "horizon" not in bad


def test_the_name_is_trimmed_and_capped(data):
    got = decode(data, "v=1&n=" + "%20%20abc%20%20")
    assert got["name"] == "abc"
    long = decode(data, "v=1&n=" + "x" * 200)
    assert len(long["name"]) == 60
    assert "name" not in decode(data, "v=1&n=%20%20")


def test_the_page_ships_the_scenario_controls(data):
    html = build_html()
    for hook in ('id="scenario-list"', 'id="scenario-name"', 'id="scenario-save"',
                 'id="scenario-delete"', 'id="copy-link"', 'id="scenario-tag"',
                 "decodeScenario(location.hash", 'addEventListener("hashchange"'):
        assert hook in html, hook
    # The static document names where saved views would appear, rather than
    # shipping an empty select.
    assert "— saved on this device —" in html
    # The paste-into-an-open-page path reads the event's own URL: a render
    # between the change and the handler replaceStates the old fragment back.
    assert "e.newURL" in html


# ---- client figures in the fragment ---------------------------------------

def city_id(data: dict) -> str:
    return data["views"]["city"][next(iter(data["archetypes"]))][0]["id"]


def test_overrides_survive_the_round_trip(data):
    """Two cities, three fields, a unicode source — everything comes back."""
    got = run_js(data, """
const rows = DATA.views.city[Object.keys(DATA.archetypes)[0]];
const s = defaultScenarioState();
s.overrides = {
  [rows[0].id]: {
    w: {v: 4200, source: "Recruiter – Hays Kraków", date: "2026-08-27"},
    t: {v: 22, source: "Provider RFI", date: "2026-08-26"},
  },
  [rows[1].id]: {l: {v: 34, source: "Payroll schedule", date: "2026-08-20"}},
};
console.log(JSON.stringify(decodeScenario(encodeScenario(s)).overrides));
""")
    rows = data["views"]["city"][next(iter(data["archetypes"]))]
    a, b = rows[0]["id"], rows[1]["id"]
    assert got[a]["w"] == {"v": 4200, "source": "Recruiter – Hays Kraków", "date": "2026-08-27"}
    assert got[a]["t"]["v"] == 22
    assert got[b]["l"] == {"v": 34, "source": "Payroll schedule", "date": "2026-08-20"}


def test_a_figure_without_a_source_is_dropped(data):
    """The source is the tier: without one it is an assumption, not a figure."""
    cid = city_id(data)
    frag = f"v=1&x={cid}~w~4200~2026-08-27~%20%20"
    assert "overrides" not in decode(data, frag)


def test_each_invalid_override_is_dropped_alone(data):
    cid = city_id(data)
    frag = ("v=1"
            f"&x=nowhere:Utopia~w~4200~2026-08-27~src"      # unknown city
            f"&x={cid}~z~4200~2026-08-27~src"                # unknown field
            f"&x={cid}~w~0~2026-08-27~src"                   # wage floor
            f"&x={cid}~w~abc~2026-08-27~src"                 # not a number
            f"&x={cid}~w~4200~yesterday~src"                 # not a date
            f"&x={cid}~t~22~2026-08-27~ok")                  # the one valid entry
    got = decode(data, frag)
    assert got["overrides"] == {cid: {"t": {"v": 22, "source": "ok", "date": "2026-08-27"}}}


def test_override_ceilings_clamp_and_tildes_cannot_break_the_format(data):
    cid = city_id(data)
    got = decode(data, f"v=1&x={cid}~w~999999~2026-08-27~src&x={cid}~l~400~2026-08-27~src")
    assert got["overrides"][cid]["w"]["v"] == 99999
    assert got["overrides"][cid]["l"]["v"] == round(C.LOADING_FACTOR_MAX * 100)
    # A tilde in the source would shift every later field; encoding strips it.
    enc = run_js(data, f"""
const s = defaultScenarioState();
s.overrides = {{{json.dumps(city_id(data))}: {{w: {{v: 4200, source: "a~b~c", date: "2026-08-27"}}}}}};
console.log(JSON.stringify(decodeScenario(encodeScenario(s)).overrides));
""")
    assert enc[cid]["w"]["source"] == "a b c"


def test_a_view_with_figures_is_never_the_default_view(data):
    got = run_js(data, f"""
const s = defaultScenarioState();
s.overrides = {{{json.dumps(city_id(data))}: {{w: {{v: 4200, source: "x", date: "2026-08-27"}}}}}};
console.log(JSON.stringify(isDefaultScenario(s)));
""")
    assert got is False


def test_the_quoted_wage_reaches_the_ranking(data):
    """pillarValues reads the override, so scoring, bands and the MC all see it."""
    from src.dashboard import SCORING_JS

    cid = city_id(data)
    script = f"""
const DATA = {json.dumps(data)};
const state = {{hq: DATA.hq, overrides: {{{json.dumps(cid)}: {{w: {{v: 123, source: "s", date: "2026-08-27"}}}}}}}};
{SCORING_JS}
const rows = DATA.views.city[Object.keys(DATA.archetypes)[0]];
const items = pillarValues(rows);
const hit = items.find((it) => it.row.id === {json.dumps(cid)});
const other = items.find((it) => it.row.id !== {json.dumps(cid)});
console.log(JSON.stringify({{cost: hit.v.cost, otherUntouched: other.v.cost === other.row.cost}}));
"""
    out = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr[:1500]
    got = json.loads(out.stdout.strip().splitlines()[-1])
    assert got["cost"] == 123
    assert got["otherUntouched"] is True
