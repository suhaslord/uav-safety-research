import csv
import json
from collections import Counter
from types import SimpleNamespace
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from phase25_lib import (  # noqa: E402
    Box,
    box_from_yolo,
    calibration_summary,
    clustered_bootstrap_delta,
    iou_xyxy,
    load_input_lock,
    match_predictions,
    read_protected_manifest,
    sha256_file,
    validate_phase25_inputs,
)
from run_phase25_frame_audit import _validate_aggregates  # noqa: E402


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


def test_matching_rejects_non_finite_scores_and_out_of_frame_labels():
    with pytest.raises(ValueError, match="finite confidence"):
        match_predictions([Box(0, 0.1, 0.1, 0.9, 0.9)], [Box(0, 0.1, 0.1, 0.9, 0.9, float("nan"))])
    with pytest.raises(ValueError, match="outside the image"):
        box_from_yolo(0, 0.95, 0.5, 0.2, 0.2)


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
    lock["phase23_robust"]["checkpoint_source"] = "original local training directory"
    lock_path = tmp_path / "phase25_input_lock.json"
    lock_path.write_text(json.dumps(lock), encoding="utf-8")
    with pytest.raises(ValueError, match="Original detector inference software versions are not locked"):
        load_input_lock(lock_path)


def test_input_lock_rejects_checkpoint_hash_without_provenance(tmp_path):
    lock = json.loads((ROOT / "docs/phase25_input_lock.json").read_text(encoding="utf-8"))
    lock["phase23_robust"]["checkpoint_sha256"] = "a" * 64
    lock_path = tmp_path / "phase25_input_lock.json"
    lock_path.write_text(json.dumps(lock), encoding="utf-8")
    with pytest.raises(ValueError, match="checkpoint source is not documented"):
        load_input_lock(lock_path)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _synthetic_output(tmp_path):
    output = tmp_path / "phase25-output"
    output.mkdir()
    manifest = read_protected_manifest(ROOT / "results/phase25_failure_atlas/protected_test_manifest.csv")
    metrics = []
    boxes = []
    targets = []
    aggregates = []
    for model in ("baseline", "phase23"):
        for condition in ("clean", "blur", "low_light", "noise", "occlusion", "mixed"):
            aggregates.append({
                "model": model, "condition": condition,
                "precision": 0.5, "recall": 0.5, "map50": 0.5, "map50_95": 0.4,
            })
    for frame_index, frame in enumerate(manifest):
        span = 0.5 + (frame_index % 7) * 0.05
        lo, hi = 0.5 - span / 2, 0.5 + span / 2
        target_count = 2 if frame_index == 0 else 1
        for condition_index, condition in enumerate(("clean", "blur", "low_light", "noise", "occlusion", "mixed")):
            base_ok = (frame_index + condition_index) % 2 == 0
            phase23_ok = (frame_index + condition_index) % 3 != 0
            for model, success in (("baseline", base_ok), ("phase23", phase23_ok)):
                add_false_positive = model == "baseline" and frame_index == 0 and condition_index == 0
                metrics.append({
                    "frame_id": frame["image"], "sequence": frame["sequence"], "frame_index": frame["frame_index"],
                    "condition": condition, "model": model, "gt_count": target_count,
                    "detection_count": int(success) + int(add_false_positive), "tp": int(success), "fp": int(add_false_positive),
                    "fn": target_count - int(success), "frame_success": str(success and target_count == 1),
                    "best_confidence_any": 0.8 if success else (0.6 if add_false_positive else ""), "best_confidence_tp": 0.8 if success else "",
                    "best_iou": 1.0 if success else 0.0,
                    "source_target_area_ratio": span * span,
                    "source_target_center_x": 0.5, "source_target_center_y": 0.5,
                    "source_target_edge_distance": 0.5, "source_brightness_mean": 0.5,
                    "source_contrast_std": 0.2, "source_sharpness_gradient_energy": 0.03,
                    "view_brightness_mean": 0.45, "view_contrast_std": 0.18,
                    "view_sharpness_gradient_energy": 0.02,
                })
                if success:
                    boxes.append({
                        "frame_id": frame["image"], "sequence": frame["sequence"], "condition": condition,
                        "model": model, "prediction_index": 0, "class_id": 0,
                        "x0": lo, "y0": lo, "x1": hi, "y1": hi,
                        "confidence": 0.8, "matched_gt_index": 0, "match_iou": 1.0,
                        "is_true_positive": "True",
                    })
                if add_false_positive:
                    boxes.append({
                        "frame_id": frame["image"], "sequence": frame["sequence"], "condition": condition,
                        "model": model, "prediction_index": int(success), "class_id": 0,
                        "x0": 0.01, "y0": 0.01, "x1": 0.08, "y1": 0.08,
                        "confidence": 0.6, "matched_gt_index": "", "match_iou": 0.0,
                        "is_true_positive": "False",
                    })
                targets.append({
                    "frame_id": frame["image"], "sequence": frame["sequence"], "condition": condition,
                    "model": model, "target_index": 0, "class_id": 0,
                    "x0": lo, "y0": lo, "x1": hi, "y1": hi, "area_ratio": span * span,
                    "center_x": 0.5, "center_y": 0.5, "edge_distance": 0.5,
                    "detected": success, "matched_prediction_index": 0 if success else "",
                    "matched_confidence": 0.8 if success else "", "match_iou": 1.0 if success else "",
                })
                if target_count == 2:
                    targets.append({
                        "frame_id": frame["image"], "sequence": frame["sequence"], "condition": condition,
                        "model": model, "target_index": 1, "class_id": 0,
                        "x0": 0.8, "y0": 0.8, "x1": 0.95, "y1": 0.95,
                        "area_ratio": 0.15 * 0.15, "center_x": 0.875, "center_y": 0.875,
                        "edge_distance": 0.125, "detected": False,
                        "matched_prediction_index": "", "matched_confidence": "", "match_iou": "",
                    })
    _write_csv(output / "frame_condition_metrics.csv", metrics)
    _write_csv(output / "prediction_boxes.csv", boxes)
    _write_csv(output / "ground_truth_targets.csv", targets)
    _write_csv(output / "aggregate_validation.csv", aggregates)
    names = ("frame_condition_metrics.csv", "prediction_boxes.csv", "ground_truth_targets.csv", "aggregate_validation.csv")
    (output / "run_manifest.json").write_text(json.dumps({
        "phase": "phase25",
        "status": "predictions_generated",
        "aggregate_reproduction_passed": True,
        "model_training_performed": False,
        "confidence_threshold_tuned_on_test": False,
        "protected_manifest_sha256": "8605cf1cbf9e8769c0324bf066078f9964f232ac3128131c8bd0b689bb7b64b7",
        "frame_count": 86,
        "condition_count": 6,
        "frame_condition_views": 516,
        "model_frame_condition_rows": 1032,
        "output_tables_sha256": {name: sha256_file(output / name) for name in names},
    }), encoding="utf-8")
    return output


