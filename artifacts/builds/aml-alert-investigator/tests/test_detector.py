from detector import detect_structuring


def txn(date, ref, amount, direction="CREDIT"):
    return {"date": date, "ref": ref, "amount": amount, "direction": direction}


def test_fires_on_three_in_window():
    txns = [txn("20260101", "A", 9000.0), txn("20260108", "B", 9500.0), txn("20260114", "C", 8500.0)]
    assert detect_structuring(txns) == {
        "detected": True,
        "occurrences": 3,
        "window_start": "2026-01-01",
        "window_end": "2026-01-14",
        "refs": ["A", "B", "C"],
        "total": 27000.0,
    }


def test_window_dates_are_iso_not_the_input_format():
    txns = [txn("20181101", "A", 9000.0), txn("20181102", "B", 9000.0), txn("20181103", "C", 9000.0)]
    result = detect_structuring(txns)
    assert result["window_start"] == "2018-11-01"
    assert result["window_end"] == "2018-11-03"


def test_bounds_inclusive_at_lower_and_upper():
    txns = [txn("20260101", "A", 8000.00), txn("20260102", "B", 9999.99), txn("20260103", "C", 8500.0)]
    result = detect_structuring(txns)
    assert result["detected"] is True
    assert result["refs"] == ["A", "B", "C"]
    assert result["total"] == 26499.99


def test_amounts_outside_bounds_do_not_count():
    txns = [
        txn("20260101", "A", 7999.99),
        txn("20260102", "B", 10000.00),
        txn("20260103", "C", 9000.0),
        txn("20260104", "D", 9000.0),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_window_spans_fourteen_days_inclusive():
    txns = [txn("20260101", "A", 9000.0), txn("20260108", "B", 9000.0), txn("20260115", "C", 9000.0)]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_window_slides_to_densest_anchor():
    txns = [
        txn("20260101", "A", 9000.0),
        txn("20260108", "B", 9000.0),
        txn("20260115", "C", 9000.0),
        txn("20260116", "D", 9000.0),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is True
    assert result["window_start"] == "2026-01-08"
    assert result["window_end"] == "2026-01-16"
    assert result["refs"] == ["B", "C", "D"]


def test_debits_are_ignored():
    txns = [
        txn("20260101", "A", 9000.0, "CREDIT"),
        txn("20260102", "B", 9000.0, "DEBIT"),
        txn("20260103", "C", 9000.0, "CREDIT"),
        txn("20260104", "D", 9000.0, "DEBIT"),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_debits_do_not_pad_the_occurrence_count():
    txns = [
        txn("20260101", "A", 9000.0, "DEBIT"),
        txn("20260102", "B", 9000.0, "DEBIT"),
        txn("20260103", "C", 9000.0, "DEBIT"),
    ]
    result = detect_structuring(txns)
    assert result["detected"] is False
    assert result["occurrences"] == 0


def test_not_detected_keeps_shape_and_count():
    result = detect_structuring([txn("20260101", "A", 9000.0)])
    assert result == {
        "detected": False,
        "occurrences": 1,
        "window_start": None,
        "window_end": None,
        "refs": [],
        "total": 0.0,
    }


def test_empty_input_not_detected():
    result = detect_structuring([])
    assert result["detected"] is False
    assert result["occurrences"] == 0


def test_custom_parameters():
    txns = [txn("20260101", "A", 500.0), txn("20260102", "B", 600.0)]
    result = detect_structuring(txns, lower_bound=400.0, upper_bound=700.0, occurrences=2, window_days=2)
    assert result["detected"] is True
    assert result["refs"] == ["A", "B"]


def test_same_date_keeps_input_order():
    txns = [txn("20260101", "Z", 9000.0), txn("20260101", "A", 9000.0), txn("20260101", "M", 9000.0)]
    assert detect_structuring(txns)["refs"] == ["Z", "A", "M"]


def test_total_rounded_to_two_decimals():
    txns = [txn("20260101", "A", 8000.10), txn("20260102", "B", 8000.20), txn("20260103", "C", 8000.30)]
    assert detect_structuring(txns)["total"] == 24000.6
