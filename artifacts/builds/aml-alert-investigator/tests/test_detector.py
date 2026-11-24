"""Pytest tests for the AML-STR structuring detector."""

from detector import detect_structuring


def txn(date: str, ref: str, amount: float, direction: str = "CREDIT") -> dict:
    return {"date": date, "ref": ref, "amount": amount, "direction": direction}


def test_three_in_window_detected():
    result = detect_structuring([
        txn("20250101", "A", 9000),
        txn("20250105", "B", 9500),
        txn("20250110", "C", 8000),
    ])
    assert result == {
        "detected": True,
        "occurrences": 3,
        "window_start": "2025-01-01",
        "window_end": "2025-01-10",
        "refs": ["A", "B", "C"],
        "total": 26500.0,
    }


def test_window_dates_are_iso_not_the_input_format():
    result = detect_structuring([
        txn("20181101", "A", 9000),
        txn("20181102", "B", 9000),
        txn("20181103", "C", 9000),
    ])
    assert result["window_start"] == "2018-11-01"
    assert result["window_end"] == "2018-11-03"


def test_lower_bound_inclusive():
    result = detect_structuring([txn("20250101", "A", 8000), txn("20250102", "B", 8000), txn("20250103", "C", 8000)])
    assert result["detected"] is True


def test_upper_bound_inclusive():
    result = detect_structuring([txn("20250101", "A", 9999.99), txn("20250102", "B", 9999.99), txn("20250103", "C", 9999.99)])
    assert result["detected"] is True
    assert result["total"] == 29999.97


def test_below_lower_bound_excluded():
    result = detect_structuring([txn("20250101", "A", 7999.99), txn("20250102", "B", 7999.99), txn("20250103", "C", 7999.99)])
    assert result["detected"] is False
    assert result["occurrences"] == 0


def test_at_or_above_ten_thousand_excluded():
    result = detect_structuring([txn("20250101", "A", 10000), txn("20250102", "B", 10000), txn("20250103", "C", 10000)])
    assert result["detected"] is False
    assert result["occurrences"] == 0


def test_debits_ignored():
    result = detect_structuring([
        txn("20250101", "A", 9000, "DEBIT"),
        txn("20250102", "B", 9000, "DEBIT"),
        txn("20250103", "C", 9000),
    ])
    assert result["detected"] is False
    assert result["occurrences"] == 1


def test_window_spans_fourteen_days_inclusive():
    result = detect_structuring([
        txn("20250101", "A", 9000),
        txn("20250108", "B", 9000),
        txn("20250114", "C", 9000),
    ])
    assert result["detected"] is True
    assert result["window_start"] == "2025-01-01"
    assert result["window_end"] == "2025-01-14"


def test_fifteen_day_span_not_in_one_window():
    result = detect_structuring([
        txn("20250101", "A", 9000),
        txn("20250108", "B", 9000),
        txn("20250115", "C", 9000),
    ])
    assert result["detected"] is False
    assert result["occurrences"] == 2
    assert result["window_start"] is None
    assert result["window_end"] is None
    assert result["refs"] == []
    assert result["total"] == 0.0


def test_not_detected_keeps_shape():
    result = detect_structuring([])
    assert set(result) == {"detected", "occurrences", "window_start", "window_end", "refs", "total"}
    assert result["detected"] is False
    assert result["occurrences"] == 0


def test_occurrences_threshold_respected():
    txns = [txn("20250101", "A", 9000), txn("20250102", "B", 9000)]
    assert detect_structuring(txns, occurrences=2)["detected"] is True
    assert detect_structuring(txns, occurrences=3)["detected"] is False


def test_input_order_does_not_change_result():
    result = detect_structuring([
        txn("20250110", "C", 9000),
        txn("20250101", "A", 9000),
        txn("20250105", "B", 9000),
    ])
    assert result["refs"] == ["A", "B", "C"]
    assert result["window_start"] == "2025-01-01"
    assert result["window_end"] == "2025-01-10"


def test_best_window_chosen_and_ties_go_earliest():
    txns = [
        txn("20250101", "A", 9000),
        txn("20250102", "B", 9000),
        txn("20250103", "C", 9000),
        txn("20250201", "D", 9000),
        txn("20250202", "E", 9000),
        txn("20250203", "F", 9000),
    ]
    result = detect_structuring(txns)
    assert result["refs"] == ["A", "B", "C"]
    assert result["window_start"] == "2025-01-01"


def test_total_rounded_to_two_places():
    result = detect_structuring([
        txn("20250101", "A", 8000.10),
        txn("20250102", "B", 8000.20),
        txn("20250103", "C", 8000.30),
    ])
    assert result["total"] == 24000.6
