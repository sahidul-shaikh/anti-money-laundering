"""Actimize AML-STR structuring detector (AML-STR-CCE-INN-A-D01-DST).

A transaction qualifies when its direction is CREDIT and its amount lies in
[lower_bound, upper_bound], both ends inclusive. The rule fires when at least
`occurrences` qualifying transactions fall in one window of `window_days`
calendar days, inclusive: dates d with start <= d <= start + window_days - 1.
The earliest-starting window that reaches the threshold is reported.
Window dates in the result are ISO-8601 (YYYY-MM-DD); input dates are YYYYMMDD.
"""

from datetime import datetime, timedelta

QUALIFYING_DIRECTION = "CREDIT"


def _day(date: str) -> datetime:
    """Parse a YYYYMMDD string."""
    return datetime.strptime(date, "%Y%m%d")


def _iso(date: str) -> str:
    """Reformat a YYYYMMDD string as ISO-8601 YYYY-MM-DD."""
    return _day(date).date().isoformat()


def _qualifying(transactions: list[dict], lower_bound: float, upper_bound: float) -> list[dict]:
    """Return qualifying transactions sorted by date; ties keep input order."""
    picked = [
        t
        for t in transactions
        if t["direction"] == QUALIFYING_DIRECTION
        and lower_bound <= float(t["amount"]) <= upper_bound
    ]
    return sorted(picked, key=lambda t: t["date"])


def _window_from(items: list[dict], start_index: int, window_days: int) -> list[dict]:
    """Return the items from start_index that fall within window_days of its date."""
    last = _day(items[start_index]["date"]) + timedelta(days=window_days - 1)
    return [t for t in items[start_index:] if _day(t["date"]) <= last]


def _fired(window: list[dict]) -> dict:
    """Result when the rule fires: window dates run from the first to the last qualifying item."""
    return {
        "detected": True,
        "occurrences": len(window),
        "window_start": _iso(window[0]["date"]),
        "window_end": _iso(window[-1]["date"]),
        "refs": [t["ref"] for t in window],
        "total": round(sum(float(t["amount"]) for t in window), 2),
    }


def _not_fired(best: int) -> dict:
    """Result when the rule does not fire: occurrences is the largest count in any window."""
    return {
        "detected": False,
        "occurrences": best,
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
    """Detect AML-STR structuring over a list of transactions.

    Each transaction has keys date (YYYYMMDD), ref, amount and direction.
    Returns keys detected, occurrences, window_start, window_end, refs, total.
    """
    items = _qualifying(transactions, lower_bound, upper_bound)
    best = 0
    for i in range(len(items)):
        window = _window_from(items, i, window_days)
        best = max(best, len(window))
        if len(window) >= occurrences:
            return _fired(window)
    return _not_fired(best)
