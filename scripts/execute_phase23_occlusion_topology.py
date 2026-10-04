"""Lossless v2 execution of the Phase 23 Occlusion Topology Experiment.

Authenticates sources, committed methods and runtime, then generates lossless
treatments. Gates the exact generated zero-dose inventory before treatment
inference. Requires a fresh output directory and never resumes historical runs.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
from io import BytesIO
import json
import math
import os
import platform
import shutil
import sys
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
from PIL import Image
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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
    compute_achieved_dose,
    apply_mask,
)
from phase25_lib import (
    Box,
    box_from_yolo,
    frame_metrics,
    sha256_file,
)
from uav_safety.real_landing_dataset import read_yolo_boxes
from phase25_reconstruction_lock import load_lock, verify_archive, verify_images

# ---------------------------------------------------------------------------
# Locked Constants
# ---------------------------------------------------------------------------
EXPECTED_MANIFEST_SHA = "8605cf1cbf9e8769c0324bf066078f9964f232ac3128131c8bd0b689bb7b64b7"
EXPECTED_BUNDLE_SHA = "a55531930988deeadf81853d00b63c7e589c6b7fd2270f57653abdb5cdd3e55d"
EXPECTED_CKPT_SHA = "43240be969708c32b3e11340c9846b3a588baf361378398677c794d16a455310"
PROTOCOL_V1_1_PATH = REPO_ROOT / "docs/phase25_phase23_occlusion_topology_protocol_v1_1.json"
EXPECTED_PROTOCOL_V1_1_SHA = "b4637e5b9b0c9551ac6a106d20fe8bc62f05d50b7030432c1c4e1bf7cf771a29"
PROTOCOL_V2_PATH = REPO_ROOT / "docs/phase25_topology_lossless_v2_2.json"
EXECUTION_SCHEMA = "aegisland.phase25.topology-lossless.v2.2"
FROZEN_RELEASE_MANIFEST = REPO_ROOT / "results/research_revalidation_2026_10_03/frozen_manifest.json"

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
        if not math.isfinite(float(class_id)) or float(class_id) != int(class_id) or int(class_id) < 0:
            raise ValueError("Invalid prediction class")
        if not math.isfinite(float(score)) or not 0.0 <= float(score) <= 1.0:
            raise ValueError("Invalid prediction confidence")
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
    source_root: Path,
    archive_path: Path,
    checkpoint_dir: Path,
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

    # Extract only the authenticated checkpoint; reject arbitrary archive paths.
    ckpt_path = checkpoint_dir / "best.pt"
    with zipfile.ZipFile(bundle_path, "r") as archive:
        with archive.open("best.pt") as source, ckpt_path.open("wb") as target:
            shutil.copyfileobj(source, target)
    if not ckpt_path.exists():
        raise FileNotFoundError("best.pt missing from bundle")
    ckpt_sha = sha256_file(ckpt_path)
    if ckpt_sha != EXPECTED_CKPT_SHA:
        raise ValueError(f"Checkpoint SHA mismatch: {ckpt_sha} != {EXPECTED_CKPT_SHA}")
    print(f"[OK] Checkpoint verified: SHA={ckpt_sha[:16]}...")

    verify_source_inventory(manifest_rows, source_root, stress_root, archive_path)
    manifest_rows = authenticate_clean_records(manifest_rows, stress_root)
    print("[OK] ALL PART 4 GATES PASSED\n")

    return manifest_rows, ckpt_path


def authenticate_clean_records(rows: list[dict[str, str]], stress: Path) -> list[dict[str, str]]:
    """Bind generation inputs to the frozen clean inventory and label bytes."""
    lock = load_lock()
    inventory = hashlib.sha256()
    authenticated = []
    for row in rows:
        image_sha = sha256_file(stress / "clean/images/test" / row["image"])
        label_bytes = (stress / "clean/labels/test" / row["label"]).read_bytes()
        label_sha = hashlib.sha256(label_bytes).hexdigest()
        normalized = label_bytes.replace(b"\r\n", b"\n")
        accepted = {label_sha, hashlib.sha256(normalized).hexdigest(),
                    hashlib.sha256(normalized.replace(b"\n", b"\r\n")).hexdigest()}
        expected = lock["protected_test_files"][row["image"]]
        if row["label"] != expected["label"] or expected["label_sha256"] not in accepted:
            raise ValueError(f"Clean label changed since authentication: {row['label']}")
        inventory.update(f"{row['image']}:{image_sha}\n".encode())
        authenticated.append({**row, "clean_image_sha256": image_sha, "clean_label_sha256": label_sha})
    if inventory.hexdigest() != lock["condition_image_inventory_sha256"]["clean"]:
        raise ValueError("Clean images changed since authentication")
    return authenticated


def verify_source_inventory(rows: list[dict[str, str]], source: Path, stress: Path, archive: Path) -> None:
    lock = load_lock()
    verify_archive(archive, lock)
    for folder, field in (("images/test", "image"), ("labels/test", "label")):
        if {p.name for p in (source / folder).iterdir() if p.is_file()} != {r[field] for r in rows}:
            raise ValueError(f"Incorrect protected source inventory: {folder}")
    verify_images(rows, source, stress, lock)


def verify_runtime() -> dict[str, str]:
    expected = json.loads((REPO_ROOT / "docs/phase25_input_lock.json").read_text(encoding="utf-8"))["phase25_runtime"]
    observed = {"python_version": platform.python_version(),
                **{f"{name}_version": importlib.metadata.version(name)
                   for name in ("ultralytics", "torch", "numpy", "pillow")}}
    if expected.get("status") != "locked" or any(expected.get(name) != value for name, value in observed.items()):
        raise ValueError(f"Inference runtime mismatch: expected {expected}, observed {observed}")
    return observed


def verify_method_lock() -> dict:
    protocol = json.loads(PROTOCOL_V2_PATH.read_text(encoding="utf-8"))
    if protocol["schema"] != EXECUTION_SCHEMA:
        raise ValueError("Unsupported topology execution protocol")
    methods = protocol["method_text_sha256"]
    required = {"scripts/execute_phase23_occlusion_topology.py", "scripts/generate_occlusion_topology.py",
                "scripts/phase25_lib.py", "scripts/phase25_reconstruction_lock.py",
                "src/uav_safety/real_landing_dataset.py", "scripts/build_real_image_stress_suite.py",
                "scripts/prepare_kios_real_yolo_split.py", "docs/phase25_input_lock.json",
                "docs/phase25_reconstruction_lock.json", str(PROTOCOL_V1_1_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
                str(FROZEN_RELEASE_MANIFEST.relative_to(REPO_ROOT)).replace("\\", "/")}
    if set(methods) != required:
        raise ValueError("Incomplete topology method lock")
    for relative, expected in methods.items():
        actual = hashlib.sha256((REPO_ROOT / relative).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        if actual != expected:
            raise ValueError(f"Topology method changed since freeze: {relative}")
    tracked = [*methods, str(PROTOCOL_V2_PATH.relative_to(REPO_ROOT))]
    subprocess.run(["git", "diff", "--exit-code", "HEAD", "--", *tracked], cwd=REPO_ROOT, check=True,
                   stdout=subprocess.DEVNULL)
    subprocess.run(["git", "ls-files", "--error-unmatch", "--", *tracked], cwd=REPO_ROOT, check=True,
                   stdout=subprocess.DEVNULL)
    return protocol


def require_fresh_output(out_dir: Path) -> None:
    manifest = json.loads(FROZEN_RELEASE_MANIFEST.read_text(encoding="utf-8"))
    protected = {REPO_ROOT / "results/phase25_occlusion_topology"}
    protected.update(REPO_ROOT.joinpath(*Path(relative).parts[:2])
                     for relative in manifest["files_sha256"] if Path(relative).parts[0] == "results")
    resolved = out_dir.resolve()
    if any(resolved == path.resolve() or path.resolve() in resolved.parents for path in protected):
        raise ValueError("The historical topology and frozen release directories are immutable; choose a new output directory")
    if out_dir.exists() and (not out_dir.is_dir() or any(out_dir.iterdir())):
        raise ValueError(f"Output must be a new or empty directory: {out_dir}")


def atomic_write_lossless_image(image: Image.Image, path: Path) -> str:
    if path.exists():
        raise ValueError(f"Refusing to reuse a treatment image: {path}")
    fd, temporary = tempfile.mkstemp(suffix=".png", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            image.save(handle, format="PNG")
            handle.flush()
            os.fsync(handle.fileno())
        with Image.open(temporary) as decoded:
            if not np.array_equal(np.asarray(decoded.convert("RGB")), np.asarray(image.convert("RGB"))):
                raise ValueError("Lossless image failed decoded-pixel identity")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return sha256_file(path)


def run_zero_dose_baseline_gate(
    model: YOLO,
    treatment_rows: list[dict[str, object]],
    out_dir: Path,
) -> dict[str, dict[str, float]]:
    """Compare each generated topology control set to the 86-frame reference.

    Pooling identical controls changes sample-size-dependent confidence-curve
    interpolation in Ultralytics; every gate must retain one view per frame.
    """
    controls = [r for r in treatment_rows if float(r["requested_dose"]) == 0.0]
    if not controls:
        raise ValueError("No generated zero-dose controls")
    expected = {(r["frame_id"], topo) for r in treatment_rows for topo in TOPOLOGIES}
    if len(controls) != len(expected) or {(r["frame_id"], r["topology"]) for r in controls} != expected:
        raise ValueError("Incomplete generated zero-dose inventory")
    observed_by_topology = {}
    gate_records = {}
    for topology in TOPOLOGIES:
        selected = [r for r in controls if r["topology"] == topology]
        cond_dir = out_dir / "zero_dose_gate" / topology
        for row in selected:
            image = Path(row["image_path"])
            if sha256_file(image) != row["generated_image_sha256"]:
                raise ValueError(f"Generated control changed: {image}")
            label_bytes = Path(row["label_path"]).read_bytes()
            if hashlib.sha256(label_bytes).hexdigest() != row["label_sha256"]:
                raise ValueError(f"Generated control label changed: {row['label_path']}")
            destination = cond_dir / "images/test" / image.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.link(image, destination)
            label = cond_dir / "labels/test" / f"{image.stem}.txt"
            label.parent.mkdir(parents=True, exist_ok=True)
            with label.open("xb") as handle:
                handle.write(label_bytes)
        temp_yaml = out_dir / f"clean_gate_{topology}.yaml"
        temp_yaml.write_text(
            f"path: {json.dumps(str(cond_dir.resolve()))}\n"
            "train: images/test\nval: images/test\ntest: images/test\nnames:\n  0: landing_pad\n",
            encoding="utf-8",
        )
        val_res = model.val(
            data=str(temp_yaml), split="test", imgsz=IMGSZ, conf=CONF, iou=IOU,
            max_det=MAX_DET, batch=BATCH, device=DEVICE, verbose=False, plots=False,
            project=str(out_dir / "val_output"), name=f"zero_dose_gate_{topology}", exist_ok=True,
        )
        observed = {"precision": float(val_res.box.mp), "recall": float(val_res.box.mr),
                    "map50": float(val_res.box.map50), "map50_95": float(val_res.box.map)}
        if any(not math.isfinite(value) or not 0.0 <= value <= 1.0 for value in observed.values()):
            raise RuntimeError(f"Zero-dose gate produced invalid aggregate metrics for {topology}")
        observed_by_topology[topology] = observed
        gate_records[topology] = {
            metric: {"observed": observed[metric], "historical": historical,
                     "delta": abs(observed[metric] - historical),
                     "passed": abs(observed[metric] - historical) <= GATE_TOLERANCE}
            for metric, historical in HISTORICAL_CLEAN_METRICS.items()
        }
        if not all(record["passed"] for record in gate_records[topology].values()):
            gate_file = out_dir / "zero_dose_gate_FAILED.json"
            gate_file.write_text(json.dumps(gate_records, indent=2), encoding="utf-8")
            raise RuntimeError(f"ZERO-DOSE BASELINE GATE FAILED for {topology}! Gate saved to {gate_file}")
        print(f"[OK] {topology}: {len(selected)} generated zero-dose controls passed (all deltas <= 0.001)")
    return observed_by_topology


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
    labels_out_dir = out_dir / "labels"
    labels_out_dir.mkdir(parents=True, exist_ok=True)

    treatment_rows = []
    total_views = len(manifest_rows) * len(TOPOLOGIES) * len(DEFAULT_DOSES)
    count = 0

    print(f"Generating {total_views} treatment images with atomic writes...")

    for row in manifest_rows:
        frame_id = row["image"]
        sequence = row["sequence"]
        img_path = clean_img_dir / frame_id
        lbl_path = clean_lbl_dir / row["label"]

        image_bytes = img_path.read_bytes()
        source_sha = hashlib.sha256(image_bytes).hexdigest()
        label_bytes = lbl_path.read_bytes()
        label_sha = hashlib.sha256(label_bytes).hexdigest()
        if source_sha != row.get("clean_image_sha256") or label_sha != row.get("clean_label_sha256"):
            raise ValueError(f"Clean input changed since authentication: {frame_id}")
        snapshot_label = labels_out_dir / row["label"]
        with snapshot_label.open("xb") as handle:
            handle.write(label_bytes)
        with Image.open(BytesIO(image_bytes)) as source_image:
            img = source_image.convert("RGB")
        img_w, img_h = img.size

        labels = read_yolo_boxes(snapshot_label, class_id=0)
        if len(labels) != 1:
            raise ValueError(f"The locked topology protocol requires one ground truth target: {frame_id}")
        target = labels[0]
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
                out_name = f"{Path(frame_id).stem}__{topo}__{dose_str}.png"
                out_path = images_out_dir / out_name

                rng = _rng_for(Path(frame_id).stem, topo, dose)

                if dose <= 0.0:
                    mask = np.zeros((img_h, img_w), dtype=np.uint8)
                else:
                    mask = MASK_GENERATORS[topo](img_w, img_h, target_yolo, dose, rng)
                achieved_dose, mask_px, box_px = compute_achieved_dose(mask, target_yolo, img_w, img_h)
                if box_px == 0:
                    raise ValueError(f"Target has no rasterized pixels: {frame_id}")
                dose_error = abs(achieved_dose - dose)
                occluded = apply_mask(img, mask) if dose > 0.0 else img
                gen_sha = atomic_write_lossless_image(occluded, out_path)

                # Decode validation
                with Image.open(out_path) as verify_img:
                    verify_img.verify()

                treatment_rows.append({
                    "frame_id": frame_id,
                    "sequence": sequence,
                    "topology": topo,
                    "requested_dose": dose,
                    "achieved_dose": achieved_dose,
                    "dose_error": dose_error,
                    "mask_pixels": mask_px,
                    "box_pixels": box_px,
                    "visible_box_fraction": 1.0 - achieved_dose,
                    "image_path": str(out_path.resolve()),
                    "label_path": str(snapshot_label.resolve()),
                    "label_sha256": label_sha,
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
        for rec in chunk_recs:
            if sha256_file(Path(rec["image_path"])) != rec["generated_image_sha256"]:
                raise ValueError(f"Treatment image changed after generation: {rec['image_path']}")
            if sha256_file(Path(rec["label_path"])) != rec["label_sha256"]:
                raise ValueError(f"Treatment label changed after verification: {rec['label_path']}")
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
    zero_dose_gate_metrics: dict[str, dict[str, float]],
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
        "label_sha256",
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
    raw_fields = ["frame_id", "sequence", "topology", "requested_dose", "achieved_dose",
                  "prediction_index", "class_id", "x0", "y0", "x1", "y1", "confidence",
                  "matched_gt_index", "match_iou", "is_true_positive"]
    with open(raw_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=raw_fields)
        writer.writeheader()
        writer.writerows(raw_predictions)
    raw_sha = sha256_file(raw_path)
    print(f"Saved {len(raw_predictions)} raw predictions to {raw_path}")
    print(f"  raw_predictions.csv SHA-256: {raw_sha}")

    # 3. Gate verification record
    gate_record_path = out_dir / "zero_dose_gate_record.json"
    gate_record_path.write_text(
        json.dumps({
            "status": "PASS",
            "historical_baseline": HISTORICAL_CLEAN_METRICS,
            "zero_dose_observed_by_topology": zero_dose_gate_metrics,
            "tolerance": GATE_TOLERANCE,
            "checkpoint_sha256": EXPECTED_CKPT_SHA,
            "manifest_sha256": EXPECTED_MANIFEST_SHA,
            "protocol_v1_1_sha256": EXPECTED_PROTOCOL_V1_1_SHA,
            "execution_protocol": EXECUTION_SCHEMA,
            "protocol_v2_sha256": sha256_file(PROTOCOL_V2_PATH),
            "control_dataset": "all generated requested-dose-zero PNGs",
            "control_views": sum(float(r["requested_dose"]) == 0.0 for r in final_views),
            "comparison_unit": "one generated view per protected frame, separately for each topology",
            "control_views_by_topology": {topo: sum(float(r["requested_dose"]) == 0.0 and r["topology"] == topo
                                                     for r in final_views) for topo in TOPOLOGIES},
        }, indent=2),
        encoding="utf-8",
    )
    print(f"Saved zero-dose gate record to {gate_record_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 23 lossless topology v2.2 runner")
    parser.add_argument("--manifest", type=Path, default=REPO_ROOT / "results/phase25_failure_atlas/protected_test_manifest.csv")
    parser.add_argument("--bundle", type=Path, default=REPO_ROOT / "data/external/phase25_inputs/phase23_recovery_bundle.zip")
    parser.add_argument("--stress-root", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True, help="new, empty v2 directory; historical output is protected")
    parser.add_argument("--execute", action="store_true", help="compatibility flag; this command always executes v2.2")
    args = parser.parse_args()

    require_fresh_output(args.out_dir)
    protocol = verify_method_lock()
    execution_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    runtime = verify_runtime()
    os.environ["YOLO_AUTOINSTALL"] = "False"
    from ultralytics import YOLO

    with tempfile.TemporaryDirectory(prefix="phase25_topology_v2_") as checkpoint_dir:
        manifest_rows, ckpt_path = verify_inputs(args.manifest, args.bundle, args.stress_root,
                                                args.source_root, args.archive, Path(checkpoint_dir))
        args.out_dir.mkdir(parents=True, exist_ok=True)
        treatment_rows = generate_treatment_dataset(manifest_rows, args.stress_root, args.out_dir)
        model = YOLO(str(ckpt_path))
        zero_dose_metrics = run_zero_dose_baseline_gate(model, treatment_rows, args.out_dir)
        final_views, raw_predictions = run_treatment_inference(model, treatment_rows, args.out_dir)
        save_artifacts(final_views, raw_predictions, zero_dose_metrics, args.out_dir)
        receipt = {"execution_protocol": protocol["schema"], "runtime": runtime,
                   "git_commit": execution_commit,
                   "protocol_sha256": sha256_file(PROTOCOL_V2_PATH), "method_text_sha256": protocol["method_text_sha256"],
                   "source_archive_sha256": sha256_file(args.archive), "checkpoint_sha256": EXPECTED_CKPT_SHA,
                   "manifest_sha256": sha256_file(args.manifest), "bundle_sha256": sha256_file(args.bundle),
                   "topology_views_sha256": sha256_file(args.out_dir / "topology_views.csv"),
                   "raw_predictions_sha256": sha256_file(args.out_dir / "raw_predictions.csv"),
                   "zero_dose_gate_record_sha256": sha256_file(args.out_dir / "zero_dose_gate_record.json"),
                   "views": len(final_views), "status": "complete"}
        (args.out_dir / "run_manifest.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    print("\n" + "=" * 70)
    print("PHASE 23 TREATMENT INFERENCE COMPLETE AND VERIFIED!")
    print("=" * 70)


if __name__ == "__main__":
    main()
