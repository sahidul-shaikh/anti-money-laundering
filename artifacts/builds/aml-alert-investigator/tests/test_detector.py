"""Pytest tests for the AML-STR structuring detector."""
from datetime import date, timedelta

from detector import detect_structuring

BASE = date(2026, 1, 1)


def txn(offset, ref, amount, direction="CREDIT"):
    """Build a transaction dict dated `offset` days after BASE."""
    day = BASE + timedelta(days=offset)
    return {"date": day.strftime("%Y%m%d"), "ref": ref, "amount": amount, "direction": direction}


def test_detects_three_credits_in_window():
    txns = [txn(0, "A", 9000.0), txn(3, "B", 8500.0), txn(10, "C", 9500.0)]
    result = detect_structuring(txns)
    assert result["detected"] is True
    assert result["occurrences"] == 3
    assert result["window_start"] == "2026-01-01"
    assert result["window_end"] == "2026-01-11"
    assert result["refs"] == ["A", "B", "C"]
    assert result["total"] == 27000.0


def test_returns_exactly_six_keys():
    keys = {"detected", "occurrences", "window_start", "window_end", "refs", "total"}
    assert set(detect_structuring([])) == keys
    assert set(detect_structuring([txn(0, "A", 9000.0)])) == keys


def test_lower_bound_is_inclusive():
    txns = [txn(0, "A", 8000.00), txn(1, "B", 8000.00), txn(2, "C", 8000.00)]
    assert detect_structuring(txns)["detected"] is True


def test_upper_bound_is_inclusive():
    txns = [txn(0, "A", 9999.99), txn(1, "B", 9999.99), txn(2, "C", 9999.99)]
    assert detect_structuring(txns)["detected"] is True


def test_amounts_outside_bounds_do_not_count():
    txns = [txn(0, "A", 7999.99), txn(1, "B", 10000.00), txn(2, "C", 9000.0)]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 1


def test_debits_are_ignored():
    txns = [txn(0, "A", 9000.0, "DEBIT"), txn(1, "B", 9000.0, "DEBIT"), txn(2, "C", 9000.0, "DEBIT")]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 0


def test_window_spans_fourteen_calendar_dates_inclusive():
    # Offsets 0 and 13 fall in one 14-day window; offset 14 does not.
    txns = [txn(0, "A", 9000.0), txn(13, "B", 9000.0), txn(14, "C", 9000.0)]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_item_on_last_window_day_counts():
    txns = [txn(0, "A", 9000.0), txn(13, "B", 9000.0), txn(13, "C", 9000.0)]
    result = detect_structuring(txns)
    assert result["detected"] is True
    assert result["window_end"] == "2026-01-14"


def test_densest_window_is_reported():
    txns = [
        txn(0, "A", 9000.0), txn(1, "B", 9000.0),
        txn(30, "C", 9000.0), txn(31, "D", 9000.0), txn(32, "E", 9000.0), txn(33, "F", 9000.0),
    ]
    result = detect_structuring(txns)
    assert result["occurrences"] == 4
    assert result["window_start"] == "2026-01-31"
    assert result["window_end"] == "2026-02-03"
    assert result["refs"] == ["C", "D", "E", "F"]


def test_refs_sorted_by_date_then_input_order():
    txns = [txn(5, "LATE", 9000.0), txn(2, "FIRST", 9000.0), txn(5, "TIE", 9000.0)]
    result = detect_structuring(txns)
    assert result["refs"] == ["FIRST", "LATE", "TIE"]


def test_total_rounded_to_two_places():
    txns = [txn(0, "A", 8000.10), txn(1, "B", 8500.20), txn(2, "C", 9000.333)]
    assert detect_structuring(txns)["total"] == 25500.63


def test_not_detected_empty_input_shape():
    result = detect_structuring([])
    assert result == {
        "detected": False,
        "occurrences": 0,
        "window_start": None,
        "window_end": None,
        "refs": [],
        "total": 0.0,
    }


def test_custom_parameters_are_honoured():
    txns = [txn(0, "A", 500.0), txn(1, "B", 600.0)]
    result = detect_structuring(txns, lower_bound=400.0, upper_bound=700.0, occurrences=2, window_days=2)
    assert result["detected"] is True
    assert result["refs"] == ["A", "B"]
    assert result["total"] == 1100.0


def test_window_dates_are_iso_formatted():
    txns = [txn(0, "A", 9000.0), txn(1, "B", 9000.0), txn(2, "C", 9000.0)]
    result = detect_structuring(txns)
    assert result["window_start"] == "2026-01-01"
    assert result["window_end"] == "2026-01-03"
