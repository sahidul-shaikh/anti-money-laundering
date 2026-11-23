"""Actimize AML-STR structuring detector.

Implements rule AML-STR-CCE-INN-A-D01-DST (structured incremental
cash-equivalent deposits): flags three or more qualifying credits whose
amounts fall within ``[lower_bound, upper_bound]`` (inclusive of both
ends) occurring within a rolling window that spans ``window_days``
calendar days. Only credits are evaluated; debits are ignored.

Window semantics: a window of ``window_days`` days spans that many
calendar days inclusive of both endpoints, so the earliest and latest
qualifying transaction in a triggering window may differ by at most
``window_days - 1`` days (e.g. a 14-day window covers day 1 through
day 14 inclusive, a 13-day gap between the two).

Detection fires at the earliest point in time the occurrence threshold
is met, as a real-time monitor would, rather than searching the whole
history for the single biggest cluster.

When the threshold is never met, ``occurrences`` still reports the size
of the largest qualifying cluster found within a single window_days
span, but no evidence is asserted: ``refs`` is empty, ``total`` is 0.0,
and ``window_start``/``window_end`` are ``None``. A citation is only
ever returned for a cluster that actually triggered the rule.
"""

from datetime import datetime, timedelta


def detect_structuring(
    transactions: list[dict],
    lower_bound: float = 8000.0,
    upper_bound: float = 9999.99,
    occurrences: int = 3,
    window_days: int = 14,
) -> dict:
    qualifying = []
    for txn in transactions:
        if str(txn["direction"]).strip().lower() != "credit":
            continue
        amount = txn["amount"]
        if amount < lower_bound or amount > upper_bound:
            continue
        txn_date = datetime.strptime(txn["date"], "%Y%m%d").date()
        qualifying.append((txn_date, txn))

    qualifying.sort(key=lambda pair: pair[0])

    if not qualifying:
        return {
            "detected": False,
            "occurrences": 0,
            "window_start": None,
            "window_end": None,
            "refs": [],
            "total": 0.0,
        }

    max_span = timedelta(days=window_days - 1)
    left = 0
    best_left, best_right, best_size = 0, 0, 0
    detected = False

    for right in range(len(qualifying)):
        while qualifying[right][0] - qualifying[left][0] > max_span:
            left += 1
        size = right - left + 1
        if size > best_size:
            best_size = size
            best_left, best_right = left, right
        if size >= occurrences:
            best_left, best_right, best_size = left, right, size
            detected = True
            break

    group = [txn for _, txn in qualifying[best_left:best_right + 1]]

    if not detected:
        return {
            "detected": False,
            "occurrences": len(group),
            "window_start": None,
            "window_end": None,
            "refs": [],
            "total": 0.0,
        }

    return {
        "detected": True,
        "occurrences": len(group),
        "window_start": group[0]["date"],
        "window_end": group[-1]["date"],
        "refs": [txn["ref"] for txn in group],
        "total": round(sum(txn["amount"] for txn in group), 2),
    }
