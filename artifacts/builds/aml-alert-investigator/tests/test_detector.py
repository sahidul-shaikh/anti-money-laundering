from detector import detect_structuring


def txn(date: str, ref: str, amount: float, direction: str = "CREDIT") -> dict:
    return {"date": date, "ref": ref, "amount": amount, "direction": direction}


def test_three_in_window_detected_with_last_item_as_window_end():
    txns = [
        txn("20260101", "A", 9000.00),
        txn("20260108", "B", 9500.00),
        txn("20260114", "C", 8200.00),
    ]
    result = detect_structuring(txns)
    assert result == {
        "detected": True,
        "occurrences": 3,
        "window_start": "2026-01-01",
        "window_end": "2026-01-14",
        "refs": ["A", "B", "C"],
        "total": 26700.00,
    }


def test_lower_and_upper_bounds_are_inclusive():
    txns = [
        txn("20260101", "A", 8000.00),
        txn("20260102", "B", 9999.99),
        txn("20260103", "C", 8500.00),
    ]
    assert detect_structuring(txns)["detected"] is True


def test_amounts_just_outside_bounds_do_not_count():
    txns = [
        txn("20260101", "A", 7999.99),
        txn("20260102", "B", 10000.00),
        txn("20260103", "C", 9000.00),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 1


def test_debits_are_excluded_before_counting():
    txns = [
        txn("20260101", "A", 9000.00),
        txn("20260102", "B", 9000.00),
        txn("20260103", "C", 9000.00, direction="DEBIT"),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_window_spans_fourteen_calendar_days_inclusive():
    inside = [
        txn("20260101", "A", 9000.00),
        txn("20260102", "B", 9000.00),
        txn("20260114", "C", 9000.00),
    ]
    assert detect_structuring(inside)["detected"] is True

    outside = [
        txn("20260101", "A", 9000.00),
        txn("20260102", "B", 9000.00),
        txn("20260115", "C", 9000.00),
    ]
    result = detect_structuring(outside)
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_not_detected_keeps_all_keys_and_reports_largest_count():
    txns = [txn("20260101", "A", 9000.00), txn("20260201", "B", 9000.00)]
    result = detect_structuring(txns)
    assert result == {
        "detected": False,
        "occurrences": 1,
        "window_start": None,
        "window_end": None,
        "refs": [],
        "total": 0.0,
    }


def test_empty_input_is_not_detected():
    result = detect_structuring([])
    assert result["detected"] is False
    assert result["occurrences"] == 0
    assert result["refs"] == []


def test_ties_resolve_to_earliest_window():
    txns = [
        txn("20260101", "A", 9000.00),
        txn("20260102", "B", 9000.00),
        txn("20260103", "C", 9000.00),
        txn("20260301", "D", 9000.00),
        txn("20260302", "E", 9000.00),
        txn("20260303", "F", 9000.00),
    ]
    result = detect_structuring(txns)
    assert result["refs"] == ["A", "B", "C"]
    assert result["window_start"] == "2026-01-01"


def test_refs_follow_date_order_not_input_order():
    txns = [
        txn("20260103", "C", 9000.00),
        txn("20260101", "A", 9000.00),
        txn("20260102", "B", 9000.00),
    ]
    assert detect_structuring(txns)["refs"] == ["A", "B", "C"]


def test_custom_occurrences_and_window_days():
    txns = [txn("20260101", "A", 9000.00), txn("20260105", "B", 9000.00)]
    assert detect_structuring(txns, occurrences=2, window_days=5)["detected"] is True
    assert detect_structuring(txns, occurrences=2, window_days=4)["detected"] is False


def test_window_dates_are_iso_formatted():
    txns = [
        txn("20181101", "A", 9000.00),
        txn("20181105", "B", 9000.00),
        txn("20181110", "C", 9000.00),
    ]
    result = detect_structuring(txns)
    assert result["window_start"] == "2018-11-01"
    assert result["window_end"] == "2018-11-10"
