from pathlib import Path
import json

import pytest

from scripts.verify_phase23_research_replay import authenticate_recovery, boolean, clean_stress_pairs, CONDITIONS, RECOVERY_COMMIT
from scripts.verify_phase26_admission_protocol import verify_lock, verify_screen

ROOT = Path(__file__).resolve().parents[1]


def population():
    frames = [{"image": "a.jpg", "sequence": "scene_a"}, {"image": "b.jpg", "sequence": "scene_b"}]
    rows = [{"frame_id": f["image"], "sequence": f["sequence"], "model": m, "condition": c,
             "frame_success": c == "clean", "tp": int(c == "clean"), "fp": 0, "fn": int(c != "clean")}
            for f in frames for m in ("baseline", "phase23") for c in CONDITIONS]
    return frames, rows


def test_clean_stress_pairs_are_within_each_model_not_cross_model():
    frames, rows = population()
    pairs = clean_stress_pairs(rows, frames)
    assert len(pairs) == 20
    assert {r["model"] for r in pairs} == {"baseline", "phase23"}
    assert all(r["outcome"] == "regressed" for r in pairs)
    assert all(r["condition"] != "clean" for r in pairs)


@pytest.mark.parametrize("damage", ["missing", "duplicate", "extra"])
def test_pair_population_is_complete_and_unique(damage):
    frames, rows = population()
    if damage == "missing": rows.pop()
    elif damage == "duplicate": rows.append(dict(rows[0]))
    else: rows.append(dict(rows[0], frame_id="unknown.jpg"))
    with pytest.raises(ValueError, match="Missing or duplicate"):
        clean_stress_pairs(rows, frames)


def test_missing_outcomes_cannot_become_success():
    for value in [None, "", "unknown", 1, 0]:
        with pytest.raises(ValueError): boolean(value)


def test_recovery_uses_only_exact_f090da03_research_files():
    assert RECOVERY_COMMIT == "f090da03d20b2425c5addccb4d19117c8991bcc1"
    evidence = authenticate_recovery()
    assert len(evidence) == 10
    assert not any(r["path"].startswith("deploy/") for r in evidence)


def test_recorded_replay_and_clean_stress_pairs_reconcile():
    record = json.loads((ROOT / "results/research_revalidation_2026_10_03/replay_receipt.json").read_text())
    assert record["comparison"] == "EXACT_MATCH" and record["maximum_absolute_delta"] == 0
    assert record["phase23_cells_checked"] == 24
    assert all(record["frozen_tables_byte_identical"].values())
    assert record["cross_model_transition_counts"] == {"recovered": 49, "regressed": 65, "both_pass": 223, "both_fail": 179}
    assert record["clean_stressed_pair_count"] == 860


def test_admission_lock_does_not_claim_independent_validation():
    report = verify_lock()
    assert report["status"] == "PASS"
    assert report["admission_status"] == "NO_DATASET_ADMITTED"
    assert report["test_inference_authorized"] is False


def test_screening_pass_alone_does_not_admit_a_dataset():
    lock = json.loads((ROOT / "docs/phase26_admission_execution_lock.json").read_text())
    screen = {"status": "screened_pending_provenance_ontology_rights_review", "reasons": [],
              "reference_archive_sha256": lock["screening"]["kios_reference_archive_sha256"],
              "reference_count": 422, "near_match_threshold_dhash": 9, "exact_overlaps": [], "near_match_flags": [],
              "candidate_count": 30, "dev_count": 15, "test_count": 15,
              "images": [{"session_id": "dev" if i < 15 else "test", "target_count": 0 if i == 0 else 1} for i in range(30)]}
    report = verify_screen(screen)
    assert report["status"] == "SCREENED_REQUIRES_DOCUMENTED_HUMAN_REVIEWS"
    assert report["admitted"] is False and report["test_inference_authorized"] is False
    screen["near_match_threshold_dhash"] = 8
    assert "duplicate_or_distance_gate_not_clear" in verify_screen(screen)["reasons"]


def test_release_manifest_rejects_changed_and_escaping_files(tmp_path):
    from scripts.validate_research_release import verify_manifest, VERSION, SCOPE
    manifest = {"schema": "aegisland.research-release-candidate.v1", "version": VERSION, "scope": SCOPE,
                "status": "FROZEN_RELEASE_CANDIDATE", "independent_dataset_admitted": False,
                "files_sha256": {"README.md": "0" * 64}}
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Frozen artifact changed"):
        verify_manifest(path)
    manifest["files_sha256"] = {"../outside.txt": "0" * 64}
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="escaped the repository"):
        verify_manifest(path)


def test_release_requires_a_clean_committed_tree(monkeypatch):
    from scripts import validate_research_release as release
    monkeypatch.setattr(release, "repository_state", lambda: {"head": "0" * 40, "dirty": True})
    with pytest.raises(ValueError, match="clean committed"):
        release.verify()


def test_release_does_not_ignore_baseline_verification_failure(monkeypatch):
    from scripts import validate_research_release as release
    monkeypatch.setattr(release, "verify_manifest", lambda: {})
    monkeypatch.setattr(release.reproduce_release, "verify", lambda: {"status": "committed_artifact_mismatch"})
    with pytest.raises(ValueError, match="Phase 25A hashes"):
        release.verify(allow_dirty=True)


def test_controlled_summary_preserves_failed_original_and_no_threshold_claim():
    analysis = json.loads((ROOT / "results/research_revalidation_2026_10_03/controlled_occlusion/analysis.json").read_text())
    assert analysis["recovery_source_commit"] == RECOVERY_COMMIT
    assert analysis["baseline_failures_before_added_occlusion"] == 33
    assert analysis["clean_successes"] == 53
    assert analysis["detector_inference_run"] is False
    assert analysis["object_classes"] == ["landing_pad"]
    assert "no threshold criterion was preregistered" in " ".join(analysis["limitations"]).lower()
