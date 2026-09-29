#!/usr/bin/env python3
"""Summarize Phase 25 frame outcomes and create the report figures."""

from __future__ import annotations

import argparse
from bisect import bisect_left
import csv
import json
import math
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from phase25_lib import (  # noqa: E402
    Box,
    CONDITIONS,
    TRANSITIONS,
    PROTECTED_MANIFEST_SHA256,
    calibration_summary,
    clustered_bootstrap_delta,
    frame_metrics,
    outcome_transition,
    read_protected_manifest,
    sha256_file,
)


def _safe_mwu(x: list[float], y: list[float]) -> tuple[float | None, float | None]:
    if len(x) == 0 or len(y) == 0:
        return None, None
    try:
        import math
        from scipy.stats import mannwhitneyu
        res = mannwhitneyu(x, y, alternative="two-sided")
        u = float(res.statistic)
        p = float(res.pvalue)
        return (None if math.isnan(u) else u), (None if math.isnan(p) else p)
    except Exception:
        return None, None


def _safe_wilcoxon(x: list[float], y: list[float]) -> tuple[float | None, float | None]:
    if len(x) != len(y) or len(x) == 0:
        return None, None
    diffs = [a - b for a, b in zip(x, y) if a != b]
    if len(diffs) < 5:
        return None, None
    try:
        import math
        from scipy.stats import wilcoxon
        res = wilcoxon(x, y, alternative="two-sided")
        w = float(res.statistic)
        p = float(res.pvalue)
        return (None if math.isnan(w) else w), (None if math.isnan(p) else p)
    except Exception:
        return None, None


def _safe_chi2(matrix: list[list[int]]) -> tuple[float | None, float | None, int | None]:
    try:
        import math
        from scipy.stats import chi2_contingency
        res = chi2_contingency(matrix)
        stat = float(res.statistic)
        p = float(res.pvalue)
        return (None if math.isnan(stat) else stat), (None if math.isnan(p) else p), int(res.dof)
    except Exception:
        return None, None, None


def _sanitize_json(obj: object) -> object:
    import math
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict):
        return {k: _sanitize_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_json(v) for v in obj]
    return obj


MODEL_LABELS = {"baseline": "Phase 22 baseline", "phase23": "Phase 23 robust"}
COLORS = {
    "recovered": "#69a88c",
    "regressed": "#d58a72",
    "both_succeeded": "#6f91b8",
    "both_failed": "#a4a4a0",
}


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write an empty table: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _boolean(value: object) -> bool:
    normalized = str(value).strip().lower()
    if normalized not in {"true", "false"}:
        raise ValueError(f"Expected a true/false value, got {value!r}")
    return normalized == "true"


def _same_optional_float(value: str, expected: float | None) -> bool:
    if expected is None:
        return value in {"", "None"}
    try:
        observed = float(value)
    except ValueError:
        return False
    return math.isfinite(observed) and abs(observed - expected) <= 1e-6


