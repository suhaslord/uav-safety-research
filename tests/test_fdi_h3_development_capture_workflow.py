"""H3 PX4 capture workflow must remain development-only and auditable."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / ".github/workflows/fdi-h3-px4-development-capture.yml"


def text():
    return CAPTURE.read_text(encoding="utf-8")


def test_capture_reuses_proven_px4_simulator_path_but_not_frozen_trials():
    body = text()
    assert "PX4_RELEASE: v1.17.0" in body
    assert "PX4_SIMULATOR_MODEL: gz_x500" in body
    assert "python scripts/run_px4_gazebo_mission.py" in body
    assert "scripts.fdi_h3_px4_ulog_preflight" in body
    assert "scripts.fdi_h3_px4_development_trace" in body
    assert "phase8-px4-gazebo-evidence" not in body


def test_capture_cannot_be_mistaken_for_h3_detector_accuracy():
    body = text()
    assert "DEVELOPMENT_ONLY" in body
    assert "can_claim_h3_results" in body
    assert "fault_injection_verified" in body
    assert "false" in body.lower()
    assert "actions/upload-artifact@v4" in body
    assert "retention-days: 14" in body
    assert "if: always()" in body


def test_capture_preserves_raw_ulog_and_pinned_source():
    body = text()
    assert "PX4-PX4_AUTOPILOT_SHA" in body
    assert "px4_gazebo_raw.ulg" in body
    assert "raw_ulog_sha256" in body
    assert "if-no-files-found: warn" in body
