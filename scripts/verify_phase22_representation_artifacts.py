#!/usr/bin/env python3
"""Replay Phase 22 representation evidence without any detector inference."""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from phase25_lib import Box, box_from_yolo, frame_metrics, sha256_file
from run_phase22_representation_study import unique_population, paired_analysis, stage_a_gate
from uav_safety.real_landing_dataset import read_yolo_boxes


def verify(output: Path, source: Path) -> dict:
    run = json.loads((output / "run_manifest.json").read_text())
    if sha256_file(output / "protocol.json") != run["protocol_sha256"]:
        raise ValueError("Protocol hash changed")
    for name, expected in run["output_sha256"].items():
        if sha256_file(output / name) != expected:
            raise ValueError(f"Artifact hash changed: {name}")
    with (output / "representation_manifest.csv").open(newline="") as handle:
        manifest = list(csv.DictReader(handle))
    unique_population(manifest)
    with (output / "frame_metrics.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        if row["success"] not in {"True", "False"}:
            raise ValueError("Invalid success boolean")
        row["success"] = row["success"] == "True"
        for name in ("TP", "FP", "FN", "gt_count", "prediction_count"):
            row[name] = int(row[name])
        for name in ("best_iou", "matched_confidence", "best_confidence_any"):
            row[name] = float(row[name]) if row[name] else None
    unique_population(rows)
    groups = defaultdict(list)
    with (output / "raw_predictions.csv").open(newline="") as handle:
        for raw in csv.DictReader(handle):
            groups[(raw["frame_id"], raw["representation"])].append(raw)
    population = {(r["frame_id"], r["representation"]) for r in rows}
    if not set(groups).issubset(population):
        raise ValueError("Prediction has unknown frame/representation")
    for row in rows:
        key = row["frame_id"], row["representation"]
        raw = groups[key]
        if [int(r["prediction_index"]) for r in raw] != list(range(len(raw))):
            raise ValueError("Duplicate or noncontiguous prediction indices")
        boxes = [Box(int(r["class_id"]), *(float(r[k]) for k in ("x0", "y0", "x1", "y1", "confidence"))) for r in raw]
        label = source / "labels/test" / Path(row["frame_id"]).with_suffix(".txt").name
        expected_label_sha = next(m["label_sha256"] for m in manifest if m["frame_id"] == row["frame_id"])
        if sha256_file(label) != expected_label_sha:
            raise ValueError("Protected replay label changed")
        labels = read_yolo_boxes(label, class_id=0)
        truth = [box_from_yolo(b.class_id, b.x_center, b.y_center, b.width, b.height) for b in labels]
        actual, matched = frame_metrics(truth, boxes, iou_threshold=.5)
        mapping = {"success": "frame_success", "TP": "tp", "FP": "fp", "FN": "fn", "gt_count": "gt_count",
                   "best_iou": "best_iou", "matched_confidence": "best_confidence_tp", "best_confidence_any": "best_confidence_any"}
        if any(row[name] != actual[metric] for name, metric in mapping.items()) or row["prediction_count"] != len(boxes):
            raise ValueError(f"Frame metrics do not replay: {key}")
        for exported, expected in zip(raw, matched, strict=True):
            if (float(exported["match_iou"]) != expected["match_iou"]
                    or (exported["is_true_positive"] == "True") != expected["is_true_positive"]
                    or (int(exported["matched_gt_index"]) if exported["matched_gt_index"] else None) != expected["matched_gt_index"]):
                raise ValueError(f"Prediction matching does not replay: {key}")
    paired = json.loads((output / "paired_representation_analysis.json").read_text())
    if paired_analysis(rows, manifest) != paired:
        raise ValueError("Paired statistics do not replay")
    aggregate = json.loads((output / "aggregate_metrics.json").read_text())
    gate = stage_a_gate(aggregate, complete=True, deterministic=True, hashes_verified=True)
    if gate != run["stage_a"] or gate != json.loads((output / "stage_a_gate.json").read_text()):
        raise ValueError("Stage A gate does not replay")
    return {"status": "PASS", "frame_rows_replayed": len(rows), "prediction_rows_replayed": sum(map(len, groups.values())),
            "paired_statistics_replayed": True, "detector_inference_run": False,
            "scope": "artifact hashes, saved boxes/matches, frame metrics, statistics, and recorded metric gate; aggregate detector reevaluation requires study runner"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.out, args.source), indent=2))
