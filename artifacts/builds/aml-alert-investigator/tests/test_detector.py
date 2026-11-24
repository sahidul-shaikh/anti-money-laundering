import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from detector import detect_structuring

KEYS = {"detected", "occurrences", "window_start", "window_end", "refs", "total"}


def txn(date: str, ref: str, amount: float, direction: str = "CREDIT") -> dict:
    return {"date": date, "ref": ref, "amount": amount, "direction": direction}


def test_fires_on_three_credits_in_window():
    result = detect_structuring([
        txn("20260101", "a", 9000.0),
        txn("20260105", "b", 9500.0),
        txn("20260110", "c", 8500.0),
    ])
    assert result == {
        "detected": True,
        "occurrences": 3,
        "window_start": "2026-01-01",
        "window_end": "2026-01-10",
        "refs": ["a", "b", "c"],
        "total": 27000.0,
    }


def test_result_has_exactly_the_documented_keys():
    assert set(detect_structuring([])) == KEYS
    assert set(detect_structuring([txn("20260101", "a", 9000.0)])) == KEYS


def test_window_of_14_days_includes_day_plus_13():
    result = detect_structuring([
        txn("20260101", "t1", 9000.0),
        txn("20260114", "t2", 9000.0),
        txn("20260108", "t3", 9000.0),
    ])
    assert result["detected"] is True
    assert result["window_start"] == "2026-01-01"
    assert result["window_end"] == "2026-01-14"
    assert result["refs"] == ["t1", "t3", "t2"]


def test_day_plus_14_falls_outside_window():
    result = detect_structuring([
        txn("20260101", "t1", 9000.0),
        txn("20260114", "t2", 9000.0),
        txn("20260115", "t3", 9000.0),
    ])
    assert result == {
        "detected": False,
        "occurrences": 2,
        "window_start": None,
        "window_end": None,
        "refs": [],
        "total": 0.0,
    }


def test_lower_and_upper_bounds_are_inclusive():
    result = detect_structuring([
        txn("20260101", "lo", 8000.00),
        txn("20260102", "hi", 9999.99),
        txn("20260103", "mid", 8000.01),
    ])
    assert result["detected"] is True
    assert result["refs"] == ["lo", "hi", "mid"]
    assert result["total"] == 26000.0


def test_just_below_lower_bound_does_not_qualify():
    result = detect_structuring([
        txn("20260101", "a", 7999.99),
        txn("20260102", "b", 9000.0),
        txn("20260103", "c", 9000.0),
    ])
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_exactly_10000_does_not_qualify():
    result = detect_structuring([
        txn("20260101", "a", 10000.00),
        txn("20260102", "b", 9000.0),
        txn("20260103", "c", 9000.0),
    ])
    assert result["detected"] is False
    assert result["occurrences"] == 2
    assert result["refs"] == []


def test_debits_are_ignored():
    result = detect_structuring([
        txn("20260101", "a", 9000.0, "DEBIT"),
        txn("20260102", "b", 9000.0, "DEBIT"),
        txn("20260103", "c", 9000.0, "DEBIT"),
    ])
    assert result["detected"] is False
    assert result["occurrences"] == 0


def test_debits_do_not_count_toward_occurrences():
    result = detect_structuring([
        txn("20260101", "a", 9000.0),
        txn("20260102", "b", 9000.0, "DEBIT"),
        txn("20260103", "c", 9000.0),
    ])
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_not_fired_reports_qualifying_count_and_empty_fields():
    result = detect_structuring([txn("20260101", "a", 9000.0)])
    assert result == {
        "detected": False,
        "occurrences": 1,
        "window_start": None,
        "window_end": None,
        "refs": [],
        "total": 0.0,
    }


def test_empty_input_is_not_detected():
    assert detect_structuring([]) == {
        "detected": False,
        "occurrences": 0,
        "window_start": None,
        "window_end": None,
        "refs": [],
        "total": 0.0,
    }


def test_earliest_firing_window_is_reported():
    result = detect_structuring([
        txn("20260101", "early", 9000.0),
        txn("20260120", "x", 9000.0),
        txn("20260121", "y", 9000.0),
        txn("20260122", "z", 9000.0),
    ])
    assert result["window_start"] == "2026-01-20"
    assert result["window_end"] == "2026-01-22"
    assert result["refs"] == ["x", "y", "z"]
    assert result["occurrences"] == 3


def test_refs_are_in_date_order_with_input_order_on_ties():
    result = detect_structuring([
        txn("20260103", "c", 9000.0),
        txn("20260101", "a", 9000.0),
        txn("20260101", "b", 9000.0),
    ])
    assert result["refs"] == ["a", "b", "c"]


def test_custom_parameters_are_honoured():
    result = detect_structuring(
        [txn("20260101", "a", 500.0), txn("20260101", "b", 500.0)],
        lower_bound=100.0,
        upper_bound=600.0,
        occurrences=2,
        window_days=1,
    )
    assert result["detected"] is True
    assert result["window_start"] == "2026-01-01"
    assert result["window_end"] == "2026-01-01"
    assert result["total"] == 1000.0


def test_total_is_rounded_to_two_decimals():
    result = detect_structuring([
        txn("20260101", "a", 8000.10),
        txn("20260102", "b", 8000.20),
        txn("20260103", "c", 8000.30),
    ])
    assert result["total"] == 24000.6
