#!/usr/bin/env python3
"""Build the public Atlas from authenticated baseline and Phase 23 prediction tables."""

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


def verified_phase23_cases(baseline_frames):
    source = ROOT / "results/phase25_failure_atlas"
    receipt = json.loads((ROOT / "results/research_revalidation_2026_10_03/replay_receipt.json").read_text())
    if receipt["comparison"] != "EXACT_MATCH" or receipt["maximum_absolute_delta"] != 0:
        raise ValueError("Phase 23 replay has not matched published aggregates exactly")
    if receipt["checkpoint_sha256"] != "43240be969708c32b3e11340c9846b3a588baf361378398677c794d16a455310":
        raise ValueError("Phase 23 checkpoint identity changed")
    for name, expected in receipt["replay_table_sha256"].items():
        if hashlib.sha256((source / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Replayed Phase 23 table changed: {name}")
    cases = {}
    with (source / "frame_condition_metrics.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["model"] != "phase23":
                continue
            key = row["frame_id"], row["condition"]
            if key in cases or key not in baseline_frames:
                raise ValueError("Duplicate or unknown Phase 23 case")
            cases[key] = {"id": key[0], "condition": key[1], "sequence": row["sequence"],
                          "tp": int(row["tp"]), "fp": int(row["fp"]), "fn": int(row["fn"]),
                          "pass": row["frame_success"] == "True", "count": int(row["detection_count"]),
                          "iou": round(float(row["best_iou"]), 4), "score": round(float(row["best_confidence_any"]), 4),
                          "gt": baseline_frames[key]["gt"], "boxes": [], "omitted": 0}
    total = displayed = 0
    with (source / "prediction_boxes.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["model"] != "phase23":
                continue
            item = cases[row["frame_id"], row["condition"]]
            total += 1
            score = float(row["confidence"])
            if score < DISPLAY_FLOOR and row["is_true_positive"] != "True":
                item["omitted"] += 1
                continue
            item["boxes"].append([*box(row), round(score, 4), round(float(row["match_iou"]), 4), int(row["is_true_positive"] == "True")])
            displayed += 1
    if set(cases) != set(baseline_frames) or sum(c["count"] for c in cases.values()) != total:
        raise ValueError("Incomplete Phase 23 prediction population")
    return {"status": "original_checkpoint_replay_verified", "checkpoint_sha256": receipt["checkpoint_sha256"],
            "prediction_rows": total, "displayed_rows": displayed,
            "cases": [cases[key] for key in sorted(cases, key=lambda k: (k[0], CONDITIONS.index(k[1])))],
            "source_hashes": receipt["replay_table_sha256"]}


def build() -> bytes:
    manifest = json.loads((SOURCE / "run_manifest.json").read_text())
    if manifest["phase23_frame_outcomes_available"] is not False or manifest["frame_rows"] != 516:
        raise ValueError("Expected baseline-only 516-case diagnostic")
    for name, expected in manifest["table_sha256"].items():
        raw = (SOURCE / name).read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        if actual != expected and not name.endswith(".gz"):
            norm_lf = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
            norm_crlf = hashlib.sha256(raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")).hexdigest()
            if norm_lf == expected or norm_crlf == expected:
                actual = expected
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
        "phase23_comparison_csv": hashlib.sha256(PHASE23_COMPARISON.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
    }
    result = {
        "status": "paired_verified", "phase23": verified_phase23_cases(frames), "conditions": CONDITIONS,
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
