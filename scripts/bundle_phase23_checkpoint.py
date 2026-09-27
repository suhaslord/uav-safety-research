#!/usr/bin/env python3
"""Package the original local Phase 23 checkpoint for the Phase 25 audit."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import platform
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_ARGS = ROOT / "results/phase23_robust_detector/training/phase23_robust_yolo11n/args.yaml"
LOCAL_WEIGHTS = ROOT / "results/phase23_robust_detector/training/phase23_robust_yolo11n/weights/best.pt"
DEFAULT_OUTPUT = ROOT / "data/external/phase25_inputs/phase23_recovery_bundle.zip"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def recorded_weights() -> Path | None:
    for line in REFERENCE_ARGS.read_text(encoding="utf-8").splitlines():
        if line.startswith("save_dir:"):
            return Path(line.partition(":")[2].strip().strip("\"'")) / "weights" / "best.pt"
    return None


def find_weights(explicit: Path | None) -> Path:
    candidates = [explicit] if explicit else [LOCAL_WEIGHTS, recorded_weights()]
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(
        "Phase 23 best.pt was not found in this repo or the original save_dir. "
        "If the training folder moved, pass --weights PATH_TO_ORIGINAL_BEST_PT."
    )


def observed_versions() -> dict[str, str | None]:
    packages: dict[str, str | None] = {}
    for name in ("ultralytics", "torch", "numpy", "Pillow"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    return packages


def bundle(weights: Path, output: Path) -> dict[str, object]:
    if not zipfile.is_zipfile(weights):
        raise ValueError("The candidate is not a PyTorch ZIP checkpoint; check the selected best.pt")
    if output.exists():
        raise FileExistsError(f"Bundle already exists: {output}. Move it before retrying.")

    local_args = weights.parent.parent / "args.yaml"
    report: dict[str, object] = {
        "status": "checkpoint_candidate_requires_phase25_reconciliation",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_source": str(weights),
        "checkpoint_sha256": sha256_file(weights),
        "checkpoint_bytes": weights.stat().st_size,
        "reference_args_sha256": sha256_file(REFERENCE_ARGS),
        "local_args_sha256": sha256_file(local_args) if local_args.is_file() else None,
        "environment_observed_at_bundle_time": {
            "python_version": platform.python_version(),
            "python_executable": sys.executable,
            "packages": observed_versions(),
        },
        "note": "Observed packages may differ from the original evaluation environment. "
        "This bundle does not establish checkpoint identity or reproduce Phase 23 metrics.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(weights, "best.pt")
        archive.write(REFERENCE_ARGS, "reference_args.yaml")
        if local_args.is_file():
            archive.write(local_args, "local_args.yaml")
        archive.writestr("recovery_manifest.json", json.dumps(report, indent=2) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, help="Original Phase 23 weights/best.pt, if its folder moved")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        weights = find_weights(args.weights)
        report = bundle(weights, args.output.resolve())
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        parser.exit(2, f"Recovery blocked: {exc}\n")
    print(f"Bundle: {args.output.resolve()}")
    print(f"Checkpoint SHA-256: {report['checkpoint_sha256']}")
    print("Upload the bundle for aggregate reconciliation; it is not a verified Phase 25 result yet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
