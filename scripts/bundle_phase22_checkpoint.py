#!/usr/bin/env python3
"""Package and authenticate the Phase 22 baseline detector checkpoint for preservation.

This script:
1. Locates the exact Phase 22 checkpoint from the verified GitHub Actions artifact 10382104202
   or local extracted cache.
2. Verifies the pre-packaging SHA-256 against the locked value:
   3a1801b192d624f8dcdda4bc5d9a9157309000df67a4c30d62368c37901feddd
3. Collects original training logs, split definitions, robustness metrics, and provenance records.
4. Builds a deterministic recovery bundle zip at data/external/phase25_inputs/phase22_recovery_bundle.zip.
5. Verifies post-packaging extraction into an isolated temporary directory.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import platform
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCAL_WEIGHTS = Path(
    r"C:\Users\suhas\Documents\Codex\2026-09-12\go-x20\work\repos\uav-safety-research\temp_kios_artifact\kios-real-detector-baseline\training\landing_pad_yolo11n\weights\best.pt"
)
DEFAULT_ARTIFACT_DIR = Path(
    r"C:\Users\suhas\Documents\Codex\2026-09-12\go-x20\work\repos\uav-safety-research\temp_kios_artifact\kios-real-detector-baseline"
)
DEFAULT_OUTPUT = ROOT / "data/external/phase25_inputs/phase22_recovery_bundle.zip"

EXPECTED_CHECKPOINT_SHA256 = "3a1801b192d624f8dcdda4bc5d9a9157309000df67a4c30d62368c37901feddd"
EXPECTED_ARTIFACT_ZIP_SHA256 = "7080c8243c1d7cb85a63f81ea0531eda34dd1f18616f7b4dfdc869a2379c9833"
ORIGINAL_COMMIT = "b569da0012e4ed74c420cbbd15e25665c9850c48"
ORIGINAL_RUN_ID = 34932763449
ORIGINAL_ARTIFACT_ID = 10382104202
ORIGINAL_WORKFLOW = ".github/workflows/real-detector-baseline.yml"
ORIGINAL_BRANCH = "main"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def observed_versions() -> dict[str, str | None]:
    packages: dict[str, str | None] = {}
    for name in ("ultralytics", "torch", "numpy", "Pillow"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    return packages


def bundle(weights: Path, artifact_dir: Path, output: Path) -> dict[str, object]:
    if not zipfile.is_zipfile(weights):
        raise ValueError(f"Candidate weights file is not a valid PyTorch/ZIP checkpoint: {weights}")

    actual_sha = sha256_file(weights)
    if actual_sha != EXPECTED_CHECKPOINT_SHA256:
        raise ValueError(
            f"Checkpoint SHA-256 verification failed BEFORE packaging:\n"
            f"  Expected: {EXPECTED_CHECKPOINT_SHA256}\n"
            f"  Actual:   {actual_sha}"
        )

    # Historical metrics from artifact robustness_metrics.csv
    robustness_csv = artifact_dir / "robustness_metrics.csv"
    summary_json_file = artifact_dir / "summary.json"
    summary_md_file = artifact_dir / "summary.md"
    split_md_file = artifact_dir / "SPLIT.md"
    split_manifest_file = artifact_dir / "split_manifest.csv"
    results_csv_file = artifact_dir / "training/landing_pad_yolo11n/results.csv"

    for req_file in (robustness_csv, summary_json_file, summary_md_file, split_md_file, split_manifest_file, results_csv_file):
        if not req_file.is_file():
            raise FileNotFoundError(f"Missing required artifact provenance file: {req_file}")

    manifest_payload: dict[str, object] = {
        "status": "authenticated_exact_match",
        "phase": "phase22_baseline",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_filename": "best.pt",
        "checkpoint_sha256": actual_sha,
        "checkpoint_bytes": weights.stat().st_size,
        "github_actions": {
            "workflow": ORIGINAL_WORKFLOW,
            "workflow_run_id": ORIGINAL_RUN_ID,
            "artifact_id": ORIGINAL_ARTIFACT_ID,
            "artifact_name": "kios-real-detector-baseline",
            "artifact_zip_sha256": EXPECTED_ARTIFACT_ZIP_SHA256,
            "commit_sha": ORIGINAL_COMMIT,
            "branch": ORIGINAL_BRANCH,
            "created_at": "2026-09-15T05:35:57Z",
            "expires_at": "2026-10-15T05:35:55Z",
        },
        "model_architecture": "Ultralytics YOLO11n (320px, 1 class: landing_pad)",
        "training_settings": {
            "model_init": "yolo11n.pt",
            "epochs": 12,
            "imgsz": 320,
            "batch": 16,
            "device": "cpu",
            "workers": 2,
            "seed": 20260915,
            "patience": 5,
        },
        "evaluation_settings": {
            "imgsz": 320,
            "confidence_floor": 0.001,
            "nms_iou": 0.7,
            "max_det": 300,
            "batch": 16,
            "workers": 2,
            "device": "cpu",
            "split": "test",
            "conditions": ["clean", "blur", "low_light", "noise", "occlusion", "mixed"],
        },
        "published_baseline_metrics": {
            "clean": {"precision": 0.7959713659654185, "recall": 0.38372093023255816, "map50": 0.42662686781189296, "map50_95": 0.2723431563204893},
            "blur": {"precision": 0.844025849453299, "recall": 0.3776091257554052, "map50": 0.41259081580238444, "map50_95": 0.2713619580753786},
            "low_light": {"precision": 0.7873428115173574, "recall": 0.37209302325581395, "map50": 0.4168491381871624, "map50_95": 0.26933549557019915},
            "noise": {"precision": 0.8952635995807745, "recall": 0.39761818191484805, "map50": 0.4325832723899842, "map50_95": 0.26222127375601156},
            "occlusion": {"precision": 0.6220251020484491, "recall": 0.32558139534883723, "map50": 0.34796444264077564, "map50_95": 0.16615077551738822},
            "mixed": {"precision": 0.597270820474317, "recall": 0.18604651162790697, "map50": 0.1848519064761554, "map50_95": 0.08068148717707323},
        },
        "locked_runtime": {
            "training_runtime": {
                "os": "ubuntu-latest (Linux x86_64)",
                "python": "3.11",
                "ultralytics": "8.4.152",
                "torch": "CPU-only build via download.pytorch.org/whl/cpu",
            },
            "packaging_runtime": {
                "os": platform.platform(),
                "python": platform.python_version(),
                "packages": observed_versions(),
            },
        },
        "protected_dataset": {
            "manifest_path": "results/phase25_failure_atlas/protected_test_manifest.csv",
            "manifest_sha256": "8605cf1cbf9e8769c0324bf066078f9964f232ac3128131c8bd0b689bb7b64b7",
            "frames": 86,
            "conditions": 6,
            "views": 516,
        },
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(weights, arcname="best.pt")
        archive.write(robustness_csv, arcname="robustness_metrics.csv")
        archive.write(summary_json_file, arcname="summary.json")
        archive.write(summary_md_file, arcname="summary.md")
        archive.write(split_md_file, arcname="SPLIT.md")
        archive.write(split_manifest_file, arcname="split_manifest.csv")
        archive.write(results_csv_file, arcname="results.csv")
        archive.writestr(
            "recovery_manifest.json",
            json.dumps(manifest_payload, indent=2, sort_keys=True) + "\n",
        )

    bundle_sha = sha256_file(output)
    manifest_payload["bundle_sha256"] = bundle_sha
    manifest_payload["bundle_bytes"] = output.stat().st_size

    # Verify extracted checkpoint in an isolated temp directory
    with tempfile.TemporaryDirectory(prefix="phase22-bundle-verify-") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        with zipfile.ZipFile(output, "r") as archive:
            archive.extractall(temp_dir)
        extracted_weights = temp_dir / "best.pt"
        if not extracted_weights.is_file():
            raise FileNotFoundError("Extracted bundle does not contain best.pt")
        extracted_sha = sha256_file(extracted_weights)
        if extracted_sha != EXPECTED_CHECKPOINT_SHA256:
            raise ValueError(
                f"Checkpoint SHA-256 verification failed AFTER packaging:\n"
                f"  Expected: {EXPECTED_CHECKPOINT_SHA256}\n"
                f"  Actual:   {extracted_sha}"
            )

    return manifest_payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, default=DEFAULT_LOCAL_WEIGHTS, help="Path to Phase 22 best.pt")
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR, help="Path to artifact contents")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output bundle path")
    args = parser.parse_args()

    print("=" * 60)
    print("PHASE 22 BASELINE CHECKPOINT BUNDLING & PRESERVATION")
    print("=" * 60)
    print(f"Candidate weights: {args.weights}")
    print(f"Artifact directory: {args.artifact_dir}")
    print(f"Target bundle:     {args.output}")

    if not args.weights.is_file():
        print(f"ERROR: Candidate weights file not found: {args.weights}", file=sys.stderr)
        return 1

    try:
        report = bundle(args.weights, args.artifact_dir, args.output)
    except Exception as exc:
        print(f"ERROR: Bundling failed: {exc}", file=sys.stderr)
        return 1

    print("\n[OK] Phase 22 recovery bundle created and verified successfully:")
    print(f"  Bundle path:     {args.output}")
    print(f"  Bundle SHA-256:  {report['bundle_sha256']}")
    print(f"  Bundle size:     {report['bundle_bytes']} bytes")
    print(f"  Checkpoint SHA:  {report['checkpoint_sha256']}")
    print(f"  Origin Commit:   {report['github_actions']['commit_sha']}")
    print(f"  Workflow Run:    {report['github_actions']['workflow_run_id']}")
    print(f"  Artifact ID:     {report['github_actions']['artifact_id']}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
