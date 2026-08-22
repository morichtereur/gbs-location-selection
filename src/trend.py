"""Direction, once there is more than one snapshot to compare.

A single point-in-time sample cannot say whether a market is growing, and that
is the question a location decision actually turns on — a hub adding employers
is a different proposition from one shedding them at the same cost.

Nothing here infers a trend from one snapshot. With one it says so and stops.
Run `make fetch` again in a month and this starts answering.
"""

from __future__ import annotations

import duckdb

from src import config as C
from src.delivery import IN_SCOPE, _org_type, classify
from src.gbs_fetch import DB_PATH


def snapshot_dates() -> list[str]:
    if not DB_PATH.exists():
        return []
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        rows = con.execute(
            "SELECT CAST(snapshot AS VARCHAR) FROM main.snapshots ORDER BY snapshot"
        ).fetchall()
    except duckdb.CatalogException:
        return []
    finally:
        con.close()
    return [r[0] for r in rows]


def per_snapshot() -> dict[str, dict[str, dict]]:
    """In-scope postings and distinct employers, per market, per snapshot."""
    org_type = _org_type()
    con = duckdb.connect(str(DB_PATH), read_only=True)
    rows = con.execute(
        """
        SELECT CAST(o.snapshot AS VARCHAR), p.country, p.title, p.description, p.company
        FROM main.observations o JOIN main.postings p USING (id)
        """
    ).fetchall()
    con.close()

    out: dict[str, dict[str, dict]] = {}
    for snapshot, country, title, description, company in rows:
        if classify(title, description, company, org_type) not in IN_SCOPE:
            continue
        rec = out.setdefault(snapshot, {}).setdefault(
            country, {"postings": 0, "employers": set()}
        )
        rec["postings"] += 1
        rec["employers"].add((company or "").strip().lower())
    return out


def main() -> None:
    snaps = snapshot_dates()
    if not snaps:
        print("No snapshots recorded yet. Run `make fetch`.")
        return
    if len(snaps) == 1:
        counts = per_snapshot().get(snaps[0], {})
        print(f"One snapshot held ({snaps[0]}). A trend needs at least two.\n")
        print(f"{'market':16}{'in-scope':>10}{'employers':>11}")
        for iso2 in sorted(counts, key=lambda k: -counts[k]["postings"]):
            rec = counts[iso2]
            print(f"  {C.MARKETS[iso2]['name']:14}{rec['postings']:10}"
                  f"{len(rec['employers']):11}")
        print("\nRun `make fetch` again in a month to start measuring direction.")
        return

    data = per_snapshot()
    first, last = snaps[0], snaps[-1]
    print(f"Change from {first} to {last}\n")
    print(f"{'market':16}{'postings':>20}{'employers':>20}")
    for iso2 in C.MARKETS:
        a = data.get(first, {}).get(iso2)
        b = data.get(last, {}).get(iso2)
        if not a or not b:
            continue
        dp = b["postings"] - a["postings"]
        de = len(b["employers"]) - len(a["employers"])
        print(f"  {C.MARKETS[iso2]['name']:14}"
              f"{a['postings']:>8} → {b['postings']:<4} {dp:+4}"
              f"{len(a['employers']):>8} → {len(b['employers']):<4} {de:+4}")


if __name__ == "__main__":
    main()
