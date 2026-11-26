"""Actimize AML-STR structuring rule AML-STR-CCE-INN-A-D01-DST.

Qualifying transactions are inbound (direction CREDIT) with amounts in
[lower_bound, upper_bound], both bounds inclusive. The rule fires when at least
`occurrences` qualifying transactions fall within one window of `window_days`
calendar days. A window starting on date D covers D through D + (window_days - 1),
so 14 days spans 14 calendar dates inclusive.

When the rule fires, the reported window is the one holding the most qualifying
transactions (earliest start on a tie). window_start and window_end are the dates
of the first and last qualifying transaction in that window, formatted ISO-8601
(YYYY-MM-DD). Input dates are YYYYMMDD and are not changed by this. refs lists
those transactions in date order, ties kept in input order. total is their amount
sum, rounded to 2 decimal places.

When the rule does not fire, detected is False, window_start and window_end are
None, refs is empty, total is 0.0, and occurrences is the largest count of
qualifying transactions in any single window (0 if none qualify).
"""
from datetime import datetime, timedelta

DIRECTION = "CREDIT"
INPUT_DATE_FORMAT = "%Y%m%d"
OUTPUT_DATE_FORMAT = "%Y-%m-%d"


def _qualifying(transactions, lower_bound, upper_bound):
    """Return (date, ref, amount) for qualifying transactions, sorted by date."""
    rows = []
    for t in transactions:
        amount = float(t["amount"])
        if t["direction"].upper() != DIRECTION:
            continue
        if not lower_bound <= amount <= upper_bound:
            continue
        day = datetime.strptime(t["date"], INPUT_DATE_FORMAT).date()
        rows.append((day, t["ref"], amount))
    return sorted(rows, key=lambda r: r[0])


def _window_members(rows, start, window_days):
    """Return the rows dated from start through start + window_days - 1."""
    end = start + timedelta(days=window_days - 1)
    return [r for r in rows if start <= r[0] <= end]


def _densest_window(rows, window_days):
    """Return the window anchored on a qualifying date with the most rows."""
    best = []
    for day, _, _ in rows:
        members = _window_members(rows, day, window_days)
        if len(members) > len(best):
            best = members
    return best


def detect_structuring(
    transactions: list[dict],
    lower_bound: float = 8000.0,
    upper_bound: float = 9999.99,
    occurrences: int = 3,
    window_days: int = 14,
) -> dict:
    """Apply the AML-STR structuring rule to a list of transaction dicts.

    Each dict carries date (YYYYMMDD), ref, amount and direction (CREDIT or DEBIT).
    Returns detected, occurrences, window_start, window_end (YYYY-MM-DD), refs and total.
    """
    rows = _qualifying(transactions, lower_bound, upper_bound)
    best = _densest_window(rows, window_days)
    if not best or len(best) < occurrences:
        return {
            "detected": False,
            "occurrences": len(best),
            "window_start": None,
            "window_end": None,
            "refs": [],
            "total": 0.0,
        }
    return {
        "detected": True,
        "occurrences": len(best),
        "window_start": best[0][0].strftime(OUTPUT_DATE_FORMAT),
        "window_end": best[-1][0].strftime(OUTPUT_DATE_FORMAT),
        "refs": [r[1] for r in best],
        "total": round(sum(r[2] for r in best), 2),
    }
