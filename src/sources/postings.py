"""Demand side, from the GBS Agentic Shift postings snapshot.

Every location index on the market measures talent *supply*. None of them
measure who else is already hiring that talent in the same market, or what
kind of work that market demonstrably staffs. This pillar is the one input
here that is not available off the shelf.

One hard constraint shapes what can be read off it. The snapshot was fetched
with a per-country page cap, so posting counts are censored from above: India
at 295 and Switzerland at 108 reflects the cap being hit in one and not the
other, not the true size of either market. Every metric below is therefore a
*ratio* within a country's own sample, which the cap does not distort.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import duckdb

from src import config as C

# The org-type classifier lives in the other repository and is reused rather
# than reimplemented, so the two studies cannot drift apart on who counts as
# a provider.
_SHIFT_ROOT = C.POSTINGS_DB.parent.parent


def _org_type():
    """Load orgtype.py from the sibling repository by path.

    Not a plain import: both repositories call their package `src`, so an
    ordinary `from src.orgtype import ...` resolves to this one and fails.
    """
    module_path = _SHIFT_ROOT / "src" / "orgtype.py"
    if not module_path.exists():
        raise FileNotFoundError(
            f"org-type classifier not found at {module_path}. This pillar "
            "reuses the gbs-agentic-shift classifier so the two studies "
            "cannot drift apart on who counts as a provider."
        )
    spec = importlib.util.spec_from_file_location("shift_orgtype", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.org_type


def load(db_path: Path | None = None) -> dict[str, dict]:
    path = db_path or C.POSTINGS_DB
    if not path.exists():
        raise FileNotFoundError(
            f"postings snapshot not found at {path}. This pillar reuses the "
            "gbs-agentic-shift sample; clone that repository alongside this one."
        )
    org_type = _org_type()
    con = duckdb.connect(str(path), read_only=True)
    rows = con.execute(
        """
        SELECT p.country, p.company, l.label
        FROM postings p JOIN labels l USING (id)
        WHERE l.label IN ('transactional', 'judgment', 'agent_ops')
        """
    ).fetchall()
    con.close()

    agg: dict[str, dict] = {}
    for country, company, label in rows:
        kind = org_type(company)
        if kind == "advisory":
            # Advises on GBS rather than performing it — a different labour
            # market that matches the same search terms.
            continue
        rec = agg.setdefault(
            country,
            {"n": 0, "transactional": 0, "judgment": 0, "agent_ops": 0,
             "bpo": 0, "companies": set()},
        )
        rec["n"] += 1
        rec[label] += 1
        rec["bpo"] += 1 if kind == "bpo" else 0
        rec["companies"].add((company or "").strip().lower())

    out: dict[str, dict] = {}
    for iso2, rec in agg.items():
        if iso2 not in C.MARKETS or rec["n"] == 0:
            continue
        n = rec["n"]
        out[iso2] = {
            "postings_in_scope": n,
            "transactional_share": rec["transactional"] / n,
            "judgment_share": rec["judgment"] / n,
            "agent_ops_share": rec["agent_ops"] / n,
            # An established outsourcing ecosystem: providers already deliver
            # this work here, so the operating pattern is proven locally.
            "bpo_share": rec["bpo"] / n,
            # Distinct employers per posting. Low means a few large employers
            # dominate hiring — a market that is easier to enter and harder to
            # retain in.
            "employer_fragmentation": len(rec["companies"]) / n,
            "year": 2026,
            "source": "gbs-agentic-shift snapshot",
        }
    return out