def test_analyzer_reconciles_synthetic_frame_outputs_and_writes_figures(tmp_path):
    output = _synthetic_output(tmp_path)

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
    assert summary["annotated_targets"] == 87
    assert summary["model_target_condition_rows"] == 87 * 6 * 2
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
    with (output / "failure_by_target_size.csv").open(newline="", encoding="utf-8") as handle:
        size_rows = list(csv.DictReader(handle))
    assert sum(int(row["source_targets"]) for row in size_rows) == 87
    assert sum(int(row["target_condition_cases_per_model"]) for row in size_rows) == 87 * 6


def test_analyzer_replays_matching_even_if_table_hashes_are_refreshed(tmp_path):
    output = _synthetic_output(tmp_path)
    frame_path = output / "frame_condition_metrics.csv"
    boxes_path = output / "prediction_boxes.csv"
    target_path = output / "ground_truth_targets.csv"
    with frame_path.open(newline="", encoding="utf-8") as handle:
        frames = list(csv.DictReader(handle))
    with boxes_path.open(newline="", encoding="utf-8") as handle:
        boxes = list(csv.DictReader(handle))
    with target_path.open(newline="", encoding="utf-8") as handle:
        targets = list(csv.DictReader(handle))
    frames[0]["best_iou"] = "0.75"
    boxes[0]["match_iou"] = "0.75"
    targets[0]["match_iou"] = "0.75"
    for path, rows in ((frame_path, frames), (boxes_path, boxes), (target_path, targets)):
        _write_csv(path, rows)
    manifest_path = output / "run_manifest.json"
    run_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for path in (frame_path, boxes_path, target_path):
        run_manifest["output_tables_sha256"][path.name] = sha256_file(path)
    manifest_path.write_text(json.dumps(run_manifest), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/analyze_phase25_failures.py"), "--results-dir", str(output)],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert "disagree with replayed box matching" in result.stderr
    assert not (output / "summary.json").exists()


@pytest.mark.parametrize(
    ("table", "field", "value", "message"),
    [
        ("aggregate_validation.csv", "precision", "nan", "Invalid aggregate validation metric"),
        ("frame_condition_metrics.csv", "source_brightness_mean", "nan", "Nonfinite image feature"),
        ("frame_condition_metrics.csv", "source_target_area_ratio", "0.01", "Image features differ across paired cases"),
    ],
)
def test_analyzer_rejects_corrupt_features_and_metrics_with_refreshed_hashes(tmp_path, table, field, value, message):
    output = _synthetic_output(tmp_path)
    path = output / table
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    rows[0][field] = value
    _write_csv(path, rows)
    manifest_path = output / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["output_tables_sha256"][table] = sha256_file(path)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/analyze_phase25_failures.py"), "--results-dir", str(output)],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert message in result.stderr
    assert not (output / "summary.json").exists()


@pytest.mark.parametrize("bad_source", ["observed_metric", "uncompared_metric", "reference_metric"])
def test_aggregate_reproduction_rejects_non_finite_metrics(tmp_path, bad_source):
    conditions = ("clean", "blur", "low_light", "noise", "occlusion", "mixed")
    box = SimpleNamespace(mp=0.8, mr=0.75, map50=0.7, map=0.6)
    if bad_source == "observed_metric":
        box.mr = float("nan")
    elif bad_source == "uncompared_metric":
        box.mp = float("nan")

    class FakeModel:
        def val(self, **kwargs):
            return SimpleNamespace(box=box)

    comparison = {
        condition: {"baseline_recall": 0.75, "baseline_map50": 0.7}
        for condition in conditions
    }
    phase23 = {
        condition: {"precision": 0.8, "recall": 0.75, "map50": 0.7, "map50_95": 0.6}
        for condition in conditions
    }
    if bad_source == "reference_metric":
        comparison["clean"]["baseline_recall"] = float("inf")

    with pytest.raises(
        RuntimeError,
        match=rf"non-finite or out-of-range metrics for baseline/clean: {'precision' if bad_source == 'uncompared_metric' else 'recall'}",
    ):
        _validate_aggregates(
            models={"baseline": FakeModel(), "phase23": FakeModel()},
            inference_settings={
                "baseline": {"imgsz": 320, "confidence_floor": 0.001, "nms_iou": 0.7, "max_det": 300, "batch": 1, "workers": 0, "device": "cpu"},
                "phase23": {"imgsz": 480, "confidence_floor": 0.001, "nms_iou": 0.7, "max_det": 300, "batch": 1, "workers": 0, "device": "cpu"},
            },
            metric_tolerance=0.001,
            args=SimpleNamespace(stress_root=tmp_path),
            reference={"comparison": comparison, "phase23": phase23},
            temp_root=tmp_path,
        )
