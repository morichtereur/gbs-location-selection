"""What the document says before any script runs.

The page is written by JavaScript, so the file as shipped used to be a set of
empty tags and half-finished sentences. `src/fallback.py` renders the declared
scenario into it at build time, which makes this the fourth place a piece of
the page exists twice — and, like the other three, it is bound by running the
page's own code and requiring the two to agree.

They are compared on what they *say*, not byte for byte. The live stability
meter runs 2,000 draws in the browser against 10,000 in Python, so the
percentages differ in the last point or two by construction; asserting equality
there would force one of the two to lie. Cities, bands, order and prose are
asserted exactly, because those must not differ at all.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess

import pytest

from src import config as C
from src import fallback, population
from src.dashboard import SCENARIO_JS, SCORING_JS, TEMPLATE, build_html, payload

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node not available")
pytestmark = pytest.mark.skipif(
    not (population.DB_PATH.exists() and C.POSTINGS_DB.exists()),
    reason="postings snapshot not present",
)


@pytest.fixture(scope="module")
def data() -> dict:
    return payload()


@pytest.fixture(scope="module")
def html() -> str:
    return build_html()


@pytest.fixture(scope="module")
def slots(data) -> dict:
    return fallback.slots(data)


def text(markup: str) -> str:
    """Visible text, with tags and runs of whitespace collapsed."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", "", markup)).strip()


# --- the defect this fixes -------------------------------------------------

def test_no_slot_ships_empty(html):
    """The original defect: 'at least ___ postings behind it' in the shipped file."""
    # The scenario tag is empty by design at the default view — it carries a
    # name only once the reader has given the view one.
    allowed_empty = {"scenario-tag"}
    empties = re.findall(
        r'id="([a-z-]+)"\s*>\s*</(?:span|div|p|ul|dl|table|h2|h3|select)>', html
    )
    assert [e for e in empties if e not in allowed_empty] == [], empties


def test_the_broken_sentences_are_complete(html):
    body = text(html[html.index("<body>"):])
    assert "at least 10 postings behind it" in body
    assert "in at least 65% of runs" in body
    # And the eyebrow is a sentence rather than two separators round a hole.
    assert "11 GBS and GCC cities · 7 pillars · one snapshot" in body


def test_the_finding_is_readable_without_script(html):
    body = text(html[html.index("<body>"):])
    assert "finish level at the top" in body
    assert "At the transactional hub’s starting weights" in body
    for city in ("Mumbai", "Chennai", "Pune", "Bangalore", "Hyderabad"):
        assert city in body


def test_every_exhibit_has_content_before_script(slots):
    for key in ("rows", "case", "table", "beyond", "tzstrip", "corr",
                "limits", "sources", "settles-yes", "settles-no", "sliders",
                "next", "next-note"):
        assert slots[key].strip(), key


def test_the_form_controls_carry_their_defaults(html):
    """An empty select reads as broken even when nothing can be selected."""
    assert 'value="100"' in html            # roles moved
    assert 'value="25"' in html             # employer loading, per cent
    assert 'value="15"' in html             # attrition backfill, per cent
    assert re.search(r'id="horizon"[^>]*value="0"', html)
    assert '<option value="zurich" selected>' in html
    assert '<option value="ch" selected>' in html


def test_one_row_per_city_everywhere_a_city_is_listed(data, slots):
    n = len(data["views"]["city"][next(iter(data["archetypes"]))])
    assert slots["rows"].count('class="row') == n
    assert slots["case"].count('class="case-row"') == n
    assert slots["table"].count("<tr>") == n + 1  # + the header row


# --- parity with the page's own rendering ---------------------------------

