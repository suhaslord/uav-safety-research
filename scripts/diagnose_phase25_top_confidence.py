#!/usr/bin/env python3
"""Read-only Phase 25 top-prediction risk audit for AegisLand's landing objective.

Checks the existing frozen source hashes before computing whether the highest
confidence landing-target box itself overlaps a labeled pad at IoU >= 0.50.
This deliberately does NOT select a confidence threshold or admit Phase 26 data.
The 86 real frames are from two reused KIOS videos, with six dependent views.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

BOX_FIELDS = ("x0", "y0", "x1", "y1")
DESCRIPTIVE_CUTOFFS = (0.05, 0.25, 0.50, 0.75, 0.90)
TARGET_CLASS_ID = 0
MATCH_IOU = 0.50
REQUIRED_TABLES = ("aggregate_validation.csv", "frame_condition_metrics.csv",
                   "prediction_boxes.csv", "ground_truth_targets.csv")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as src:
        for block in iter(lambda: src.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rows(path: Path):
    with path.open(newline="", encoding="utf-8") as src:
        yield from csv.DictReader(src)


def key(row):
    return (row["frame_id"], row["condition"], row["model"])


def box(row, *, allow_degenerate=False):
    values = tuple(float(row[k]) for k in BOX_FIELDS)
    if (any(not math.isfinite(x) or not 0 <= x <= 1 for x in values)
            or values[2] < values[0] or values[3] < values[1]
            or not allow_degenerate and (values[2] == values[0] or values[3] == values[1])):
        raise ValueError(f"Invalid normalized-area box: {values}")
    return values


def iou(left, right):
    # Boundary-clipped predictions with zero area remain false positives.
    if left[2] == left[0] or left[3] == left[1]:
        return 0.0
    dx = max(0.0, min(left[2], right[2]) - max(left[0], right[0]))
    dy = max(0.0, min(left[3], right[3]) - max(left[1], right[1]))
    union = ((left[2] - left[0]) * (left[3] - left[1])
             + (right[2] - right[0]) * (right[3] - right[1]) - dx * dy)
    return dx * dy / union


def update_top(previous, candidate):
    """The earliest prediction index wins equal-score ties; no labels enter."""
    if previous is None:
        return candidate
    if (candidate["confidence"] > previous["confidence"]
            or candidate["confidence"] == previous["confidence"]
            and candidate["index"] < previous["index"]):
        return candidate
    return previous


def diagnostics(table_root: Path):
    manifest_path = table_root / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (manifest.get("phase") != "phase25"
            or manifest.get("status") != "predictions_generated"
            or manifest.get("analysis_type") != "retrospective_descriptive_audit"):
        raise ValueError("Not the frozen Phase 25 retrospective prediction record")
    locked = manifest.get("output_tables_sha256")
    if not isinstance(locked, dict) or set(locked) != set(REQUIRED_TABLES):
        raise ValueError("Manifest lacks the four exact original table hashes")
    for name in REQUIRED_TABLES:
        if sha256(table_root / name) != locked[name]:
            raise ValueError(f"Frozen Phase 25 table changed: {name}")

    metric_rows = {}
    for row in rows(table_root / "frame_condition_metrics.csv"):
        k = key(row)
        if k in metric_rows:
            raise ValueError(f"Duplicate frame-condition-model case: {k}")
        metric_rows[k] = row
    if (len(metric_rows) != 1032 or {k[2] for k in metric_rows} != {"baseline", "phase23"}
            or len({k[0] for k in metric_rows}) != 86
            or len({k[1] for k in metric_rows}) != 6):
        raise ValueError("Phase 25 record has unexpected model/frame/condition inventory")

    ground_truth = defaultdict(list)
    target_index_set = defaultdict(set)
    for item in rows(table_root / "ground_truth_targets.csv"):
        k = key(item)
        if k not in metric_rows or int(item["class_id"]) != TARGET_CLASS_ID:
            raise ValueError(f"Unknown target case/class: {k}")
        index = int(item["target_index"])
        if index in target_index_set[k]:
            raise ValueError(f"Duplicate ground truth index: {k}, {index}")
        target_index_set[k].add(index)
        ground_truth[k].append(box(item))

    top = {}
    counts = defaultdict(int)
    seen_indices = defaultdict(set)
    for item in rows(table_root / "prediction_boxes.csv"):
        k = key(item)
        if k not in metric_rows:
            raise ValueError(f"Prediction without frozen frame: {k}")
        index = int(item["prediction_index"])
        if index < 0 or index in seen_indices[k]:
            raise ValueError(f"Invalid/duplicate prediction index: {k}, {index}")
        seen_indices[k].add(index)
        counts[k] += 1
        category = int(item["class_id"])
        if category < 0:
            raise ValueError(f"Invalid predicted class: {k}")
        score = float(item["confidence"])
        if not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError(f"Invalid confidence: {k}")
        # The score is prediction-only. Ground-truth matching happens afterward.
        if category == TARGET_CLASS_ID:
            top[k] = update_top(top.get(k), {
                "index": index, "confidence": score, "box": box(item, allow_degenerate=True)
            })

    report_rows = []
    for k in sorted(metric_rows):
        row = metric_rows[k]
        gt = int(row["gt_count"])
        detection_count = int(row["detection_count"])
        if gt < 1 or len(ground_truth[k]) != gt:
            raise ValueError(f"Missing or incorrect ground truth inventory: {k}")
        if counts[k] != detection_count or seen_indices[k] != set(range(detection_count)):
            raise ValueError(f"Predictions do not reconcile to frame counts: {k}")
        stored_success = row["frame_success"].strip().lower()
        if stored_success not in {"true", "false"}:
            raise ValueError(f"Invalid stored frame_success value: {k}")
        frame_success = stored_success == "true"
        if frame_success != (int(row["tp"]) == gt and int(row["fn"]) == 0):
            raise ValueError(f"Stored frame success contradicts frozen TP/FN: {k}")
        candidate = top.get(k)
        highest_confidence = candidate["confidence"] if candidate else 0.0
        max_iou = (max(iou(candidate["box"], gt_box) for gt_box in ground_truth[k])
                   if candidate else 0.0)
        report_rows.append({
            "frame_id": k[0], "condition": k[1], "model": k[2],
            "sequence": row["sequence"],
            "top_confidence": highest_confidence,
            "top_index": candidate["index"] if candidate else "",
            "top_best_iou": max_iou,
            "top_correct_iou50": int(candidate is not None and max_iou >= MATCH_IOU),
            "any_match_frame_success": int(frame_success),
            "any_match_but_top_wrong": int(frame_success and max_iou < MATCH_IOU),
        })

    by_case = defaultdict(list)
    for row in report_rows:
        by_case[(row["model"], row["condition"])].append(row)

    summary = []
    for (model, condition), cases in sorted(by_case.items()):
        if len(cases) != 86:
            raise ValueError(f"Unexpected number of reused test frames in {(model, condition)}")
        cutoffs = []
        for threshold in DESCRIPTIVE_CUTOFFS:
            accepted = [case for case in cases if case["top_confidence"] >= threshold]
            wrong = sum(1 - x["top_correct_iou50"] for x in accepted)
            cutoffs.append({
                "example_threshold_not_selected": threshold,
                "accepted": len(accepted),
                "accepted_top_errors": wrong,
                "accepted_top_error_fraction": wrong / len(accepted) if accepted else None,
                "accepted_fraction": len(accepted) / len(cases)
            })
        summary.append({
            "model": model, "condition": condition,
            "reused_views": len(cases),
            "top_correct_count": sum(r["top_correct_iou50"] for r in cases),
            "any_match_success_count": sum(r["any_match_frame_success"] for r in cases),
            "any_match_but_top_wrong": sum(r["any_match_but_top_wrong"] for r in cases),
            "illustrative_operating_points": cutoffs
        })
    return report_rows, {
        "title": "AegisLand Phase 25 top-confidence localization audit",
        "status": "retrospective_descriptive_only",
        "reused_protected_frames": 86,
        "source_sequences": 2,
        "dependent_stress_conditions": 6,
        "frame_model_condition_rows": len(report_rows),
        "top_score_label_free": True,
        "correctness": "highest-confidence landing-target prediction IoU >= 0.50 against any annotated pad",
        "any_match_frame_success_is_not_top_prediction_correctness": True,
        "threshold_selected": False,
        "independent_phase26_test_set_used": False,
        "flight_safety_or_controller_test": False,
        "input_table_sha256": locked,
        "cases": summary,
        "limitations": [
            "All 86 protected KIOS frames were already evaluated; never use these results to choose a prospective reliability threshold.",
            "The six conditions reuse the same frames; the two continuous source videos are not independent capture sessions.",
            "No empty-target images here; confidence-based false accepts on absent pads cannot be estimated.",
            "Top-box localization is not state-estimation reliability, controller intervention, or safe touchdown probability.",
            "No confidence threshold has been frozen for an independent Phase 26 dataset."
        ]
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results-dir", default="results/phase25_failure_atlas", type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()
    if args.out_dir.exists():
        raise ValueError("Refusing to overwrite a prior independent diagnostic output")
    detail, summary = diagnostics(args.results_dir)
    args.out_dir.mkdir(parents=True)
    with (args.out_dir / "top_prediction_outcomes.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(detail[0]))
        writer.writeheader()
        writer.writerows(detail)
    (args.out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": summary["status"], "frames": summary["reused_protected_frames"],
        "cases": len(summary["cases"]),
        "top_box_vs_any_match_mismatches": sum(row["any_match_but_top_wrong"] for row in summary["cases"]),
        "threshold_selected": False
    }, indent=2))


if __name__ == "__main__":
    main()
