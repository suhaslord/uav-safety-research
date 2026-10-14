#!/usr/bin/env python3
"""Offline AegisLand inference on local images using the authenticated baseline.

This optional CPU-only prototype processes still images, not a camera feed or
an aircraft. It has no labels, ground truth, control outputs, test calibration,
or flight safety claim. The cutoff is selected manually for demonstration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from scripts.phase26_reliability import confidence_score, top_prediction, accept

CHECKPOINT_SHA256 = "3a1801b192d624f8dcdda4bc5d9a9157309000df67a4c30d62368c37901feddd"
EXTENSIONS = {".jpg", ".jpeg", ".png"}


def sha256(path: Path) -> str:
    hash_ = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            hash_.update(block)
    return hash_.hexdigest()


def image_list(location: Path) -> list[Path]:
    if location.is_file():
        images = [location] if location.suffix.lower() in EXTENSIONS else []
    elif location.is_dir():
        images = sorted(p for p in location.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONS)
    else:
        raise ValueError("Image path does not exist")
    if not images or len(images) > 500:
        raise ValueError("Provide 1–500 existing JPG/PNG images")
    return images


def predictions_from_result(output: object) -> list[dict]:
    boxes = output.boxes
    if boxes is None:
        return []
    coordinates = boxes.xyxyn.cpu().tolist()
    scores = boxes.conf.cpu().tolist()
    classes = boxes.cls.cpu().tolist()
    if len(coordinates) != len(scores) or len(scores) != len(classes):
        raise ValueError("Invalid detector output arrays")
    parsed = []
    for coords, score, category in zip(coordinates, scores, classes, strict=True):
        if (len(coords) != 4 or any(not math.isfinite(float(v)) or not 0 <= float(v) <= 1 for v in coords)
                or coords[2] < coords[0] or coords[3] < coords[1]
                or not math.isfinite(float(score)) or not 0 <= float(score) <= 1):
            raise ValueError("Detector emitted invalid normalized predictions")
        if int(category) != category or category < 0:
            raise ValueError("Invalid prediction class")
        parsed.append({
            "class": "landing_target" if category == 0 else "other",
            "score": float(score),
            "box": [float(v) for v in coords],
        })
    return parsed


def run(images: Path, weights: Path, cutoff: float, model_factory=None) -> dict:
    if not (0 < cutoff <= 1 and math.isfinite(cutoff)):
        raise ValueError("Illustrative cutoff must be finite and in (0, 1]")
    if not weights.is_file() or sha256(weights) != CHECKPOINT_SHA256:
        raise ValueError("Only the authenticated Phase 22 baseline best.pt is allowed")
    files = image_list(images)
    if model_factory is None:
        try:
            from ultralytics import YOLO
        except ImportError as error:
            raise RuntimeError("Install Ultralytics to run local model inference") from error
        model_factory = YOLO
    detector = model_factory(str(weights))
    cases = []
    for path in files:
        # Original baseline post-NMS settings; no labels or test outcome fed in.
        output = detector.predict(source=str(path), imgsz=320, conf=0.001, iou=0.7,
                                  max_det=300, device="cpu", verbose=False, save=False)
        if len(output) != 1:
            raise ValueError("Expected one detector result for each still image")
        pred = predictions_from_result(output[0])
        top = top_prediction(pred)
        cases.append({
            "image": str(path.resolve()),
            "image_sha256": sha256(path),
            "top_score": confidence_score(pred),
            "top_box": top["box"] if top else None,
            "accepted": accept(pred, cutoff),
            "all_post_nms_predictions": len(pred),
            "note": "No ground truth provided or assessed.",
        })
    return {
        "schema": "aegisland.offline-image-inference.v1",
        "mode": "illustrative_unvalidated_still_image_inference",
        "checkpoint_sha256": CHECKPOINT_SHA256,
        "model": "original_frozen_phase22_baseline",
        "inference_settings": {"imgsz": 320, "confidence_floor": 0.001,
                               "nms_iou": 0.7, "max_det": 300, "device": "cpu"},
        "illustrative_cutoff": cutoff,
        "threshold_tuned": False,
        "labels_used": False,
        "independent_test_validated": False,
        "flight_control_available": False,
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=Path, required=True, help="Local JPG/PNG image or folder")
    parser.add_argument("--weights", type=Path, required=True, help="Verified Phase 22 baseline best.pt")
    parser.add_argument("--illustrative-cutoff", type=float, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Output exists. Choose a new report path to preserve prior attempts.")
    result = run(args.images, args.weights, args.illustrative_cutoff)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Saved {len(result['cases'])} offline image decisions to {args.out}")


if __name__ == "__main__":
    main()
