"""Which pillars is the answer actually hostage to?

Seven pillars are declared and weighted, and it does not follow that seven
pillars decide anything. A pillar whose removal leaves the shortlist untouched
is not carrying the result — it is decoration with a weight attached, and a
reader is entitled to know which is which before arguing about its number.

The question matters most for capability. It is the only pillar built from this
project's own classifier rather than an official statistic, it carries the
classification error corrected in `stability.py` and the subset bias measured in
`validate.py`, and it is what moved India ahead of Germany. If the answer does
not need it, that reversal is far less interesting than it looked. If it does,
the error and bias in it matter more than any other input here.

Each pillar is removed in turn — its weight set to zero and the rest
renormalised — and the top band is compared with the declared weighting.
"""

from __future__ import annotations

from src import config as C
from src.panel import build, with_centres
from src.score import PILLARS
from src.stability import run


def top_band(panel, archetype: str, weights: dict[str, float]) -> list[str]:
    result = run(panel, archetype, weights=weights)
    return sorted(panel[k].name for k in result.band if result.band[k] == 1)


def main() -> None:
    panel = build()
    cities = {k: m for k, m in with_centres(panel).items() if m.is_city and m.complete}

    for archetype, spec in C.ARCHETYPES.items():
        declared = spec["weights"]
        baseline = top_band(cities, archetype, declared)
        print(f"\n=== {spec['label']}")
        print(f"  declared top band: {', '.join(baseline)}\n")
        print(f"  {'pillar removed':18}{'top band':10}  what changes")

        for pillar in PILLARS:
            remaining = {p: w for p, w in declared.items() if p != pillar}
            total = sum(remaining.values())
            if total <= 0:
                continue
            without = {p: w / total for p, w in remaining.items()}
            without[pillar] = 0.0
            band = top_band(cities, archetype, without)

            if band == baseline:
                print(f"  {pillar:18}{'unchanged':10}  —")
            else:
                gone = [c for c in baseline if c not in band]
                new = [c for c in band if c not in baseline]
                bits = []
                if gone:
                    bits.append("drops " + ", ".join(gone))
                if new:
                    bits.append("adds " + ", ".join(new))
                print(f"  {pillar:18}{'CHANGED':10}  {'; '.join(bits)}")


if __name__ == "__main__":
    main()
