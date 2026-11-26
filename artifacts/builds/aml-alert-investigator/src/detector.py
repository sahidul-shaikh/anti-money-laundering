"""Actimize AML-STR structuring rule AML-STR-CCE-INN-A-D01-DST.

Rule as implemented:
- Only credits count. Direction is compared case-insensitively with surrounding
  whitespace ignored, so "credit", "CREDIT" and " Credit " all count. Debits are
  dropped before any window is evaluated.
- A transaction qualifies when lower_bound <= amount <= upper_bound (both inclusive).
- A window of window_days spans window_days calendar days inclusive, so the
  last qualifying item must satisfy (date - first_date).days < window_days.
- The rule fires when some window holds at least `occurrences` qualifying items.
  The earliest such window is reported; its refs are in date order, with ties
  kept in input order.
- window_start and window_end are the dates of the first and last qualifying
  items in the reported window, as ISO-8601 strings (YYYY-MM-DD). Input dates
  remain YYYYMMDD.
- total is the sum of the amounts of the reported window, rounded to cents.
- When the rule does not fire: detected is False, occurrences is the largest
  qualifying count found in any window, window_start and window_end are None,
  refs is empty and total is 0.0.
"""

from datetime import datetime

DATE_FORMAT = "%Y%m%d"


def detect_structuring(
    transactions: list[dict],
    lower_bound: float = 8000.0,
    upper_bound: float = 9999.99,
    occurrences: int = 3,
    window_days: int = 14,
) -> dict:
    """Flag a run of near-threshold credits reaching `occurrences` within `window_days`."""
    qualifying = sorted(
        (
            t
            for t in transactions
            if _is_credit(t)
            and lower_bound <= float(t["amount"]) <= upper_bound
        ),
        key=lambda t: t["date"],
    )
    days = [datetime.strptime(t["date"], DATE_FORMAT).date() for t in qualifying]

    max_count = 0
    found = None
    for start in range(len(qualifying)):
        end = _window_end(days, start, window_days)
        max_count = max(max_count, end - start)
        if found is None and end - start >= occurrences:
            found = (start, end)

    if found is None:
        return {
            "detected": False,
            "occurrences": max_count,
            "window_start": None,
            "window_end": None,
            "refs": [],
            "total": 0.0,
        }

    start, end = found
    window = qualifying[start:end]
    return {
        "detected": True,
        "occurrences": len(window),
        "window_start": days[start].isoformat(),
        "window_end": days[end - 1].isoformat(),
        "refs": [t["ref"] for t in window],
        "total": round(sum(float(t["amount"]) for t in window), 2),
    }


def _is_credit(txn: dict) -> bool:
    """True when the transaction direction is credit, ignoring case and surrounding spaces."""
    return str(txn["direction"]).strip().lower() == "credit"


def _window_end(days: list, start: int, window_days: int) -> int:
    """Index one past the last item within window_days calendar days of days[start]."""
    end = start
    while end < len(days) and (days[end] - days[start]).days < window_days:
        end += 1
    return end
