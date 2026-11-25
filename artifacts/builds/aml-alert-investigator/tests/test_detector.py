"""Tests for detect_structuring. Run with: PYTHONPATH=src pytest tests"""

from detector import detect_structuring


def txn(date, ref, amount, direction="CREDIT"):
    return {"date": date, "ref": ref, "amount": amount, "direction": direction}


def test_three_credits_in_window_fire():
    txns = [
        txn("20260105", "A", 8500.0),
        txn("20260101", "B", 9000.0),
        txn("20260110", "C", 9999.99),
    ]
    assert detect_structuring(txns) == {
        "detected": True,
        "occurrences": 3,
        "window_start": "2026-01-01",
        "window_end": "2026-01-10",
        "refs": ["B", "A", "C"],
        "total": 27499.99,
    }


def test_lower_bound_inclusive():
    txns = [txn(f"2026010{i}", f"R{i}", 8000.0) for i in range(1, 4)]
    assert detect_structuring(txns)["detected"] is True


def test_below_lower_bound_excluded():
    txns = [txn(f"2026010{i}", f"R{i}", 7999.99) for i in range(1, 4)]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 0


def test_upper_bound_inclusive():
    txns = [txn(f"2026010{i}", f"R{i}", 9999.99) for i in range(1, 4)]
    assert detect_structuring(txns)["detected"] is True


def test_10000_does_not_qualify():
    txns = [
        txn("20260101", "A", 9000.0),
        txn("20260102", "B", 9000.0),
        txn("20260103", "C", 10000.0),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_debits_ignored():
    txns = [
        txn("20260101", "A", 9000.0),
        txn("20260102", "B", 9000.0),
        txn("20260103", "C", 9000.0, direction="DEBIT"),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_window_includes_d_plus_13_and_excludes_d_plus_14():
    inside = [txn("20260101", "A", 9000.0), txn("20260102", "B", 9000.0), txn("20260114", "C", 9000.0)]
    assert detect_structuring(inside)["detected"] is True

    outside = [txn("20260101", "A", 9000.0), txn("20260102", "B", 9000.0), txn("20260115", "C", 9000.0)]
    result = detect_structuring(outside)
    assert result["detected"] is False
    assert result["occurrences"] == 3


def test_window_days_parameter():
    txns = [txn("20260101", "A", 9000.0), txn("20260102", "B", 9000.0), txn("20260115", "C", 9000.0)]
    result = detect_structuring(txns, window_days=15)
    assert result["detected"] is True
    assert result["window_end"] == "2026-01-15"


def test_occurrences_parameter():
    txns = [txn("20260101", "A", 9000.0), txn("20260102", "B", 9000.0)]
    assert detect_structuring(txns, occurrences=2)["detected"] is True


def test_occurrences_counts_only_triggering_window():
    txns = [
        txn("20260101", "A", 9000.0),
        txn("20260102", "B", 9000.0),
        txn("20260103", "C", 9000.0),
        txn("20260120", "D", 9000.0),
    ]
    result = detect_structuring(txns)
    assert result["occurrences"] == 3
    assert result["window_end"] == "2026-01-03"
    assert result["refs"] == ["A", "B", "C"]


def test_earliest_qualifying_window_reported():
    txns = [
        txn("20260101", "A", 9000.0),
        txn("20260102", "B", 9000.0),
        txn("20260103", "C", 9000.0),
        txn("20260201", "D", 9000.0),
        txn("20260202", "E", 9000.0),
        txn("20260203", "F", 9000.0),
    ]
    result = detect_structuring(txns)
    assert result["window_start"] == "2026-01-01"
    assert result["refs"] == ["A", "B", "C"]


def test_same_day_keeps_input_order():
    txns = [
        txn("20260101", "X", 9000.0),
        txn("20260101", "Y", 9000.0),
        txn("20260101", "Z", 9000.0),
    ]
    assert detect_structuring(txns)["refs"] == ["X", "Y", "Z"]


def test_total_rounded_to_2dp():
    txns = [
        txn("20260101", "A", 8000.10),
        txn("20260102", "B", 8000.20),
        txn("20260103", "C", 8000.30),
    ]
    assert detect_structuring(txns)["total"] == 24000.6


def test_not_detected_shape():
    assert detect_structuring([]) == {
        "detected": False,
        "occurrences": 0,
        "window_start": None,
        "window_end": None,
        "refs": [],
        "total": 0.0,
    }
