"""Actimize AML-STR-CCE-INN-A-D01-DST structuring detector.

Flags a structuring pattern when at least `occurrences` CREDIT transactions
with amounts in [lower_bound, upper_bound] fall inside one window of
`window_days` calendar days. Both ends of the window are counted, so a
14-day window spans 14 dates (day 0 through day 13 after its start).

Rule choices where the contract is silent:
- Bounds are inclusive: lower_bound <= amount <= upper_bound.
- Only direction "CREDIT" counts. DEBIT rows are dropped before counting.
- Windows are anchored on each qualifying transaction date in turn. The
  earliest anchor whose window reaches `occurrences` is reported, and the
  report includes every qualifying transaction inside that window.
- window_start and window_end are the dates of the first and last qualifying
  transaction in the reported window, not the nominal window edges. They are
  returned as ISO-8601 strings (YYYY-MM-DD). Input dates stay YYYYMMDD.
- refs are in date order. Ties keep input order (stable sort).
- total is the sum of the reported amounts, rounded to 2 dp once at the end.
- Not detected: detected is False, occurrences is the largest qualifying count
  seen in any window (0 if none), window_start and window_end are None,
  refs is [], total is 0.0.
"""

from datetime import date, datetime


def _parse(yyyymmdd) -> date:
    """Parse a YYYYMMDD value (string or int) into a date."""
    return datetime.strptime(str(yyyymmdd), "%Y%m%d").date()


def _qualifying(transactions: list[dict], lower_bound: float, upper_bound: float) -> list[dict]:
    """CREDIT rows with amount inside the inclusive bounds, sorted by date."""
    rows = [
        t
        for t in transactions
        if t["direction"] == "CREDIT" and lower_bound <= float(t["amount"]) <= upper_bound
    ]
    return sorted(rows, key=lambda t: _parse(t["date"]))


def _window_from(rows: list[dict], start: int, window_days: int) -> list[dict]:
    """Qualifying rows from index `start` whose date is within window_days of it."""
    first = _parse(rows[start]["date"])
    members = []
    for t in rows[start:]:
        if (_parse(t["date"]) - first).days >= window_days:
            break
        members.append(t)
    return members


def _hit(members: list[dict]) -> dict:
    """Result dict for a window that fired."""
    amounts = [float(t["amount"]) for t in members]
    return {
        "detected": True,
        "occurrences": len(members),
        "window_start": _parse(members[0]["date"]).isoformat(),
        "window_end": _parse(members[-1]["date"]).isoformat(),
        "refs": [t["ref"] for t in members],
        "total": round(sum(amounts), 2),
    }


def _miss(best: int) -> dict:
    """Result dict when no window fired; occurrences is the best count seen."""
    return {
        "detected": False,
        "occurrences": best,
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
    """Detect structuring: `occurrences` CREDIT amounts in bounds within `window_days`.

    Each transaction has keys date (YYYYMMDD), ref, amount, direction.
    Returns keys detected, occurrences, window_start, window_end (ISO-8601),
    refs, total.
    """
    rows = _qualifying(transactions, lower_bound, upper_bound)
    best = 0
    for start in range(len(rows)):
        members = _window_from(rows, start, window_days)
        if len(members) >= occurrences:
            return _hit(members)
        best = max(best, len(members))
    return _miss(best)
