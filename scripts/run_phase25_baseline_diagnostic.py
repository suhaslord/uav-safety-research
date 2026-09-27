#!/usr/bin/env python3
"""Export real Phase 22 baseline boxes on the frozen Phase 25 reconstruction.

This is a single-model diagnostic. It never fills the paired Phase 25 tables.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]

from audit_kios_reconstruction import audit  # noqa: E402
from phase25_lib import CONDITIONS, box_from_yolo, frame_metrics, image_features, sha256_file  # noqa: E402
from run_phase25_frame_audit import _normalized_predictions  # noqa: E402
from uav_safety.real_landing_dataset import read_yolo_boxes  # noqa: E402

REFERENCE = ROOT / "results/phase23_robust_detector/robustness_comparison.csv"
PROTECTED = ROOT / "results/phase25_failure_atlas/protected_test_manifest.csv"
INPUT_LOCK = ROOT / "docs/phase25_input_lock.json"
SAMPLE_FRAME = "land_pad2__2100.jpg"  # Existing site illustration, chosen before inference.


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"Empty table: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_boxes(path: Path, rows: list[dict[str, object]]) -> None:
    fields = ("frame_id", "sequence", "condition", "model", "prediction_index", "class_id",
              "x0", "y0", "x1", "y1", "confidence", "matched_gt_index", "match_iou", "is_true_positive")
    with path.open("wb") as binary:
        with gzip.GzipFile(filename="", mode="wb", fileobj=binary, mtime=0, compresslevel=9) as zipped:
            # close the text wrapper first so the gzip trailer is written afterwards.
            import io
            with io.TextIOWrapper(zipped, encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
    with gzip.open(path, "rt", encoding="utf-8", newline="") as check:
        actual = sum(1 for _ in csv.DictReader(check))
    if actual != len(rows):
        raise ValueError(f"Incomplete prediction archive: {actual} != {len(rows)}")


def run(args: argparse.Namespace) -> None:
    if args.out.exists() and any(args.out.iterdir()):
        raise ValueError(f"Output exists: {args.out}. Use a new directory.")
    verified = audit(args.archive, args.source, args.stress, args.baseline)
    lock = json.loads(INPUT_LOCK.read_text(encoding="utf-8"))
    settings = lock["inference_settings"]["baseline"]
    if settings != {"imgsz": 320, "confidence_floor": .001, "nms_iou": .7, "max_det": 300,
                    "batch": 16, "workers": 2, "device": "cpu"}:
        raise ValueError("Baseline inference settings changed since the Phase 25 freeze")
    frames = read_rows(PROTECTED)
    if len(frames) != 86 or {row["image"] for row in frames} != set(json.loads(
        (ROOT / "docs/phase25_reconstruction_lock.json").read_text(encoding="utf-8"))["protected_test_files"]):
        raise ValueError("Protected frame IDs changed")
    reference = {row["condition"]: row for row in read_rows(REFERENCE)}
    if set(reference) != set(CONDITIONS):
        raise ValueError("Published reference does not contain all conditions")

    from ultralytics import YOLO
    model = YOLO(str(args.baseline))
    aggregate = []
    with tempfile.TemporaryDirectory(prefix="phase25-baseline-validation-") as temp:
        for condition in CONDITIONS:
            data_yaml = Path(temp) / f"{condition}.yaml"
            data_yaml.write_text(
                f"path: {(args.stress / condition).resolve()}\n"
                "train: images/test\nval: images/test\ntest: images/test\n"
                "names:\n  0: landing_pad\n", encoding="utf-8")
            metrics = model.val(
                data=str(data_yaml), split="test", imgsz=320, conf=.001, iou=.7,
                max_det=300, batch=16, workers=2, device="cpu", plots=False,
                verbose=False, project=temp, name=f"baseline-{condition}", exist_ok=True)
            recall, map50 = float(metrics.box.mr), float(metrics.box.map50)
            expected = reference[condition]
            if any(not math.isfinite(value) or not 0 <= value <= 1 for value in (recall, map50)):
                raise ValueError(f"Invalid baseline metrics for {condition}")
            if (abs(recall - float(expected["baseline_recall"])) > .001
                    or abs(map50 - float(expected["baseline_map50"])) > .001):
                raise ValueError(f"Baseline aggregates did not reproduce for {condition}; no boxes exported")
            aggregate.append({"condition": condition, "recall": recall, "map50": map50,
                              "published_recall": expected["baseline_recall"],
                              "published_map50": expected["baseline_map50"]})
    print("All six published baseline aggregates reproduced", flush=True)

    boxes: list[dict[str, object]] = []
    frames_out: list[dict[str, object]] = []
    targets: list[dict[str, object]] = []
    sample: dict[str, object] = {}
    for condition in CONDITIONS:
        paths = [args.stress / condition / "images/test" / frame["image"] for frame in frames]
        predictions = model.predict(
            source=[str(path) for path in paths], imgsz=320, conf=.001, iou=.7,
            max_det=300, batch=16, device="cpu", verbose=False, stream=True)
        for frame, path, output in zip(frames, paths, predictions, strict=True):
            if Path(output.path).name != path.name:
                raise ValueError("Prediction order differs from protected manifest")
            labels = read_yolo_boxes(args.stress / condition / "labels/test" / frame["label"], class_id=0)
            truth = [box_from_yolo(box.class_id, box.x_center, box.y_center, box.width, box.height)
                     for box in labels]
            metrics, matched_boxes = frame_metrics(truth, _normalized_predictions(output), iou_threshold=.5)
            features = image_features(path, truth)
            frames_out.append({"frame_id": frame["image"], "sequence": frame["sequence"],
                               "frame_index": frame["frame_index"], "condition": condition,
                               "model": "phase22_baseline", **metrics,
                               "target_area_ratio": features["target_area_ratio"],
                               "brightness_mean": features["brightness_mean"],
                               "sharpness_gradient_energy": features["sharpness_gradient_energy"]})
            boxes.extend({"frame_id": frame["image"], "sequence": frame["sequence"],
                          "condition": condition, "model": "phase22_baseline", **row}
                         for row in matched_boxes)
            for index, target in enumerate(truth):
                targets.append({"frame_id": frame["image"], "condition": condition,
                                "target_index": index, "x0": target.x0, "y0": target.y0,
                                "x1": target.x1, "y1": target.y1,
                                "detected": any(row["is_true_positive"] and row["matched_gt_index"] == index
                                                for row in matched_boxes)})
            if frame["image"] == SAMPLE_FRAME:
                top = max(matched_boxes, key=lambda row: float(row["confidence"]), default=None)
                sample[condition] = {"frame_success": metrics["frame_success"],
                                     "gt_count": len(truth), "tp": metrics["tp"],
                                     "fp": metrics["fp"], "fn": metrics["fn"],
                                     "top_prediction": {key: top[key] for key in
                                                        ("x0", "y0", "x1", "y1", "confidence", "match_iou", "is_true_positive")}
                                     if top else None}
        print(f"Predicted {condition}: {len(frames)} protected frames", flush=True)

    if len(frames_out) != 516 or len(sample) != 6 or len(targets) < 516:
        raise ValueError("Incomplete baseline frame inventory")
    summary = []
    for condition in CONDITIONS:
        group = [row for row in frames_out if row["condition"] == condition]
        summary.append({"condition": condition, "frames": len(group),
                        "successful_frames": sum(row["frame_success"] for row in group),
                        "tp": sum(row["tp"] for row in group), "fp": sum(row["fp"] for row in group),
                        "fn": sum(row["fn"] for row in group)})
    result = {"status": "baseline_only_real_predictions", "model": "Phase 22 frozen baseline",
              "frame_condition_cases": 516, "condition_summary": summary,
              "existing_site_frame": SAMPLE_FRAME, "site_frame_predictions": sample,
              "limits": "Retrospective single-model diagnostic on reconstructed stresses; Phase 23 paired outcomes unavailable. "
                        "A .001 prediction floor yields many low-score boxes. No threshold tuned on this test set."}

    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out / "aggregate_validation.csv", aggregate)
    write_csv(args.out / "frame_condition_metrics.csv", frames_out)
    write_csv(args.out / "ground_truth_targets.csv", targets)
    write_boxes(args.out / "prediction_boxes.csv.gz", boxes)
    (args.out / "summary.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    outputs = ("aggregate_validation.csv", "frame_condition_metrics.csv", "ground_truth_targets.csv",
               "prediction_boxes.csv.gz", "summary.json")
    manifest = {
        "status": "baseline_only_reconstructed_input_diagnostic",
        "phase25_paired_audit_complete": False,
        "phase23_frame_outcomes_available": False,
        "model_retrained": False,
        "input_verification": {key: value for key, value in verified.items() if key != "limits"},
        "source_archive_sha256": sha256_file(args.archive),
        "checkpoint_sha256": sha256_file(args.baseline),
        "runtime": {"python": platform.python_version(), **{name: importlib.metadata.version(name)
                    for name in ("torch", "ultralytics", "numpy", "Pillow")}},
        "inference": settings,
        "matching": "one-to-one, confidence-ranked, class 0, IoU >= 0.50",
        "reference_sha256": sha256_file(REFERENCE),
        "protected_manifest_sha256": sha256_file(PROTECTED),
        "method_sha256": {name: sha256_file(ROOT / name) for name in (
            "scripts/run_phase25_baseline_diagnostic.py", "scripts/phase25_lib.py",
            "scripts/run_phase25_frame_audit.py", "scripts/audit_kios_reconstruction.py")},
        "table_sha256": {name: sha256_file(args.out / name) for name in outputs},
        "frame_rows": len(frames_out), "target_rows": len(targets), "prediction_rows": len(boxes),
    }
    (args.out / "run_manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}: {len(frames_out)} views, {len(boxes)} predicted boxes")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--stress", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=ROOT / "results/phase25_baseline_diagnostic")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
