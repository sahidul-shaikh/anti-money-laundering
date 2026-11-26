"""Tests for the AML-STR structuring detector."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from detector import detect_structuring  # noqa: E402


def txn(date: str, ref: str, amount: float, direction: str = "credit") -> dict:
    return {"date": date, "ref": ref, "amount": amount, "direction": direction}


def test_three_in_range_within_window_detected():
    txns = [
        txn("20260101", "a", 9000),
        txn("20260105", "b", 8500),
        txn("20260110", "c", 9900),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is True
    assert result["occurrences"] == 3
    assert result["window_start"] == "2026-01-01"
    assert result["window_end"] == "2026-01-10"
    assert result["refs"] == ["a", "b", "c"]
    assert result["total"] == 27400.0


def test_lower_bound_is_inclusive():
    txns = [txn("20260101", "a", 8000.00), txn("20260102", "b", 8000.00), txn("20260103", "c", 8000.00)]
    assert detect_structuring(txns)["detected"] is True


def test_upper_bound_is_inclusive_and_above_is_excluded():
    inclusive = [txn("20260101", "a", 9999.99), txn("20260102", "b", 9999.99), txn("20260103", "c", 9999.99)]
    assert detect_structuring(inclusive)["detected"] is True

    above = [txn("20260101", "a", 10000), txn("20260102", "b", 10000), txn("20260103", "c", 10000)]
    result = detect_structuring(above)
    assert result["detected"] is False
    assert result["occurrences"] == 0


def test_below_lower_bound_excluded():
    txns = [txn("20260101", "a", 7999.99), txn("20260102", "b", 7999.99), txn("20260103", "c", 7999.99)]
    assert detect_structuring(txns)["detected"] is False


def test_window_of_14_days_is_inclusive_span():
    within = [txn("20260101", "a", 9000), txn("20260108", "b", 9000), txn("20260114", "c", 9000)]
    assert detect_structuring(within)["detected"] is True

    outside = [txn("20260101", "a", 9000), txn("20260108", "b", 9000), txn("20260115", "c", 9000)]
    result = detect_structuring(outside)
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_not_detected_has_same_keys_and_empty_window():
    txns = [txn("20260101", "a", 9000), txn("20260102", "b", 9000)]
    result = detect_structuring(txns)
    assert set(result) == {"detected", "occurrences", "window_start", "window_end", "refs", "total"}
    assert result["detected"] is False
    assert result["occurrences"] == 2
    assert result["window_start"] is None
    assert result["window_end"] is None
    assert result["refs"] == []
    assert result["total"] == 0.0


def test_refs_come_back_in_date_order_regardless_of_input_order():
    txns = [txn("20260110", "c", 9000), txn("20260101", "a", 9000), txn("20260105", "b", 9000)]
    result = detect_structuring(txns)
    assert result["refs"] == ["a", "b", "c"]
    assert result["window_start"] == "2026-01-01"
    assert result["window_end"] == "2026-01-10"


def test_window_dates_are_iso_format():
    txns = [txn("20181101", "a", 9000), txn("20181103", "b", 9000), txn("20181105", "c", 9000)]
    result = detect_structuring(txns)
    assert result["window_start"] == "2018-11-01"
    assert result["window_end"] == "2018-11-05"


def test_debits_are_ignored():
    txns = [
        txn("20260101", "a", 9000, "debit"),
        txn("20260102", "b", 9000, "debit"),
        txn("20260103", "c", 9000, "debit"),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 0


def test_debits_do_not_pad_the_occurrence_count():
    txns = [
        txn("20260101", "a", 9000, "credit"),
        txn("20260102", "b", 9000, "debit"),
        txn("20260103", "c", 9000, "credit"),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_credits_are_counted_across_interleaved_debits():
    txns = [
        txn("20260101", "a", 9000, "credit"),
        txn("20260102", "b", 9000, "debit"),
        txn("20260103", "c", 9000, "credit"),
        txn("20260104", "d", 9000, "credit"),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is True
    assert result["refs"] == ["a", "c", "d"]
    assert result["window_start"] == "2026-01-01"
    assert result["window_end"] == "2026-01-04"


def test_direction_is_case_insensitive():
    txns = [
        txn("20260101", "a", 9000, "CREDIT"),
        txn("20260102", "b", 9000, " Credit "),
        txn("20260103", "c", 9000, "credit"),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is True
    assert result["refs"] == ["a", "b", "c"]


def test_custom_parameters_are_honoured():
    txns = [txn("20260101", "a", 500), txn("20260120", "b", 500)]
    result = detect_structuring(
        txns, lower_bound=400, upper_bound=600, occurrences=2, window_days=30
    )
    assert result["detected"] is True
    assert result["occurrences"] == 2
    assert result["window_end"] == "2026-01-20"
