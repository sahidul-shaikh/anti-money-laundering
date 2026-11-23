"""Pytest tests for the AML-STR structuring detector."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from detector import detect_structuring  # noqa: E402


def txn(date: str, ref: str, amount: float, direction: str = "CREDIT") -> dict:
    return {"date": date, "ref": ref, "amount": amount, "direction": direction}


def test_fires_on_three_credits_in_window():
    txns = [
        txn("20240101", "A", 9000.00),
        txn("20240105", "B", 8500.00),
        txn("20240110", "C", 9500.50),
    ]
    result = detect_structuring(txns)
    assert result == {
        "detected": True,
        "occurrences": 3,
        "window_start": "2024-01-01",
        "window_end": "2024-01-10",
        "refs": ["A", "B", "C"],
        "total": 27000.50,
    }


def test_lower_bound_inclusive_and_just_below_excluded():
    txns = [txn("20240101", "A", 8000.00), txn("20240102", "B", 8000.00), txn("20240103", "C", 7999.99)]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_upper_bound_inclusive():
    txns = [txn("20240101", "A", 9999.99), txn("20240102", "B", 9999.99), txn("20240103", "C", 9999.99)]
    result = detect_structuring(txns)
    assert result["detected"] is True
    assert result["refs"] == ["A", "B", "C"]


def test_exactly_10000_excluded():
    txns = [txn("20240101", "A", 10000.00), txn("20240102", "B", 9000.00), txn("20240103", "C", 9000.00)]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 2
    assert result["refs"] == []


def test_debits_ignored():
    txns = [
        txn("20240101", "A", 9000.00),
        txn("20240102", "B", 9000.00, direction="DEBIT"),
        txn("20240103", "C", 9000.00),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_window_spans_fourteen_days_inclusive():
    txns = [txn("20240101", "A", 9000.00), txn("20240107", "B", 9000.00), txn("20240114", "C", 9000.00)]
    result = detect_structuring(txns)
    assert result["detected"] is True
    assert result["window_start"] == "2024-01-01"
    assert result["window_end"] == "2024-01-14"


def test_day_fourteen_falls_outside_window():
    txns = [txn("20240101", "A", 9000.00), txn("20240112", "B", 9000.00), txn("20240115", "C", 9000.00)]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_densest_window_is_reported():
    txns = [
        txn("20240101", "A", 8500.00),
        txn("20240201", "B", 8500.00),
        txn("20240202", "C", 8500.00),
        txn("20240203", "D", 8500.00),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is True
    assert result["window_start"] == "2024-02-01"
    assert result["window_end"] == "2024-02-03"
    assert result["refs"] == ["B", "C", "D"]


def test_not_fired_keeps_counts_and_nulls_window_fields():
    result = detect_structuring([txn("20240101", "A", 9000.00)])
    assert result == {
        "detected": False,
        "occurrences": 1,
        "window_start": None,
        "window_end": None,
        "refs": [],
        "total": 0.0,
    }


def test_empty_input_not_fired():
    result = detect_structuring([])
    assert result == {
        "detected": False,
        "occurrences": 0,
        "window_start": None,
        "window_end": None,
        "refs": [],
        "total": 0.0,
    }


def test_custom_parameters_respected():
    txns = [txn("20240101", "A", 500.00), txn("20240102", "B", 500.00)]
    result = detect_structuring(txns, lower_bound=400.0, upper_bound=600.0, occurrences=2, window_days=1)
    assert result["detected"] is False
    result = detect_structuring(txns, lower_bound=400.0, upper_bound=600.0, occurrences=2, window_days=2)
    assert result["detected"] is True
    assert result["total"] == 1000.0


def test_refs_ordered_by_date_then_ref():
    txns = [txn("20240103", "Z", 9000.00), txn("20240101", "M", 9000.00), txn("20240101", "B", 9000.00)]
    result = detect_structuring(txns)
    assert result["refs"] == ["B", "M", "Z"]
