"""Where the figures came from, and when.

The point of this module is that nothing here is typed by hand, so the tests
are mostly about the two ways that can fail: a date invented where no data
supports one, and a vintage that describes something other than what it labels.
"""

from __future__ import annotations

import duckdb
import pytest

from src import config as C
from src import provenance
from src.gbs_fetch import DB_PATH
from src.panel import Market, drift_window

has_db = DB_PATH.exists()
needs_db = pytest.mark.skipif(not has_db, reason=f"no postings snapshot at {DB_PATH}")


def test_a_missing_database_reports_absence_rather_than_a_date(tmp_path, monkeypatch):
    """A fresh clone must say the sample is unavailable, not remember one."""
    monkeypatch.setattr(provenance, "DB_PATH", tmp_path / "nothing.duckdb")
    assert provenance.postings_snapshot() is None
    assert provenance.as_of() == "sample not fetched"


def test_a_database_without_the_snapshots_table_is_not_a_snapshot(tmp_path, monkeypatch):
    """An older database predates the provenance table; that is absence, not a crash."""
    path = tmp_path / "bare.duckdb"
    con = duckdb.connect(str(path))
    con.execute("CREATE TABLE postings (id VARCHAR)")
    con.close()
    monkeypatch.setattr(provenance, "DB_PATH", path)
    assert provenance.postings_snapshot() is None


def test_a_second_snapshot_stops_the_page_calling_it_one(tmp_path, monkeypatch):
    """`isSnapshot` gates the wording, so it has to follow the row count."""
    path = tmp_path / "two.duckdb"
    con = duckdb.connect(str(path))
    con.execute(
        "CREATE TABLE snapshots (snapshot DATE, markets VARCHAR, "
        "max_pages INTEGER, terms INTEGER, note VARCHAR)"
    )
    con.execute("INSERT INTO snapshots VALUES ('2026-08-22', 'pl,in', 42, 5, '')")
    con.execute("INSERT INTO snapshots VALUES ('2026-09-22', 'pl,in', 42, 5, '')")
    con.execute("CREATE TABLE postings (id VARCHAR)")
    con.execute("INSERT INTO postings VALUES ('a'), ('b')")
    con.close()
    monkeypatch.setattr(provenance, "DB_PATH", path)

    snap = provenance.postings_snapshot()
    assert snap["count"] == 2
    assert snap["isSnapshot"] is False
    # The latest is what the page dates itself by.
    assert snap["date"] == "2026-09-22"
    assert snap["dateLabel"] == "22 September 2026"
    assert snap["marketCount"] == 2
    assert snap["postingsFetched"] == 2


@needs_db
def test_the_real_snapshot_is_one_point_in_time_and_says_so():
    snap = provenance.postings_snapshot()
    assert snap is not None
    assert snap["count"] >= 1
    assert snap["isSnapshot"] == (snap["count"] == 1)
    assert snap["postingsFetched"] > 0
    assert snap["marketCount"] == len(snap["markets"])
    # The terms are the sample definition; an empty list would make the
    # provenance line claim a scrape it cannot describe.
    assert snap["terms"], "search terms must be reported"
    assert snap["termCount"] >= 1
    assert snap["maxPages"] >= 1


def test_a_date_is_rendered_readably_and_a_bad_one_survives():
    assert provenance._pretty("2026-08-22") == "22 August 2026"
    assert provenance._pretty("2026-08-22T21:06:51Z") == "22 August 2026"
    assert provenance._pretty(None) is None
    # Not a date: returned as given rather than raising inside a render.
    assert provenance._pretty("not-a-date") == "not-a-date"


def test_a_span_collapses_when_every_observation_shares_a_year():
    assert provenance._span([2025, 2025, 2025]) == "2025"
    assert provenance._span([2020, 2025, 2023]) == "2020–2025"
    assert provenance._span([]) is None
    assert provenance._span([None, None]) is None


def _market(iso2: str, **kw) -> Market:
    m = Market(iso2=iso2, name=iso2, market_type="delivery")
    for k, v in kw.items():
        setattr(m, k, v)
    return m


def test_vintages_report_the_oldest_observation_not_the_freshest():
    """A 2020 wage must not hide inside a sentence that says 2025."""
    panel = {
        "a": _market("a", cost_year=2020, talent_employed_year=2025, risk_year=2024),
        "b": _market("b", cost_year=2025, talent_employed_year=2025, risk_year=2024),
    }
    v = provenance.vintages(panel)
    assert v["Cost"] == "2020–2025"
    assert v["Talent"] == "2025"
    assert v["Governance"] == "2024"


def test_a_vintage_with_nothing_behind_it_is_none():
    panel = {"a": _market("a")}
    v = provenance.vintages(panel)
    assert v["Cost"] is None and v["Region"] is None and v["Durability"] is None


def test_durability_is_dated_by_its_measurement_window_not_the_cost_year():
    """The drift is measured over up to ten years, so the cost span understates it."""
    panel = {
        "a": _market("a", cost_year=2025, drift_window=(2011, 2025)),
        "b": _market("b", cost_year=2024, drift_window=(2015, 2024)),
    }
    v = provenance.vintages(panel)
    assert v["Durability"] == "2011–2025"
    assert v["Cost"] == "2024–2025"
    assert v["Durability"] != v["Cost"]


def test_the_drift_window_is_the_one_the_rate_is_actually_measured_over():
    """Mirrors `_cagr`'s own selection, or the label would describe another window."""
    hist = {y: 100.0 * (1.03 ** (y - 2010)) for y in range(2010, 2026)}
    # Ten-year cap: 2015 rather than 2010.
    assert drift_window(hist) == (2015, 2025)
    # Too little history to measure a rate at all.
    assert drift_window({2024: 100.0, 2025: 103.0}) is None
    # A three-year minimum window.
    assert drift_window({2023: 100.0, 2024: 101.0, 2025: 102.0}) is None
    assert drift_window({2020: 100.0, 2024: 110.0, 2025: 112.0}) == (2020, 2025)


def test_the_region_vintage_only_counts_rows_that_carry_a_region():
    panel = {
        "a": _market("a", region_year="2023"),
        "b": _market("b", region_year=None),
        "c": _market("c", region_year="not a year"),
    }
    assert provenance.vintages(panel)["Region"] == "2023"


@pytest.mark.skipif(not C.POSTINGS_DB.exists(), reason="no contaminant sample")
def test_the_second_sample_is_reported_with_its_own_date():
    """It never enters the ranking, but it does enter the stability column."""
    other = provenance.contaminant_sample()
    assert other is not None
    assert other["postings"] > 0
    assert other["dateLabel"]
    assert other["repo"] == "gbs-agentic-shift"


@needs_db
def test_the_page_dates_itself_from_the_data():
    from src.dashboard import payload

    if not C.POSTINGS_DB.exists():
        pytest.skip("postings snapshot not present")
    data = payload()
    snap = provenance.postings_snapshot()
    assert data["asOf"] == snap["dateLabel"]
    assert data["provenance"]["postings"]["date"] == snap["date"]
    # Every source shows a vintage, and none of them is a placeholder.
    for s in data["sources"]:
        assert s["vintage"], s["pillar"]
        assert s["vintage"] != "None", s["pillar"]
    # And every city carries the two counts the page reports per row.
    for rows in data["views"]["city"].values():
        for row in rows:
            assert row["postings"] is not None, row["name"]
            assert row["postingsSeen"] is not None, row["name"]
            assert row["postings"] <= row["postingsSeen"], row["name"]
