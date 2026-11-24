"""Actimize AML-STR-CCE-INN-A-D01-DST: structuring detector.

Judgements where the requirement is silent:
- Qualifying: direction == "credit" (case-insensitive) and lower_bound <= amount <= upper_bound.
  Both bounds are inclusive.
- Window: a window anchored on day D covers D through D + window_days - 1. Inclusive, so
  14 days span 14 calendar days.
- Fires when some window holds at least `occurrences` qualifying transactions. The earliest
  firing window is reported.
- window_start and window_end are the ISO-8601 dates (YYYY-MM-DD) of the first and last
  qualifying transactions in the reported window, not the nominal window edges. Transaction
  dates remain YYYYMMDD on input.
- refs: qualifying transactions in the reported window, ordered by date. Equal dates keep input order.
- total: sum of their amounts, rounded to 2 dp once, at the end.
- occurrences: qualifying count in the reported window. When not detected, the peak count in any window.
- Not detected: window_start and window_end are None, refs is [], total is 0.0.
"""

from datetime import date, datetime, timedelta

QUALIFYING_DIRECTION = "credit"


def _day(txn: dict) -> date:
    """Parse the YYYYMMDD date of a transaction."""
    return datetime.strptime(str(txn["date"]), "%Y%m%d").date()


def _qualifies(txn: dict, lower_bound: float, upper_bound: float) -> bool:
    """True when the transaction is in the counted direction and inside the amount bounds."""
    return (
        str(txn["direction"]).lower() == QUALIFYING_DIRECTION
        and lower_bound <= txn["amount"] <= upper_bound
    )


def _window_from(hits: list[dict], start: int, window_days: int) -> list[dict]:
    """Qualifying transactions from hits[start] onward that fall within window_days of it.

    hits must be sorted by date.
    """
    last = _day(hits[start]) + timedelta(days=window_days - 1)
    members = []
    for txn in hits[start:]:
        if _day(txn) > last:
            break
        members.append(txn)
    return members


def _detected(members: list[dict]) -> dict:
    """Result for a firing window."""
    return {
        "detected": True,
        "occurrences": len(members),
        "window_start": _day(members[0]).isoformat(),
        "window_end": _day(members[-1]).isoformat(),
        "refs": [t["ref"] for t in members],
        "total": round(sum(t["amount"] for t in members), 2),
    }


def _not_detected(peak_count: int) -> dict:
    """Result when no window reaches the occurrence count."""
    return {
        "detected": False,
        "occurrences": peak_count,
        "window_start": None,
        "window_end": None,
        "refs": [],
        "total": 0.0,
    }


def detect_structuring(
    transactions: list[dict],
    lower_bound: float = 8000.0,
    upper_bound: float = 9999.99,
    occurrences: int = 3,
    window_days: int = 14,
) -> dict:
    """Detect repeated just-below-threshold credits within a rolling window."""
    hits = sorted(
        (t for t in transactions if _qualifies(t, lower_bound, upper_bound)),
        key=_day,
    )
    peak = 0
    for start in range(len(hits)):
        members = _window_from(hits, start, window_days)
        if len(members) >= occurrences:
            return _detected(members)
        peak = max(peak, len(members))
    return _not_detected(peak)
