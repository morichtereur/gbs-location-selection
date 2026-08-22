"""The study population: GBS and GCC finance postings, classified two ways.

Every posting that survives here has passed two independent classifiers, each
answering a different question:

- `src/delivery.py` — is this shared-services or capability-centre work, and
  which delivery model? Its precision is measured in `eval/precision_audit.md`
  at roughly 80% on a twenty-posting audit.
- the work-family taxonomy from the sibling GBS Agentic Shift study, loaded by
  file path rather than reimplemented — is this transactional or judgment work?

Reusing the second rather than writing a new one keeps the capability pillar
speaking the same language as the study it came from, even though the sample
underneath it has been replaced.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from functools import lru_cache

import duckdb

from src import config as C
from src.delivery import IN_SCOPE, _org_type, classify
from src.gbs_fetch import DB_PATH


@dataclass
class Posting:
    country: str
    city: str | None
    company: str
    model: str      # 'gcc' or 'gbs'
    family: str     # 'transactional', 'judgment', 'agent_ops' or 'ambiguous'


def _taxonomy():
    path = C.POSTINGS_DB.parent.parent / "src" / "taxonomy.py"
    if not path.exists():
        raise FileNotFoundError(
            f"work-family taxonomy not found at {path}. This project reuses the "
            "gbs-agentic-shift taxonomy; clone that repository alongside it."
        )
    spec = importlib.util.spec_from_file_location("shift_taxonomy", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # Registered before execution: the module defines a dataclass, and
    # @dataclass resolves its own module out of sys.modules while the class
    # body runs. Without this it raises on a None lookup.
    sys.modules["shift_taxonomy"] = module
    spec.loader.exec_module(module)
    return module.classify_text


def _clean_city(location: str | None) -> str | None:
    from src.centres import COUNTRY_ONLY

    if not location:
        return None
    city = location.split(",")[0].strip()
    if len(city) < 2 or city.lower() in COUNTRY_ONLY:
        return None
    return C.CITY_ALIASES.get(city.lower(), city)


@lru_cache(maxsize=1)
def load() -> tuple[Posting, ...]:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"{DB_PATH} not found. Run `make fetch` to build the GBS/GCC sample "
            "(needs free Adzuna API credentials)."
        )
    org_type = _org_type()
    classify_text = _taxonomy()
    con = duckdb.connect(str(DB_PATH), read_only=True)
    rows = con.execute(
        "SELECT country, title, description, company, location FROM postings"
    ).fetchall()
    con.close()

    out: list[Posting] = []
    for country, title, description, company, location in rows:
        model = classify(title, description, company, org_type)
        if model not in IN_SCOPE:
            continue
        result = classify_text(f"{title or ''} || {description or ''}")
        out.append(
            Posting(
                country=country,
                city=_clean_city(location),
                company=(company or "").strip().lower(),
                model=model,
                family="ambiguous" if result.ambiguous else result.label,
            )
        )
    return tuple(out)


def shares(postings) -> dict:
    """Work-family shares over the postings the taxonomy could decide.

    Ambiguous postings are excluded from the denominator and reported
    separately: folding them into either family would invent a decision the
    taxonomy explicitly declined to make.
    """
    decided = [p for p in postings if p.family in ("transactional", "judgment", "agent_ops")]
    n = len(decided)
    if n == 0:
        return {"n": 0, "n_all": len(postings)}
    return {
        "n": n,
        "n_all": len(postings),
        "ambiguous_share": 1 - n / len(postings) if postings else 0.0,
        "transactional_share": sum(p.family == "transactional" for p in decided) / n,
        "judgment_share": sum(p.family == "judgment" for p in decided) / n,
        "agent_ops_share": sum(p.family == "agent_ops" for p in decided) / n,
        "gcc_share": sum(p.model == "gcc" for p in decided) / n,
        "employers": len({p.company for p in decided}),
    }
