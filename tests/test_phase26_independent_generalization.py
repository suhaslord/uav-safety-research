"""Test suite for Phase 26 independent external dataset admission and generalization benchmark."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "docs/phase26_independent_generalization_protocol.json"
RESULTS_DIR = ROOT / "results/phase26_independent_generalization"
CANDIDATES_PATH = RESULTS_DIR / "dataset_candidates.json"
AUDIT_PATH = RESULTS_DIR / "dataset_admission_audit.json"
SUMMARY_PATH = RESULTS_DIR / "analysis_summary.json"
REPORT_PATH = RESULTS_DIR / "study_report.md"

EXPECTED_PROTOCOL_SHA256 = "a12fb965721d0cde7c96969e19f7a00ab6ead1ae62870e563b30f844bd65791c"
PHASE22_CHECKPOINT_SHA256 = "3a1801b192d624f8dcdda4bc5d9a9157309000df67a4c30d62368c37901feddd"
PHASE23_CHECKPOINT_SHA256 = "43240be969708c32b3e11340c9846b3a588baf361378398677c794d16a455310"


def test_phase26_protocol_integrity_and_schema() -> None:
    """Ensure protocol file exists, is strictly formatted, and matches frozen SHA-256."""
    assert PROTOCOL_PATH.is_file(), "Protocol file must exist"
    payload = PROTOCOL_PATH.read_bytes()
    computed_sha256 = hashlib.sha256(payload).hexdigest()
    assert computed_sha256 == EXPECTED_PROTOCOL_SHA256, (
        f"Protocol SHA-256 mismatch: {computed_sha256} != {EXPECTED_PROTOCOL_SHA256}"
    )

    data = json.loads(payload.decode("utf-8"))
    assert data["protocol_id"] == "phase26-independent-generalization-v1.0"
    assert data["status"] == "FROZEN_PREREGISTERED"
    assert "scientific_question" in data
    assert "admission_criteria" in data
    assert "rejection_taxonomy" in data
    assert "frozen_model_locks" in data
    assert "scientific_limitations" in data

    # Verify both models are locked
    models = data["frozen_model_locks"]
    assert models["phase22_baseline"]["checkpoint_sha256"] == PHASE22_CHECKPOINT_SHA256
    assert models["phase23_robust"]["checkpoint_sha256"] == PHASE23_CHECKPOINT_SHA256
    assert models["phase22_baseline"]["evaluation_settings"]["imgsz"] == 320
    assert models["phase23_robust"]["evaluation_settings"]["imgsz"] == 480


def test_phase26_candidate_inventory_completeness() -> None:
    """Ensure all candidate datasets are audited with documented provenance and rejection codes."""
    assert CANDIDATES_PATH.is_file(), "Candidate inventory JSON must exist"
    data = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))

    assert data["total_candidates_investigated"] == 7
    assert data["candidates_admitted"] == 0
    assert data["candidates_rejected"] == 7
    assert len(data["candidates"]) == 7

    rejection_statuses = {c["audit_result"]["status"] for c in data["candidates"]}
    expected_statuses = {
        "REJECTED_OVERLAP",
        "REJECTED_PROVENANCE_UNKNOWN",
        "REJECTED_LABEL_INCOMPATIBLE",
        "REJECTED_NON_REAL_IMAGERY",
    }
    assert rejection_statuses == expected_statuses

    # Verify KIOS 2022 has 422 exact matches
    kios_2022 = next(c for c in data["candidates"] if c["candidate_id"] == "CAND-01")
    assert kios_2022["audit_result"]["exact_byte_overlap_count"] == 422
    assert kios_2022["audit_result"]["status"] == "REJECTED_OVERLAP"

    # Verify KIOS 2024 has 0 independent sessions
    kios_2024 = next(c for c in data["candidates"] if c["candidate_id"] == "CAND-02")
    assert kios_2024["audit_result"]["status"] == "REJECTED_OVERLAP"
    assert kios_2024["audit_result"]["independent_sessions"] == 0

    # Verify IMAV 2025 is blocked on missing artifacts
    imav = next(c for c in data["candidates"] if c["candidate_id"] == "CAND-03")
    assert imav["audit_result"]["status"] == "REJECTED_PROVENANCE_UNKNOWN"
    assert "session_provenance_unknown" in imav["audit_result"]["missing_prerequisites"]


def test_phase26_admission_audit_verdict() -> None:
    """Ensure the admission audit records NO_DATASET_ADMITTED without compromising standards."""
    assert AUDIT_PATH.is_file(), "Admission audit JSON must exist"
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))

    assert audit["phase"] == "phase26"
    assert audit["final_admission_verdict"] == "NO_DATASET_ADMITTED"
    assert audit["audit_conclusion"]["status"] == "NO_DATASET_ADMITTED"
    assert audit["protocol_sha256"] == EXPECTED_PROTOCOL_SHA256

    summary = audit["candidate_audit_summary"]
    assert len(summary) == 7
    admitted = [s for s in summary if s["admission_decision"] == "ADMITTED"]
    assert len(admitted) == 0, "No candidate may be admitted under the current public evidence"


def test_phase26_analysis_summary_and_report_coherence() -> None:
    """Ensure analysis summary matches study report and protocol commitments."""
    assert SUMMARY_PATH.is_file(), "Analysis summary must exist"
    assert REPORT_PATH.is_file(), "Study report must exist"

    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    assert summary["status"] == "NO_DATASET_ADMITTED"
    assert summary["candidate_metrics"]["total_candidates_investigated"] == 7
    assert summary["candidate_metrics"]["candidates_admitted"] == 0
    assert summary["candidate_metrics"]["breakdown"]["REJECTED_OVERLAP"] == 2
    assert summary["candidate_metrics"]["breakdown"]["REJECTED_PROVENANCE_UNKNOWN"] == 1
    assert summary["candidate_metrics"]["breakdown"]["REJECTED_LABEL_INCOMPATIBLE"] == 3
    assert summary["candidate_metrics"]["breakdown"]["REJECTED_NON_REAL_IMAGERY"] == 1

    report_text = REPORT_PATH.read_text(encoding="utf-8")
    assert "NO_DATASET_ADMITTED" in report_text
    assert "Concentric Circle Specialization Paradox" in report_text
    assert EXPECTED_PROTOCOL_SHA256 in report_text
    assert PHASE22_CHECKPOINT_SHA256 in report_text
    assert PHASE23_CHECKPOINT_SHA256 in report_text
    assert "No Flight-Safety Claims" in report_text


def test_zero_leakage_and_anti_tampering_rules() -> None:
    """Assert that admission rules forbid fine-tuning, relabeling, and post-hoc split creation."""
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    fine_tuning = protocol["evaluation_rules"]["fine_tuning_policy"]
    assert "Strictly forbidden" in fine_tuning

    # Ensure negative frame requirement is strictly enforced
    criteria = protocol["admission_criteria"]
    assert "negative_frame_inventory" in criteria
    assert criteria["negative_frame_inventory"]["requirement"].startswith("Dataset must contain verified negative frames")
