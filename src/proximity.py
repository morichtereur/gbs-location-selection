"""Overlapping working hours between a market and the declared headquarters.

Deterministic: no source to be stale, no estimate to resample. A market's
working day is projected into headquarters time and intersected with the
headquarters working day. Eight hours means a shared day; one hour means a
handover.

The abstraction is a fixed 9-to-5 on both ends, which is what a location study
means when it says "nearshore". Shift working, follow-the-sun models and
daylight saving are all outside it, and all three would move the answer.
"""

from __future__ import annotations

from src import config as C


def hq_offset(hq: str) -> float:
    """UTC offset for a headquarters key, or for a market code.

    Both are accepted because the headquarters list and the candidate market
    list are separate things that happen to overlap: Singapore is a market and
    also somewhere a CFO organisation sits.
    """
    if hq in C.HQ_BY_KEY:
        return C.HQ_BY_KEY[hq][1]
    if hq in C.UTC_OFFSET:
        return C.UTC_OFFSET[hq]
    raise KeyError(f"unknown headquarters {hq!r}")


def overlap_hours(iso2: str, hq: str | None = None) -> float:
    """Hours of the market's working day that fall inside the HQ's."""
    shift = C.UTC_OFFSET[iso2] - hq_offset(hq or C.HQ)
    start, end = C.WORKING_DAY
    # The market's day, expressed on the HQ clock.
    market_start, market_end = start - shift, end - shift
    return max(0.0, min(end, market_end) - max(start, market_start))
