"""Structuring detector for Actimize AML-STR rule AML-STR-CCE-INN-A-D01-DST.

A transaction qualifies when it is a CREDIT and its amount lies in
[lower_bound, upper_bound], both bounds inclusive. The rule fires on the first
window of window_days calendar days (both endpoints inclusive) that holds at
least `occurrences` qualifying transactions. Windows start at each qualifying
transaction in date order.

Input dates are YYYYMMDD. window_start and window_end are YYYY-MM-DD.

When the rule does not fire, occurrences is the largest number of qualifying
transactions in any single window (0 if none qualify) and the window fields are
None.
"""

from datetime import date, datetime, timedelta
from typing import NamedTuple


class _Txn(NamedTuple):
    day: date
    ref: str
    amount: float


def detect_structuring(
    transactions: list[dict],
    lower_bound: float = 8000.0,
    upper_bound: float = 9999.99,
    occurrences: int = 3,
    window_days: int = 14,
) -> dict:
    """Return the structuring detection result for one alert's transactions.

    Keys: detected, occurrences, window_start, window_end, refs, total.
    """
    qualifying = _qualifying(transactions, lower_bound, upper_bound)
    windows = [_window(qualifying, i, window_days) for i in range(len(qualifying))]
    for window in windows:
        if len(window) >= occurrences:
            return _detected(window)
    return _not_detected(max((len(w) for w in windows), default=0))


def _qualifying(transactions: list[dict], lower: float, upper: float) -> list[_Txn]:
    """Credits with amount in [lower, upper], in date order (stable for equal dates)."""
    txns = [
        _Txn(datetime.strptime(t["date"], "%Y%m%d").date(), t["ref"], t["amount"])
        for t in transactions
        if t["direction"] == "CREDIT" and lower <= t["amount"] <= upper
    ]
    return sorted(txns, key=lambda t: t.day)


def _window(qualifying: list[_Txn], start_index: int, window_days: int) -> list[_Txn]:
    """Qualifying transactions from start_index whose date falls within window_days of its first day, inclusive."""
    last_day = qualifying[start_index].day + timedelta(days=window_days - 1)
    return [t for t in qualifying[start_index:] if t.day <= last_day]


def _detected(window: list[_Txn]) -> dict:
    """Result for a window that reached the occurrence threshold."""
    return {
        "detected": True,
        "occurrences": len(window),
        "window_start": window[0].day.isoformat(),
        "window_end": window[-1].day.isoformat(),
        "refs": [t.ref for t in window],
        "total": round(float(sum(t.amount for t in window)), 2),
    }


def _not_detected(peak: int) -> dict:
    """Result when no window reached the occurrence threshold; peak is the largest window count."""
    return {
        "detected": False,
        "occurrences": peak,
        "window_start": None,
        "window_end": None,
        "refs": [],
        "total": 0.0,
    }
