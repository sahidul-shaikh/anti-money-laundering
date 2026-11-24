"""Tests for the AML-STR structuring detector."""

from detector import detect_structuring


def txn(day: str, ref: str, amount: float, direction: str = "credit") -> dict:
    return {"date": day, "ref": ref, "amount": amount, "direction": direction}


def test_fires_on_three_qualifying_credits_in_window():
    result = detect_structuring([
        txn("20240101", "A", 9000),
        txn("20240105", "B", 9500),
        txn("20240110", "C", 8200),
    ])
    assert result == {
        "detected": True,
        "occurrences": 3,
        "window_start": "2024-01-01",
        "window_end": "2024-01-10",
        "refs": ["A", "B", "C"],
        "total": 26700.0,
    }


def test_two_occurrences_do_not_fire():
    result = detect_structuring([txn("20240101", "A", 9000), txn("20240105", "B", 9000)])
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_lower_bound_is_inclusive():
    result = detect_structuring([txn("20240101", n, 8000) for n in "ABC"])
    assert result["detected"] is True


def test_below_lower_bound_excluded():
    result = detect_structuring([txn("20240101", n, 7999.99) for n in "ABC"])
    assert result["detected"] is False
    assert result["occurrences"] == 0


def test_upper_bound_inclusive_and_10000_excluded():
    assert detect_structuring([txn("20240101", n, 9999.99) for n in "ABC"])["detected"] is True
    assert detect_structuring([txn("20240101", n, 10000.0) for n in "ABC"])["detected"] is False


def test_only_credits_count():
    txns = [
        txn("20240101", "A", 9000),
        txn("20240102", "B", 9000, "debit"),
        txn("20240103", "C", 9000),
    ]
    assert detect_structuring(txns)["detected"] is False


def test_window_spans_fourteen_days_inclusive():
    result = detect_structuring([
        txn("20240101", "A", 9000),
        txn("20240107", "B", 9000),
        txn("20240114", "C", 9000),
    ])
    assert result["detected"] is True
    assert result["window_end"] == "2024-01-14"


def test_day_fifteen_is_outside_window():
    result = detect_structuring([
        txn("20240101", "A", 9000),
        txn("20240107", "B", 9000),
        txn("20240115", "C", 9000),
    ])
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_reports_earliest_firing_window():
    txns = [
        txn("20240101", "A", 9000),
        txn("20240102", "B", 9000),
        txn("20240103", "C", 9000),
        txn("20240301", "D", 9000),
        txn("20240302", "E", 9000),
        txn("20240303", "F", 9000),
    ]
    result = detect_structuring(txns)
    assert result["window_start"] == "2024-01-01"
    assert result["refs"] == ["A", "B", "C"]


def test_window_counts_every_qualifying_item_in_it():
    txns = [txn("20240101", n, 9000) for n in "ABCD"]
    result = detect_structuring(txns)
    assert result["occurrences"] == 4
    assert result["refs"] == ["A", "B", "C", "D"]


def test_refs_sorted_by_date_regardless_of_input_order():
    txns = [
        txn("20240110", "C", 9000),
        txn("20240101", "A", 9000),
        txn("20240105", "B", 9000),
    ]
    result = detect_structuring(txns)
    assert result["refs"] == ["A", "B", "C"]
    assert result["window_start"] == "2024-01-01"


def test_parameters_override_defaults():
    txns = [txn("20240101", "A", 500), txn("20240102", "B", 600)]
    result = detect_structuring(
        txns, lower_bound=400, upper_bound=700, occurrences=2, window_days=2
    )
    assert result["detected"] is True
    assert result["refs"] == ["A", "B"]


def test_not_detected_has_same_keys():
    assert detect_structuring([]) == {
        "detected": False,
        "occurrences": 0,
        "window_start": None,
        "window_end": None,
        "refs": [],
        "total": 0.0,
    }


def test_total_rounded_to_cents():
    txns = [
        txn("20240101", "A", 8000.10),
        txn("20240102", "B", 8000.20),
        txn("20240103", "C", 8000.30),
    ]
    assert detect_structuring(txns)["total"] == 24000.6
