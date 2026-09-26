import csv
import json
from collections import Counter
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from phase25_lib import (  # noqa: E402
    Box,
    calibration_summary,
    clustered_bootstrap_delta,
    iou_xyxy,
    load_input_lock,
    match_predictions,
    read_protected_manifest,
    validate_phase25_inputs,
)


def test_frozen_manifest_has_86_frames_and_two_source_sequences():
    rows = read_protected_manifest(ROOT / "results/phase25_failure_atlas/protected_test_manifest.csv")
    assert len(rows) == 86
    assert Counter(row["sequence"] for row in rows) == {"land_pad": 66, "land_pad2": 20}


def test_iou_and_confidence_ranked_one_to_one_matching():
    target = Box(0, 0.1, 0.1, 0.9, 0.9)
    duplicate_high = Box(0, 0.1, 0.1, 0.9, 0.9, 0.91)
    duplicate_low = Box(0, 0.12, 0.12, 0.88, 0.88, 0.72)
    wrong_class = Box(1, 0.1, 0.1, 0.9, 0.9, 0.99)

    assert iou_xyxy(target, duplicate_high) == 1.0
    matches = match_predictions([target], [duplicate_low, wrong_class, duplicate_high])
    assert [match.is_true_positive for match in matches] == [False, False, True]
    assert matches[2].ground_truth_index == 0
    assert matches[0].iou > 0.9


def test_calibration_keeps_confidence_one_in_the_last_fixed_bin():
    rows, summary = calibration_summary([
        {"confidence": 0.05, "is_true_positive": False},
        {"confidence": 0.95, "is_true_positive": True},
        {"confidence": 1.0, "is_true_positive": False},
    ])
    assert rows[0]["count"] == 1
    assert rows[-1]["count"] == 2
    assert summary["prediction_count"] == 3
    assert summary["brier_score"] is not None


def test_cluster_bootstrap_skips_two_sequences_and_is_seeded_with_enough_groups():
    two = [
        {"sequence": group, "baseline_success": False, "phase23_success": True}
        for group in ("a", "b")
    ]
    assert clustered_bootstrap_delta(two) is None
    ten = [
        {"sequence": str(index), "baseline_success": False, "phase23_success": index % 2 == 0}
        for index in range(10)
    ]
    assert clustered_bootstrap_delta(ten, replicates=100, seed=4) == clustered_bootstrap_delta(ten, replicates=100, seed=4)


def test_input_gate_stays_blocked_until_exact_checkpoint_and_software_are_locked(tmp_path):
    with pytest.raises(ValueError, match="Exact Phase 23 checkpoint is not locked"):
        validate_phase25_inputs(
            source_root=tmp_path / "missing-source",
            stress_root=tmp_path / "missing-stress",
            baseline_weights=tmp_path / "missing-baseline.pt",
            phase23_weights=tmp_path / "missing-phase23.pt",
            protected_manifest=ROOT / "results/phase25_failure_atlas/protected_test_manifest.csv",
        )


def test_input_lock_pins_recovered_baseline_and_marks_missing_phase23_source():
    lock = json.loads((ROOT / "docs/phase25_input_lock.json").read_text(encoding="utf-8"))
    assert lock["phase22_baseline"]["actions_artifact_id"] == 10382104202
    assert lock["phase23_robust"]["status"] == "blocked_pending_exact_checkpoint_recovery"
    assert lock["phase23_robust"]["checkpoint_sha256"] is None
    assert lock["phase25_runtime"]["status"] == "blocked_pending_original_version_recovery"
    with pytest.raises(ValueError, match="Exact Phase 23 checkpoint is not locked"):
        load_input_lock()


