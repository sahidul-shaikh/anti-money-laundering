"""Pytest tests for the structuring detector."""

from detector import detect_structuring


def txn(date: str, ref: str, amount: float, direction: str = "CREDIT") -> dict:
    return {"date": date, "ref": ref, "amount": amount, "direction": direction}


def test_three_qualifying_credits_in_window_detected():
    txns = [
        txn("20240101", "A", 9000.0),
        txn("20240105", "B", 9000.0),
        txn("20240110", "C", 9000.0),
    ]
    result = detect_structuring(txns)
    assert result == {
        "detected": True,
        "occurrences": 3,
        "window_start": "2024-01-01",
        "window_end": "2024-01-10",
        "refs": ["A", "B", "C"],
        "total": 27000.0,
    }


def test_two_qualifying_credits_not_detected():
    txns = [txn("20240101", "A", 9000.0), txn("20240102", "B", 9000.0)]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_lower_bound_inclusive():
    txns = [txn("20240101", "A", 8000.0), txn("20240102", "B", 8000.0), txn("20240103", "C", 8000.0)]
    assert detect_structuring(txns)["detected"] is True


def test_upper_bound_inclusive():
    txns = [txn("20240101", "A", 9999.99), txn("20240102", "B", 9999.99), txn("20240103", "C", 9999.99)]
    assert detect_structuring(txns)["detected"] is True


def test_above_upper_bound_excluded():
    txns = [txn("20240101", "A", 10000.0), txn("20240102", "B", 9000.0), txn("20240103", "C", 9000.0)]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_below_lower_bound_excluded():
    txns = [
        txn("20240101", "A", 7999.99),
        txn("20240102", "B", 9000.0),
        txn("20240103", "C", 9000.0),
        txn("20240104", "D", 9000.0),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is True
    assert result["refs"] == ["B", "C", "D"]


def test_debits_ignored():
    txns = [
        txn("20240101", "A", 9000.0, "DEBIT"),
        txn("20240102", "B", 9000.0, "DEBIT"),
        txn("20240103", "C", 9000.0, "CREDIT"),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 1


def test_window_spans_14_calendar_days_inclusive():
    txns = [
        txn("20240101", "A", 9000.0),
        txn("20240108", "B", 9000.0),
        txn("20240114", "C", 9000.0),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is True
    assert result["window_start"] == "2024-01-01"
    assert result["window_end"] == "2024-01-14"


def test_fifteen_day_span_not_in_one_window():
    txns = [
        txn("20240101", "A", 9000.0),
        txn("20240108", "B", 9000.0),
        txn("20240115", "C", 9000.0),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_window_end_is_last_qualifying_item_not_window_edge():
    txns = [
        txn("20240101", "A", 9000.0),
        txn("20240102", "B", 9000.0),
        txn("20240103", "C", 9000.0),
    ]
    result = detect_structuring(txns, window_days=14)
    assert result["window_end"] == "2024-01-03"


def test_occurrences_parameter_respected():
    txns = [txn("20240101", "A", 9000.0), txn("20240102", "B", 9000.0)]
    assert detect_structuring(txns, occurrences=2)["detected"] is True
    assert detect_structuring(txns, occurrences=3)["detected"] is False


def test_best_window_chosen_when_several_exist():
    txns = [
        txn("20240101", "A", 9000.0),
        txn("20240201", "B", 9000.0),
        txn("20240202", "C", 9000.0),
        txn("20240203", "D", 9000.0),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is True
    assert result["refs"] == ["B", "C", "D"]
    assert result["window_start"] == "2024-02-01"


def test_same_day_transactions_each_count():
    txns = [txn("20240101", "A", 9000.0), txn("20240101", "B", 9000.0), txn("20240101", "C", 9000.0)]
    assert detect_structuring(txns)["detected"] is True


def test_total_rounded_to_cents():
    txns = [
        txn("20240101", "A", 8000.10),
        txn("20240102", "B", 9000.20),
        txn("20240103", "C", 9999.99),
    ]
    assert detect_structuring(txns)["total"] == 27000.29


def test_not_detected_shape_matches_detected_shape():
    detected_keys = set(detect_structuring([txn("20240101", "A", 9000.0)] * 3).keys())
    not_detected_keys = set(detect_structuring([]).keys())
    assert detected_keys == not_detected_keys == {
        "detected", "occurrences", "window_start", "window_end", "refs", "total",
    }


def test_not_detected_empty_input():
    assert detect_structuring([]) == {
        "detected": False,
        "occurrences": 0,
        "window_start": None,
        "window_end": None,
        "refs": [],
        "total": 0.0,
    }
