"""The oracle for the structuring detector.

Committed, fixed, and never shown to the model that writes the code. The build
stage generates src/detector.py from the PRD; this file decides whether it is
correct. If the two disagree, the code is wrong - not the test.

Every assertion here traces to a clause of PRD.md section 6 or 7.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

DEFAULT_PATH = (
    Path(__file__).resolve().parents[2]
    / "artifacts" / "builds" / "aml-alert-investigator" / "src" / "detector.py"
)


def load_detector():
    path = Path(os.environ.get("DETECTOR_PATH", DEFAULT_PATH))
    if not path.exists():
        pytest.fail(f"no detector at {path}: the development stage has not run")
    spec = importlib.util.spec_from_file_location("generated_detector", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "detect_structuring"):
        pytest.fail("detector.py does not define detect_structuring")
    return module.detect_structuring


detect = load_detector()


def txn(date: str, amount: float, ref: str = "", direction: str = "CREDIT") -> dict:
    return {
        "date": date,
        "ref": ref or f"R{date}{int(amount)}",
        "amount": amount,
        "direction": direction,
    }


# -- the rule fires -----------------------------------------------------


def test_three_qualifying_credits_in_window_detect():
    result = detect([
        txn("20181101", 9000.0, "A"),
        txn("20181105", 9100.0, "B"),
        txn("20181110", 9200.0, "C"),
    ])
    assert result["detected"] is True
    assert result["occurrences"] == 3
    assert result["refs"] == ["A", "B", "C"]
    assert result["total"] == pytest.approx(27300.0)


def test_refs_are_in_date_order_whatever_the_input_order():
    result = detect([
        txn("20181110", 9200.0, "C"),
        txn("20181101", 9000.0, "A"),
        txn("20181105", 9100.0, "B"),
    ])
    assert result["detected"] is True
    assert result["refs"] == ["A", "B", "C"]


def test_more_than_the_threshold_still_detects():
    result = detect([txn(f"201811{d:02d}", 9000.0, f"R{d}") for d in (1, 3, 5, 7, 9)])
    assert result["detected"] is True
    assert result["occurrences"] >= 3


def test_window_dates_are_iso_not_the_input_format():
    # Transactions arrive as YYYYMMDD from the monitoring extract. The case
    # management system this feeds takes ISO-8601, so the detector converts.
    result = detect([
        txn("20181101", 9000.0, "A"),
        txn("20181105", 9100.0, "B"),
        txn("20181110", 9200.0, "C"),
    ])
    assert result["window_start"] == "2018-11-01", (
        "window_start is ISO-8601. Only the two window dates in the result are "
        "reformatted: transactions still arrive as YYYYMMDD and everything "
        "else about reading them is unchanged."
    )
    assert result["window_end"] == "2018-11-10", "window_end is ISO-8601 too"


# -- the rule does not fire ---------------------------------------------


def test_two_qualifying_credits_do_not_reach_the_threshold():
    result = detect([txn("20181101", 9000.0, "A"), txn("20181105", 9500.0, "B")])
    assert result["detected"] is False
    assert result["occurrences"] == 2
    assert result["refs"] == []
    assert result["total"] == 0.0
    assert result["window_start"] is None
    assert result["window_end"] is None


def test_amounts_above_the_band_never_qualify():
    result = detect([txn(f"201811{d:02d}", 12000.0) for d in (1, 2, 3)])
    assert result["detected"] is False
    assert result["occurrences"] == 0


def test_amounts_below_the_band_never_qualify():
    result = detect([txn(f"201811{d:02d}", 500.0) for d in (1, 2, 3)])
    assert result["detected"] is False
    assert result["occurrences"] == 0


def test_an_empty_list_is_handled():
    result = detect([])
    assert result["detected"] is False
    assert result["occurrences"] == 0
    assert result["refs"] == []
    assert result["total"] == 0.0


# -- boundaries ---------------------------------------------------------


def test_lower_bound_is_inclusive():
    result = detect([txn(f"201811{d:02d}", 8000.0) for d in (1, 2, 3)])
    assert result["detected"] is True, "8,000.00 is inside the band"


def test_upper_bound_is_inclusive():
    result = detect([txn(f"201811{d:02d}", 9999.99) for d in (1, 2, 3)])
    assert result["detected"] is True, "9,999.99 is inside the band"


def test_ten_thousand_is_outside_the_band():
    result = detect([txn(f"201811{d:02d}", 10000.0) for d in (1, 2, 3)])
    assert result["detected"] is False, "10,000.00 belongs to AML-ECT, not AML-STR"
    assert result["occurrences"] == 0


# -- the window ---------------------------------------------------------


def test_window_includes_both_endpoints():
    # 1 Nov and 14 Nov are thirteen days apart: inside a 14-day window.
    result = detect([
        txn("20181101", 9000.0, "A"),
        txn("20181107", 9000.0, "B"),
        txn("20181114", 9000.0, "C"),
    ])
    assert result["detected"] is True
    assert result["refs"] == ["A", "B", "C"]


def test_transactions_spread_beyond_the_window_do_not_detect():
    result = detect([
        txn("20181101", 9000.0, "A"),
        txn("20181120", 9000.0, "B"),
        txn("20181210", 9000.0, "C"),
    ])
    assert result["detected"] is False


def test_a_qualifying_cluster_inside_a_longer_history_detects():
    spread = [txn("20180101", 9000.0, "OLD1"), txn("20180601", 9000.0, "OLD2")]
    cluster = [
        txn("20181101", 9000.0, "A"),
        txn("20181103", 9000.0, "B"),
        txn("20181105", 9000.0, "C"),
    ]
    result = detect(spread + cluster)
    assert result["detected"] is True
    assert set(result["refs"]) >= {"A", "B", "C"}


# -- direction ----------------------------------------------------------


def test_debits_are_ignored():
    result = detect([
        txn("20181101", 9000.0, "A", direction="DEBIT"),
        txn("20181103", 9000.0, "B", direction="DEBIT"),
        txn("20181105", 9000.0, "C", direction="DEBIT"),
    ])
    assert result["detected"] is False
    assert result["occurrences"] == 0


def test_debits_do_not_pad_the_occurrence_count():
    result = detect([
        txn("20181101", 9000.0, "A"),
        txn("20181102", 9000.0, "D1", direction="DEBIT"),
        txn("20181103", 9000.0, "B"),
    ])
    assert result["detected"] is False
    assert result["occurrences"] == 2
    assert "D1" not in result["refs"]


# -- parameters and shape -----------------------------------------------


def test_thresholds_are_overridable():
    txns = [txn("20181101", 5000.0, "A"), txn("20181103", 5000.0, "B")]
    assert detect(txns, lower_bound=4000, upper_bound=6000, occurrences=2)["detected"]


def test_window_is_overridable():
    txns = [
        txn("20181101", 9000.0, "A"),
        txn("20181102", 9000.0, "B"),
        txn("20181120", 9000.0, "C"),
    ]
    assert detect(txns, window_days=60)["detected"] is True


def test_output_has_exactly_the_contracted_keys():
    result = detect([txn("20181101", 9000.0)])
    assert set(result) == {
        "detected", "occurrences", "window_start", "window_end", "refs", "total",
    }


def test_total_is_rounded_to_two_places():
    result = detect([
        txn("20181101", 9000.555, "A"),
        txn("20181102", 9000.555, "B"),
        txn("20181103", 9000.555, "C"),
    ])
    assert result["total"] == round(result["total"], 2)
