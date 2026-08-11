from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_WORKFLOW = ROOT / ".github/workflows/phase8-px4-gazebo-evidence.yml"
FINAL_AUDIT_WORKFLOW = ROOT / ".github/workflows/phase8-final-audit.yml"
MISSION_SCRIPT = ROOT / "scripts/run_px4_gazebo_mission.py"


def test_px4_evidence_workflow_installs_requirements_in_active_python() -> None:
    text = EVIDENCE_WORKFLOW.read_text(encoding="utf-8")
    assert "python -m pip install -r /tmp/PX4-Autopilot/Tools/setup/requirements.txt" in text
    assert "import kconfiglib" in text
    assert "Startup script returned successfully" in text


def test_px4_evidence_ulog_discovery_is_run_scoped() -> None:
    text = EVIDENCE_WORKFLOW.read_text(encoding="utf-8")
    assert "build/px4_sitl_default/rootfs/log" in text
    assert "rootfs/fs/microsd/log" not in text
    assert "-newer /tmp/phase8-evidence/px4_run_started" in text
    assert "find /tmp/PX4-Autopilot -type f -name '*.ulg'" not in text
    assert "px4_ulog_source_path.txt" in text
    assert "mission.get('completed') is True" in text
    assert "takeoff_time" in text
    assert "groundtruth_duration_s" in text


def test_px4_evidence_preserves_frozen_research_boundaries() -> None:
    text = EVIDENCE_WORKFLOW.read_text(encoding="utf-8")
    assert "bd62e3b31431306fd9d897f560be7325d711d21a" in text
    assert "b4e9838555e935a5ec42690495315473629b58f6" in text
    assert "src/uav_safety/trace_validation.py" in text
    assert "scripts/run_phase8_trace_validation.py" in text
    assert "external_simulator_seen" in text
    assert "controller_tuning_allowed" in text
    assert "simulation_only" in text


def test_px4_evidence_provenance_identifies_simulator_and_actions_run() -> None:
    text = EVIDENCE_WORKFLOW.read_text(encoding="utf-8")
    assert "PX4_RELEASE: v1.17.0" in text
    assert "PX4_SIMULATOR_MODEL: gz_x500" in text
    assert "PX4_SIMULATOR_MODEL: gz_x500_vision" not in text
    assert 'test "$PX4_SIMULATOR_MODEL" = "gz_x500"' in text
    assert "GITHUB_RUN_ID" in text
    assert "GITHUB_RUN_ATTEMPT" in text
    assert "raw_ulog_sha256" in text
    assert "comparison_manifest_sha256" in text


def test_px4_mission_waits_for_local_position_and_armability() -> None:
    text = MISSION_SCRIPT.read_text(encoding="utf-8")
    assert "health.is_local_position_ok and health.is_armable" in text
    assert '"readiness_requirement": "local_position_ok_and_armable"' in text
    assert "PX4 local-position estimator/armability did not become ready" in text


def test_phase8_final_audit_runs_on_evidence_branch_and_checks_freeze() -> None:
    text = FINAL_AUDIT_WORKFLOW.read_text(encoding="utf-8")
    assert "phase8-px4-gazebo-evidence" in text
    assert "fetch-depth: 0" in text
    assert "Verify frozen Phase 8 and Phase 6B evidence boundaries" in text
    assert "git diff --exit-code \"$PHASE8_FROZEN\"" in text