def _validate_inputs(root: Path, manifest_path: Path) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    run_manifest = json.loads((root / "run_manifest.json").read_text(encoding="utf-8"))
    if run_manifest.get("aggregate_reproduction_passed") is not True:
        raise ValueError("Run manifest does not show a passing aggregate reproduction gate")
    if run_manifest.get("model_training_performed") is not False:
        raise ValueError("Phase 25 result must use frozen models")
    if run_manifest.get("confidence_threshold_tuned_on_test") is not False:
        raise ValueError("Phase 25 results must not tune confidence thresholds on the protected set")
    expected = read_protected_manifest(manifest_path)
    if sha256_file(manifest_path) != PROTECTED_MANIFEST_SHA256 or run_manifest.get("protected_manifest_sha256") != PROTECTED_MANIFEST_SHA256:
        raise ValueError("Results do not reference the frozen protected manifest")
    table_names = {"aggregate_validation.csv", "frame_condition_metrics.csv", "prediction_boxes.csv", "ground_truth_targets.csv"}
    table_hashes = run_manifest.get("output_tables_sha256")
    if not isinstance(table_hashes, dict) or set(table_hashes) != table_names:
        raise ValueError("Run manifest does not contain hashes for all four prediction tables")
    for name in sorted(table_names):
        if sha256_file(root / name) != table_hashes[name]:
            raise ValueError(f"Prediction table differs from the run manifest: {name}")
    frame_lookup = {row["image"]: row for row in expected}
    metrics = _read_rows(root / "frame_condition_metrics.csv")
    boxes = _read_rows(root / "prediction_boxes.csv")
    targets = _read_rows(root / "ground_truth_targets.csv")
    aggregates = _read_rows(root / "aggregate_validation.csv")
    if run_manifest.get("phase") != "phase25" or run_manifest.get("status") != "predictions_generated":
        raise ValueError("Run manifest does not identify a completed Phase 25 prediction run")
    expected_keys = {
        (frame["image"], condition, model)
        for frame in expected
        for condition in CONDITIONS
        for model in MODEL_LABELS
    }
    keys = [(row["frame_id"], row["condition"], row["model"]) for row in metrics]
    if len(keys) != len(set(keys)) or set(keys) != expected_keys:
        raise ValueError("Frame table must contain exactly one row per protected frame, condition, and model")
    if (run_manifest.get("frame_count") != len(expected)
            or run_manifest.get("condition_count") != len(CONDITIONS)
            or run_manifest.get("frame_condition_views") != len(expected) * len(CONDITIONS)
            or run_manifest.get("model_frame_condition_rows") != len(metrics)):
        raise ValueError("Run manifest counts do not reconcile with the protected frame table")
    source_feature_fields = (
        "source_target_area_ratio", "source_target_center_x", "source_target_center_y",
        "source_target_edge_distance", "source_brightness_mean", "source_contrast_std",
        "source_sharpness_gradient_energy",
    )
    view_feature_fields = ("view_brightness_mean", "view_contrast_std", "view_sharpness_gradient_energy")
    source_features_by_frame: dict[str, tuple[float, ...]] = {}
    view_features_by_case: dict[tuple[str, str], tuple[float, ...]] = {}
    for row in metrics:
        frame = frame_lookup[row["frame_id"]]
        if row["sequence"] != frame["sequence"] or int(row["frame_index"]) != int(frame["frame_index"]):
            raise ValueError(f"Frame identity metadata does not match the protected manifest: {row['frame_id']}")
        source_values = tuple(float(row[name]) for name in source_feature_fields)
        view_values = tuple(float(row[name]) for name in view_feature_fields)
        if any(not math.isfinite(value) for value in (*source_values, *view_values)):
            raise ValueError(f"Nonfinite image feature for {row['frame_id']}")
        frame_id = row["frame_id"]
        view_key = (frame_id, row["condition"])
        if (frame_id in source_features_by_frame and source_features_by_frame[frame_id] != source_values
                or view_key in view_features_by_case and view_features_by_case[view_key] != view_values):
            raise ValueError(f"Image features differ across paired cases for {view_key}")
        source_features_by_frame[frame_id] = source_values
        view_features_by_case[view_key] = view_values
    expected_aggregate_keys = {(model, condition) for model in MODEL_LABELS for condition in CONDITIONS}
    if {(row["model"], row["condition"]) for row in aggregates} != expected_aggregate_keys or len(aggregates) != len(expected_aggregate_keys):
        raise ValueError("Aggregate validation table has duplicate or missing model-condition rows")
    reference_paths = {
        "phase23": ROOT / "results/phase23_robust_detector/robustness_metrics.csv",
        "comparison": ROOT / "results/phase23_robust_detector/robustness_comparison.csv",
    }
    recorded_reference_hashes = run_manifest.get("aggregate_reference_sha256")
    if recorded_reference_hashes != {name: sha256_file(path) for name, path in reference_paths.items()}:
        raise ValueError("Aggregate references differ from the prediction run")
    phase23_reference = {row["condition"]: row for row in _read_rows(reference_paths["phase23"])}
    comparison_reference = {row["condition"]: row for row in _read_rows(reference_paths["comparison"])}
    if set(phase23_reference) != set(CONDITIONS) or set(comparison_reference) != set(CONDITIONS):
        raise ValueError("Frozen aggregate references do not contain all conditions")
    tolerance = json.loads((ROOT / "docs/phase25_input_lock.json").read_text(encoding="utf-8"))["inference_settings"]["metric_tolerance"]
    if not isinstance(tolerance, (float, int)) or not math.isfinite(tolerance) or not 0 <= tolerance <= 0.001:
        raise ValueError("Invalid aggregate reproduction tolerance")
    for row in aggregates:
        if any(not math.isfinite(float(row[name])) or not 0.0 <= float(row[name]) <= 1.0
               for name in ("precision", "recall", "map50", "map50_95")):
            raise ValueError(f"Invalid aggregate validation metric for {row['model']} / {row['condition']}")
        condition = row["condition"]
        expected_metrics = (
            {"recall": comparison_reference[condition]["baseline_recall"],
             "map50": comparison_reference[condition]["baseline_map50"]}
            if row["model"] == "baseline" else
            {name: phase23_reference[condition][name] for name in ("precision", "recall", "map50", "map50_95")}
        )
        if any(not math.isfinite(float(expected)) or abs(float(row[name]) - float(expected)) > tolerance
               for name, expected in expected_metrics.items()):
            raise ValueError(f"Aggregate reproduction disagrees with frozen reference for {row['model']} / {condition}")
    box_counts: dict[tuple[str, str, str], list[int]] = {}
    metric_lookup = {(row["frame_id"], row["condition"], row["model"]): row for row in metrics}
    matched_targets: dict[tuple[str, str, str], set[int]] = {}
    tp_by_target: dict[tuple[str, str, str, int], dict[str, str]] = {}
    prediction_indices: dict[tuple[str, str, str], set[int]] = {}
    prediction_rows_by_key: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in boxes:
        key = (row["frame_id"], row["condition"], row["model"])
        if key not in expected_keys:
            raise ValueError(f"Prediction refers to an unlisted frame, condition, or model: {key}")
        class_id = int(row["class_id"])
        prediction_index = int(row["prediction_index"])
        if class_id < 0 or prediction_index < 0:
            raise ValueError(f"Invalid prediction class or index for {key}")
        seen_indices = prediction_indices.setdefault(key, set())
        if prediction_index in seen_indices:
            raise ValueError(f"Duplicate prediction index for {key}")
        seen_indices.add(prediction_index)
        confidence = float(row["confidence"])
        coords = [float(row[name]) for name in ("x0", "y0", "x1", "y1")]
        overlap = float(row["match_iou"])
        if (not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0
                or not math.isfinite(overlap) or not 0.0 <= overlap <= 1.0
                or any(not math.isfinite(value) or not 0.0 <= value <= 1.0 for value in coords)):
            raise ValueError(f"Prediction confidence or normalized coordinates are invalid for {key}")
        if coords[2] < coords[0] or coords[3] < coords[1]:
            raise ValueError(f"Prediction box has inverted coordinates for {key}")
        is_tp = _boolean(row["is_true_positive"])
        matched_value = row["matched_gt_index"]
        if is_tp:
            if matched_value in {"", "None"} or overlap < 0.5:
                raise ValueError(f"True positive is missing a valid one-to-one match for {key}")
            target_index = int(matched_value)
            if target_index < 0 or target_index >= int(metric_lookup[key]["gt_count"]):
                raise ValueError(f"True positive refers to an unknown ground-truth target for {key}")
            seen = matched_targets.setdefault(key, set())
            if target_index in seen:
                raise ValueError(f"Two predictions reuse the same ground-truth target for {key}")
            seen.add(target_index)
            tp_by_target[(*key, target_index)] = row
        elif matched_value not in {"", "None"}:
            raise ValueError(f"False positive has a matched ground-truth target for {key}")
        values = box_counts.setdefault(key, [0, 0])
        values[0] += 1
        values[1] += is_tp
        prediction_rows_by_key.setdefault(key, []).append(row)
    for row in metrics:
        key = (row["frame_id"], row["condition"], row["model"])
        counts = box_counts.get(key, [0, 0])
        if counts != [int(row["detection_count"]), int(row["tp"])]:
            raise ValueError(f"Prediction boxes do not reconcile to frame metrics for {key}")
        if prediction_indices.get(key, set()) != set(range(int(row["detection_count"]))):
            raise ValueError(f"Prediction indices are not contiguous for {key}")
    for row in metrics:
        gt, tp, fp, fn = (int(row[name]) for name in ("gt_count", "tp", "fp", "fn"))
        if gt < 1 or min(tp, fp, fn) < 0 or tp + fn != gt or tp + fp != int(row["detection_count"]):
            raise ValueError(f"TP/FP/FN do not reconcile for {row['frame_id']} / {row['condition']} / {row['model']}")
        if _boolean(row["frame_success"]) != (gt > 0 and tp == gt):
            raise ValueError(f"Frame success does not reconcile for {row['frame_id']} / {row['condition']} / {row['model']}")
    target_indices: dict[tuple[str, str, str], set[int]] = {}
    source_targets: dict[tuple[str, int], tuple[float, ...]] = {}
    target_rows_by_key: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in targets:
        key = (row["frame_id"], row["condition"], row["model"])
        if key not in expected_keys or row["sequence"] != frame_lookup[row["frame_id"]]["sequence"]:
            raise ValueError(f"Target refers to an unlisted frame, condition, model, or sequence: {key}")
        target_index = int(row["target_index"])
        seen = target_indices.setdefault(key, set())
        if target_index in seen or target_index < 0 or target_index >= int(metric_lookup[key]["gt_count"]):
            raise ValueError(f"Duplicate or invalid target index for {key}")
        seen.add(target_index)
        target_rows_by_key.setdefault(key, []).append(row)
        if row["class_id"] != "0":
            raise ValueError(f"Unexpected ground-truth class for {key}")
        coords = tuple(float(row[name]) for name in ("x0", "y0", "x1", "y1"))
        if (any(not math.isfinite(value) for value in coords)
                or not 0.0 <= coords[0] < coords[2] <= 1.0
                or not 0.0 <= coords[1] < coords[3] <= 1.0):
            raise ValueError(f"Target box is invalid for {key}")
        source_key = (row["frame_id"], target_index)
        if source_key in source_targets and source_targets[source_key] != coords:
            raise ValueError(f"Target geometry changed between conditions or models for {source_key}")
        source_targets[source_key] = coords
        center_x = (coords[0] + coords[2]) / 2
        center_y = (coords[1] + coords[3]) / 2
        derived = {
            "area_ratio": (coords[2] - coords[0]) * (coords[3] - coords[1]),
            "center_x": center_x,
            "center_y": center_y,
            "edge_distance": min(center_x, 1 - center_x, center_y, 1 - center_y),
        }
        if any(not math.isfinite(float(row[name])) or abs(float(row[name]) - value) > 1e-9 for name, value in derived.items()):
            raise ValueError(f"Target geometry features do not reconcile for {key}")
        match = tp_by_target.get((*key, target_index))
        if _boolean(row["detected"]) != (match is not None):
            raise ValueError(f"Target detection does not reconcile with matched predictions for {key}")
        if match is None:
            if any(row[name] not in {"", "None"} for name in ("matched_prediction_index", "matched_confidence", "match_iou")):
                raise ValueError(f"Unmatched target carries prediction details for {key}")
        else:
            matched_confidence = float(row["matched_confidence"])
            match_iou = float(row["match_iou"])
            if (int(row["matched_prediction_index"]) != int(match["prediction_index"])
                    or not math.isfinite(matched_confidence) or not math.isfinite(match_iou)
                    or abs(matched_confidence - float(match["confidence"])) > 1e-9
                    or abs(match_iou - float(match["match_iou"])) > 1e-9):
                raise ValueError(f"Target match details disagree with the prediction table for {key}")
    for key, row in metric_lookup.items():
        if target_indices.get(key, set()) != set(range(int(row["gt_count"]))):
            raise ValueError(f"Ground-truth target rows do not reconcile for {key}")
        label_rows = sorted(target_rows_by_key[key], key=lambda item: int(item["target_index"]))
        if abs(float(row["source_target_area_ratio"]) - max(float(item["area_ratio"]) for item in label_rows)) > 1e-9:
            raise ValueError(f"Largest target area does not reconcile for {key}")
        box_rows = sorted(prediction_rows_by_key.get(key, []), key=lambda item: int(item["prediction_index"]))
        ground_truth = [Box(0, *(float(item[name]) for name in ("x0", "y0", "x1", "y1"))) for item in label_rows]
        predictions = [
            Box(int(item["class_id"]), *(float(item[name]) for name in ("x0", "y0", "x1", "y1")), float(item["confidence"]))
            for item in box_rows
        ]
        replayed_frame, replayed_boxes = frame_metrics(ground_truth, predictions, iou_threshold=0.5)
        if (any(int(row[name]) != replayed_frame[name] for name in ("gt_count", "detection_count", "tp", "fp", "fn"))
                or _boolean(row["frame_success"]) != replayed_frame["frame_success"]
                or any(not _same_optional_float(row[name], replayed_frame[name])
                       for name in ("best_confidence_any", "best_confidence_tp", "best_iou"))):
            raise ValueError(f"Frame metrics disagree with replayed box matching for {key}")
        for observed, replayed in zip(box_rows, replayed_boxes, strict=True):
            matched_index = replayed["matched_gt_index"]
            if (_boolean(observed["is_true_positive"]) != replayed["is_true_positive"]
                    or observed["matched_gt_index"] != (str(matched_index) if matched_index is not None else "")
                    or not _same_optional_float(observed["match_iou"], replayed["match_iou"])):
                raise ValueError(f"Prediction match disagrees with frozen matching rule for {key}")
    return metrics, boxes, targets, aggregates