def test_input_lock_requires_runtime_versions_after_checkpoint_hash_is_recorded(tmp_path):
    lock = json.loads((ROOT / "docs/phase25_input_lock.json").read_text(encoding="utf-8"))
    lock["phase23_robust"]["checkpoint_sha256"] = "a" * 64
    lock_path = tmp_path / "phase25_input_lock.json"
    lock_path.write_text(json.dumps(lock), encoding="utf-8")
    with pytest.raises(ValueError, match="Original detector inference software versions are not locked"):
        load_input_lock(lock_path)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_analyzer_reconciles_synthetic_frame_outputs_and_writes_figures(tmp_path):
    output = tmp_path / "phase25-output"
    output.mkdir()
    manifest = read_protected_manifest(ROOT / "results/phase25_failure_atlas/protected_test_manifest.csv")
    (output / "run_manifest.json").write_text(json.dumps({
        "phase": "phase25",
        "status": "predictions_generated",
        "aggregate_reproduction_passed": True,
        "model_training_performed": False,
        "confidence_threshold_tuned_on_test": False,
        "protected_manifest_sha256": "8605cf1cbf9e8769c0324bf066078f9964f232ac3128131c8bd0b689bb7b64b7",
    }), encoding="utf-8")

    metrics = []
    boxes = []
    aggregates = []
    for model in ("baseline", "phase23"):
        for condition in ("clean", "blur", "low_light", "noise", "occlusion", "mixed"):
            aggregates.append({"model": model, "condition": condition, "map50": 0.5})
    for frame_index, frame in enumerate(manifest):
        for condition_index, condition in enumerate(("clean", "blur", "low_light", "noise", "occlusion", "mixed")):
            base_ok = (frame_index + condition_index) % 2 == 0
            phase23_ok = (frame_index + condition_index) % 3 != 0
            for model, success in (("baseline", base_ok), ("phase23", phase23_ok)):
                add_false_positive = model == "baseline" and frame_index == 0 and condition_index == 0
                metrics.append({
                    "frame_id": frame["image"], "sequence": frame["sequence"], "frame_index": frame["frame_index"],
                    "condition": condition, "model": model, "gt_count": 1,
                    "detection_count": int(success) + int(add_false_positive), "tp": int(success), "fp": int(add_false_positive),
                    "fn": int(not success), "frame_success": str(success),
                    "best_confidence_any": 0.8 if success else (0.6 if add_false_positive else ""), "best_confidence_tp": 0.8 if success else "",
                    "best_iou": 0.9 if success else 0.0,
                    "source_target_area_ratio": 0.05 + (frame_index % 7) * 0.01,
                    "source_target_center_x": 0.5, "source_target_center_y": 0.5,
                    "source_target_edge_distance": 0.2, "source_brightness_mean": 0.5,
                    "source_contrast_std": 0.2, "source_sharpness_gradient_energy": 0.03,
                    "view_brightness_mean": 0.45, "view_contrast_std": 0.18,
                    "view_sharpness_gradient_energy": 0.02,
                })
                if success:
                    boxes.append({
                        "frame_id": frame["image"], "sequence": frame["sequence"], "condition": condition,
                        "model": model, "prediction_index": 0, "class_id": 0,
                        "x0": 0.1, "y0": 0.1, "x1": 0.9, "y1": 0.9,
                        "confidence": 0.8, "matched_gt_index": 0, "match_iou": 0.9,
                        "is_true_positive": "True",
                    })
                if add_false_positive:
                    boxes.append({
                        "frame_id": frame["image"], "sequence": frame["sequence"], "condition": condition,
                        "model": model, "prediction_index": 0, "class_id": 0,
                        "x0": 0.01, "y0": 0.01, "x1": 0.08, "y1": 0.08,
                        "confidence": 0.6, "matched_gt_index": "", "match_iou": 0.0,
                        "is_true_positive": "False",
                    })
    _write_csv(output / "frame_condition_metrics.csv", metrics)
    _write_csv(output / "prediction_boxes.csv", boxes)
    _write_csv(output / "aggregate_validation.csv", aggregates)

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/analyze_phase25_failures.py"), "--results-dir", str(output)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Phase 25 report written" in result.stdout
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["frame_condition_views"] == 516
    assert summary["model_frame_condition_rows"] == 1032
    assert summary["paired_statistics"]["independent_sequence_group_count"] == 2
    assert summary["paired_statistics"]["inferential_intervals_reported"] is False
    assert summary["confidence_distribution"]["baseline"]["incorrect"]["count"] == 1
    with (output / "transition_counts.csv").open(newline="", encoding="utf-8") as handle:
        transition_rows = list(csv.DictReader(handle))
    for condition in ("clean", "blur", "low_light", "noise", "occlusion", "mixed"):
        assert sum(int(row["count"]) for row in transition_rows if row["condition"] == condition) == 86
    assert (output / "figures/failure_matrix.png").is_file()
    assert (output / "figures/confidence_reliability.png").is_file()
    assert (output / "confidence_distribution.csv").is_file()
