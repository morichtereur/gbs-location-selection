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


def overlap_hours(iso2: str, hq: str | None = None) -> float:
    """Hours of the market's working day that fall inside the HQ's."""
    hq = hq or C.HQ
    shift = C.UTC_OFFSET[iso2] - C.UTC_OFFSET[hq]
    start, end = C.WORKING_DAY
    # The market's day, expressed on the HQ clock.
    market_start, market_end = start - shift, end - shift
    return max(0.0, min(end, market_end) - max(start, market_start))
