"""Proof-carrying public claims must not silently become stronger than evidence."""
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.audit_showcase_claims import EvidenceError, audit, load_snapshot


ROOT = Path(__file__).resolve().parents[1]


def test_current_archived_counts_and_external_admission_reconcile():
    record = load_snapshot(ROOT)
    phase25, phase26 = record["phase25"], record["phase26"]
    assert phase25["paired_image_views"] == 516
    assert (phase25["recovered"], phase25["regressed"],
            phase25["both_pass"], phase25["both_fail"]) == (49, 65, 223, 179)
    assert phase25["independent_new_holdout"] is False
    assert phase26["external_dataset_admitted"] is False
    assert phase26["known_KIOS_2022_byte_duplicates"] == 422
    assert phase26["independent_test_result_available"] is False


def _records():
    import json
    paired = json.loads((ROOT / "results/phase25_failure_atlas/paired_analysis_summary.json").read_text())
    admission = json.loads((ROOT / "docs/phase26_admission_report.json").read_text())
    return paired, admission


def test_fails_if_historical_counts_do_not_reconcile():
    paired, admission = _records()
    paired["counts"]["recovered"] += 1
    with pytest.raises(EvidenceError, match="do not reconcile"):
        audit(paired, admission)


def test_fails_if_claimed_success_rates_are_not_supported():
    paired, admission = _records()
    paired["rates"]["phase23_success_rate"] = 0.99
    with pytest.raises(EvidenceError, match="Contradictory"):
        audit(paired, admission)


def test_fails_if_dataset_admission_changes_without_updating_claims():
    paired, admission = _records()
    admission["candidates"][0]["admitted"] = True
    with pytest.raises(EvidenceError, match="admission changed"):
        audit(paired, admission)


def test_missing_admission_not_interpreted_as_no_dataset():
    paired, admission = _records()
    admission["candidates"] = []
    with pytest.raises(EvidenceError, match="Missing independent"):
        audit(paired, admission)


def test_boolean_counts_and_missing_admission_status_are_rejected():
    paired, admission = _records()
    paired["counts"]["recovered"] = True
    with pytest.raises(EvidenceError, match="integer counts"):
        audit(paired, admission)
    paired, admission = _records()
    del admission["candidates"][0]["admitted"]
    with pytest.raises(EvidenceError, match="explicit admission"):
        audit(paired, admission)
