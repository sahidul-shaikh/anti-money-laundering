"""Actimize AML-STR-CCE-INN-A-D01-DST structuring detector.

Rule, applied in this order:
1. Direction: only CREDIT transactions are considered.
2. Amount: lower_bound <= amount <= upper_bound, both bounds inclusive.
3. Window: a window of window_days spans window_days calendar days inclusive.
   A window anchored on date d holds qualifying transactions dated d through
   d + window_days - 1.
4. Fires when the best window holds at least `occurrences` qualifying transactions.

Input dates are YYYYMMDD. The window_start and window_end result values are
ISO-8601 (YYYY-MM-DD) dates of the first and last qualifying transactions in the
window. Result keys are always present. `occurrences` is the largest qualifying
count found in any window, whether or not the rule fires. When the rule does not
fire, window_start and window_end are None, refs is empty and total is 0.0.
"""

from datetime import date, datetime, timedelta


def _parse_date(value: str) -> date:
    """Parse a YYYYMMDD string into a date."""
    return datetime.strptime(value, "%Y%m%d").date()


def _qualifying(transactions: list[dict], lower_bound: float, upper_bound: float) -> list[tuple]:
    """Return (date, transaction) pairs that pass the direction and amount filters, sorted by date."""
    picked = [
        (_parse_date(t["date"]), t)
        for t in transactions
        if str(t["direction"]).strip().upper() == "CREDIT"
        and lower_bound <= float(t["amount"]) <= upper_bound
    ]
    return sorted(picked, key=lambda pair: pair[0])


def _best_window(items: list[tuple], window_days: int) -> list[tuple]:
    """Return the window with the most qualifying items; the earliest wins a tie."""
    best: list[tuple] = []
    for start, _ in items:
        last = start + timedelta(days=window_days - 1)
        window = [pair for pair in items if start <= pair[0] <= last]
        if len(window) > len(best):
            best = window
    return best


def detect_structuring(
    transactions: list[dict],
    lower_bound: float = 8000.0,
    upper_bound: float = 9999.99,
    occurrences: int = 3,
    window_days: int = 14,
) -> dict:
    """Detect structured credits: at least `occurrences` amounts in [lower_bound, upper_bound] within `window_days`.

    Each transaction needs date (YYYYMMDD), ref, amount and direction (CREDIT or DEBIT).
    window_start and window_end are returned as ISO-8601 dates (YYYY-MM-DD).
    """
    window = _best_window(_qualifying(transactions, lower_bound, upper_bound), window_days)
    detected = len(window) > 0 and len(window) >= occurrences
    if not detected:
        return {
            "detected": False,
            "occurrences": len(window),
            "window_start": None,
            "window_end": None,
            "refs": [],
            "total": 0.0,
        }
    txns = [pair[1] for pair in window]
    return {
        "detected": True,
        "occurrences": len(txns),
        "window_start": window[0][0].isoformat(),
        "window_end": window[-1][0].isoformat(),
        "refs": [t["ref"] for t in txns],
        "total": round(sum(float(t["amount"]) for t in txns), 2),
    }
