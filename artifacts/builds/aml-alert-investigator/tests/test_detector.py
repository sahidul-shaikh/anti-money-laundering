import pytest

from detector import detect_structuring


def txn(date, ref, amount, direction="CREDIT"):
    return {"date": date, "ref": ref, "amount": amount, "direction": direction}


def test_three_in_band_credits_in_window_detected():
    txns = [
        txn("20260101", "A", 9000),
        txn("20260105", "B", 8500),
        txn("20260110", "C", 9500),
    ]
    result = detect_structuring(txns)
    assert result == {
        "detected": True,
        "occurrences": 3,
        "window_start": "2026-01-01",
        "window_end": "2026-01-10",
        "refs": ["A", "B", "C"],
        "total": 27000.0,
    }


def test_lower_bound_is_inclusive():
    txns = [txn("20260101", "A", 8000.00), txn("20260102", "B", 8000.00), txn("20260103", "C", 8000.00)]
    assert detect_structuring(txns)["detected"] is True


def test_upper_bound_is_inclusive():
    txns = [txn("20260101", "A", 9999.99), txn("20260102", "B", 9999.99), txn("20260103", "C", 9999.99)]
    assert detect_structuring(txns)["detected"] is True


def test_amount_just_below_lower_bound_excluded():
    txns = [txn("20260101", "A", 7999.99), txn("20260102", "B", 7999.99), txn("20260103", "C", 7999.99)]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["total"] == 0.0


def test_amount_above_upper_bound_excluded():
    txns = [txn("20260101", "A", 10000), txn("20260102", "B", 10000), txn("20260103", "C", 9000)]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 1
    assert result["total"] == 0.0


def test_debit_transactions_excluded():
    txns = [
        txn("20260101", "A", 9000, "DEBIT"),
        txn("20260102", "B", 9000, "DEBIT"),
        txn("20260103", "C", 9000, "DEBIT"),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 0
    assert result["total"] == 0.0


def test_window_of_14_days_spans_14_dates_inclusive():
    txns = [txn("20260101", "A", 9000), txn("20260102", "B", 9000), txn("20260114", "C", 9000)]
    assert detect_structuring(txns)["detected"] is True


def test_fifteen_day_span_is_outside_14_day_window():
    txns = [txn("20260101", "A", 9000), txn("20260102", "B", 9000), txn("20260115", "C", 9000)]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_window_end_is_last_qualifying_date_not_window_limit():
    txns = [txn("20260101", "A", 9000), txn("20260105", "B", 9000), txn("20260110", "C", 9000)]
    assert detect_structuring(txns)["window_end"] == "2026-01-10"


def test_window_dates_are_iso_format():
    txns = [txn("20181101", "A", 9000), txn("20181103", "B", 9000), txn("20181105", "C", 9000)]
    result = detect_structuring(txns)
    assert result["window_start"] == "2018-11-01"
    assert result["window_end"] == "2018-11-05"


def test_total_is_sum_of_window_amounts():
    txns = [txn("20260101", "A", 8000.10), txn("20260102", "B", 9000.20), txn("20260103", "C", 9999.99)]
    assert detect_structuring(txns)["total"] == pytest.approx(27000.29)


def test_refs_returned_in_date_order_for_unsorted_input():
    txns = [txn("20260110", "C", 9000), txn("20260101", "A", 9000), txn("20260105", "B", 9000)]
    assert detect_structuring(txns)["refs"] == ["A", "B", "C"]


def test_earliest_qualifying_window_is_reported():
    txns = [
        txn("20260101", "A", 9000),
        txn("20260201", "B", 9000),
        txn("20260202", "C", 9000),
        txn("20260203", "D", 9000),
        txn("20260204", "E", 9000),
    ]
    result = detect_structuring(txns)
    assert result["window_start"] == "2026-02-01"
    assert result["refs"] == ["B", "C", "D", "E"]
    assert result["occurrences"] == 4


def test_non_firing_result_has_same_keys_and_best_count():
    txns = [txn("20260101", "A", 9000), txn("20260102", "B", 9000), txn("20260301", "C", 9000)]
    result = detect_structuring(txns)
    assert result == {
        "detected": False,
        "occurrences": 2,
        "window_start": None,
        "window_end": None,
        "refs": [],
        "total": 0.0,
    }


def test_empty_input_not_detected():
    assert detect_structuring([]) == {
        "detected": False,
        "occurrences": 0,
        "window_start": None,
        "window_end": None,
        "refs": [],
        "total": 0.0,
    }


@pytest.mark.parametrize("occurrences, expected", [(2, True), (3, False)])
def test_occurrences_threshold_is_at_least(occurrences, expected):
    txns = [txn("20260101", "A", 9000), txn("20260102", "B", 9000)]
    assert detect_structuring(txns, occurrences=occurrences)["detected"] is expected
