#!/usr/bin/env python3
"""Clean-room reproduction of published Phase 22 baseline metrics from GitHub Release bundle.

This script:
1. Downloads the Phase 22 recovery bundle from GitHub Releases into an isolated temporary directory
   (or uses a local bundle if specified).
2. Verifies the bundle SHA-256 and extracted best.pt SHA-256.
3. Verifies the 86 protected frames and 516 test views across 6 conditions.
4. Evaluates the recovered model under locked baseline inference parameters:
   imgsz=320, conf=0.001, iou=0.7, max_det=300, device="cpu", split="test".
5. Compares generated metrics against frozen published baseline metrics at full floating-point precision.
6. Writes a machine-readable reproduction record to results/phase22_reproduction_record.json.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import zipfile

from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_BUNDLE_SHA = "8d6eda7f8775ad899be7a8b6fbf9e6dea30678c1e28c0b687a88184ac592288b"
EXPECTED_CKPT_SHA = "3a1801b192d624f8dcdda4bc5d9a9157309000df67a4c30d62368c37901feddd"
EXPECTED_MANIFEST_SHA = "8605cf1cbf9e8769c0324bf066078f9964f232ac3128131c8bd0b689bb7b64b7"
ORIGINAL_COMMIT = "b569da0012e4ed74c420cbbd15e25665c9850c48"
ORIGINAL_RUN_ID = 34932763449
ORIGINAL_ARTIFACT_ID = 10382104202
RELEASE_TAG = "phase22-baseline-recovery"
CONDITIONS = ("clean", "blur", "low_light", "noise", "occlusion", "mixed")
METRIC_TOLERANCE = 0.001

HISTORICAL_BASELINE_METRICS: dict[str, dict[str, float]] = {
    "clean": {
        "precision": 0.7959713659654185,
        "recall": 0.38372093023255816,
        "map50": 0.42662686781189296,
        "map50_95": 0.2723431563204893,
    },
    "blur": {
        "precision": 0.844025849453299,
        "recall": 0.3776091257554052,
        "map50": 0.41259081580238444,
        "map50_95": 0.2713619580753786,
    },
    "low_light": {
        "precision": 0.7873428115173574,
        "recall": 0.37209302325581395,
        "map50": 0.4168491381871624,
        "map50_95": 0.26933549557019915,
    },
    "noise": {
        "precision": 0.8952635995807745,
        "recall": 0.39761818191484805,
        "map50": 0.4325832723899842,
        "map50_95": 0.26222127375601156,
    },
    "occlusion": {
        "precision": 0.6220251020484491,
        "recall": 0.32558139534883723,
        "map50": 0.34796444264077564,
        "map50_95": 0.16615077551738822,
    },
    "mixed": {
        "precision": 0.597270820474317,
        "recall": 0.18604651162790697,
        "map50": 0.1848519064761554,
        "map50_95": 0.08068148717707323,
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_inputs(manifest_path: Path, stress_root: Path) -> dict[str, object]:
    """Verify the protected test manifest and all 516 stress test views."""
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Protected manifest missing: {manifest_path}")

    actual_manifest_sha = sha256_file(manifest_path)
    if actual_manifest_sha != EXPECTED_MANIFEST_SHA:
        raise ValueError(
            f"Manifest SHA mismatch! Expected {EXPECTED_MANIFEST_SHA}, got {actual_manifest_sha}"
        )

    with manifest_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        manifest_frames = [row["image"] for row in reader]

    if len(manifest_frames) != 86:
        raise ValueError(f"Expected 86 protected frames, found {len(manifest_frames)}")

    frame_set = set(manifest_frames)
    condition_counts: dict[str, int] = {}
    for c in CONDITIONS:
        img_dir = stress_root / c / "images" / "test"
        lbl_dir = stress_root / c / "labels" / "test"
        if not img_dir.is_dir() or not lbl_dir.is_dir():
            raise FileNotFoundError(f"Missing images/labels for condition: {c} at {stress_root / c}")

        imgs = {p.name for p in img_dir.glob("*.jpg")}
        lbls = {p.name for p in lbl_dir.glob("*.txt")}

        if imgs != frame_set:
            missing = frame_set - imgs
            extra = imgs - frame_set
            raise ValueError(f"Condition {c} images mismatch manifest. Missing: {len(missing)}, Extra: {len(extra)}")

        expected_lbls = {f"{Path(f).stem}.txt" for f in frame_set}
        if lbls != expected_lbls:
            missing = expected_lbls - lbls
            raise ValueError(f"Condition {c} labels mismatch manifest. Missing: {len(missing)}")

        condition_counts[c] = len(imgs)

    total_views = sum(condition_counts.values())
    if total_views != 516:
        raise ValueError(f"Expected 516 views across 6 conditions, got {total_views}")

    return {
        "status": "PASS",
        "manifest_sha256": actual_manifest_sha,
        "frames": len(frame_set),
        "conditions": list(CONDITIONS),
        "views": total_views,
    }


def download_and_extract_bundle(
    temp_dir: Path, local_bundle: Path | None = None
) -> tuple[Path, str, str, dict[str, object]]:
    """Download the release bundle via GitHub CLI or local copy, and extract to isolated directory."""
    bundle_filename = "phase22_recovery_bundle.zip"
    bundle_path = temp_dir / bundle_filename

    if local_bundle and local_bundle.is_file():
        print(f"Using local recovery bundle: {local_bundle}")
        bundle_path.write_bytes(local_bundle.read_bytes())
    else:
        print(f"Downloading release bundle '{bundle_filename}' from release '{RELEASE_TAG}'...")
        subprocess.run(
            ["gh", "release", "download", RELEASE_TAG, "-p", bundle_filename, "-D", str(temp_dir)],
            check=True,
            capture_output=True,
            text=True,
        )

    if not bundle_path.is_file():
        raise FileNotFoundError(f"Bundle not found: {bundle_path}")

    actual_bundle_sha = sha256_file(bundle_path)
    if actual_bundle_sha != EXPECTED_BUNDLE_SHA:
        raise ValueError(
            f"Bundle SHA mismatch! Expected {EXPECTED_BUNDLE_SHA}, got {actual_bundle_sha}"
        )
    print(f"  Bundle SHA verified: {actual_bundle_sha}")

    extracted_dir = temp_dir / "extracted"
    with zipfile.ZipFile(bundle_path, "r") as archive:
        archive.extractall(extracted_dir)

    ckpt_path = extracted_dir / "best.pt"
    if not ckpt_path.is_file():
        raise FileNotFoundError("Extracted bundle does not contain best.pt")

    actual_ckpt_sha = sha256_file(ckpt_path)
    if actual_ckpt_sha != EXPECTED_CKPT_SHA:
        raise ValueError(
            f"Checkpoint SHA mismatch! Expected {EXPECTED_CKPT_SHA}, got {actual_ckpt_sha}"
        )
    print(f"  Checkpoint SHA verified: {actual_ckpt_sha}")

    manifest_file = extracted_dir / "recovery_manifest.json"
    manifest_data = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.is_file() else {}

    return ckpt_path, actual_bundle_sha, actual_ckpt_sha, manifest_data


def evaluate_model(
    ckpt_path: Path, stress_root: Path, temp_dir: Path
) -> dict[str, dict[str, float]]:
    """Run baseline evaluation across all 6 conditions using recovered Phase 22 model."""
    print(f"Loading recovered model from isolated path: {ckpt_path}")
    model = YOLO(str(ckpt_path))

    generated_metrics: dict[str, dict[str, float]] = {}

    for condition in CONDITIONS:
        cond_dir = stress_root / condition
        yaml_path = temp_dir / f"{condition}.yaml"
        yaml_path.write_text(
            f"path: {cond_dir.resolve()}\n"
            f"train: images/test\n"
            f"val: images/test\n"
            f"test: images/test\n"
            f"names:\n  0: landing_pad\n",
            encoding="utf-8",
        )

        val_results = model.val(
            data=str(yaml_path),
            split="test",
            imgsz=320,
            conf=0.001,
            iou=0.7,
            max_det=300,
            batch=16,
            device="cpu",
            verbose=False,
            plots=False,
            project=str(temp_dir / "val_output"),
            name=condition,
            exist_ok=True,
        )

        p = float(val_results.box.mp)
        r = float(val_results.box.mr)
        map50 = float(val_results.box.map50)
        map95 = float(val_results.box.map)

        generated_metrics[condition] = {
            "precision": p,
            "recall": r,
            "map50": map50,
            "map50_95": map95,
        }
        print(f"  [{condition.upper():9s}] P={p:.6f} | R={r:.6f} | mAP50={map50:.6f} | mAP50-95={map95:.6f}")

    return generated_metrics


def reconcile(
    generated: dict[str, dict[str, float]],
    historical: dict[str, dict[str, float]],
) -> tuple[dict[str, dict[str, float]], int, float, bool]:
    """Compare generated vs historical metrics cell by cell at full precision."""
    deltas: dict[str, dict[str, float]] = {}
    matched_cells = 0
    max_abs_delta = 0.0
    all_passed = True

    metric_keys = ("precision", "recall", "map50", "map50_95")

    for c in CONDITIONS:
        deltas[c] = {}
        for m in metric_keys:
            gen_val = generated[c][m]
            hist_val = historical[c][m]
            d = gen_val - hist_val
            deltas[c][m] = d
            abs_d = abs(d)
            if abs_d > max_abs_delta:
                max_abs_delta = abs_d
            if abs_d <= METRIC_TOLERANCE:
                matched_cells += 1
            else:
                all_passed = False

    return deltas, matched_cells, max_abs_delta, all_passed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "results/phase25_failure_atlas/protected_test_manifest.csv",
    )
    default_stress = ROOT / "data/derived/kios_real_stress"
    if not default_stress.exists():
        fallback = Path(r"C:\Users\suhas\Documents\Codex\2026-09-12\go-x20\work\repos\uav-safety-research\data\derived\kios_real_stress")
        if fallback.exists():
            default_stress = fallback
    parser.add_argument(
        "--stress-root",
        type=Path,
        default=default_stress,
    )
    parser.add_argument(
        "--bundle",
        type=Path,
        default=ROOT / "data/external/phase25_inputs/phase22_recovery_bundle.zip",
        help="Optional local recovery bundle path (falls back to GitHub Release if missing)",
    )
    parser.add_argument(
        "--output-record",
        type=Path,
        default=ROOT / "results/phase22_reproduction_record.json",
    )
    args = parser.parse_args()

    print("=== Step 1: Clean Recovery from GitHub Release / Bundle ===")
    local_bundle = args.bundle if args.bundle and args.bundle.is_file() else None
    with tempfile.TemporaryDirectory(prefix="phase22-clean-reproduction-") as temp_dir:
        temp_path = Path(temp_dir)

        ckpt_path, bundle_sha, ckpt_sha, manifest_data = download_and_extract_bundle(temp_path, local_bundle)

        print("\n=== Step 2: Verify Protected Test Dataset ===")
        dataset_info = verify_inputs(args.manifest, args.stress_root)
        print("  Dataset verified: 86 frames, 6 conditions, 516 views")
        print(f"  Manifest SHA-256: {dataset_info['manifest_sha256']}")

        print("\n=== Step 3: Run Original Baseline Aggregate Evaluation ===")
        generated_metrics = evaluate_model(ckpt_path, args.stress_root, temp_path)

    print("\n=== Step 4: Reconcile Against Published Phase 22 Baseline Results ===")
    deltas, matched_cells, max_abs_delta, all_passed = reconcile(generated_metrics, HISTORICAL_BASELINE_METRICS)

    print("\n--- 24-Cell Delta Table ---")
    print(f"{'Condition':12s} | {'P delta':14s} | {'R delta':14s} | {'mAP50 delta':14s} | {'mAP50-95 delta':14s}")
    print("-" * 74)
    for c in CONDITIONS:
        p_d = deltas[c]["precision"]
        r_d = deltas[c]["recall"]
        m50_d = deltas[c]["map50"]
        m95_d = deltas[c]["map50_95"]
        print(f"{c:12s} | {p_d:+14.10e} | {r_d:+14.10e} | {m50_d:+14.10e} | {m95_d:+14.10e}")

    print("-" * 74)
    print(f"Cells matched: {matched_cells} / 24")
    print(f"Maximum absolute delta: {max_abs_delta:.10e}")
    status = "PASS" if all_passed and matched_cells == 24 else "FAIL"
    print(f"Reproduction Status: {status}")

    print("\n=== Step 5: Save Machine-Readable Reproduction Record ===")
    record: dict[str, object] = {
        "status": status,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "release_tag": RELEASE_TAG,
        "bundle_sha256": bundle_sha,
        "checkpoint_sha256": ckpt_sha,
        "original_commit": ORIGINAL_COMMIT,
        "github_actions": {
            "workflow": ".github/workflows/real-detector-baseline.yml",
            "workflow_run_id": ORIGINAL_RUN_ID,
            "artifact_id": ORIGINAL_ARTIFACT_ID,
            "artifact_name": "kios-real-detector-baseline",
            "artifact_zip_sha256": "7080c8243c1d7cb85a63f81ea0531eda34dd1f18616f7b4dfdc869a2379c9833",
        },
        "runtime": {
            "python_version": platform.python_version(),
            "ultralytics_version": importlib.metadata.version("ultralytics"),
            "torch_version": importlib.metadata.version("torch"),
            "numpy_version": importlib.metadata.version("numpy"),
            "pillow_version": importlib.metadata.version("pillow"),
        },
        "dataset": {
            "manifest_path": str(args.manifest),
            "manifest_sha256": dataset_info["manifest_sha256"],
            "frames": dataset_info["frames"],
            "conditions": dataset_info["conditions"],
            "views": dataset_info["views"],
        },
        "evaluation_settings": {
            "imgsz": 320,
            "conf": 0.001,
            "iou": 0.7,
            "max_det": 300,
            "batch": 16,
            "device": "cpu",
            "split": "test",
            "metric_tolerance": METRIC_TOLERANCE,
        },
        "generated_metrics": generated_metrics,
        "historical_metrics": HISTORICAL_BASELINE_METRICS,
        "deltas": deltas,
        "cells_matched": matched_cells,
        "total_cells": 24,
        "max_absolute_delta": max_abs_delta,
        "reproduction_passed": all_passed,
    }

    args.output_record.parent.mkdir(parents=True, exist_ok=True)
    args.output_record.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"Reproduction record saved: {args.output_record}")

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
