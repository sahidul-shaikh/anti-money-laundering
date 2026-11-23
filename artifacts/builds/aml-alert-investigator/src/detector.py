"""Actimize AML-STR structuring rule: deposit structuring across a window.

A credit qualifies when its amount lies in [lower_bound, upper_bound], both
inclusive. Debits are ignored. The rule fires when at least `occurrences`
qualifying credits fall in one window of `window_days` calendar days, where
the window includes both endpoints (d and d + window_days - 1 share a window,
d + window_days does not). Input dates are YYYYMMDD; window dates are returned
as ISO-8601 YYYY-MM-DD.

The reported window is the one holding the most qualifying credits, earliest
on a tie. When the rule does not fire, that window's count is still reported
in `occurrences`.
"""

from datetime import date, datetime


def _parse_date(value: str) -> date:
    """Parse a YYYYMMDD string into a date."""
    return datetime.strptime(value, "%Y%m%d").date()


def _qualifying_credits(
    transactions: list[dict], lower_bound: float, upper_bound: float
) -> list[tuple[date, str, float]]:
    """Return (date, ref, amount) for in-band credits, sorted by date then ref."""
    rows = []
    for txn in transactions:
        amount = float(txn["amount"])
        if txn["direction"] == "CREDIT" and lower_bound <= amount <= upper_bound:
            rows.append((_parse_date(txn["date"]), txn["ref"], amount))
    return sorted(rows, key=lambda row: (row[0], row[1]))


def _densest_window(credits: list[tuple[date, str, float]], window_days: int) -> tuple[int, int]:
    """Return (start, end) indices of the window with the most credits.

    Each window is anchored at a credit and spans up to window_days calendar
    days inclusive. The end index is exclusive. Earliest anchor wins ties.
    """
    best_start, best_end = 0, 0
    for i, (day, _, _) in enumerate(credits):
        j = i
        while j < len(credits) and (credits[j][0] - day).days < window_days:
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
    """Apply the AML-STR structuring rule to one alert's transactions.

    Each transaction is a dict with date (YYYYMMDD), ref, amount and direction
    (CREDIT or DEBIT).

    Returns a dict with keys detected, occurrences, window_start, window_end,
    refs and total. When the rule does not fire, detected is False, refs is
    empty, total is 0.0, both window fields are None, and occurrences is the
    size of the densest window.
    """
    credits = _qualifying_credits(transactions, lower_bound, upper_bound)
    start, end = _densest_window(credits, window_days)
    count = end - start

    if count == 0 or count < occurrences:
        return {
            "detected": False,
            "occurrences": count,
            "window_start": None,
            "window_end": None,
            "refs": [],
            "total": 0.0,
        }

    window = credits[start:end]
    return {
        "detected": True,
        "occurrences": count,
        "window_start": window[0][0].isoformat(),
        "window_end": window[-1][0].isoformat(),
        "refs": [ref for _, ref, _ in window],
        "total": round(sum(amount for _, _, amount in window), 2),
    }
