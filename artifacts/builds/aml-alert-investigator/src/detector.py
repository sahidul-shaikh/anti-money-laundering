"""Actimize AML-STR-CCE-INN-A-D01-DST structuring detector.

Fires when at least `occurrences` inbound (CREDIT) transactions, each with an
amount in the closed interval [lower_bound, upper_bound], fall within a span of
`window_days` calendar days. The span is inclusive at both ends, so a window of
14 days covers 14 calendar dates (first date to first date + 13 days).

Among all windows, the one with the most qualifying transactions is reported;
ties go to the earliest window. When the rule does not fire, the reported
occurrences is that best count, and the window fields are None.
"""

from datetime import date, datetime

INPUT_DATE_FORMAT = "%Y%m%d"
DIRECTION = "CREDIT"


def _qualifying(
    transactions: list[dict], lower_bound: float, upper_bound: float
) -> list[tuple[date, str, float]]:
    """Return (date, ref, amount) for CREDIT rows within bounds, sorted by date.

    The sort is stable, so transactions on the same date keep their input order.
    """
    rows = [
        (datetime.strptime(str(t["date"]), INPUT_DATE_FORMAT).date(), t["ref"], float(t["amount"]))
        for t in transactions
        if t["direction"] == DIRECTION
        and lower_bound <= float(t["amount"]) <= upper_bound
    ]
    rows.sort(key=lambda row: row[0])
    return rows


def _window_from(
    rows: list[tuple[date, str, float]], start: int, window_days: int
) -> list[tuple[date, str, float]]:
    """Return the rows from `start` onward whose dates fall within the window.

    A row belongs to the window when it is fewer than `window_days` days after
    the window's first row.
    """
    first_date = rows[start][0]
    members = []
    for row in rows[start:]:
        if (row[0] - first_date).days >= window_days:
            break
        members.append(row)
    return members


def detect_structuring(
    transactions: list[dict],
    lower_bound: float = 8000.0,
    upper_bound: float = 9999.99,
    occurrences: int = 3,
    window_days: int = 14,
) -> dict:
    """Apply the AML-STR structuring rule to a list of transactions.

    Each transaction needs keys date (YYYYMMDD), ref, amount and direction.
    Returns a dict with keys detected, occurrences, window_start, window_end
    (ISO-8601 YYYY-MM-DD strings or None), refs (chronological) and total
    (rounded to 2 dp).
    """
    rows = _qualifying(transactions, lower_bound, upper_bound)
    best = max(
        (_window_from(rows, i, window_days) for i in range(len(rows))),
        key=len,
        default=[],
    )
    count = len(best)
    if best and count >= occurrences:
        return {
            "detected": True,
            "occurrences": count,
            "window_start": best[0][0].isoformat(),
            "window_end": best[-1][0].isoformat(),
            "refs": [ref for _, ref, _ in best],
            "total": round(sum(amount for _, _, amount in best), 2),
        }
    return {
        "detected": False,
        "occurrences": count,
        "window_start": None,
        "window_end": None,
        "refs": [],
        "total": 0.0,
    }
