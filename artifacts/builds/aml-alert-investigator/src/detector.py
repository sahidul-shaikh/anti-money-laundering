"""Actimize AML-STR-CCE-INN-A-D01-DST structuring detector.

Rule as implemented:
1. Qualify: lower_bound <= amount <= upper_bound (both inclusive) and
   direction == "CREDIT" (inbound). The direction filter runs before counting.
2. Window: a window of window_days spans window_days calendar days inclusive.
   A qualifying item dated d_j falls in the window opened by d_i when
   (d_j - d_i).days <= window_days - 1.
3. Count: each qualifying item opens a window; count the qualifying items inside
   it. The reported window has the largest count; ties go to the earliest.
4. Fire: detected when that count >= occurrences.

Output: window_start and window_end are the ISO-8601 (YYYY-MM-DD) dates of the
first and last qualifying items in the reported window, not the calendar edges
of the window. When not detected, occurrences still carries the largest window
count, the window dates are None, refs is empty and total is 0.0.
"""
from datetime import date, datetime


def _parse_date(value: str) -> date:
    """Parse a YYYYMMDD string."""
    return datetime.strptime(value, "%Y%m%d").date()


def _qualifying(transactions: list[dict], lower_bound: float, upper_bound: float) -> list[dict]:
    """Return inbound transactions within the amount bounds, sorted by date (stable)."""
    hits = [
        t
        for t in transactions
        if t["direction"] == "CREDIT" and lower_bound <= t["amount"] <= upper_bound
    ]
    return sorted(hits, key=lambda t: _parse_date(t["date"]))


def _largest_window(hits: list[dict], window_days: int) -> tuple[int, int]:
    """Return (start, end) indices of the largest window; earliest wins ties."""
    days = [_parse_date(t["date"]) for t in hits]
    best_start, best_end = 0, 0
    for i, opener in enumerate(days):
        j = i
        while j < len(days) and (days[j] - opener).days <= window_days - 1:
            j += 1
        if j - i > best_end - best_start:
            best_start, best_end = i, j
    return best_start, best_end


def detect_structuring(
    transactions: list[dict],
    lower_bound: float = 8000.0,
    upper_bound: float = 9999.99,
    occurrences: int = 3,
    window_days: int = 14,
) -> dict:
    """Detect a run of sub-threshold inbound amounts within a rolling window.

    Returns keys: detected, occurrences, window_start, window_end, refs, total.
    window_start and window_end are ISO-8601 (YYYY-MM-DD) strings.
    """
    hits = _qualifying(transactions, lower_bound, upper_bound)
    start, end = _largest_window(hits, window_days)
    window = hits[start:end]
    count = len(window)
    if count < occurrences:
        return {
            "detected": False,
            "occurrences": count,
            "window_start": None,
            "window_end": None,
            "refs": [],
            "total": 0.0,
        }
    return {
        "detected": True,
        "occurrences": count,
        "window_start": _parse_date(window[0]["date"]).isoformat(),
        "window_end": _parse_date(window[-1]["date"]).isoformat(),
        "refs": [t["ref"] for t in window],
        "total": round(sum(t["amount"] for t in window), 2),
    }
