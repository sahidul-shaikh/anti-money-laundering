"""Visible tests for detect_structuring."""

from detector import detect_structuring

KEYS = {"detected", "occurrences", "window_start", "window_end", "refs", "total"}


def credit(date, ref, amount, direction="CREDIT"):
    return {"date": date, "ref": ref, "amount": amount, "direction": direction}


def test_detects_three_inbound_in_window():
    txns = [
        credit("20240101", "A", 8500),
        credit("20240105", "B", 9000),
        credit("20240110", "C", 8800),
    ]
    result = detect_structuring(txns)
    assert set(result) == KEYS
    assert result["detected"] is True
    assert result["occurrences"] == 3
    assert result["window_start"] == "2024-01-01"
    assert result["window_end"] == "2024-01-10"
    assert result["refs"] == ["A", "B", "C"]
    assert result["total"] == 26300.0


def test_window_dates_are_iso_not_the_input_format():
    txns = [
        credit("20181101", "A", 8500),
        credit("20181102", "B", 8500),
        credit("20181103", "C", 8500),
    ]
    result = detect_structuring(txns)
    assert result["window_start"] == "2018-11-01"
    assert result["window_end"] == "2018-11-03"


def test_bounds_are_inclusive():
    txns = [
        credit("20240101", "LO", 8000.00),
        credit("20240102", "HI", 9999.99),
        credit("20240103", "MID", 9000),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is True
    assert result["refs"] == ["LO", "HI", "MID"]


def test_amounts_outside_bounds_do_not_count():
    txns = [
        credit("20240101", "BELOW", 7999.99),
        credit("20240102", "ABOVE", 10000),
        credit("20240103", "OK", 9000),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 1


def test_debits_are_ignored():
    txns = [
        credit("20240101", "A", 8500),
        credit("20240102", "B", 8500, direction="DEBIT"),
        credit("20240103", "C", 8500),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_window_span_is_fewer_than_window_days():
    # Day 0 and day 13 fall in a 14-day window; day 14 does not.
    inside = [credit("20240101", "A", 8500), credit("20240107", "B", 8500), credit("20240114", "C", 8500)]
    assert detect_structuring(inside)["detected"] is False

    within = [credit("20240101", "A", 8500), credit("20240107", "B", 8500), credit("20240113", "C", 8500)]
    result = detect_structuring(within)
    assert result["detected"] is True
    assert result["window_end"] == "2024-01-13"


def test_not_detected_shape_matches_detected_shape():
    result = detect_structuring([credit("20240101", "A", 8500)])
    assert set(result) == KEYS
    assert result["detected"] is False
    assert result["occurrences"] == 1
    assert result["refs"] == []


def test_empty_input():
    result = detect_structuring([])
    assert set(result) == KEYS
    assert result["detected"] is False
    assert result["occurrences"] == 0
    assert result["total"] == 0.0
