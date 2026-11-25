"""Structuring detector for Actimize AML-STR rule AML-STR-CCE-INN-A-D01-DST.

A credit qualifies when its amount lies within [lower_bound, upper_bound], both
inclusive. The rule fires when qualifying credits reach `occurrences` within a
window of `window_days` calendar days, both endpoints inclusive. Debits are
ignored. When several windows qualify, the earliest is reported. `refs` and
`total` cover the transactions in the reported window. When the rule does not
fire, `occurrences` is the count of all qualifying credits.
"""

import math
from datetime import date, datetime


def _parse_date(value: str) -> date:
    """Parse a YYYYMMDD string into a date."""
    return datetime.strptime(value, "%Y%m%d").date()


def _qualifying(
    transactions: list[dict], lower_bound: float, upper_bound: float
) -> list[tuple[date, str, float]]:
    """Return (date, ref, amount) for qualifying credits, sorted by date."""
    hits = [
        (_parse_date(t["date"]), t["ref"], t["amount"])
        for t in transactions
        if t["direction"] == "CREDIT" and lower_bound <= t["amount"] <= upper_bound
    ]
    return sorted(hits, key=lambda hit: hit[0])


def _first_window(
    hits: list[tuple[date, str, float]], occurrences: int, window_days: int
) -> list[tuple[date, str, float]] | None:
    """Return the earliest window holding at least `occurrences` hits, else None."""
    for start_date, _, _ in hits:
        window = [h for h in hits if start_date <= h[0] and (h[0] - start_date).days < window_days]
        if len(window) >= occurrences:
            return window
    return None


def detect_structuring(
    transactions: list[dict],
    lower_bound: float = 8000.0,
    upper_bound: float = 9999.99,
    occurrences: int = 3,
    window_days: int = 14,
) -> dict:
    """Apply AML-STR-CCE-INN-A-D01-DST to a list of transactions.

    Each transaction needs `date` (YYYYMMDD), `ref`, `amount` and `direction`
    (CREDIT or DEBIT). Returns detected, occurrences, window_start, window_end
    (YYYY-MM-DD), refs and total (2dp).
    """
    hits = _qualifying(transactions, lower_bound, upper_bound)
    window = _first_window(hits, occurrences, window_days)
    if window is None:
        return {
            "detected": False,
            "occurrences": len(hits),
            "window_start": None,
            "window_end": None,
            "refs": [],
            "total": 0.0,
        }
    return {
        "detected": True,
        "occurrences": len(window),
        "window_start": window[0][0].isoformat(),
        "window_end": window[-1][0].isoformat(),
        "refs": [ref for _, ref, _ in window],
        "total": round(math.fsum(amount for _, _, amount in window), 2),
    }
