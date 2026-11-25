"""AML-STR-CCE-INN-A-D01-DST structuring detector.

Flags a structuring pattern when at least `occurrences` inbound (CREDIT)
transactions with amounts in [lower_bound, upper_bound], both inclusive, fall
inside one window of `window_days` calendar days. A window spans `window_days`
days counting first and last day, so a transaction counts only if it is fewer
than `window_days` days after the window's first qualifying transaction.
Input dates are YYYYMMDD; the window dates in the result are ISO-8601 (YYYY-MM-DD).
"""

from datetime import datetime

INBOUND = "CREDIT"


def _parse_date(value: str) -> datetime:
    """Parse a YYYYMMDD date string."""
    return datetime.strptime(value, "%Y%m%d")


def _iso(value: str) -> str:
    """Reformat a YYYYMMDD date string as YYYY-MM-DD."""
    return _parse_date(value).date().isoformat()


def _qualifying(transactions: list[dict], lower_bound: float, upper_bound: float) -> list[dict]:
    """Inbound transactions with bounded amounts, sorted by date.

    The sort is stable, so transactions on the same date keep input order.
    """
    hits = [
        t
        for t in transactions
        if str(t["direction"]).upper() == INBOUND
        and lower_bound <= float(t["amount"]) <= upper_bound
    ]
    return sorted(hits, key=lambda t: t["date"])


def _window_from(hits: list[dict], start: int, window_days: int) -> list[dict]:
    """Qualifying transactions from `start` onward within the window opened at `start`."""
    first = _parse_date(hits[start]["date"])
    return [t for t in hits[start:] if (_parse_date(t["date"]) - first).days < window_days]


def _summary(detected: bool, window: list[dict]) -> dict:
    """Result dict for a window. Window dates are the first and last qualifying transactions, as YYYY-MM-DD."""
    if not window:
        return {
            "detected": detected,
            "occurrences": 0,
            "window_start": None,
            "window_end": None,
            "refs": [],
            "total": 0.0,
        }
    return {
        "detected": detected,
        "occurrences": len(window),
        "window_start": _iso(window[0]["date"]),
        "window_end": _iso(window[-1]["date"]),
        "refs": [t["ref"] for t in window],
        "total": round(sum(float(t["amount"]) for t in window), 2),
    }


def detect_structuring(
    transactions: list[dict],
    lower_bound: float = 8000.0,
    upper_bound: float = 9999.99,
    occurrences: int = 3,
    window_days: int = 14,
) -> dict:
    """Detect structuring in a list of transactions.

    Returns the earliest window that reaches `occurrences` qualifying transactions,
    with its count, first and last qualifying dates (YYYY-MM-DD), refs in date order,
    and the rounded sum of its amounts. When nothing fires, `occurrences` is the
    largest count found in any window and the window fields are empty.
    """
    hits = _qualifying(transactions, lower_bound, upper_bound)
    windows = [_window_from(hits, i, window_days) for i in range(len(hits))]
    fired = next((w for w in windows if len(w) >= occurrences), None)
    if fired is not None:
        return _summary(True, fired)
    best = max(windows, key=len, default=[])
    return {**_summary(False, []), "occurrences": len(best)}
