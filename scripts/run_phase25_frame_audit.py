#!/usr/bin/env python3
"""Run the frozen Phase 25 paired prediction audit after all gates pass."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

METHOD_PATHS = (
    "docs/phase25_protocol.md",
    "docs/phase25_reconstruction_lock.json",
    "scripts/phase25_lib.py",
    "scripts/phase25_reconstruction_lock.py",
    "scripts/audit_kios_reconstruction.py",
    "scripts/freeze_kios_reconstruction.py",
    "scripts/run_phase25_frame_audit.py",
    "scripts/analyze_phase25_failures.py",
    "scripts/build_real_image_stress_suite.py",
    "scripts/prepare_kios_real_yolo_split.py",
    "src/uav_safety/real_landing_dataset.py",
)
REPRODUCIBILITY_PATHS = METHOD_PATHS + (
    "docs/phase25_input_lock.json",
    "results/phase25_failure_atlas/protected_test_manifest.csv",
    "results/phase23_robust_detector/robustness_metrics.csv",
    "results/phase23_robust_detector/robustness_comparison.csv",
)

from phase25_lib import (  # noqa: E402
    CONDITIONS,
    Box,
    box_from_yolo,
    frame_metrics,
    image_features,
    sha256_file,
    validate_phase25_inputs,
)
from uav_safety.real_landing_dataset import read_yolo_boxes  # noqa: E402


def _read_csv(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    result = {row["condition"]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"Aggregate table contains duplicate conditions: {path}")
    return result


def _metric_values(metrics) -> dict[str, float]:
    return {
        "precision": float(metrics.box.mp),
        "recall": float(metrics.box.mr),
        "map50": float(metrics.box.map50),
        "map50_95": float(metrics.box.map),
    }


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write an empty table: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _normalized_predictions(result) -> list[Box]:
    if result.boxes is None or len(result.boxes) == 0:
        return []
    height, width = result.orig_shape
    if height <= 0 or width <= 0:
        raise ValueError(f"Invalid prediction image dimensions: {result.orig_shape}")
    xyxy = result.boxes.xyxy.cpu().numpy()
    classes = result.boxes.cls.cpu().numpy()
    confidence = result.boxes.conf.cpu().numpy()
    normalized = []
    for box, class_id, score in zip(xyxy, classes, confidence, strict=True):
        values = [float(value) for value in box]
        if (len(values) != 4 or any(not math.isfinite(value) for value in values)
                or not math.isfinite(float(class_id)) or not math.isfinite(float(score))):
            raise ValueError("Detector returned a non-finite or malformed prediction")
        if int(class_id) != class_id or int(class_id) < 0 or not 0.0 <= score <= 1.0:
            raise ValueError("Detector returned an invalid class or confidence")
        x0, y0, x1, y1 = (
            max(0.0, min(1.0, values[0] / width)),
            max(0.0, min(1.0, values[1] / height)),
            max(0.0, min(1.0, values[2] / width)),
            max(0.0, min(1.0, values[3] / height)),
        )
        if x1 <= x0 or y1 <= y0:
            raise ValueError("Detector returned a prediction with no area inside the image")
        normalized.append(Box(int(class_id), x0, y0, x1, y1, float(score)))
    return normalized


def _validate_aggregates(models, inference_settings, metric_tolerance, args, reference, temp_root):
    rows: list[dict[str, object]] = []
    expected_by_model = {
        "baseline": {
            condition: {
                "recall": float(row["baseline_recall"]),
                "map50": float(row["baseline_map50"]),
            }
            for condition, row in reference["comparison"].items()
        },
        "phase23": {
            condition: {
                "precision": float(row["precision"]),
                "recall": float(row["recall"]),
                "map50": float(row["map50"]),
                "map50_95": float(row["map50_95"]),
            }
            for condition, row in reference["phase23"].items()
        },
    }
    for model_name in ("baseline", "phase23"):
        model = models[model_name]
        settings = inference_settings[model_name]
        for condition in CONDITIONS:
            data_yaml = temp_root / f"{condition}.yaml"
            data_yaml.write_text(
                f"path: {(args.stress_root / condition).resolve()}\n"
                "train: images/test\nval: images/test\ntest: images/test\n"
                "names:\n  0: landing_pad\n",
                encoding="utf-8",
            )
            metrics = model.val(
                data=str(data_yaml),
                split="test",
                imgsz=settings["imgsz"],
                conf=settings["confidence_floor"],
                iou=settings["nms_iou"],
                max_det=settings["max_det"],
                batch=settings["batch"],
                workers=settings["workers"],
                device=settings["device"],
                plots=False,
                verbose=False,
                project=str(temp_root / "validation"),
                name=f"{model_name}-{condition}",
                exist_ok=True,
            )
            values = _metric_values(metrics)
            expected = expected_by_model[model_name][condition]
            non_finite = [metric for metric, value in values.items() if not math.isfinite(value) or not 0.0 <= value <= 1.0]
            non_finite.extend(metric for metric, value in expected.items() if not math.isfinite(value) or not 0.0 <= value <= 1.0)
            if non_finite:
                raise RuntimeError(
                    f"Aggregate reproduction produced non-finite or out-of-range metrics for "
                    f"{model_name}/{condition}: {', '.join(sorted(set(non_finite)))}"
                )
            mismatches = {
                metric: {"expected": expected_value, "actual": values[metric]}
                for metric, expected_value in expected.items()
                if abs(values[metric] - expected_value) > metric_tolerance
            }
            rows.append({"model": model_name, "condition": condition, **values})
            if mismatches:
                raise RuntimeError(
                    f"Aggregate reproduction failed for {model_name}/{condition}: "
                    f"{json.dumps(mismatches, sort_keys=True)}"
                )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--stress-root", type=Path, required=True)
    parser.add_argument("--baseline-weights", type=Path, required=True)
    parser.add_argument("--phase23-weights", type=Path, required=True)
    parser.add_argument("--protected-manifest", type=Path, default=ROOT / "results/phase25_failure_atlas/protected_test_manifest.csv")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "results/phase25_failure_atlas/output")
    args = parser.parse_args()

    if args.out_dir.exists() and any(args.out_dir.iterdir()):
        parser.error(f"Output directory is not empty; choose a new path: {args.out_dir}")

    try:
        inventory = validate_phase25_inputs(
            archive=args.archive,
            source_root=args.source_root,
            stress_root=args.stress_root,
            baseline_weights=args.baseline_weights,
            phase23_weights=args.phase23_weights,
            protected_manifest=args.protected_manifest,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"Phase 25 input gate: BLOCKED — {exc}", file=sys.stderr)
        return 2

    try:
        git_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *REPRODUCIBILITY_PATHS], cwd=ROOT, check=False)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"Phase 25 input gate: BLOCKED — cannot identify the committed method: {exc}", file=sys.stderr)
        return 2
    if dirty.returncode != 0:
        print("Phase 25 input gate: BLOCKED — commit all protocol, code, and reference changes before running", file=sys.stderr)
        return 2

    try:
        from ultralytics import YOLO
    except ImportError:
        print("Phase 25 input gate: BLOCKED — install the project's Ultralytics version first", file=sys.stderr)
        return 2

    input_lock = inventory["input_lock"]
    runtime_lock = input_lock["phase25_runtime"]
    observed_versions = {
        "python_version": platform.python_version(),
        "ultralytics_version": importlib.metadata.version("ultralytics"),
        "torch_version": importlib.metadata.version("torch"),
        "numpy_version": importlib.metadata.version("numpy"),
        "pillow_version": importlib.metadata.version("pillow"),
    }
    version_mismatches = {
        name: {"locked": runtime_lock[name], "observed": version}
        for name, version in observed_versions.items()
        if str(runtime_lock[name]) != version
    }
    if version_mismatches:
        print(f"Phase 25 input gate: BLOCKED — inference runtime version mismatch: {json.dumps(version_mismatches)}", file=sys.stderr)
        return 2

    models = {
        "baseline": YOLO(str(args.baseline_weights)),
        "phase23": YOLO(str(args.phase23_weights)),
    }
    inference_settings = input_lock["inference_settings"]
    reference_paths = {
        "phase23": ROOT / "results/phase23_robust_detector/robustness_metrics.csv",
        "comparison": ROOT / "results/phase23_robust_detector/robustness_comparison.csv",
    }
    phase23_reference = _read_csv(reference_paths["phase23"])
    comparison_reference = _read_csv(reference_paths["comparison"])
    if set(phase23_reference) != set(CONDITIONS) or set(comparison_reference) != set(CONDITIONS):
        raise ValueError("Committed Phase 23 aggregate tables do not contain the six frozen conditions")
    reference = {"phase23": phase23_reference, "comparison": comparison_reference}

    try:
        with tempfile.TemporaryDirectory(prefix="phase25-validation-") as temp_dir:
            temp_root = Path(temp_dir)
            aggregate_rows = _validate_aggregates(
                models,
                inference_settings,
                inference_settings["metric_tolerance"],
                args,
                reference,
                temp_root,
            )
    except RuntimeError as exc:
        print(f"Phase 25 reproduction gate: BLOCKED — {exc}", file=sys.stderr)
        return 3

    # No Phase 25 result file is created before all 12 aggregate checks pass.
    metric_rows: list[dict[str, object]] = []
    prediction_rows: list[dict[str, object]] = []
    target_rows: list[dict[str, object]] = []
    source_feature_cache: dict[str, dict[str, float | None]] = {}
    view_feature_cache: dict[tuple[str, str], dict[str, float | None]] = {}
    frame_by_name = {row["image"]: row for row in inventory["frames"]}
    source_image_dir = args.source_root / "images" / "test"
    for model_name in ("baseline", "phase23"):
        model = models[model_name]
        settings = inference_settings[model_name]
        for condition in CONDITIONS:
            paths = inventory["condition_paths"][condition]
            results = model.predict(
                source=[str(path) for path in paths],
                imgsz=settings["imgsz"],
                conf=settings["confidence_floor"],
                iou=settings["nms_iou"],
                max_det=settings["max_det"],
                batch=settings["batch"],
                device=settings["device"],
                verbose=False,
                stream=True,
            )
            for image_path, result in zip(paths, results, strict=True):
                if Path(result.path).name != image_path.name:
                    raise RuntimeError(f"Prediction order/name mismatch: {result.path} vs {image_path.name}")
                frame = frame_by_name[image_path.name]
                label_path = args.stress_root / condition / "labels" / "test" / frame["label"]
                labels = read_yolo_boxes(label_path, class_id=0)
                gt = [box_from_yolo(box.class_id, box.x_center, box.y_center, box.width, box.height) for box in labels]
                if not gt:
                    raise RuntimeError(f"No landing-pad target in {label_path}")
                predictions = _normalized_predictions(result)
                frame_values, box_rows = frame_metrics(gt, predictions, iou_threshold=0.5)
                matched = {int(row["matched_gt_index"]): row for row in box_rows if row["is_true_positive"]}
                for target_index, target in enumerate(gt):
                    match = matched.get(target_index)
                    center_x = (target.x0 + target.x1) / 2
                    center_y = (target.y0 + target.y1) / 2
                    target_rows.append({
                        "frame_id": frame["image"],
                        "sequence": frame["sequence"],
                        "condition": condition,
                        "model": model_name,
                        "target_index": target_index,
                        "class_id": target.class_id,
                        "x0": target.x0,
                        "y0": target.y0,
                        "x1": target.x1,
                        "y1": target.y1,
                        "area_ratio": (target.x1 - target.x0) * (target.y1 - target.y0),
                        "center_x": center_x,
                        "center_y": center_y,
                        "edge_distance": min(center_x, 1 - center_x, center_y, 1 - center_y),
                        "detected": match is not None,
                        "matched_prediction_index": match["prediction_index"] if match else None,
                        "matched_confidence": match["confidence"] if match else None,
                        "match_iou": match["match_iou"] if match else None,
                    })
                frame_id = frame["image"]
                if frame_id not in source_feature_cache:
                    source_feature_cache[frame_id] = image_features(source_image_dir / frame_id, gt)
                view_key = (condition, frame_id)
                if view_key not in view_feature_cache:
                    view_feature_cache[view_key] = image_features(image_path, gt)
                source_features = source_feature_cache[frame_id]
                view_features = view_feature_cache[view_key]
                metric_rows.append({
                    "frame_id": frame["image"],
                    "sequence": frame["sequence"],
                    "frame_index": int(frame["frame_index"]),
                    "condition": condition,
                    "model": model_name,
                    **frame_values,
                    **{f"source_{key}": value for key, value in source_features.items()},
                    **{f"view_{key}": value for key, value in view_features.items() if not key.startswith("target_")},
                })
                prediction_rows.extend({
                    "frame_id": frame["image"],
                    "sequence": frame["sequence"],
                    "condition": condition,
                    "model": model_name,
                    **box_row,
                } for box_row in box_rows)

    expected_metric_rows = len(inventory["frames"]) * len(CONDITIONS) * 2
    if len(metric_rows) != expected_metric_rows:
        raise RuntimeError(f"Expected {expected_metric_rows} frame/model rows, got {len(metric_rows)}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(args.out_dir / "aggregate_validation.csv", aggregate_rows)
    _write_csv(args.out_dir / "frame_condition_metrics.csv", metric_rows)
    _write_csv(args.out_dir / "ground_truth_targets.csv", target_rows)
    if prediction_rows:
        _write_csv(args.out_dir / "prediction_boxes.csv", prediction_rows)
    else:
        (args.out_dir / "prediction_boxes.csv").write_text(
            "frame_id,sequence,condition,model,prediction_index,class_id,x0,y0,x1,y1,confidence,matched_gt_index,match_iou,is_true_positive\n",
            encoding="utf-8",
        )
    table_names = ("aggregate_validation.csv", "frame_condition_metrics.csv", "prediction_boxes.csv", "ground_truth_targets.csv")
    manifest = {
        "phase": "phase25",
        "status": "predictions_generated",
        "analysis_type": "retrospective_descriptive_audit",
        "git_commit": git_commit,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "ultralytics_version": importlib.metadata.version("ultralytics"),
        "torch_version": importlib.metadata.version("torch"),
        "numpy_version": importlib.metadata.version("numpy"),
        "pillow_version": importlib.metadata.version("pillow"),
        "python_version": platform.python_version(),
        "frame_count": inventory["frame_count"],
        "condition_count": inventory["condition_count"],
        "frame_condition_views": inventory["frame_condition_count"],
        "model_frame_condition_rows": expected_metric_rows,
        "sequence_counts": inventory["sequence_counts"],
        "protected_manifest_sha256": inventory["manifest_sha256"],
        "input_lock_sha256": inventory["input_lock_sha256"],
        "reconstruction_lock_sha256": inventory["reconstruction_lock_sha256"],
        "source_archive_sha256": inventory["source_archive_sha256"],
        "condition_image_inventory_sha256": inventory["condition_image_inventory_sha256"],
        "input_lock": inventory["input_lock"],
        "baseline_weights_sha256": inventory["baseline_weights_sha256"],
        "phase23_weights_sha256": inventory["phase23_weights_sha256"],
        "baseline_actions_artifact_id": inventory["baseline_actions_artifact_id"],
        "baseline_actions_artifact_sha256": inventory["baseline_actions_artifact_sha256"],
        "stress_transform": {
            "generator": "scripts/build_real_image_stress_suite.py",
            "generator_sha256": sha256_file(ROOT / "scripts/build_real_image_stress_suite.py"),
            "seed": 20260915,
        },
        "aggregate_reference_sha256": {name: sha256_file(path) for name, path in reference_paths.items()},
        "method_files_sha256": {name: sha256_file(ROOT / name) for name in METHOD_PATHS},
        "output_tables_sha256": {name: sha256_file(args.out_dir / name) for name in table_names},
        "input_inventory": inventory["inventory"],
        "inference": inference_settings,
        "aggregate_reproduction_passed": True,
        "confidence_threshold_tuned_on_test": False,
        "model_training_performed": False,
    }
    (args.out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Phase 25 predictions written: {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
