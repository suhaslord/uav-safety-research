"""Phase 23 Occlusion Topology Experiment Runner.

Two modes:
  --dry-run   Generate masks, compute achieved doses, write CSV with empty
              prediction columns. Does NOT run model inference or write images.
  --execute   Generate images, run Phase 23 inference, fill prediction columns,
              compute frame_success, and run dose-response analysis.

              *** NOT YET AUTHORIZED — requires handoff approval ***

The script downloads and verifies the Phase 23 checkpoint from the GitHub
Release before any inference. All inference settings are locked in the
frozen protocol.

Usage:
    python scripts/run_occlusion_topology_experiment.py --dry-run \\
        --stress-root <path_to_kios_real_stress>

    python scripts/run_occlusion_topology_experiment.py --execute \\
        --stress-root <path_to_kios_real_stress>
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Constants from frozen protocol
# ---------------------------------------------------------------------------
PROTOCOL_PATH = Path("docs/phase25_phase23_occlusion_topology_protocol.json")
MANIFEST_PATH = Path("results/phase25_failure_atlas/protected_test_manifest.csv")
OUTPUT_DIR = Path("results/phase25_occlusion_topology")

EXPECTED_CKPT_SHA = "43240be969708c32b3e11340c9846b3a588baf361378398677c794d16a455310"
EXPECTED_BUNDLE_SHA = "a55531930988deeadf81853d00b63c7e589c6b7fd2270f57653abdb5cdd3e55d"
RELEASE_TAG = "phase23-checkpoint-recovery"
BUNDLE_NAME = "phase23_recovery_bundle.zip"

MANIFEST_SHA = "8605cf1cbf9e8769c0324bf066078f9964f232ac3128131c8bd0b689bb7b64b7"

# Inference settings (locked)
IMGSZ = 480
CONF = 0.001
IOU = 0.7
MAX_DET = 300
BATCH = 16
DEVICE = "0"

# Evaluation settings
MATCH_IOU = 0.50
CLASS_ID = 0


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_protocol() -> dict[str, Any]:
    """Load and verify the frozen protocol."""
    if not PROTOCOL_PATH.exists():
        raise FileNotFoundError(f"Protocol not found: {PROTOCOL_PATH}")
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol["status"] != "frozen":
        raise ValueError("Protocol is not frozen")
    if protocol["part_08_model_lock"]["checkpoint_sha256"] != EXPECTED_CKPT_SHA:
        raise ValueError("Protocol checkpoint SHA mismatch")
    print(f"[OK] Protocol loaded and verified: {protocol['protocol_name']}")
    return protocol


def verify_manifest() -> None:
    """Verify the protected test manifest."""
    actual = sha256_file(MANIFEST_PATH)
    if actual != MANIFEST_SHA:
        raise ValueError(f"Manifest SHA mismatch: {actual} != {MANIFEST_SHA}")
    with open(MANIFEST_PATH, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 86:
        raise ValueError(f"Expected 86 frames, got {len(rows)}")
    print(f"[OK] Manifest verified: {len(rows)} frames, SHA matches")


def download_and_verify_checkpoint(temp_dir: Path) -> Path:
    """Download the checkpoint from GitHub Release and verify SHAs."""
    print(f"\nDownloading bundle from release: {RELEASE_TAG}")
    bundle_path = temp_dir / BUNDLE_NAME
    subprocess.run(
        ["gh", "release", "download", RELEASE_TAG,
         "-p", BUNDLE_NAME,
         "-D", str(temp_dir)],
        check=True,
    )

    # Verify bundle SHA
    bundle_sha = sha256_file(bundle_path)
    if bundle_sha != EXPECTED_BUNDLE_SHA:
        raise ValueError(f"Bundle SHA mismatch: {bundle_sha}")
    print(f"[OK] Bundle SHA verified: {bundle_sha[:16]}...")

    # Extract
    import zipfile
    with zipfile.ZipFile(bundle_path) as zf:
        zf.extractall(temp_dir / "extracted")

    # Find checkpoint
    ckpt_path = temp_dir / "extracted" / "best.pt"
    if not ckpt_path.exists():
        # Search subdirectories
        for p in (temp_dir / "extracted").rglob("best.pt"):
            ckpt_path = p
            break

    if not ckpt_path.exists():
        raise FileNotFoundError("best.pt not found in extracted bundle")

    ckpt_sha = sha256_file(ckpt_path)
    if ckpt_sha != EXPECTED_CKPT_SHA:
        raise ValueError(f"Checkpoint SHA mismatch: {ckpt_sha}")
    print(f"[OK] Checkpoint SHA verified: {ckpt_sha[:16]}...")

    return ckpt_path


def run_dry_run(stress_root: Path) -> None:
    """Run the experiment in dry-run mode (no inference, no images)."""
    # Import generator
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from generate_occlusion_topology import generate_all, write_records_csv

    output_dir = OUTPUT_DIR / "generated"

    print(f"\n{'='*60}")
    print("DRY-RUN MODE")
    print(f"{'='*60}")
    print("  Generating masks and computing achieved doses...")
    print("  NO images will be written")
    print("  NO model inference will be run")
    print()

    records = generate_all(
        manifest_path=MANIFEST_PATH,
        stress_root=stress_root,
        output_dir=output_dir,
        dry_run=True,
    )

    csv_path = OUTPUT_DIR / "topology_views.csv"
    csv_sha = write_records_csv(records, csv_path)

    print(f"\n{'='*60}")
    print("DRY-RUN RESULTS")
    print(f"{'='*60}")
    print(f"  Total views: {len(records)}")
    print(f"  Frames:     {len(set(r.frame_id for r in records))}")
    print(f"  Topologies: {sorted(set(r.topology for r in records))}")
    print(f"  Doses:      {len(set(r.requested_dose for r in records))}")
    print(f"  CSV path:   {csv_path}")
    print(f"  CSV SHA:    {csv_sha}")

    # Dose error summary
    from collections import defaultdict
    errors: dict[str, list[float]] = defaultdict(list)
    for r in records:
        if r.requested_dose > 0:
            errors[r.topology].append(r.dose_error)

    print(f"\nDose error summary (excluding dose=0):")
    for topo in sorted(errors.keys()):
        errs = errors[topo]
        print(f"  {topo:15s}: mean={np.mean(errs):.4f}  "
              f"max={np.max(errs):.4f}  median={np.median(errs):.4f}")

    # Zero-dose check
    zero = [r for r in records if r.requested_dose == 0.0]
    all_identity = all(r.achieved_dose == 0.0 for r in zero)
    print(f"\nZero-dose identity: {'PASS' if all_identity else 'FAIL'}")

    # Prediction fields empty
    all_empty = all(
        r.pred_count == "" and r.best_iou == "" and r.best_confidence == ""
        and r.tp == "" and r.fp == "" and r.fn == "" and r.frame_success == ""
        for r in records
    )
    print(f"Prediction fields empty: {'PASS' if all_empty else 'FAIL'}")

    if not all_identity:
        raise RuntimeError("Zero-dose identity check FAILED")
    if not all_empty:
        raise RuntimeError("Prediction fields not empty in dry-run")

    print(f"\n{'='*60}")
    print("DRY-RUN PASSED -- experiment is ready for execution")
    print(f"{'='*60}")


def run_execute(stress_root: Path) -> None:
    """Run the full experiment with inference.

    NOT YET AUTHORIZED — prints a message and exits.
    """
    print(f"\n{'='*60}")
    print("EXECUTE MODE")
    print(f"{'='*60}")
    print()
    print("*** EXECUTION IS NOT YET AUTHORIZED ***")
    print()
    print("The frozen protocol requires handoff approval before running")
    print("Phase 23 inference on topology-occluded images.")
    print()
    print("To execute, the next agent must:")
    print("  1. Download and verify the Phase 23 checkpoint")
    print("  2. Generate all 5160 occluded images")
    print("  3. Run Phase 23 inference with locked settings")
    print("  4. Compute frame_success for each view")
    print("  5. Run dose-response analysis")
    print("  6. Run statistical tests per protocol")
    print()
    print("Checkpoint SHA-256:")
    print(f"  {EXPECTED_CKPT_SHA}")
    print()
    print("Inference settings:")
    print(f"  imgsz={IMGSZ}, conf={CONF}, iou={IOU}, max_det={MAX_DET}")
    print(f"  device={DEVICE}")
    print(f"{'='*60}")
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 23 Occlusion Topology Experiment Runner",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true",
                      help="Compute dose feasibility without running inference")
    mode.add_argument("--execute", action="store_true",
                      help="Run full experiment with inference (NOT YET AUTHORIZED)")
    parser.add_argument(
        "--stress-root", type=Path, required=True,
        help="Path to kios_real_stress directory",
    )
    args = parser.parse_args()

    # Verify protocol and manifest
    verify_protocol()
    verify_manifest()

    if args.dry_run:
        run_dry_run(args.stress_root)
    elif args.execute:
        run_execute(args.stress_root)


if __name__ == "__main__":
    main()
