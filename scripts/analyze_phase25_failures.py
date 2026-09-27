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
    if set(row["condition"] for row in aggregates) != set(CONDITIONS) or set(row["model"] for row in aggregates) != set(MODEL_LABELS):
        raise ValueError("Aggregate validation table does not contain both models across all conditions")
    if len(aggregates) != len(CONDITIONS) * len(MODEL_LABELS):
        raise ValueError("Aggregate validation table has duplicate or missing model-condition rows")
    for row in aggregates:
        if any(not math.isfinite(float(row[name])) or not 0.0 <= float(row[name]) <= 1.0
               for name in ("precision", "recall", "map50", "map50_95")):
            raise ValueError(f"Invalid aggregate validation metric for {row['model']} / {row['condition']}")
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
        if coords[2] <= coords[0] or coords[3] <= coords[1]:
            raise ValueError(f"Prediction box has non-positive area for {key}")
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
        elif (int(row["matched_prediction_index"]) != int(match["prediction_index"])
              or abs(float(row["matched_confidence"]) - float(match["confidence"])) > 1e-9
              or abs(float(row["match_iou"]) - float(match["match_iou"])) > 1e-9):
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
        "limits": {
            "test_set_already_used_for_phase23_phase24": True,
            "landing_safety_established": False,
            "controller_behavior_evaluated": False,
            "flight_readiness_established": False,
        },
    }
    return condition_rows, transition_rows, summary, calibration_rows, feature_rows, size_rows, confidence_distribution_rows


def _figures(metrics, condition_rows, calibration_rows, size_rows, out: Path) -> None:
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
        condition_rows, transition_rows, summary, calibration_rows, feature_rows, size_rows, confidence_distribution_rows = _summaries(metrics, boxes, targets, aggregates, args.results_dir)
        _figures(metrics, condition_rows, calibration_rows, size_rows, args.results_dir)
        _write_rows(args.results_dir / "condition_summary.csv", condition_rows)
        _write_rows(args.results_dir / "transition_counts.csv", transition_rows)
        _write_rows(args.results_dir / "confidence_calibration.csv", calibration_rows)
        _write_rows(args.results_dir / "confidence_distribution.csv", confidence_distribution_rows)
        _write_rows(args.results_dir / "feature_summary.csv", feature_rows)
        _write_rows(args.results_dir / "failure_by_target_size.csv", size_rows)
        (args.results_dir / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        _write_summary(summary, condition_rows, confidence_distribution_rows, args.results_dir)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"Phase 25 analysis gate: BLOCKED — {exc}", file=sys.stderr)
        return 2
    print(f"Phase 25 report written: {args.results_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
