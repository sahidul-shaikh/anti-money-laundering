from detector import detect_structuring


def txn(date: str, ref: str, amount: float, direction: str = "CREDIT") -> dict:
    return {"date": date, "ref": ref, "amount": amount, "direction": direction}


EXPECTED_KEYS = {"detected", "occurrences", "window_start", "window_end", "refs", "total"}


def test_three_in_range_credits_fire():
    result = detect_structuring([
        txn("20260101", "A", 9000.0),
        txn("20260103", "B", 8500.0),
        txn("20260105", "C", 9500.0),
    ])
    assert result == {
        "detected": True,
        "occurrences": 3,
        "window_start": "2026-01-01",
        "window_end": "2026-01-05",
        "refs": ["A", "B", "C"],
        "total": 27000.0,
    }


def test_lower_bound_inclusive():
    result = detect_structuring([txn("20260101", f"R{i}", 8000.00) for i in range(3)])
    assert result["detected"] is True
    assert result["occurrences"] == 3


def test_upper_bound_inclusive():
    result = detect_structuring([txn("20260101", f"R{i}", 9999.99) for i in range(3)])
    assert result["detected"] is True


def test_exactly_10000_does_not_qualify():
    result = detect_structuring([txn("20260101", f"R{i}", 10000.00) for i in range(3)])
    assert result["detected"] is False
    assert result["occurrences"] == 0


def test_below_lower_bound_does_not_qualify():
    result = detect_structuring([txn("20260101", f"R{i}", 7999.99) for i in range(3)])
    assert result["detected"] is False
    assert result["occurrences"] == 0


def test_debits_are_ignored():
    result = detect_structuring([
        txn("20260101", "A", 9000.0, "DEBIT"),
        txn("20260102", "B", 9000.0, "DEBIT"),
        txn("20260103", "C", 9000.0, "CREDIT"),
    ])
    assert result["detected"] is False
    assert result["occurrences"] == 1
    assert result["refs"] == []


def test_window_spans_fourteen_days_inclusive():
    result = detect_structuring([
        txn("20260101", "A", 9000.0),
        txn("20260107", "B", 9000.0),
        txn("20260114", "C", 9000.0),
    ])
    assert result["detected"] is True
    assert result["window_start"] == "2026-01-01"
    assert result["window_end"] == "2026-01-14"


def test_day_fourteen_falls_outside_window():
    result = detect_structuring([
        txn("20260101", "A", 9000.0),
        txn("20260107", "B", 9000.0),
        txn("20260115", "C", 9000.0),
    ])
    assert result["detected"] is False
    assert result["occurrences"] == 2


def test_refs_returned_in_date_order():
    result = detect_structuring([
        txn("20260105", "C", 9000.0),
        txn("20260101", "A", 9000.0),
        txn("20260103", "B", 9000.0),
    ])
    assert result["refs"] == ["A", "B", "C"]


def test_occurrences_counts_whole_window_above_threshold():
    result = detect_structuring([txn(f"202601{d:02d}", f"R{d}", 9000.0) for d in range(1, 5)])
    assert result["detected"] is True
    assert result["occurrences"] == 4
    assert result["refs"] == ["R1", "R2", "R3", "R4"]


def test_total_rounded_to_two_dp():
    result = detect_structuring([
        txn("20260101", "A", 8000.10),
        txn("20260102", "B", 8000.20),
        txn("20260103", "C", 8000.30),
    ])
    assert result["total"] == 24000.6


def test_not_detected_shape_is_fixed():
    result = detect_structuring([txn("20260101", "A", 9000.0)])
    assert set(result) == EXPECTED_KEYS
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
    assert result == {
        "detected": False,
        "occurrences": 0,
        "window_start": None,
        "window_end": None,
        "refs": [],
        "total": 0.0,
    }


def test_custom_parameters_are_honoured():
    result = detect_structuring(
        [txn("20260101", "A", 500.0), txn("20260102", "B", 600.0)],
        lower_bound=400.0,
        upper_bound=700.0,
        occurrences=2,
        window_days=1,
    )
    assert result["detected"] is False
    assert result["occurrences"] == 1
