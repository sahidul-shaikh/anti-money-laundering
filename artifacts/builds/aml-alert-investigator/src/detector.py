"""Actimize AML-STR structuring detector, rule AML-STR-CCE-INN-A-D01-DST.

Implementer judgements where the contract is silent:
- Only CREDIT transactions count (inbound structuring). DEBIT rows are ignored.
- Amount bounds are inclusive: lower_bound <= amount <= upper_bound.
- A window of N days spans N calendar days inclusive: start d covers d .. d + (N - 1).
- Windows are anchored on each distinct qualifying date. The reported window has the
  most qualifying transactions; ties go to the earliest start date.
- Filters apply in order: direction, then bounds, then window count.
- Input dates are YYYYMMDD. window_start and window_end are returned in ISO-8601
  (YYYY-MM-DD), taken from the first and last qualifying transaction in the reported
  window. Both are None when not detected.
- occurrences is the best window count, returned whether or not the rule fires.
- total is the sum of amounts in refs, rounded to 2 dp. It is 0.0 when not detected.
"""

from datetime import date, datetime, timedelta

INPUT_DATE_FORMAT = "%Y%m%d"
OUTPUT_DATE_FORMAT = "%Y-%m-%d"
DIRECTION = "CREDIT"


def _parse_date(text: str) -> date:
    """Parse a YYYYMMDD string."""
    return datetime.strptime(text, INPUT_DATE_FORMAT).date()


def _qualifying(transactions: list[dict], lower_bound: float, upper_bound: float) -> list[dict]:
    """Keep CREDIT rows within the inclusive bounds, sorted by date (stable)."""
    kept = []
    for t in transactions:
        amount = float(t["amount"])
        if t["direction"] == DIRECTION and lower_bound <= amount <= upper_bound:
            kept.append({"date": _parse_date(t["date"]), "ref": t["ref"], "amount": amount})
    return sorted(kept, key=lambda t: t["date"])


def _best_window(items: list[dict], window_days: int) -> list[dict]:
    """Largest group of items dated within [start, start + window_days - 1]."""
    best: list[dict] = []
    for start in sorted({t["date"] for t in items}):
        last = start + timedelta(days=window_days - 1)
        group = [t for t in items if start <= t["date"] <= last]
        if len(group) > len(best):
            best = group
    return best


def detect_structuring(
    transactions: list[dict],
    lower_bound: float = 8000.0,
    upper_bound: float = 9999.99,
    occurrences: int = 3,
    window_days: int = 14,
) -> dict:
    """Detect structured CREDIT transactions within a rolling window.

    Returns keys: detected, occurrences, window_start, window_end, refs, total.
    Window dates are ISO-8601 (YYYY-MM-DD).
    """
    best = _best_window(_qualifying(transactions, lower_bound, upper_bound), window_days)
    count = len(best)
    if not best or count < occurrences:
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
        "window_start": best[0]["date"].strftime(OUTPUT_DATE_FORMAT),
        "window_end": best[-1]["date"].strftime(OUTPUT_DATE_FORMAT),
        "refs": [t["ref"] for t in best],
        "total": round(sum(t["amount"] for t in best), 2),
    }
