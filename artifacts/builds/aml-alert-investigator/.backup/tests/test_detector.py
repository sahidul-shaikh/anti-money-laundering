"""Tests for the AML-STR structuring detector."""

from detector import detect_structuring


def _txn(date, ref, amount, direction="credit"):
    return {"date": date, "ref": ref, "amount": amount, "direction": direction}


def test_detects_three_qualifying_credits_within_window():
    txns = [
        _txn("20250101", "R1", 8000.0),
        _txn("20250105", "R2", 8500.0),
        _txn("20250110", "R3", 9000.0),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is True
    assert result["occurrences"] == 3
    assert result["window_start"] == "20250101"
    assert result["window_end"] == "20250110"
    assert result["refs"] == ["R1", "R2", "R3"]
    assert result["total"] == 25500.0


def test_no_qualifying_transactions_returns_empty_shape():
    txns = [_txn("20250101", "R1", 500.0)]
    result = detect_structuring(txns)
    assert result == {
        "detected": False,
        "occurrences": 0,
        "window_start": None,
        "window_end": None,
        "refs": [],
        "total": 0.0,
    }


def test_below_threshold_reports_count_but_no_evidence():
    txns = [
        _txn("20250101", "R1", 8000.0, direction="debit"),
        _txn("20250102", "R2", 8500.0),
        _txn("20250103", "R3", 9000.0),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 2
    assert result["refs"] == []
    assert result["total"] == 0.0
    assert result["window_start"] is None
    assert result["window_end"] is None


def test_lower_bound_is_inclusive():
    txns = [_txn("20250101", "R1", 8000.0)]
    result = detect_structuring(txns, occurrences=1)
    assert result["detected"] is True
    assert result["refs"] == ["R1"]


def test_below_lower_bound_excluded():
    txns = [_txn("20250101", "R1", 7999.99)]
    result = detect_structuring(txns, occurrences=1)
    assert result["detected"] is False
    assert result["occurrences"] == 0


def test_upper_bound_is_inclusive():
    txns = [_txn("20250101", "R1", 9999.99)]
    result = detect_structuring(txns, occurrences=1)
    assert result["detected"] is True
    assert result["refs"] == ["R1"]


def test_exactly_ten_thousand_does_not_qualify():
    txns = [
        _txn("20250101", "R1", 10000.00),
        _txn("20250102", "R2", 8500.0),
        _txn("20250103", "R3", 9000.0),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 2
    assert result["refs"] == []


def test_window_boundary_thirteen_day_gap_included():
    txns = [
        _txn("20250101", "R1", 8000.0),
        _txn("20250107", "R2", 8500.0),
        _txn("20250114", "R3", 9000.0),
    ]
    result = detect_structuring(txns, window_days=14)
    assert result["detected"] is True
    assert result["window_start"] == "20250101"
    assert result["window_end"] == "20250114"


def test_window_boundary_fourteen_day_gap_excluded():
    txns = [
        _txn("20250101", "R1", 8000.0),
        _txn("20250108", "R2", 8500.0),
        _txn("20250115", "R3", 9000.0),
    ]
    result = detect_structuring(txns, window_days=14)
    assert result["detected"] is False
    assert result["occurrences"] == 2
    assert result["refs"] == []


def test_custom_parameters_are_respected():
    txns = [
        _txn("20250101", "R1", 150.0),
        _txn("20250103", "R2", 180.0),
    ]
    result = detect_structuring(
        txns, lower_bound=100.0, upper_bound=200.0, occurrences=2, window_days=7
    )
    assert result["detected"] is True
    assert result["occurrences"] == 2
    assert result["total"] == 330.0


def test_same_date_transactions_preserve_input_order():
    txns = [
        _txn("20250101", "R2", 8200.0),
        _txn("20250101", "R1", 8100.0),
        _txn("20250102", "R3", 8300.0),
    ]
    result = detect_structuring(txns)
    assert result["refs"] == ["R2", "R1", "R3"]


def test_detection_stops_at_earliest_triggering_window():
    txns = [
        _txn("20250101", "R1", 8000.0),
        _txn("20250102", "R2", 8100.0),
        _txn("20250103", "R3", 8200.0),
        _txn("20250104", "R4", 8300.0),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is True
    assert result["refs"] == ["R1", "R2", "R3"]
    assert result["window_end"] == "20250103"


def test_output_has_exactly_the_contracted_keys():
    result = detect_structuring([_txn("20250101", "R1", 9000.0)])
    assert set(result) == {
        "detected", "occurrences", "window_start", "window_end", "refs", "total",
    }
