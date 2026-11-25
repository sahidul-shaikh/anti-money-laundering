"""AML-STR structuring detector (Actimize AML-STR-CCE-INN-A-D01-DST).

Rule: at least `occurrences` CREDIT transactions whose amount lies in the
inclusive band [lower_bound, upper_bound] fall within `window_days` calendar
days. A window of N days spans N dates inclusive (d .. d+N-1).

Direction filter runs first: only CREDIT (inbound) transactions count.

When the rule fires, the earliest qualifying window is reported. Its
occurrences are every qualifying transaction inside it, refs are in date order,
window_start/window_end are the ISO-8601 dates of its first and last qualifying
transaction, and total is the sum of the window's amounts rounded to cents.
When the rule does not fire, occurrences is the largest count found in any
window, window_start/window_end are None, refs is empty and total is 0.0.
"""

from datetime import datetime

DATE_FORMAT = "%Y%m%d"


def _parse(day: str):
    """Parse a YYYYMMDD string to a date."""
    return datetime.strptime(day, DATE_FORMAT).date()


def detect_structuring(
    transactions: list[dict],
    lower_bound: float = 8000.0,
    upper_bound: float = 9999.99,
    occurrences: int = 3,
    window_days: int = 14,
) -> dict:
    """Detect structuring: `occurrences` in-band CREDITs within `window_days`."""
    qualifying = sorted(
        (
            t
            for t in transactions
            if t["direction"] == "CREDIT" and lower_bound <= t["amount"] <= upper_bound
        ),
        key=lambda t: t["date"],
    )
    days = [_parse(t["date"]) for t in qualifying]
    best = 0
    for start in range(len(qualifying)):
        end = start
        while end < len(qualifying) and (days[end] - days[start]).days < window_days:
            end += 1
        count = end - start
        if count >= occurrences:
            window = qualifying[start:end]
            return {
                "detected": True,
                "occurrences": count,
                "window_start": days[start].isoformat(),
                "window_end": days[end - 1].isoformat(),
                "refs": [t["ref"] for t in window],
                "total": round(sum((t["amount"] for t in window), 0.0), 2),
            }
        best = max(best, count)
    return {
        "detected": False,
        "occurrences": best,
        "window_start": None,
        "window_end": None,
        "refs": [],
        "total": 0.0,
    }