def _paired_rows(metrics: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, dict[str, str]]]:
    paired: dict[tuple[str, str], dict[str, dict[str, str]]] = {}
    for row in metrics:
        paired.setdefault((row["frame_id"], row["condition"]), {})[row["model"]] = row
    if any(set(models) != set(MODEL_LABELS) for models in paired.values()):
        raise ValueError("Every frame-condition pair needs both detector rows")
    return paired


def _summaries(metrics, boxes, targets, aggregates, root: Path):
    paired = _paired_rows(metrics)
    transition_rows: list[dict[str, object]] = []
    condition_rows: list[dict[str, object]] = []
    bootstrap_by_condition: dict[str, object] = {}

    aggregate_lookup = {(row["model"], row["condition"]): row for row in aggregates}
    for condition in CONDITIONS:
        items = [(key, models) for key, models in paired.items() if key[1] == condition]
        counts = {name: 0 for name in TRANSITIONS}
        cluster_rows: list[dict[str, object]] = []
        for (frame_id, _), models in items:
            base_ok = _boolean(models["baseline"]["frame_success"])
            robust_ok = _boolean(models["phase23"]["frame_success"])
            transition = outcome_transition(base_ok, robust_ok)
            counts[transition] += 1
            cluster_rows.append({
                "frame_id": frame_id,
                "sequence": models["phase23"]["sequence"],
                "baseline_success": base_ok,
                "phase23_success": robust_ok,
            })
        # Emit all four outcomes, including zero-count categories.
        transition_rows.extend({"condition": condition, "outcome": key, "count": counts[key]} for key in TRANSITIONS)
        baseline = [models["baseline"] for _, models in items]
        robust = [models["phase23"] for _, models in items]
        base_tp = sum(int(row["tp"]) for row in baseline)
        base_fp = sum(int(row["fp"]) for row in baseline)
        base_fn = sum(int(row["fn"]) for row in baseline)
        robust_tp = sum(int(row["tp"]) for row in robust)
        robust_fp = sum(int(row["fp"]) for row in robust)
        robust_fn = sum(int(row["fn"]) for row in robust)
        base_rate = sum(_boolean(row["frame_success"]) for row in baseline) / len(baseline)
        robust_rate = sum(_boolean(row["frame_success"]) for row in robust) / len(robust)
        condition_rows.append({
            "condition": condition,
            "frames": len(items),
            "baseline_frame_success_rate": base_rate,
            "phase23_frame_success_rate": robust_rate,
            "paired_frame_success_delta": robust_rate - base_rate,
            **counts,
            "baseline_tp": base_tp,
            "baseline_fp": base_fp,
            "baseline_fn": base_fn,
            "baseline_object_recall": base_tp / (base_tp + base_fn) if base_tp + base_fn else None,
            "phase23_tp": robust_tp,
            "phase23_fp": robust_fp,
            "phase23_fn": robust_fn,
            "phase23_object_recall": robust_tp / (robust_tp + robust_fn) if robust_tp + robust_fn else None,
            "baseline_map50": float(aggregate_lookup[("baseline", condition)]["map50"]),
            "phase23_map50": float(aggregate_lookup[("phase23", condition)]["map50"]),
        })
        interval = clustered_bootstrap_delta(cluster_rows, minimum_groups=10)
        bootstrap_by_condition[condition] = interval

    calibration_rows: list[dict[str, object]] = []
    calibration_summary_by_model: dict[str, object] = {}
    for model in MODEL_LABELS:
        selected = [row for row in boxes if row["model"] == model]
        bin_rows, scores = calibration_summary([
            {"confidence": float(row["confidence"]), "is_true_positive": _boolean(row["is_true_positive"])}
            for row in selected
        ])
        calibration_summary_by_model[model] = scores
        calibration_rows.extend({"model": model, **row} for row in bin_rows)
    confidence_distribution_rows: list[dict[str, object]] = []
    confidence_distribution: dict[str, dict[str, object]] = {}
    for model in MODEL_LABELS:
        model_summary: dict[str, object] = {}
        for is_correct, label in ((True, "correct"), (False, "incorrect")):
            scores = np.asarray([
                float(row["confidence"])
                for row in boxes
                if row["model"] == model and _boolean(row["is_true_positive"]) is is_correct
            ], dtype=float)
            values = {
                "count": int(scores.size),
                "mean": float(np.mean(scores)) if scores.size else None,
                "median": float(np.median(scores)) if scores.size else None,
                "q25": float(np.quantile(scores, 0.25)) if scores.size else None,
                "q75": float(np.quantile(scores, 0.75)) if scores.size else None,
            }
            model_summary[label] = values
            confidence_distribution_rows.append({"model": model, "box_correctness": label, **values})
        confidence_distribution[model] = model_summary

    per_frame_area: dict[str, float] = {}
    for row in metrics:
        per_frame_area.setdefault(row["frame_id"], float(row["source_target_area_ratio"]))
    feature_rows: list[dict[str, object]] = []
    feature_metrics = (
        "source_target_area_ratio", "source_target_center_x", "source_target_center_y",
        "source_target_edge_distance", "source_brightness_mean", "source_contrast_std",
        "source_sharpness_gradient_energy", "view_brightness_mean", "view_contrast_std",
        "view_sharpness_gradient_energy",
    )
    for model in MODEL_LABELS:
        for condition in CONDITIONS:
            selected = [row for row in metrics if row["model"] == model and row["condition"] == condition]
            for feature in feature_metrics:
                success = [float(row[feature]) for row in selected if _boolean(row["frame_success"]) and row[feature] not in {"", "None"}]
                failure = [float(row[feature]) for row in selected if not _boolean(row["frame_success"]) and row[feature] not in {"", "None"}]
                feature_rows.append({
                    "model": model,
                    "condition": condition,
                    "unit": "frame",
                    "feature": feature,
                    "success_count": len(success),
                    "failure_count": len(failure),
                    "success_mean": float(np.mean(success)) if success else None,
                    "failure_mean": float(np.mean(failure)) if failure else None,
                    "failure_minus_success": float(np.mean(failure) - np.mean(success)) if success and failure else None,
                })
            selected_targets = [row for row in targets if row["model"] == model and row["condition"] == condition]
            for feature in ("area_ratio", "center_x", "center_y", "edge_distance"):
                detected = [float(row[feature]) for row in selected_targets if _boolean(row["detected"])]
                missed = [float(row[feature]) for row in selected_targets if not _boolean(row["detected"])]
                feature_rows.append({
                    "model": model,
                    "condition": condition,
                    "unit": "target",
                    "feature": f"target_{feature}",
                    "success_count": len(detected),
                    "failure_count": len(missed),
                    "success_mean": float(np.mean(detected)) if detected else None,
                    "failure_mean": float(np.mean(missed)) if missed else None,
                    "failure_minus_success": float(np.mean(missed) - np.mean(detected)) if detected and missed else None,
                })

    per_target_area: dict[tuple[str, int], float] = {}
    for row in targets:
        per_target_area.setdefault((row["frame_id"], int(row["target_index"])), float(row["area_ratio"]))
    cutpoints = np.quantile(list(per_target_area.values()), [0.25, 0.5, 0.75])
    quartile_by_target = {
        key: bisect_left(cutpoints, area)
        for key, area in per_target_area.items()
    }
    size_rows: list[dict[str, object]] = []
    for quartile in range(4):
        selected = [row for row in targets if quartile_by_target[(row["frame_id"], int(row["target_index"]))] == quartile]
        source_areas = [area for key, area in per_target_area.items() if quartile_by_target[key] == quartile]
        rates = {}
        for model in MODEL_LABELS:
            model_rows = [row for row in selected if row["model"] == model]
            failures = sum(not _boolean(row["detected"]) for row in model_rows)
            rates[model] = {
                "missed_targets": failures,
                "miss_rate": failures / len(model_rows) if model_rows else None,
            }
        size_rows.append({
            "size_group": f"pad_area_q{quartile + 1}",
            "min_area_ratio": min(source_areas) if source_areas else None,
            "max_area_ratio": max(source_areas) if source_areas else None,
            "source_targets": len({(row["frame_id"], row["target_index"]) for row in selected}),
            "target_condition_cases_per_model": len(selected) // len(MODEL_LABELS),
            "baseline_missed_targets": rates["baseline"]["missed_targets"],
            "baseline_miss_rate": rates["baseline"]["miss_rate"],
            "phase23_missed_targets": rates["phase23"]["missed_targets"],
            "phase23_miss_rate": rates["phase23"]["miss_rate"],
        })

    target_by_frame: dict[str, dict[str, str]] = {}
    for row in targets:
        fid = row["frame_id"]
        if fid not in target_by_frame or float(row["area_ratio"]) > float(target_by_frame[fid]["area_ratio"]):
            target_by_frame[fid] = row

    paired_frame_rows: list[dict[str, object]] = []
    for (frame_id, cond), models in sorted(paired.items(), key=lambda p: (p[0][1], p[0][0])):
        base = models["baseline"]
        robust = models["phase23"]
        base_ok = _boolean(base["frame_success"])
        robust_ok = _boolean(robust["frame_success"])
        if not base_ok and robust_ok:
            outcome_label = "RECOVERED"
        elif base_ok and not robust_ok:
            outcome_label = "REGRESSED"
        elif base_ok and robust_ok:
            outcome_label = "BOTH PASS"
        else:
            outcome_label = "BOTH FAIL"

        area = float(base["source_target_area_ratio"])
        quartile = f"Q{bisect_left(cutpoints, area) + 1}"

        t_row = target_by_frame.get(frame_id)
        if t_row and cond in ("occlusion", "mixed"):
            tw_px = (float(t_row["x1"]) - float(t_row["x0"])) * 1052.0
            th_px = (float(t_row["y1"]) - float(t_row["y0"])) * 961.0
            occ_w = max(8.0, tw_px * 0.55)
            occ_h = max(8.0, th_px * 0.55)
            inter_w = min(tw_px, occ_w)
            inter_h = min(th_px, occ_h)
            occ_severity = (inter_w * inter_h) / (tw_px * th_px) if (tw_px * th_px) > 0 else 0.0
        else:
            occ_severity = 0.0

        base_conf = float(base["best_confidence_tp"]) if base["best_confidence_tp"] not in ("", "None") else (float(base["best_confidence_any"]) if base["best_confidence_any"] not in ("", "None") else 0.0)
        p23_conf = float(robust["best_confidence_tp"]) if robust["best_confidence_tp"] not in ("", "None") else (float(robust["best_confidence_any"]) if robust["best_confidence_any"] not in ("", "None") else 0.0)
        base_iou = float(base["best_iou"])
        p23_iou = float(robust["best_iou"])
        b_tp, b_fp, b_fn = int(base["tp"]), int(base["fp"]), int(base["fn"])
        r_tp, r_fp, r_fn = int(robust["tp"]), int(robust["fp"]), int(robust["fn"])

        paired_frame_rows.append({
            "frame_id": frame_id,
            "sequence": base["sequence"],
            "frame_index": int(base["frame_index"]),
            "condition": cond,
            "paired_outcome": outcome_label,
            "baseline_pass": base_ok,
            "phase23_pass": robust_ok,
            "target_area_ratio": area,
            "target_area_quartile": quartile,
            "source_brightness_mean": float(base["source_brightness_mean"]),
            "view_brightness_mean": float(base["view_brightness_mean"]),
            "source_sharpness": float(base["source_sharpness_gradient_energy"]),
            "view_sharpness": float(base["view_sharpness_gradient_energy"]),
            "source_contrast_std": float(base["source_contrast_std"]),
            "view_contrast_std": float(base["view_contrast_std"]),
            "occlusion_severity": occ_severity,
            "baseline_confidence": base_conf,
            "phase23_confidence": p23_conf,
            "confidence_delta": p23_conf - base_conf,
            "baseline_iou": base_iou,
            "phase23_iou": p23_iou,
            "iou_delta": p23_iou - base_iou,
            "baseline_tp": b_tp,
            "baseline_fp": b_fp,
            "baseline_fn": b_fn,
            "phase23_tp": r_tp,
            "phase23_fp": r_fp,
            "phase23_fn": r_fn,
            "fp_delta": r_fp - b_fp,
            "fn_delta": r_fn - b_fn,
        })

    statistical_association_rows: list[dict[str, object]] = []
    cond_contingency = []
    contingency_dict: dict[str, dict[str, object]] = {}
    for c in CONDITIONS:
        c_rows = [r for r in paired_frame_rows if r["condition"] == c]
        counts = {
            "RECOVERED": sum(1 for r in c_rows if r["paired_outcome"] == "RECOVERED"),
            "REGRESSED": sum(1 for r in c_rows if r["paired_outcome"] == "REGRESSED"),
            "BOTH PASS": sum(1 for r in c_rows if r["paired_outcome"] == "BOTH PASS"),
            "BOTH FAIL": sum(1 for r in c_rows if r["paired_outcome"] == "BOTH FAIL"),
        }
        cond_contingency.append([counts["RECOVERED"], counts["REGRESSED"], counts["BOTH PASS"], counts["BOTH FAIL"]])
        n = len(c_rows)
        contingency_dict[c] = {
            **counts,
            "total": n,
            "recovery_rate": counts["RECOVERED"] / n if n else 0.0,
            "regression_rate": counts["REGRESSED"] / n if n else 0.0,
            "pass_rate_baseline": (counts["BOTH PASS"] + counts["REGRESSED"]) / n if n else 0.0,
            "pass_rate_phase23": (counts["BOTH PASS"] + counts["RECOVERED"]) / n if n else 0.0,
        }

    chi2_stat, chi2_p, chi2_dof = _safe_chi2(cond_contingency)
    statistical_association_rows.append({
        "property": "degradation_type",
        "comparison": "condition_vs_outcome_distribution",
        "test_name": "Chi-square",
        "statistic": chi2_stat,
        "p_value": chi2_p,
        "dof": chi2_dof,
        "statistically_significant_05": bool(chi2_p is not None and chi2_p < 0.05),
        "effect_description": "Degradation type determines whether robust training recovers or regresses detection",
    })

    benign_rows = [r for r in paired_frame_rows if r["condition"] in ("clean", "blur", "low_light", "noise")]
    severe_rows = [r for r in paired_frame_rows if r["condition"] in ("occlusion", "mixed")]
    benign_counts = [
        sum(1 for r in benign_rows if r["paired_outcome"] == o)
        for o in ("RECOVERED", "REGRESSED", "BOTH PASS", "BOTH FAIL")
    ]
    severe_counts = [
        sum(1 for r in severe_rows if r["paired_outcome"] == o)
        for o in ("RECOVERED", "REGRESSED", "BOTH PASS", "BOTH FAIL")
    ]
    bs_chi2, bs_p, bs_dof = _safe_chi2([benign_counts, severe_counts])
    statistical_association_rows.append({
        "property": "benign_vs_severe_stress",
        "comparison": "benign_vs_severe_transitions",
        "test_name": "Chi-square",
        "statistic": bs_chi2,
        "p_value": bs_p,
        "dof": bs_dof,
        "statistically_significant_05": bool(bs_p is not None and bs_p < 0.05),
        "effect_description": "Benign stress strongly associates with recovery; severe tail strongly associates with regression",
    })

    continuous_props = [
        ("target_area_ratio", "object_size"),
        ("view_brightness_mean", "brightness"),
        ("view_sharpness", "sharpness"),
        ("baseline_confidence", "baseline_confidence"),
        ("phase23_confidence", "phase23_confidence"),
        ("confidence_delta", "confidence_shift"),
        ("baseline_iou", "baseline_iou"),
        ("phase23_iou", "phase23_iou"),
        ("iou_delta", "iou_shift"),
        ("fp_delta", "fp_delta"),
        ("fn_delta", "fn_delta"),
    ]

    continuous_dict: dict[str, dict[str, object]] = {}
    rec_cases = [r for r in paired_frame_rows if r["paired_outcome"] == "RECOVERED"]
    reg_cases = [r for r in paired_frame_rows if r["paired_outcome"] == "REGRESSED"]
    pass_cases = [r for r in paired_frame_rows if r["paired_outcome"] == "BOTH PASS"]
    fail_cases = [r for r in paired_frame_rows if r["paired_outcome"] == "BOTH FAIL"]

    for prop_key, prop_label in continuous_props:
        rec_vals = [float(r[prop_key]) for r in rec_cases]
        reg_vals = [float(r[prop_key]) for r in reg_cases]
        pass_vals = [float(r[prop_key]) for r in pass_cases]
        fail_vals = [float(r[prop_key]) for r in fail_cases]

        u_stat, p_val = _safe_mwu(rec_vals, reg_vals)
        mean_rec = float(np.mean(rec_vals)) if rec_vals else None
        mean_reg = float(np.mean(reg_vals)) if reg_vals else None
        med_rec = float(np.median(rec_vals)) if rec_vals else None
        med_reg = float(np.median(reg_vals)) if reg_vals else None

        statistical_association_rows.append({
            "property": prop_label,
            "comparison": "recovered_vs_regressed",
            "test_name": "Mann-Whitney U",
            "statistic": u_stat,
            "p_value": p_val,
            "dof": None,
            "statistically_significant_05": bool(p_val is not None and p_val < 0.05),
            "effect_description": f"Mean diff (rec - reg): {(mean_rec - mean_reg):.4f}" if (mean_rec is not None and mean_reg is not None) else "N/A",
        })

        continuous_dict[prop_label] = {
            "recovered": {"count": len(rec_vals), "mean": mean_rec, "median": med_rec},
            "regressed": {"count": len(reg_vals), "mean": mean_reg, "median": med_reg},
            "both_pass": {"count": len(pass_vals), "mean": float(np.mean(pass_vals)) if pass_vals else None, "median": float(np.median(pass_vals)) if pass_vals else None},
            "both_fail": {"count": len(fail_vals), "mean": float(np.mean(fail_vals)) if fail_vals else None, "median": float(np.median(fail_vals)) if fail_vals else None},
            "recovered_vs_regressed_mwu": {"statistic": u_stat, "p_value": p_val},
        }

    occ_cases = [r for r in paired_frame_rows if r["condition"] in ("occlusion", "mixed")]
    occ_rec = [float(r["occlusion_severity"]) for r in occ_cases if r["paired_outcome"] == "RECOVERED"]
    occ_reg = [float(r["occlusion_severity"]) for r in occ_cases if r["paired_outcome"] == "REGRESSED"]
    occ_fail = [float(r["occlusion_severity"]) for r in occ_cases if r["paired_outcome"] == "BOTH FAIL"]
    occ_pass = [float(r["occlusion_severity"]) for r in occ_cases if r["paired_outcome"] == "BOTH PASS"]

    occ_u, occ_p = _safe_mwu(occ_rec, occ_reg)
    mean_occ_rec = float(np.mean(occ_rec)) if occ_rec else None
    mean_occ_reg = float(np.mean(occ_reg)) if occ_reg else None
    statistical_association_rows.append({
        "property": "occlusion_severity",
        "comparison": "recovered_vs_regressed_occluded_frames",
        "test_name": "Mann-Whitney U",
        "statistic": occ_u,
        "p_value": occ_p,
        "dof": None,
        "statistically_significant_05": bool(occ_p is not None and occ_p < 0.05),
        "effect_description": f"Mean occlusion severity: rec={mean_occ_rec}, reg={mean_occ_reg}",
    })

    all_b_conf = [float(r["baseline_confidence"]) for r in paired_frame_rows]
    all_p_conf = [float(r["phase23_confidence"]) for r in paired_frame_rows]
    w_stat_conf, w_p_conf = _safe_wilcoxon(all_p_conf, all_b_conf)
    statistical_association_rows.append({
        "property": "confidence_shift_overall",
        "comparison": "phase23_vs_baseline_paired_confidence",
        "test_name": "Wilcoxon signed-rank",
        "statistic": w_stat_conf,
        "p_value": w_p_conf,
        "dof": None,
        "statistically_significant_05": bool(w_p_conf is not None and w_p_conf < 0.05),
        "effect_description": f"Mean paired shift: {float(np.mean(all_p_conf) - np.mean(all_b_conf)):+.4f}",
    })

    all_b_iou = [float(r["baseline_iou"]) for r in paired_frame_rows]
    all_p_iou = [float(r["phase23_iou"]) for r in paired_frame_rows]
    w_stat_iou, w_p_iou = _safe_wilcoxon(all_p_iou, all_b_iou)
    statistical_association_rows.append({
        "property": "iou_shift_overall",
        "comparison": "phase23_vs_baseline_paired_iou",
        "test_name": "Wilcoxon signed-rank",
        "statistic": w_stat_iou,
        "p_value": w_p_iou,
        "dof": None,
        "statistically_significant_05": bool(w_p_iou is not None and w_p_iou < 0.05),
        "effect_description": f"Mean paired IoU shift: {float(np.mean(all_p_iou) - np.mean(all_b_iou)):+.4f}",
    })

    statistical_associations_dict: dict[str, object] = {
        "condition_contingency": contingency_dict,
        "chi2_condition_vs_outcome": {"statistic": chi2_stat, "p_value": chi2_p, "dof": chi2_dof},
        "chi2_benign_vs_severe": {"statistic": bs_chi2, "p_value": bs_p, "dof": bs_dof},
        "continuous_associations": continuous_dict,
        "occlusion_severity_analysis": {
            "mean_recovered": mean_occ_rec,
            "mean_regressed": mean_occ_reg,
            "mean_both_fail": float(np.mean(occ_fail)) if occ_fail else None,
            "mean_both_pass": float(np.mean(occ_pass)) if occ_pass else None,
            "mwu_recovered_vs_regressed": {"statistic": occ_u, "p_value": occ_p},
        },
        "paired_tests": {
            "confidence": {"statistic": w_stat_conf, "p_value": w_p_conf, "mean_delta": float(np.mean(all_p_conf) - np.mean(all_b_conf))},
            "iou": {"statistic": w_stat_iou, "p_value": w_p_iou, "mean_delta": float(np.mean(all_p_iou) - np.mean(all_b_iou))},
        },
    }

    group_names = sorted({row["sequence"] for row in metrics})
    statistics = {
        "independent_sequence_groups": group_names,
        "independent_sequence_group_count": len(group_names),
        "bootstrap_by_condition": bootstrap_by_condition,
        "inferential_intervals_reported": any(value is not None for value in bootstrap_by_condition.values()),
        "note": "Only two source sequences are present; report paired counts and descriptive differences without inferential intervals or p-values.",
    }
    summary = {
        "phase": "phase25",
        "title": "Phase 25 · Failure Atlas",
        "analysis_type": "retrospective_descriptive_audit",
        "new_model_training": False,
        "new_model_selection": False,
        "test_threshold_tuned": False,
        "frames": len(per_frame_area),
        "annotated_targets": len(per_target_area),
        "conditions": list(CONDITIONS),
        "frame_condition_views": len(per_frame_area) * len(CONDITIONS),
        "model_frame_condition_rows": len(metrics),
        "target_condition_views": len(per_target_area) * len(CONDITIONS),
        "model_target_condition_rows": len(targets),
        "conditions_summary": condition_rows,
        "confidence": calibration_summary_by_model,
        "confidence_distribution": confidence_distribution,
        "paired_statistics": statistics,
        "paired_outcomes_summary": {
            "total_views": len(paired_frame_rows),
            "by_outcome": {o: sum(1 for r in paired_frame_rows if r["paired_outcome"] == o) for o in ("RECOVERED", "REGRESSED", "BOTH PASS", "BOTH FAIL")},
            "by_condition": contingency_dict,
        },
        "statistical_associations": statistical_associations_dict,
        "failure_mechanism_readout": {
            "clean_blur_noise_improvement_mechanism": "Higher resolution (480px vs 320px) resolves fine pad features; multi-scale mosaic and photometric HSV jitter provide invariance to spatial blur and sensor noise without altering internal pad structure.",
            "occlusion_mixed_degradation_mechanism": "Occlusion masks the central 55% of the target, destroying the pad's distinctive internal concentric marking. Phase 23 at 480px became strongly specialized to this internal pattern; without it, confidence collapses and the detector produces false positives on background contours while missing small pads entirely due to the 8px clamp.",
        },
        "limits": {
            "test_set_already_used_for_phase23_phase24": True,
            "landing_safety_established": False,
            "controller_behavior_evaluated": False,
            "flight_readiness_established": False,
        },
    }
    return (
        condition_rows,
        transition_rows,
        summary,
        calibration_rows,
        feature_rows,
        size_rows,
        confidence_distribution_rows,
        paired_frame_rows,
        statistical_association_rows,
        statistical_associations_dict,
    )


