"""Tests for the AML-STR structuring detector."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from detector import detect_structuring  # noqa: E402


def tx(date, ref, amount, direction="CREDIT"):
    """Build one transaction dict."""
    return {"date": date, "ref": ref, "amount": amount, "direction": direction}


def test_detects_three_in_window_with_full_result():
    txns = [
        tx("20250101", "r1", 9000.0),
        tx("20250105", "r2", 9500.0),
        tx("20250110", "r3", 8100.0),
    ]
    assert detect_structuring(txns) == {
        "detected": True,
        "occurrences": 3,
        "window_start": "2025-01-01",
        "window_end": "2025-01-10",
        "refs": ["r1", "r2", "r3"],
        "total": 26600.0,
    }


def test_window_dates_are_iso_not_the_input_format():
    txns = [
        tx("20181101", "r1", 9000.0),
        tx("20181102", "r2", 9000.0),
        tx("20181103", "r3", 9000.0),
    ]
    result = detect_structuring(txns)
    assert result["window_start"] == "2018-11-01"
    assert result["window_end"] == "2018-11-03"


def test_lower_and_upper_bounds_are_inclusive():
    txns = [
        tx("20250101", "lo", 8000.00),
        tx("20250102", "hi", 9999.99),
        tx("20250103", "mid", 9000.00),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is True
    assert result["refs"] == ["lo", "hi", "mid"]


def test_amounts_just_outside_bounds_do_not_count():
    txns = [
        tx("20250101", "a", 7999.99),
        tx("20250102", "b", 10000.00),
        tx("20250103", "c", 10000.01),
    ]
    result = detect_structuring(txns)
    assert result == {
        "detected": False,
        "occurrences": 0,
        "window_start": None,
        "window_end": None,
        "refs": [],
        "total": 0.0,
    }


def test_debit_rows_are_ignored():
    txns = [
        tx("20250101", "r1", 9000.0),
        tx("20250102", "r2", 9000.0, direction="DEBIT"),
        tx("20250103", "r3", 9000.0),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_window_spans_exactly_window_days_dates():
    inside = [
        tx("20250101", "r1", 9000.0),
        tx("20250108", "r2", 9000.0),
        tx("20250114", "r3", 9000.0),
    ]
    result = detect_structuring(inside)
    assert result["detected"] is True
    assert result["window_start"] == "2025-01-01"
    assert result["window_end"] == "2025-01-14"


def test_date_fourteen_days_after_start_is_outside_window():
    txns = [
        tx("20250101", "r1", 9000.0),
        tx("20250108", "r2", 9000.0),
        tx("20250115", "r3", 9000.0),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_not_detected_still_reports_best_window_count():
    txns = [
        tx("20250101", "r1", 9000.0),
        tx("20250102", "r2", 9000.0),
        tx("20250301", "r3", 9000.0),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 2
    assert set(result) == {
        "detected",
        "occurrences",
        "window_start",
        "window_end",
        "refs",
        "total",
    }


def test_unsorted_input_reports_refs_in_date_order():
    txns = [
        tx("20250110", "late", 9000.0),
        tx("20250101", "early", 9000.0),
        tx("20250105", "mid", 9000.0),
    ]
    result = detect_structuring(txns)
    assert result["refs"] == ["early", "mid", "late"]
    assert result["window_start"] == "2025-01-01"
    assert result["window_end"] == "2025-01-10"


def test_total_is_rounded_to_two_decimals():
    txns = [
        tx("20250101", "r1", 8000.111),
        tx("20250102", "r2", 8000.111),
        tx("20250103", "r3", 8000.111),
    ]
    assert detect_structuring(txns)["total"] == 24000.33


def test_custom_parameters_are_honoured():
    txns = [
        tx("20250101", "r1", 100.0),
        tx("20250103", "r2", 150.0),
    ]
    result = detect_structuring(
        txns, lower_bound=50.0, upper_bound=200.0, occurrences=2, window_days=3
    )
    assert result["detected"] is True
    assert result["refs"] == ["r1", "r2"]
