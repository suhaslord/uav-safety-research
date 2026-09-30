#!/usr/bin/env python3
"""Build the compact public Atlas from the verified baseline-only audit tables."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "results/phase25_baseline_diagnostic"
DEST = ROOT / "deploy/vercel/failure-atlas-data.json"
PHASE23_COMPARISON = ROOT / "results/phase23_robust_detector/robustness_comparison.csv"
CONDITIONS = ("clean", "blur", "low_light", "noise", "occlusion", "mixed")
DISPLAY_FLOOR = .01  # Rendering only; outcomes always use all detections >= .001.


def rows(name: str):
    path = SOURCE / name
    opener = gzip.open if name.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", newline="") as handle:
        yield from csv.DictReader(handle)


def box(row):
    return [round(float(row[key]), 6) for key in ("x0", "y0", "x1", "y1")]


def build() -> bytes:
    manifest = json.loads((SOURCE / "run_manifest.json").read_text())
    if manifest["phase23_frame_outcomes_available"] is not False or manifest["frame_rows"] != 516:
        raise ValueError("Expected baseline-only 516-case diagnostic")
    for name, expected in manifest["table_sha256"].items():
        actual = hashlib.sha256((SOURCE / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Tampered source table: {name}")
    targets = defaultdict(list)
    for row in rows("ground_truth_targets.csv"):
        targets[(row["frame_id"], row["condition"])].append(box(row))
    frames = {}
    for row in rows("frame_condition_metrics.csv"):
        key = (row["frame_id"], row["condition"])
        if key in frames or row["model"] != "phase22_baseline":
            raise ValueError(f"Duplicate or unexpected model: {key}")
        frames[key] = {
            "id": row["frame_id"], "sequence": row["sequence"], "condition": row["condition"],
            "tp": int(row["tp"]), "fp": int(row["fp"]), "fn": int(row["fn"]),
            "count": int(row["detection_count"]), "pass": row["frame_success"] == "True",
            "iou": round(float(row["best_iou"]), 4),
            "score": round(float(row["best_confidence_any"]), 4),
            "size": round(float(row["target_area_ratio"]), 7),
            "brightness": round(float(row["brightness_mean"]), 4),
            "sharpness": round(float(row["sharpness_gradient_energy"]), 6),
            "gt": targets[key], "boxes": [], "omitted": 0,
        }
    displayed = 0
    for row in rows("prediction_boxes.csv.gz"):
        item = frames[(row["frame_id"], row["condition"])]
        score = float(row["confidence"])
        if score < DISPLAY_FLOOR and row["is_true_positive"] != "True":
            item["omitted"] += 1
            continue
        item["boxes"].append([*box(row), round(score, 4), round(float(row["match_iou"]), 4),
                              1 if row["is_true_positive"] == "True" else 0])
        displayed += 1
    if len(frames) != 516 or sum(row["count"] for row in frames.values()) != manifest["prediction_rows"]:
        raise ValueError("Frame or prediction count mismatch")
    if sum(len(row["gt"]) for row in frames.values()) != manifest["target_rows"]:
        raise ValueError("Ground truth count mismatch")
    if sum(len(row["boxes"]) + row["omitted"] for row in frames.values()) != manifest["prediction_rows"]:
        raise ValueError("Display subset dropped predictions without accounting for them")
    ids = sorted({key[0] for key in frames})
    if len(ids) != 86 or {key[1] for key in frames} != set(CONDITIONS):
        raise ValueError("Protected frame and condition manifest mismatch")
    summary = json.loads((SOURCE / "summary.json").read_text())
    phase23_condition_aggregates = {}
    with PHASE23_COMPARISON.open("rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            condition = row["condition"]
            if condition not in CONDITIONS or condition in phase23_condition_aggregates:
                raise ValueError(f"Unexpected or duplicate Phase 23 aggregate condition: {condition}")
            metrics = {"map50": float(row["phase23_map50"]), "recall": float(row["phase23_recall"])}
            if any(not math.isfinite(metric) or not 0 <= metric <= 1 for metric in metrics.values()):
                raise ValueError(f"Invalid Phase 23 aggregate metrics for {condition}")
            phase23_condition_aggregates[condition] = metrics
    if set(phase23_condition_aggregates) != set(CONDITIONS):
        raise ValueError("Phase 23 aggregate table must contain each of the six conditions exactly once")
    source_hashes = {
        **manifest["table_sha256"],
        "phase23_comparison_csv": hashlib.sha256(PHASE23_COMPARISON.read_bytes()).hexdigest(),
    }
    result = {
        "status": "baseline_only", "phase23": None, "conditions": CONDITIONS,
        "phase23_condition_aggregates": phase23_condition_aggregates,
        "frame_ids": ids, "display_floor": DISPLAY_FLOOR, "inference_floor": .001,
        "prediction_rows": manifest["prediction_rows"], "displayed_rows": displayed,
        "condition_summary": summary["condition_summary"],
        "source_hashes": source_hashes,
        "cases": [frames[(frame, condition)] for frame in ids for condition in CONDITIONS],
    }
    return (json.dumps(result, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output = build()
    if args.check:
        if not DEST.exists() or DEST.read_bytes() != output:
            raise SystemExit("Failure Atlas site data is stale; regenerate it")
    else:
        DEST.write_bytes(output)
        print(f"Wrote {len(output)} bytes to {DEST.relative_to(ROOT)}")
