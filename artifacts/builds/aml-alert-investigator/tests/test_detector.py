"""Pytest tests for the AML-STR structuring detector."""

from detector import detect_structuring


def txn(date: str, ref: str, amount: float, direction: str = "CREDIT") -> dict:
    return {"date": date, "ref": ref, "amount": amount, "direction": direction}


def test_fires_on_three_in_fourteen_day_window():
    txns = [
        txn("20260101", "A", 9000),
        txn("20260108", "B", 9500),
        txn("20260114", "C", 8200),
    ]
    result = detect_structuring(txns)
    assert result == {
        "detected": True,
        "occurrences": 3,
        "window_start": "2026-01-01",
        "window_end": "2026-01-14",
        "refs": ["A", "B", "C"],
        "total": 26700.0,
    }


def test_window_dates_are_iso_not_the_input_format():
    txns = [
        txn("20181101", "A", 9000),
        txn("20181102", "B", 9000),
        txn("20181103", "C", 9000),
    ]
    result = detect_structuring(txns)
    assert result["window_start"] == "2018-11-01"
    assert result["window_end"] == "2018-11-03"


def test_window_spans_exactly_fourteen_days():
    txns = [
        txn("20260101", "A", 9000),
        txn("20260108", "B", 9000),
        txn("20260115", "C", 9000),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_bounds_are_inclusive():
    txns = [
        txn("20260101", "A", 8000.0),
        txn("20260102", "B", 9999.99),
        txn("20260103", "C", 9000.0),
    ]
    assert detect_structuring(txns)["detected"] is True


def test_outside_bounds_excluded():
    txns = [
        txn("20260101", "A", 7999.99),
        txn("20260102", "B", 10000.00),
        txn("20260103", "C", 9000.0),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 1


def test_debits_do_not_count():
    txns = [
        txn("20260101", "A", 9000, "DEBIT"),
        txn("20260102", "B", 9000, "DEBIT"),
        txn("20260103", "C", 9000, "CREDIT"),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 1


def test_not_detected_shape_matches_detected_shape():
    result = detect_structuring([])
    assert set(result) == {
        "detected",
        "occurrences",
        "window_start",
        "window_end",
        "refs",
        "total",
    }
    assert result == {
        "detected": False,
        "occurrences": 0,
        "window_start": None,
        "window_end": None,
        "refs": [],
        "total": 0.0,
    }


def test_same_day_transactions_each_count():
    txns = [
        txn("20260201", "A", 9000),
        txn("20260201", "B", 9100),
        txn("20260201", "C", 9200),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is True
    assert result["refs"] == ["A", "B", "C"]
    assert result["window_start"] == result["window_end"] == "2026-02-01"


def test_refs_ordered_by_date_then_input_order():
    txns = [
        txn("20260105", "C", 9000),
        txn("20260101", "A", 9000),
        txn("20260105", "D", 9000),
        txn("20260103", "B", 9000),
    ]
    result = detect_structuring(txns)
    assert result["refs"] == ["A", "B", "C", "D"]


def test_custom_occurrences_and_window():
    txns = [
        txn("20260101", "A", 9000),
        txn("20260103", "B", 9000),
    ]
    result = detect_structuring(txns, occurrences=2, window_days=3)
    assert result["detected"] is True
    assert result["window_end"] == "2026-01-03"
