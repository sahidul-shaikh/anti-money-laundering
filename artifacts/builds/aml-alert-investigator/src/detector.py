"""Actimize AML-STR structuring rule AML-STR-CCE-INN-A-D01-DST.

Fires when at least `occurrences` CREDIT transactions, each with an amount in
[lower_bound, upper_bound] (both inclusive), fall inside one window of
`window_days` calendar days (both endpoints inclusive). DEBIT transactions are
ignored. A transaction dated d and one dated d + (window_days - 1) share a
window; d + window_days does not.

Result keys:
    detected      True when the rule fires.
    occurrences   Qualifying transactions in the firing window. When the rule
                  does not fire, the largest qualifying count in any window.
    window_start  YYYY-MM-DD of the earliest qualifying item in the firing
                  window, or None.
    window_end    YYYY-MM-DD of the latest qualifying item in the firing
                  window, or None.
    refs          Refs of the qualifying transactions in the firing window,
                  in date order (input order breaks ties), or [].
    total         Sum of the amounts in refs, rounded to 2 dp, or 0.0.
"""

from datetime import date, datetime, timedelta

Hit = tuple[date, str, float]


def _qualifying(transactions: list[dict], lower_bound: float, upper_bound: float) -> list[Hit]:
    """Credits within the bounds, sorted by date. The sort is stable."""
    hits = [
        (datetime.strptime(t["date"], "%Y%m%d").date(), t["ref"], t["amount"])
        for t in transactions
        if t["direction"] == "CREDIT" and lower_bound <= t["amount"] <= upper_bound
    ]
    return sorted(hits, key=lambda hit: hit[0])


def _window(hits: list[Hit], start: date, window_days: int) -> list[Hit]:
    """Hits dated from start to start + window_days - 1, both inclusive."""
    last = start + timedelta(days=window_days - 1)
    return [hit for hit in hits if start <= hit[0] <= last]


def _fired(group: list[Hit]) -> dict:
    """Result for a firing window. group is sorted by date."""
    return {
        "detected": True,
        "occurrences": len(group),
        "window_start": group[0][0].isoformat(),
        "window_end": group[-1][0].isoformat(),
        "refs": [ref for _, ref, _ in group],
        "total": round(float(sum(amount for _, _, amount in group)), 2),
    }


def _not_fired(occurrences: int) -> dict:
    """Result when no window reaches the occurrence threshold."""
    return {
        "detected": False,
        "occurrences": occurrences,
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
    """Evaluate AML-STR structuring over a list of transactions.

    Each transaction has date (YYYYMMDD), ref, amount and direction (CREDIT or
    DEBIT). The earliest window that meets the threshold is reported.
    """
    hits = _qualifying(transactions, lower_bound, upper_bound)
    best: list[Hit] = []
    for start, _, _ in hits:
        group = _window(hits, start, window_days)
        if len(group) >= occurrences:
            return _fired(group)
        if len(group) > len(best):
            best = group
    return _not_fired(len(best))
