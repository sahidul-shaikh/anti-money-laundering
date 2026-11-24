"""Pytest tests for the AML-STR structuring detector."""

from detector import detect_structuring


def tx(date: str, ref: str, amount: float, direction: str = "CREDIT") -> dict:
    return {"date": date, "ref": ref, "amount": amount, "direction": direction}


def test_detects_three_in_window():
    txs = [
        tx("20260101", "A", 9000.00),
        tx("20260105", "B", 8500.00),
        tx("20260110", "C", 9500.00),
    ]
    result = detect_structuring(txs)
    assert result == {
        "detected": True,
        "occurrences": 3,
        "window_start": "2026-01-01",
        "window_end": "2026-01-10",
        "refs": ["A", "B", "C"],
        "total": 27000.00,
    }


def test_window_dates_are_iso_not_the_input_format():
    txs = [tx("20181101", "A", 9000.00), tx("20181102", "B", 9000.00), tx("20181103", "C", 9000.00)]
    result = detect_structuring(txs)
    assert result["window_start"] == "2018-11-01"
    assert result["window_end"] == "2018-11-03"


def test_lower_bound_is_inclusive():
    txs = [tx("20260101", "A", 8000.00), tx("20260102", "B", 8000.00), tx("20260103", "C", 8000.00)]
    assert detect_structuring(txs)["detected"] is True


def test_below_lower_bound_excluded():
    txs = [tx("20260101", "A", 7999.99), tx("20260102", "B", 8000.00), tx("20260103", "C", 8000.00)]
    result = detect_structuring(txs)
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_upper_bound_is_inclusive():
    txs = [tx("20260101", "A", 9999.99), tx("20260102", "B", 9999.99), tx("20260103", "C", 9999.99)]
    assert detect_structuring(txs)["detected"] is True


def test_above_upper_bound_excluded():
    txs = [tx("20260101", "A", 10000.00), tx("20260102", "B", 9000.00), tx("20260103", "C", 9000.00)]
    result = detect_structuring(txs)
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_debits_ignored():
    txs = [
        tx("20260101", "A", 9000.00),
        tx("20260102", "B", 9000.00, direction="DEBIT"),
        tx("20260103", "C", 9000.00),
    ]
    result = detect_structuring(txs)
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_window_spans_exactly_14_calendar_dates():
    # 20260101 to 20260114 is 14 calendar dates: inside the window.
    inside = [tx("20260101", "A", 9000.00), tx("20260107", "B", 9000.00), tx("20260114", "C", 9000.00)]
    assert detect_structuring(inside)["detected"] is True

    # 20260101 to 20260115 is 15 calendar dates: outside the window.
    outside = [tx("20260101", "A", 9000.00), tx("20260107", "B", 9000.00), tx("20260115", "C", 9000.00)]
    result = detect_structuring(outside)
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_best_window_reported_with_its_own_end_date():
    txs = [
        tx("20260101", "A", 9000.00),
        tx("20260201", "B", 9000.00),
        tx("20260202", "C", 9000.00),
        tx("20260205", "D", 9000.00),
        tx("20260210", "E", 9000.00),
    ]
    result = detect_structuring(txs)
    assert result["detected"] is True
    assert result["window_start"] == "2026-02-01"
    assert result["window_end"] == "2026-02-10"
    assert result["refs"] == ["B", "C", "D", "E"]
    assert result["occurrences"] == 4


def test_refs_chronological_regardless_of_input_order():
    txs = [tx("20260110", "C", 9000.00), tx("20260101", "A", 9000.00), tx("20260105", "B", 9000.00)]
    assert detect_structuring(txs)["refs"] == ["A", "B", "C"]


def test_same_day_ties_keep_input_order():
    txs = [tx("20260101", "Z", 9000.00), tx("20260101", "Y", 9000.00), tx("20260101", "X", 9000.00)]
    assert detect_structuring(txs)["refs"] == ["Z", "Y", "X"]


def test_custom_occurrences_threshold():
    txs = [tx("20260101", "A", 9000.00), tx("20260102", "B", 9000.00)]
    assert detect_structuring(txs, occurrences=2)["detected"] is True
    assert detect_structuring(txs, occurrences=3)["detected"] is False


def test_not_detected_has_same_keys_and_counts():
    result = detect_structuring([])
    assert set(result) == {"detected", "occurrences", "window_start", "window_end", "refs", "total"}
    assert result["detected"] is False
    assert result["occurrences"] == 0
    assert result["window_start"] is None
    assert result["window_end"] is None
    assert result["refs"] == []
    assert result["total"] == 0.0


def test_total_rounded_to_two_decimals():
    txs = [tx("20260101", "A", 8000.001), tx("20260102", "B", 8000.001), tx("20260103", "C", 8000.001)]
    assert detect_structuring(txs)["total"] == 24000.0
