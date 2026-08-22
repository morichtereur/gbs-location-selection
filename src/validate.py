"""Is the subset the capability pillar can read representative of the whole?

The work-family taxonomy decides about two thirds of in-scope postings and
declines the rest, and the shares are computed on what it can read. That is only
safe if the readable subset resembles the unreadable one, and nothing in this
study checked whether it does.

It does not. Postings that only the local-language supplement can decide run far
more transactional than the ones the English taxonomy handles, which says the
undecided remainder — largely non-English — is being left out of a measure it
would move.

This bounds the damage rather than modelling it away: the supplement's own mix
is a small sample, too thin to build a prior on, but strong enough to ask what
happens if every undecided posting looked like it. `make validate` prints the
answer and checks whether the study's headline output survives.
"""

from __future__ import annotations

import collections
import dataclasses

import duckdb

from src import config as C
from src import workfamily
from src.centres import _clean
from src.delivery import IN_SCOPE, _org_type, classify
from src.gbs_fetch import DB_PATH
from src.panel import build, with_centres
from src.population import _taxonomy
from src.stability import run


def routes() -> tuple[collections.Counter, dict, dict]:
    """Which classifier decided each posting, and what it said."""
    org_type, classify_text = _org_type(), _taxonomy()
    con = duckdb.connect(str(DB_PATH), read_only=True)
    rows = con.execute(
        "SELECT country, title, description, company, location FROM postings"
    ).fetchall()
    con.close()

    route = collections.Counter()
    family_by_route = collections.defaultdict(collections.Counter)
    per_place = collections.defaultdict(lambda: {"t": 0, "j": 0, "u": 0})

    for country, title, description, company, location in rows:
        if classify(title, description, company, org_type) not in IN_SCOPE:
            continue
        text = f"{title or ''} || {description or ''}"
        result = classify_text(text)
        if not result.ambiguous:
            which, family = "english taxonomy", result.label
        else:
            family = workfamily.decide(text)
            which = "local supplement" if family else "undecided"
        route[which] += 1
        if family in ("transactional", "judgment"):
            family_by_route[which][family] += 1

        for key in ((country, None), (country, _clean(location))):
            if key[1] is None and key[0] is None:
                continue
            bucket = per_place[key]
            if family == "transactional":
                bucket["t"] += 1
            elif family == "judgment":
                bucket["j"] += 1
            elif family != "agent_ops":
                bucket["u"] += 1
    return route, family_by_route, per_place


def supplement_mix(family_by_route) -> float | None:
    counts = family_by_route.get("local supplement")
    total = sum(counts.values()) if counts else 0
    return counts["transactional"] / total if total else None


def main() -> None:
    route, family_by_route, per_place = routes()
    total = sum(route.values())
    print(f"In-scope postings: {total}\n")
    print("Decided by:")
    for name, count in route.most_common():
        print(f"  {name:20}{count:5}  ({count / total:.0%})")

    print("\nTransactional share, by which classifier could read the posting:")
    for name in ("english taxonomy", "local supplement"):
        counts = family_by_route.get(name)
        n = sum(counts.values()) if counts else 0
        if n:
            print(f"  {name:20}{counts['transactional'] / n:5.0%}  (n={n})")

    supp = supplement_mix(family_by_route)
    if supp is None:
        print("\nNo supplement-decided postings; nothing to bound against.")
        return

    print(
        f"\nThe gap is the warning: postings only the supplement can read run "
        f"{supp:.0%} transactional.\nIf every undecided posting looked like them, "
        "each market's share would move:"
    )
    print(f"\n  {'market':8}{'measured':>10}{'bounded':>10}{'shift':>9}")
    for iso2 in sorted(C.MARKETS):
        rec = per_place.get((iso2, None))
        if not rec:
            continue
        decided = rec["t"] + rec["j"]
        if not decided:
            continue
        measured = rec["t"] / decided
        bounded = (rec["t"] + supp * rec["u"]) / (decided + rec["u"])
        print(f"  {iso2:8}{measured:10.0%}{bounded:10.0%}{(bounded - measured) * 100:+8.0f}pp")

    print("\nDoes the headline output survive that bound?")
    panel = build()
    base = {k: m for k, m in with_centres(panel).items() if m.is_city and m.complete}
    for archetype in C.ARCHETYPES:
        now = run(base, archetype)
        bounded_panel = {}
        for key, market in base.items():
            copy = dataclasses.replace(market)
            rec = per_place.get((market.parent, market.name))
            n = (rec["t"] + rec["j"] + rec["u"]) if rec else 0
            if n:
                share = (rec["t"] + supp * rec["u"]) / n
                prior = C.CAPABILITY_PRIOR_STRENGTH
                national = market.capability_shrunk_from or share
                copy.transactional_share = (n * share + prior * national) / (n + prior)
                copy.judgment_share = 1.0 - copy.transactional_share
            bounded_panel[key] = copy
        alt = run(bounded_panel, archetype)
        top_now = sorted(base[k].name for k in now.band if now.band[k] == 1)
        top_alt = sorted(bounded_panel[k].name for k in alt.band if alt.band[k] == 1)
        verdict = "unchanged" if top_now == top_alt else "CHANGED"
        print(f"\n  {C.ARCHETYPES[archetype]['label']}: top band {verdict}")
        print(f"    measured: {', '.join(top_now)}")
        if top_now != top_alt:
            print(f"    bounded : {', '.join(top_alt)}")


if __name__ == "__main__":
    main()
