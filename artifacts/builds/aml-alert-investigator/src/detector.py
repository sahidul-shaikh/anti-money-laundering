"""Actimize AML-STR structuring rule AML-STR-CCE-INN-A-D01-DST.

Clause mapping:
- Bounds: a transaction qualifies when lower_bound <= amount <= upper_bound. Both ends inclusive.
- Direction: only CREDIT transactions qualify. DEBIT transactions are ignored entirely, for the
  trigger and for the occurrence count.
- Window: an anchor qualifying transaction opens a window of window_days calendar days,
  inclusive: anchor date up to anchor date + window_days - 1.
- Trigger: the rule fires when a window holds at least `occurrences` qualifying transactions.
- Reported window: the anchor window with the most qualifying transactions. Ties go to the
  earliest anchor. window_end is the date of its last qualifying transaction.
- Not fired: detected is False, occurrences is the peak count across all windows (0 if none),
  window_start and window_end are None, refs is empty and total is 0.0.

Input dates are YYYYMMDD strings. window_start and window_end are returned as ISO-8601
(YYYY-MM-DD). Refs are in date order. Transactions sharing a date keep their input order.
"""

from datetime import date, datetime, timedelta


def _day(text: str) -> date:
    """Parse a YYYYMMDD string."""
    return datetime.strptime(text, "%Y%m%d").date()


def _qualifying(transactions: list[dict], lower_bound: float, upper_bound: float) -> list[dict]:
    """CREDIT transactions whose amount is within the inclusive bounds, in date order."""
    hits = [
        t
        for t in transactions
        if t["direction"] == "CREDIT" and lower_bound <= float(t["amount"]) <= upper_bound
    ]
    return sorted(hits, key=lambda t: _day(t["date"]))


def _peak_window(hits: list[dict], window_days: int) -> list[dict]:
    """Qualifying transactions in the anchor window with the most members."""
    peak: list[dict] = []
    for anchor in hits:
        start = _day(anchor["date"])
        end = start + timedelta(days=window_days)
        members = [t for t in hits if start <= _day(t["date"]) < end]
        if len(members) > len(peak):
            peak = members
    return peak


def detect_structuring(
    transactions: list[dict],
    lower_bound: float = 8000.0,
    upper_bound: float = 9999.99,
    occurrences: int = 3,
    window_days: int = 14,
) -> dict:
    """Apply the AML-STR structuring rule to one account's transactions.

    Returns keys: detected, occurrences, window_start, window_end, refs, total.
    """
    window = _peak_window(_qualifying(transactions, lower_bound, upper_bound), window_days)
    if not window or len(window) < occurrences:
        return {
            "detected": False,
            "occurrences": len(window),
            "window_start": None,
            "window_end": None,
            "refs": [],
            "total": 0.0,
        }
    return {
        "detected": True,
        "occurrences": len(window),
        "window_start": _day(window[0]["date"]).isoformat(),
        "window_end": _day(window[-1]["date"]).isoformat(),
        "refs": [t["ref"] for t in window],
        "total": round(sum(float(t["amount"]) for t in window), 2),
    }