def _render_under_node(data: dict) -> dict:
    """Run the page's render functions against a DOM shim and collect the slots.

    Only the pure functions in SCORING_JS plus the page script's own renderers
    are needed, so the script is taken from the built document and the handful
    of browser APIs it touches on the way through are stubbed.
    """
    script = TEMPLATE[TEMPLATE.rindex("<script>") + len("<script>"):]
    script = script[:script.rindex("</script>")]
    script = (script.replace("__DATA__", json.dumps(data))
              .replace("__SCORING__", SCORING_JS)
              .replace("__SCENARIO__", SCENARIO_JS))
    harness = """
const sink = {};
// Exhibit 1 is built by creating elements and appending them, not by setting
// innerHTML, so the shim has to collect children as well as markup or the
// ranking never reaches the comparison.
const node = () => ({
  _h: "", _kids: [],
  set innerHTML(v) { this._h = v; this._kids = []; },
  get innerHTML() { return this._h; },
  set textContent(v) { this._h = v; }, get textContent() { return this._h; },
  set value(v) { this._v = v; }, get value() { return this._v; },
  html() { return this._h + this._kids.map((k) => k.html()).join(""); },
  style: {}, dataset: {}, classList: {add(){}, remove(){}},
  addEventListener() {}, setAttribute() {}, removeAttribute() {},
  querySelector: () => node(), querySelectorAll: () => [],
  appendChild(k) { this._kids.push(k); },
  closest: () => node(), getBoundingClientRect: () => ({top: 0}),
  focus() {}, open: false,
});
// The page declares its own `const $ = (s) => document.querySelector(s)`, which
// shadows anything defined here — so the cache has to live in querySelector
// itself. Stubbing `$` looked like it worked and quietly captured nothing.
globalThis.document = {
  createElement: () => node(),
  querySelector: (s) => (sink[s] = sink[s] || node()),
  querySelectorAll: () => [], documentElement: {getAttribute: () => "light",
  setAttribute() {}}, addEventListener() {},
};
globalThis.matchMedia = () => ({matches: false, addEventListener() {}});
globalThis.window = {addEventListener() {}, print() {}, scrollY: 0};
// The scenario layer reads the URL at load and writes it on every render.
globalThis.location = {hash: "", pathname: "/", search: "", href: "http://local/"};
globalThis.history = {replaceState() {}};
// Never fired: the row animation schedules work through it, and calling it
// synchronously re-enters the render it was scheduled from.
globalThis.requestAnimationFrame = () => 0;
globalThis.MutationObserver = class { observe() {} disconnect() {} };
globalThis.getComputedStyle = () => ({getPropertyValue: () => ""});
globalThis.navigator = {clipboard: {writeText: async () => {}}};
"""
    tail = """
render();
const out = {};
for (const [k, v] of Object.entries(sink)) out[k.replace('#','')] = v.html();
console.log("@@" + JSON.stringify(out));
"""
    out = subprocess.run(
        [node, "-e", harness + script + tail],
        capture_output=True, text=True, timeout=180,
    )
    # A failure here, never a skip: the shim is ours to maintain, and a skip
    # once hid a page-script regression behind a green run.
    assert out.returncode == 0, (
        "page script failed under the DOM shim — extend the shim in this file:\n"
        + out.stderr.strip()[-1500:]
    )
    line = [x for x in out.stdout.splitlines() if x.startswith("@@")]
    assert line, "render() produced no slots under the shim"
    return json.loads(line[-1][2:])


@needs_node
def test_the_fallback_and_the_page_say_the_same_thing(data, slots):
    """Prose slots must match word for word: these are the page's claims."""
    live = _render_under_node(data)
    keys = ("headline", "takeaway", "board-title", "belief", "corr-why",
            "exhibit-source", "foot", "case-title", "beyond-note",
            "beyond-more", "case-caveat", "corr-read", "next", "next-note")
    missing = [k for k in keys if not live.get(k)]
    assert not missing, f"the page rendered nothing for {missing}"
    for key in keys:
        assert text(slots[key]) == text(live[key]), key


@needs_node
def test_the_fallback_ranks_the_cities_the_page_ranks(data, slots):
    """Order and banding, which must not differ even by one place."""
    live = _render_under_node(data)
    assert live.get("rows"), "the page rendered no ranking under the shim"
    names = lambda m: re.findall(r'class="nm">(?:<svg.*?</svg>)?([^<]+)<', m)  # noqa: E731
    assert names(slots["rows"]) == names(live["rows"])
    bands = lambda m: re.findall(r'class="rank">([^<]*)<', m)  # noqa: E731
    assert bands(slots["rows"]) == bands(live["rows"])


# --- the link preview ------------------------------------------------------

def test_the_page_has_a_description_and_a_card(html):
    head = html[:html.index("</head>")]
    for tag in ('name="description"', 'property="og:title"',
                'property="og:description"', 'property="og:image"',
                'property="og:url"', 'name="twitter:card"'):
        assert tag in head, tag
    assert 'content="summary_large_image"' in head
    assert 'property="og:image:width" content="1200"' in head
    assert 'property="og:image:height" content="630"' in head


def test_the_description_states_the_finding_rather_than_the_subject(html):
    m = re.search(r'<meta name="description" content="([^"]+)"', html)
    assert m, "no description"
    desc = m.group(1)
    assert "Mumbai" in desc and "cannot separate them" in desc
    assert "starting weights" in desc
    # Long enough to be useful, short enough not to be truncated to nothing.
    assert 120 <= len(desc) <= 400, len(desc)


def test_the_card_image_is_an_absolute_https_url(html):
    """A data: URI is rejected by every crawler that matters."""
    m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
    assert m and m.group(1).startswith("https://"), m and m.group(1)
    assert m.group(1).endswith(".png")


def test_the_card_renders_at_the_size_the_tags_promise(data, tmp_path):
    png = pytest.importorskip("PIL.Image", reason="Pillow not installed")
    from src.og import HEIGHT, WIDTH, render

    path = render(data, tmp_path / "og.png")
    assert path.exists() and path.stat().st_size > 5_000
    with png.open(path) as im:
        assert im.size == (WIDTH, HEIGHT)


def test_the_card_is_drawn_from_the_same_scenario_as_the_page(data):
    """One rendering of Exhibit 1 can drift from the other; the scenario cannot."""
    from src.og import render

    s = fallback.Scenario(data)
    # Smoke: it draws without raising, for the same order the page shows.
    assert [r["name"] for r in s.order][:5] == [r["name"] for r in s.top]
    render(data, C.DATA / "og.png")
