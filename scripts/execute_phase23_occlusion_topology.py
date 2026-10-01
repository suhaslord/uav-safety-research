"""Execution script for Phase 23 Occlusion Topology Experiment.

Executes Parts 4, 5, 6, 7:
- Part 4: Strict input verification (manifest SHA, bundle SHA, checkpoint SHA, protocol SHA)
- Part 5: Zero-dose baseline gate against authenticated Phase 23 clean baseline (tolerance <= 0.001)
- Part 6: Deterministic treatment dataset generation with atomic writes and decode verification
- Part 7: Phase 23 YOLO11n inference across all 5,160 views, recording frame metrics and raw predictions
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
from PIL import Image
from ultralytics import YOLO

# Add scripts directory to path
SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(REPO_ROOT / "src"))

from generate_occlusion_topology import (
    YoloBox,
    MASK_GENERATORS,
    TOPOLOGIES,
    DEFAULT_DOSES,
    GLOBAL_SEED,
    FILL_COLOR,
    _rng_for,
    read_yolo_label,
    compute_achieved_dose,
    apply_mask,
    atomic_write_image,
)
from phase25_lib import (
    Box,
    box_from_yolo,
    frame_metrics,
    sha256_file,
)
from uav_safety.real_landing_dataset import read_yolo_boxes

# ---------------------------------------------------------------------------
# Locked Constants
# ---------------------------------------------------------------------------
EXPECTED_MANIFEST_SHA = "8605cf1cbf9e8769c0324bf066078f9964f232ac3128131c8bd0b689bb7b64b7"
EXPECTED_BUNDLE_SHA = "a55531930988deeadf81853d00b63c7e589c6b7fd2270f57653abdb5cdd3e55d"
EXPECTED_CKPT_SHA = "43240be969708c32b3e11340c9846b3a588baf361378398677c794d16a455310"
PROTOCOL_V1_1_PATH = Path("docs/phase25_phase23_occlusion_topology_protocol_v1_1.json")
EXPECTED_PROTOCOL_V1_1_SHA = "b4637e5b9b0c9551ac6a106d20fe8bc62f05d50b7030432c1c4e1bf7cf771a29"

# Clean baseline historical values
HISTORICAL_CLEAN_METRICS = {
    "precision": 0.7169366595101914,
    "recall": 0.5930232558139535,
    "map50": 0.5551842475528265,
    "map50_95": 0.222675649160523,
}
GATE_TOLERANCE = 0.001

# Inference hyperparameters (locked)
IMGSZ = 480
CONF = 0.001
IOU = 0.7
MAX_DET = 300
BATCH = 16
DEVICE = "0"
MATCH_IOU = 0.50
CLASS_ID = 0


def _normalized_predictions(result) -> list[Box]:
    """Extract normalized Box objects from an Ultralytics prediction Result."""
    if result.boxes is None or len(result.boxes) == 0:
        return []
    height, width = result.orig_shape
    if height <= 0 or width <= 0:
        raise ValueError(f"Invalid image shape: {result.orig_shape}")
    xyxy = result.boxes.xyxy.cpu().numpy()
    classes = result.boxes.cls.cpu().numpy()
    confidence = result.boxes.conf.cpu().numpy()
    normalized = []
    for box, class_id, score in zip(xyxy, classes, confidence, strict=True):
        values = [float(v) for v in box]
        if len(values) != 4 or any(not math.isfinite(v) for v in values):
            raise ValueError("Non-finite prediction coordinates")
        x0 = max(0.0, min(1.0, values[0] / width))
        y0 = max(0.0, min(1.0, values[1] / height))
        x1 = max(0.0, min(1.0, values[2] / width))
        y1 = max(0.0, min(1.0, values[3] / height))
        if x1 < x0 or y1 < y0:
            raise ValueError("Inverted coordinates")
        normalized.append(Box(int(class_id), x0, y0, x1, y1, float(score)))
    return normalized


def verify_inputs(
    manifest_path: Path,
    bundle_path: Path,
    stress_root: Path,
) -> tuple[list[dict[str, str]], Path]:
    """Execute Part 4 input verification."""
    print("=" * 70)
    print("PART 4: CHECK EXECUTION INPUTS")
    print("=" * 70)

    # 1. Manifest verification
    manifest_sha = sha256_file(manifest_path)
    if manifest_sha != EXPECTED_MANIFEST_SHA:
        raise ValueError(f"Manifest SHA mismatch: {manifest_sha} != {EXPECTED_MANIFEST_SHA}")
    with open(manifest_path, encoding="utf-8", newline="") as f:
        manifest_rows = list(csv.DictReader(f))
    if len(manifest_rows) != 86:
        raise ValueError(f"Expected 86 frames, got {len(manifest_rows)}")
    seq_counts = {"land_pad": 0, "land_pad2": 0}
    for r in manifest_rows:
        seq_counts[r["sequence"]] += 1
    if seq_counts != {"land_pad": 66, "land_pad2": 20}:
        raise ValueError(f"Sequence counts mismatch: {seq_counts}")
    print(f"[OK] Manifest verified: 86 frames (66 land_pad, 20 land_pad2), SHA={manifest_sha[:16]}...")

    # 2. Protocol verification
    if not PROTOCOL_V1_1_PATH.exists():
        raise FileNotFoundError(f"Protocol v1.1 not found: {PROTOCOL_V1_1_PATH}")
    protocol_sha = sha256_file(PROTOCOL_V1_1_PATH)
    if protocol_sha != EXPECTED_PROTOCOL_V1_1_SHA:
        raise ValueError(f"Protocol v1.1 SHA mismatch: {protocol_sha} != {EXPECTED_PROTOCOL_V1_1_SHA}")
    print(f"[OK] Protocol v1.1 verified: SHA={protocol_sha[:16]}...")

    # 3. Bundle verification & extraction
    bundle_sha = sha256_file(bundle_path)
    if bundle_sha != EXPECTED_BUNDLE_SHA:
        raise ValueError(f"Bundle SHA mismatch: {bundle_sha} != {EXPECTED_BUNDLE_SHA}")
    print(f"[OK] Bundle verified: SHA={bundle_sha[:16]}...")

    # Extract to temp directory
    temp_dir = Path(tempfile.mkdtemp(prefix="phase23_exec_"))
    with zipfile.ZipFile(bundle_path, "r") as archive:
        archive.extractall(temp_dir)
    ckpt_path = temp_dir / "best.pt"
    if not ckpt_path.exists():
        raise FileNotFoundError("best.pt missing from bundle")
    ckpt_sha = sha256_file(ckpt_path)
    if ckpt_sha != EXPECTED_CKPT_SHA:
        raise ValueError(f"Checkpoint SHA mismatch: {ckpt_sha} != {EXPECTED_CKPT_SHA}")
    print(f"[OK] Checkpoint verified: SHA={ckpt_sha[:16]}...")

    # 4. Check clean image and label existence
    clean_images_dir = stress_root / "clean" / "images" / "test"
    clean_labels_dir = stress_root / "clean" / "labels" / "test"
    for r in manifest_rows:
        img_p = clean_images_dir / r["image"]
        lbl_p = clean_labels_dir / r["label"]
        if not img_p.exists():
            raise FileNotFoundError(f"Missing clean image: {img_p}")
        if not lbl_p.exists():
            raise FileNotFoundError(f"Missing clean label: {lbl_p}")
    print(f"[OK] All 86 clean images and labels present in {stress_root}")
    print("[OK] ALL PART 4 GATES PASSED\n")

    return manifest_rows, ckpt_path


def run_zero_dose_baseline_gate(
    model: YOLO,
    stress_root: Path,
    out_dir: Path,
) -> dict[str, float]:
    """Execute Part 5 zero-dose baseline gate."""
    print("=" * 70)
    print("PART 5: ZERO-DOSE BASELINE GATE")
    print("=" * 70)

    cond_dir = stress_root / "clean"
    temp_yaml = out_dir / "clean_gate.yaml"
    temp_yaml.write_text(
        f"path: {cond_dir.resolve()}\n"
        f"train: images/test\n"
        f"val: images/test\n"
        f"test: images/test\n"
        f"names:\n  0: landing_pad\n",
        encoding="utf-8",
    )

    val_res = model.val(
        data=str(temp_yaml),
        split="test",
        imgsz=IMGSZ,
        conf=CONF,
        iou=IOU,
        max_det=MAX_DET,
        batch=BATCH,
        device=DEVICE,
        verbose=False,
        plots=False,
        project=str(out_dir / "val_output"),
        name="zero_dose_gate",
        exist_ok=True,
    )

    observed = {
        "precision": float(val_res.box.mp),
        "recall": float(val_res.box.mr),
        "map50": float(val_res.box.map50),
        "map50_95": float(val_res.box.map),
    }

    print("\nComparing zero-dose against historical Phase 23 clean baseline:")
    all_passed = True
    gate_records = {}
    for metric, hist_val in HISTORICAL_CLEAN_METRICS.items():
        obs_val = observed[metric]
        delta = abs(obs_val - hist_val)
        passed = delta <= GATE_TOLERANCE
        if not passed:
            all_passed = False
        status_str = "[PASS]" if passed else "[FAIL]"
        print(f"  {metric:<10}: observed={obs_val:.6f} | historical={hist_val:.6f} | delta={delta:.6e} {status_str}")
        gate_records[metric] = {
            "observed": obs_val,
            "historical": hist_val,
            "delta": delta,
            "passed": passed,
        }

    if not all_passed:
        gate_file = out_dir / "zero_dose_gate_FAILED.json"
        gate_file.write_text(json.dumps(gate_records, indent=2), encoding="utf-8")
        raise RuntimeError(f"ZERO-DOSE BASELINE GATE FAILED! Gate saved to {gate_file}")

    print("\n[OK] ZERO-DOSE BASELINE GATE PASSED (all deltas <= 0.001)\n")
    return observed


def generate_treatment_dataset(
    manifest_rows: list[dict[str, str]],
    stress_root: Path,
    out_dir: Path,
) -> list[dict[str, object]]:
    """Execute Part 6 deterministic treatment dataset generation."""
    print("=" * 70)
    print("PART 6: GENERATE FINAL TREATMENT DATASET")
    print("=" * 70)

    clean_img_dir = stress_root / "clean" / "images" / "test"
    clean_lbl_dir = stress_root / "clean" / "labels" / "test"
    images_out_dir = out_dir / "images"
    images_out_dir.mkdir(parents=True, exist_ok=True)

    treatment_rows = []
    total_views = len(manifest_rows) * len(TOPOLOGIES) * len(DEFAULT_DOSES)
    count = 0

    print(f"Generating {total_views} treatment images with atomic writes...")

    for row in manifest_rows:
        frame_id = row["image"]
        sequence = row["sequence"]
        img_path = clean_img_dir / frame_id
        lbl_path = clean_lbl_dir / row["label"]

        source_sha = sha256_file(img_path)
        img = Image.open(img_path).convert("RGB")
        img_w, img_h = img.size

        labels = read_yolo_boxes(lbl_path, class_id=0)
        if not labels:
            raise ValueError(f"No ground truth label for {frame_id}")
        target = max(labels, key=lambda b: b.width * b.height)
        target_yolo = YoloBox(
            class_id=target.class_id,
            x_center=target.x_center,
            y_center=target.y_center,
            width=target.width,
            height=target.height,
        )

        for topo in TOPOLOGIES:
            for dose in DEFAULT_DOSES:
                count += 1
                if count % 500 == 0 or count == total_views:
                    print(f"  Generated {count}/{total_views} views...")

                dose_str = f"{dose:.2f}".replace(".", "p")
                out_name = f"{Path(frame_id).stem}__{topo}__{dose_str}.jpg"
                out_path = images_out_dir / out_name

                rng = _rng_for(Path(frame_id).stem, topo, dose)

                if dose <= 0.0:
                    mask = np.zeros((img_h, img_w), dtype=np.uint8)
                    achieved_dose = 0.0
                    mask_px = 0
                    box_px = int(round(target_yolo.width * img_w * target_yolo.height * img_h))
                    dose_error = 0.0
                    if out_path.exists():
                        gen_sha = sha256_file(out_path)
                    else:
                        gen_sha = atomic_write_image(img, out_path)
                else:
                    mask = MASK_GENERATORS[topo](img_w, img_h, target_yolo, dose, rng)
                    achieved_dose, mask_px, box_px = compute_achieved_dose(mask, target_yolo, img_w, img_h)
                    dose_error = abs(achieved_dose - dose)
                    if out_path.exists():
                        gen_sha = sha256_file(out_path)
                    else:
                        occluded = apply_mask(img, mask)
                        gen_sha = atomic_write_image(occluded, out_path)

                # Decode validation
                with Image.open(out_path) as verify_img:
                    verify_img.verify()

                treatment_rows.append({
                    "frame_id": frame_id,
                    "sequence": sequence,
                    "topology": topo,
                    "requested_dose": dose,
                    "achieved_dose": round(achieved_dose, 6),
                    "dose_error": round(dose_error, 6),
                    "mask_pixels": mask_px,
                    "box_pixels": box_px,
                    "visible_box_fraction": round(1.0 - achieved_dose, 6),
                    "image_path": str(out_path.resolve()),
                    "label_path": str(lbl_path.resolve()),
                    "source_image_sha256": source_sha,
                    "generated_image_sha256": gen_sha,
                })

    print(f"[OK] Generated and validated {len(treatment_rows)} treatment images\n")
    return treatment_rows


def run_treatment_inference(
    model: YOLO,
    treatment_rows: list[dict[str, object]],
    out_dir: Path,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Execute Part 7 Phase 23 inference across all treatment views in safe chunks."""
    print("=" * 70)
    print("PART 7: RUN PHASE 23 INFERENCE")
    print("=" * 70)

    CHUNK_SIZE = 86  # Chunk size fits cleanly in GPU memory
    print(f"Running inference on {len(treatment_rows)} images in chunks of {CHUNK_SIZE} (batch={BATCH}, device={DEVICE})...")

    final_views = []
    raw_predictions = []

    for i in range(0, len(treatment_rows), CHUNK_SIZE):
        chunk_recs = treatment_rows[i : i + CHUNK_SIZE]
        chunk_paths = [r["image_path"] for r in chunk_recs]

        if (i // CHUNK_SIZE) % 5 == 0 or i + CHUNK_SIZE >= len(treatment_rows):
            print(f"  Inference progress: {min(i + CHUNK_SIZE, len(treatment_rows))}/{len(treatment_rows)} views...")

        results = model.predict(
            source=chunk_paths,
            imgsz=IMGSZ,
            conf=CONF,
            iou=IOU,
            max_det=MAX_DET,
            batch=BATCH,
            device=DEVICE,
            verbose=False,
            stream=False,
        )

        for rec, res in zip(chunk_recs, results, strict=True):
            lbl_path = Path(rec["label_path"])
            labels = read_yolo_boxes(lbl_path, class_id=0)
            gt = [box_from_yolo(b.class_id, b.x_center, b.y_center, b.width, b.height) for b in labels]
            preds = _normalized_predictions(res)

            f_vals, b_rows = frame_metrics(gt, preds, iou_threshold=MATCH_IOU)

            view_row = {
                **rec,
                "pred_count": f_vals["detection_count"],
                "best_iou": round(float(f_vals["best_iou"]), 6),
                "best_confidence": round(float(f_vals["best_confidence_any"]), 6) if f_vals["best_confidence_any"] is not None else 0.0,
                "tp": f_vals["tp"],
                "fp": f_vals["fp"],
                "fn": f_vals["fn"],
                "frame_success": f_vals["frame_success"],
            }
            final_views.append(view_row)

            for b in b_rows:
                raw_predictions.append({
                    "frame_id": rec["frame_id"],
                    "sequence": rec["sequence"],
                    "topology": rec["topology"],
                    "requested_dose": rec["requested_dose"],
                    "achieved_dose": rec["achieved_dose"],
                    **b,
                })

    print(f"[OK] Inference complete for {len(final_views)} views")
    print(f"[OK] Collected {len(raw_predictions)} raw prediction boxes\n")

    return final_views, raw_predictions


def save_artifacts(
    final_views: list[dict[str, object]],
    raw_predictions: list[dict[str, object]],
    zero_dose_gate_metrics: dict[str, float],
    out_dir: Path,
) -> None:
    """Save all Part 7 output artifacts."""
    print("=" * 70)
    print("SAVING FINAL DATASET ARTIFACTS")
    print("=" * 70)

    # 1. Primary topology views CSV
    csv_path = out_dir / "topology_views.csv"
    fieldnames = [
        "frame_id", "sequence", "topology", "requested_dose", "achieved_dose",
        "dose_error", "mask_pixels", "box_pixels", "visible_box_fraction",
        "source_image_sha256", "generated_image_sha256",
        "pred_count", "best_iou", "best_confidence", "tp", "fp", "fn", "frame_success",
    ]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in final_views:
            writer.writerow(r)
    csv_sha = sha256_file(csv_path)
    print(f"Saved {len(final_views)} rows to {csv_path}")
    print(f"  topology_views.csv SHA-256: {csv_sha}")

    # 2. Raw predictions CSV
    raw_path = out_dir / "raw_predictions.csv"
    if raw_predictions:
        raw_fields = list(raw_predictions[0].keys())
        with open(raw_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=raw_fields)
            writer.writeheader()
            for r in raw_predictions:
                writer.writerow(r)
        raw_sha = sha256_file(raw_path)
        print(f"Saved {len(raw_predictions)} raw predictions to {raw_path}")
        print(f"  raw_predictions.csv SHA-256: {raw_sha}")

    # 3. Gate verification record
    gate_record_path = out_dir / "zero_dose_gate_record.json"
    gate_record_path.write_text(
        json.dumps({
            "status": "PASS",
            "historical_baseline": HISTORICAL_CLEAN_METRICS,
            "zero_dose_observed": zero_dose_gate_metrics,
            "tolerance": GATE_TOLERANCE,
            "checkpoint_sha256": EXPECTED_CKPT_SHA,
            "manifest_sha256": EXPECTED_MANIFEST_SHA,
            "protocol_v1_1_sha256": EXPECTED_PROTOCOL_V1_1_SHA,
        }, indent=2),
        encoding="utf-8",
    )
    print(f"Saved zero-dose gate record to {gate_record_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 23 Occlusion Topology Experiment Runner")
    parser.add_argument("--manifest", type=Path, default=Path("results/phase25_failure_atlas/protected_test_manifest.csv"))
    parser.add_argument("--bundle", type=Path, default=Path("data/external/phase25_inputs/phase23_recovery_bundle.zip"))
    parser.add_argument("--stress-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=Path("results/phase25_occlusion_topology"))
    args = parser.parse_args()

    # Part 4: Verify inputs
    manifest_rows, ckpt_path = verify_inputs(args.manifest, args.bundle, args.stress_root)

    # Load model
    print(f"Loading YOLO model from {ckpt_path}...")
    model = YOLO(str(ckpt_path))

    # Part 5: Zero-dose baseline gate
    zero_dose_metrics = run_zero_dose_baseline_gate(model, args.stress_root, args.out_dir)

    # Part 6: Generate final treatment images
    treatment_rows = generate_treatment_dataset(manifest_rows, args.stress_root, args.out_dir)

    # Part 7: Run inference
    final_views, raw_predictions = run_treatment_inference(model, treatment_rows, args.out_dir)

    # Save artifacts
    save_artifacts(final_views, raw_predictions, zero_dose_metrics, args.out_dir)

    print("\n" + "=" * 70)
    print("PHASE 23 TREATMENT INFERENCE COMPLETE AND VERIFIED!")
    print("=" * 70)


if __name__ == "__main__":
    main()
