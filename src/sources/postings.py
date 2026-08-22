"""Capability pillar: what GBS and GCC work each market demonstrably staffs.

Every commercial location index measures talent *supply*. This measures what
the market actually hires for, and it is the one pillar here not available off
the shelf.

The population is the GBS/GCC sample in `src/population.py`, not the broader
finance-operations sample this project started with. That change matters: only
13% of the original 2,159 postings carried any shared-services signal, so the
capability pillar was previously describing retained finance in nine cases out
of ten. Filtering raises the transactional share in every market — Poland from
43% to 63% — because the dilution is gone.

The cost is sample size. Switzerland contributes five decided postings and the
Netherlands nine, against 88 and 154 before. Those shares are estimates with
very wide intervals, which is why the Monte Carlo redraws every one of them
from its own binomial rather than treating any as exact.
"""

from __future__ import annotations

from src import config as C
from src.population import load, shares


def load_market_shares() -> dict[str, dict]:
    postings = load()
    out: dict[str, dict] = {}
    for iso2 in C.MARKETS:
        stats = shares([p for p in postings if p.country == iso2])
        if stats["n"] == 0:
            continue
        out[iso2] = {
            "postings_in_scope": stats["n"],
            "postings_fetched": stats["n_all"],
            "ambiguous_share": stats["ambiguous_share"],
            "transactional_share": stats["transactional_share"],
            "judgment_share": stats["judgment_share"],
            "agent_ops_share": stats["agent_ops_share"],
            "gcc_share": stats["gcc_share"],
            "language_share": stats["language_share"],
            "languages": stats["languages"],
            "employers": stats["employers"],
            "year": 2026,
            "source": "Adzuna GBS/GCC sample, classified by src/delivery.py",
        }
    return out


# Kept under the original name so the panel does not need to know the source
# changed underneath it.
def load_() -> dict[str, dict]:  # pragma: no cover - alias
    return load_market_shares()