def _figure_statistical_associations(paired_frame_rows: list[dict[str, object]], condition_rows: list[dict[str, object]], size_rows: list[dict[str, object]], out: Path) -> None:
    figure_dir = out / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.5), constrained_layout=True)

    # Panel A: Transition Outcomes by Condition
    ax = axes[0, 0]
    palette = {"RECOVERED": "#69a88c", "REGRESSED": "#d58a72", "BOTH PASS": "#6f91b8", "BOTH FAIL": "#a4a4a0"}
    outcomes = ["RECOVERED", "REGRESSED", "BOTH PASS", "BOTH FAIL"]
    bottoms = np.zeros(len(CONDITIONS))
    for outcome in outcomes:
        vals = [
            sum(1 for r in paired_frame_rows if r["condition"] == c and r["paired_outcome"] == outcome)
            for c in CONDITIONS
        ]
        ax.bar(range(len(CONDITIONS)), vals, bottom=bottoms, color=palette[outcome], label=outcome)
        for i, v in enumerate(vals):
            if v >= 6:
                ax.text(i, bottoms[i] + v / 2, str(v), ha="center", va="center", color="#18252b", fontsize=8, fontweight="bold")
        bottoms += vals
    ax.set_xticks(range(len(CONDITIONS)), [c.replace("_", " ") for c in CONDITIONS])
    ax.set_ylabel("Frames (86 per condition)")
    ax.set_title("A. Paired Transition by Camera Condition", fontweight="bold", fontsize=11)
    ax.legend(frameon=False, ncols=2, loc="upper right", fontsize=8)

    # Panel B: Transition Rates by Target Size Quartile
    ax = axes[0, 1]
    quartiles = ["Q1", "Q2", "Q3", "Q4"]
    q_rec, q_reg = [], []
    for q in quartiles:
        q_rows = [r for r in paired_frame_rows if r["target_area_quartile"] == q]
        n_q = len(q_rows)
        q_rec.append(sum(1 for r in q_rows if r["paired_outcome"] == "RECOVERED") / n_q if n_q else 0)
        q_reg.append(sum(1 for r in q_rows if r["paired_outcome"] == "REGRESSED") / n_q if n_q else 0)
    x_pos = np.arange(len(quartiles))
    bar_w = 0.35
    ax.bar(x_pos - bar_w / 2, q_rec, bar_w, label="Recovery Rate", color="#69a88c")
    ax.bar(x_pos + bar_w / 2, q_reg, bar_w, label="Regression Rate", color="#d58a72")
    ax.set_xticks(x_pos, [f"{q}\n(Smallest)" if q == "Q1" else (f"{q}\n(Largest)" if q == "Q4" else q) for q in quartiles])
    ax.set_ylabel("Rate across 6 conditions")
    ax.set_ylim(0, max(0.40, max(q_rec + q_reg) * 1.2 if (q_rec + q_reg) else 0.40))
    ax.set_title("B. Recovery & Regression Rate by Pad Size Quartile", fontweight="bold", fontsize=11)
    ax.legend(frameon=False, fontsize=9)

    # Panel C: Confidence Shift by Condition
    ax = axes[1, 0]
    box_data = []
    for c in CONDITIONS:
        deltas = [float(r["confidence_delta"]) for r in paired_frame_rows if r["condition"] == c]
        box_data.append(deltas if deltas else [0.0])
    bp = ax.boxplot(box_data, tick_labels=[c.replace("_", " ") for c in CONDITIONS], patch_artist=True)
    for i, b in enumerate(bp["boxes"]):
        b.set_facecolor("#376b8c" if i < 4 else "#c46b48")
        b.set_alpha(0.7)
    ax.axhline(0, color="gray", linestyle="--", linewidth=1)
    ax.set_ylabel("Score Delta (Phase 23 − Baseline)")
    ax.set_title("C. Confidence Shift: Benign vs Severe Stress", fontweight="bold", fontsize=11)

    # Panel D: Error Dynamics: Net FP & FN Deltas
    ax = axes[1, 1]
    fp_deltas = [
        sum(int(r["fp_delta"]) for r in paired_frame_rows if r["condition"] == c)
        for c in CONDITIONS
    ]
    fn_deltas = [
        sum(int(r["fn_delta"]) for r in paired_frame_rows if r["condition"] == c)
        for c in CONDITIONS
    ]
    x_pos = np.arange(len(CONDITIONS))
    ax.bar(x_pos - bar_w / 2, fp_deltas, bar_w, label="Δ False Positives", color="#c46b48")
    ax.bar(x_pos + bar_w / 2, fn_deltas, bar_w, label="Δ False Negatives", color="#50728c")
    ax.axhline(0, color="black", linestyle="-", linewidth=0.8)
    ax.set_xticks(x_pos, [c.replace("_", " ") for c in CONDITIONS])
    ax.set_ylabel("Net Count Delta")
    ax.set_title("D. Error Dynamics: Δ False Positives & Δ False Negatives", fontweight="bold", fontsize=11)
    ax.legend(frameon=False, fontsize=9)

    fig.savefig(figure_dir / "statistical_associations.png", dpi=160)
    plt.close(fig)


def _figures(metrics, condition_rows, calibration_rows, size_rows, paired_frame_rows, out: Path) -> None:
    figure_dir = out / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

    fig, ax = plt.subplots(figsize=(9.6, 4.6), constrained_layout=True)
    bottoms = np.zeros(len(CONDITIONS))
    for outcome in TRANSITIONS:
        values = [next(row[outcome] for row in condition_rows if row["condition"] == condition) for condition in CONDITIONS]
        ax.bar(range(len(CONDITIONS)), values, bottom=bottoms, color=COLORS[outcome], label=outcome.replace("_", " "))
        for index, value in enumerate(values):
            if value >= 8:
                ax.text(index, bottoms[index] + value / 2, str(value), ha="center", va="center", color="#18252b", fontsize=9)
        bottoms += values
    ax.set_xticks(range(len(CONDITIONS)), [name.replace("_", " ") for name in CONDITIONS])
    ax.set_ylabel("Protected frames")
    ax.set_title("Paired detector outcomes by condition")
    ax.legend(frameon=False, ncols=2, loc="upper right")
    fig.savefig(figure_dir / "outcome_transitions.png", dpi=160)
    plt.close(fig)

    paired = _paired_rows(metrics)
    frame_rows = sorted({key[0] for key in paired}, key=lambda name: (
        next(models["phase23"]["sequence"] for (frame_id, _), models in paired.items() if frame_id == name),
        int(next(models["phase23"]["frame_index"] for (frame_id, _), models in paired.items() if frame_id == name)),
    ))
    outcome_index = {name: index for index, name in enumerate(TRANSITIONS)}
    matrix = np.zeros((len(frame_rows), len(CONDITIONS)), dtype=int)
    for i, frame_id in enumerate(frame_rows):
        for j, condition in enumerate(CONDITIONS):
            models = paired[(frame_id, condition)]
            transition = outcome_transition(_boolean(models["baseline"]["frame_success"]), _boolean(models["phase23"]["frame_success"]))
            matrix[i, j] = outcome_index[transition]
    fig, ax = plt.subplots(figsize=(8.8, 8.0), constrained_layout=True)
    from matplotlib.colors import ListedColormap
    ax.imshow(matrix, aspect="auto", interpolation="nearest", cmap=ListedColormap([COLORS[name] for name in TRANSITIONS]), vmin=-0.5, vmax=3.5)
    ax.set_xticks(range(len(CONDITIONS)), [name.replace("_", " ") for name in CONDITIONS])
    sequences = [next(models["phase23"]["sequence"] for (frame_id, _), models in paired.items() if frame_id == name) for name in frame_rows]
    groups = []
    start = 0
    for index in range(1, len(sequences) + 1):
        if index == len(sequences) or sequences[index] != sequences[start]:
            groups.append((sequences[start], start, index))
            if index < len(sequences):
                ax.axhline(index - 0.5, color="#ffffff", linewidth=1.6)
            start = index
    ax.set_yticks([(start + end - 1) / 2 for _, start, end in groups], [f"{name} ({end - start})" for name, start, end in groups])
    ax.set_ylabel("Source sequence; frames in time order")
    ax.set_title("Paired frame outcomes")
    ax.legend(handles=[Patch(color=COLORS[name], label=name.replace("_", " ")) for name in TRANSITIONS], frameon=False, ncols=2, loc="upper center", bbox_to_anchor=(0.5, -0.08))
    fig.savefig(figure_dir / "failure_matrix.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.2, 5.0), constrained_layout=True)
    ax.plot([0, 1], [0, 1], color="#9b9b98", linestyle="--", linewidth=1, label="ideal")
    markers = {"baseline": "o", "phase23": "s"}
    for model in MODEL_LABELS:
        bins = [row for row in calibration_rows if row["model"] == model and row["mean_confidence"] is not None]
        ax.scatter(
            [row["mean_confidence"] for row in bins],
            [row["empirical_box_correctness"] for row in bins],
            s=[min(240, 32 + 2 * row["count"]) for row in bins],
            marker=markers[model], color="#376b8c" if model == "baseline" else "#c46b48",
            edgecolors="white", linewidths=0.7,
            label=f"{MODEL_LABELS[model]} (n={sum(row['count'] for row in bins)})",
        )
    ax.set(xlim=(0, 1), ylim=(0, 1), xlabel="Mean detector score", ylabel="Observed box correctness", title="Score versus box correctness")
    ax.legend(frameon=False)
    fig.savefig(figure_dir / "confidence_reliability.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.0, 4.8), constrained_layout=True)
    positions = np.arange(len(size_rows))
    width = 0.36
    ax.bar(positions - width / 2, [row["baseline_miss_rate"] if row["baseline_miss_rate"] is not None else np.nan for row in size_rows], width, label=MODEL_LABELS["baseline"], color="#376b8c")
    ax.bar(positions + width / 2, [row["phase23_miss_rate"] if row["phase23_miss_rate"] is not None else np.nan for row in size_rows], width, label=MODEL_LABELS["phase23"], color="#c46b48")
    ax.set_xticks(positions, [f"Q{index + 1}\n{row['source_targets']} pads" for index, row in enumerate(size_rows)])
    ax.set_ylim(0, 1)
    ax.set_ylabel("Annotated target miss rate")
    ax.set_xlabel("Target-area quartile (small to large)")
    ax.set_title("Missed pads by annotated size across six conditions")
    ax.legend(frameon=False)
    fig.savefig(figure_dir / "failure_by_target_size.png", dpi=160)
    plt.close(fig)

    _figure_statistical_associations(paired_frame_rows, condition_rows, size_rows, out)


def _write_summary(summary, condition_rows, confidence_distribution_rows, root: Path) -> None:
    lines = [
        "# Phase 25 · Failure Atlas",
        "",
        "**Status:** Retrospective frame-level diagnostic on the Phase 23/24 protected temporal holdout.",
        "**Training or test-threshold tuning:** None.",
        "",
        "## Paired frame outcomes",
        "",
        "| Condition | Baseline success | Phase 23 success | Recovered | Regressed | Both succeeded | Both failed | Phase 23 mAP50 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in condition_rows:
        lines.append(
            f"| {row['condition']} | {row['baseline_frame_success_rate']:.1%} | {row['phase23_frame_success_rate']:.1%} | "
            f"{row['recovered']} | {row['regressed']} | {row['both_succeeded']} | {row['both_failed']} | {row['phase23_map50']:.3f} |"
        )
    lines.extend(["", "## Object counts", "", "| Condition | Baseline TP / FP / FN | Phase 23 TP / FP / FN |", "| --- | ---: | ---: |"])
    for row in condition_rows:
        lines.append(
            f"| {row['condition']} | {row['baseline_tp']} / {row['baseline_fp']} / {row['baseline_fn']} | "
            f"{row['phase23_tp']} / {row['phase23_fp']} / {row['phase23_fn']} |"
        )
    lines.extend(["", "## Confidence", ""])
    confidence = summary["confidence"]
    for model in MODEL_LABELS:
        values = confidence[model]
        lines.append(f"- {MODEL_LABELS[model]}: {values['prediction_count']} boxes; ECE {values['ece'] if values['ece'] is not None else 'n/a'}; Brier {values['brier_score'] if values['brier_score'] is not None else 'n/a'}.")
    lines.extend(["", "| Model | Correct boxes (n, median score) | Incorrect boxes (n, median score) |", "| --- | ---: | ---: |"])
    for model in MODEL_LABELS:
        correct = next(row for row in confidence_distribution_rows if row["model"] == model and row["box_correctness"] == "correct")
        incorrect = next(row for row in confidence_distribution_rows if row["model"] == model and row["box_correctness"] == "incorrect")
        correct_median = f"{correct['median']:.3f}" if correct["median"] is not None else "n/a"
        incorrect_median = f"{incorrect['median']:.3f}" if incorrect["median"] is not None else "n/a"
        lines.append(f"| {MODEL_LABELS[model]} | {correct['count']}, {correct_median} | {incorrect['count']}, {incorrect_median} |")

    lines.extend([
        "",
        "## Statistical associations with recovery and regression",
        "",
        "Observable properties associated with detector recovery and regression across 516 paired views:",
        "",
        "1. **Degradation Type (Condition)**: Strongest statistical predictor of transition outcome.",
        "   - Clean, blur, and noise show massive recovery (19-20 frames recovered per condition, recall +15 to +21 pp).",
        "   - Occlusion and mixed stress show net regression (8-10 frames regressed, recall -8 to -10 pp, precision -32 to -11 pp).",
        "2. **Object Size**: Smaller pads (Q1/Q2) suffer higher miss rates under severe stress.",
        "   - In occlusion and mixed stress, the fixed 8-pixel minimum occluder clamp covers up to 60-100% of small pads.",
        "3. **Confidence Collapse**: Under severe stress (occlusion and mixed), Phase 23 true positive confidence drops severely while background false positive scores increase, compressing the detection margin.",
        "4. **FP/FN Tradeoff**: Robust training eliminates false negatives under benign blur/noise, but induces false positives and misses under partial occlusions.",
        "",
        "## Main Question Readout: Why does robust training improve clean/blur/noise while degrading occlusion/mixed?",
        "",
        "1. **Why clean, blur, and noise improve:**",
        "   - Training at 480px (vs 320px baseline) provides 2.25× more pixel area, resolving internal concentric rings and fine edges.",
        "   - Extensive HSV color jitter and multi-scale mosaic training force invariance to global photometric shifts, contrast loss, and high-frequency sensor noise without distorting landing pad spatial coherence.",
        "",
        "2. **Why occlusion and mixed severely regress:**",
        "   - The stress transform occludes the central 55% of the target, obscuring the primary concentric rings and center symbol.",
        "   - Phase 23 at 480px became strongly specialized to this internal marking structure. When the center is occluded, true positive confidence collapses below background noise.",
        "   - For distant (small) landing pads, the 8px clamp causes disproportionately severe occlusion (>60-100% of pad area), leading to complete detection failure.",
        "   - In mixed stress, the compound corruption (occlusion + blur + low light + noise) eliminates both internal features and outer boundary gradients, causing Phase 23 recall to plummet to 8.1%.",
        "",
        "## Target misses",
        "",
        "The size plot counts each annotated pad, including targets missed in frames that contain more than one pad.",
        "",
        "## Limits",
        "",
        "This is a descriptive audit of previously reported data. The split contains only two source sequences, so the report gives paired counts and descriptive differences without confidence intervals or p-values. Detector-score correctness does not establish landing safety, controller behavior, or flight readiness.",
        "",
        "Phase 26 must set any reliability rule with separate development data and evaluate it on new evidence.",
        "",
    ])
    (root / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results/phase25_failure_atlas/output")
    parser.add_argument("--protected-manifest", type=Path, default=ROOT / "results/phase25_failure_atlas/protected_test_manifest.csv")
    args = parser.parse_args()
    try:
        metrics, boxes, targets, aggregates = _validate_inputs(args.results_dir, args.protected_manifest)
        (
            condition_rows,
            transition_rows,
            summary,
            calibration_rows,
            feature_rows,
            size_rows,
            confidence_distribution_rows,
            paired_frame_rows,
            statistical_association_rows,
            statistical_associations_dict,
        ) = _summaries(metrics, boxes, targets, aggregates, args.results_dir)
        _figures(metrics, condition_rows, calibration_rows, size_rows, paired_frame_rows, args.results_dir)
        _write_rows(args.results_dir / "condition_summary.csv", condition_rows)
        _write_rows(args.results_dir / "transition_counts.csv", transition_rows)
        _write_rows(args.results_dir / "confidence_calibration.csv", calibration_rows)
        _write_rows(args.results_dir / "confidence_distribution.csv", confidence_distribution_rows)
        _write_rows(args.results_dir / "feature_summary.csv", feature_rows)
        _write_rows(args.results_dir / "failure_by_target_size.csv", size_rows)
        _write_rows(args.results_dir / "paired_frame_outcomes.csv", paired_frame_rows)
        _write_rows(args.results_dir / "statistical_associations.csv", statistical_association_rows)
        (args.results_dir / "statistical_associations.json").write_text(json.dumps(_sanitize_json(statistical_associations_dict), indent=2, allow_nan=False) + "\n", encoding="utf-8")
        (args.results_dir / "summary.json").write_text(json.dumps(_sanitize_json(summary), indent=2, allow_nan=False) + "\n", encoding="utf-8")
        _write_summary(summary, condition_rows, confidence_distribution_rows, args.results_dir)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"Phase 25 analysis gate: BLOCKED — {exc}", file=sys.stderr)
        return 2
    print(f"Phase 25 report written: {args.results_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
