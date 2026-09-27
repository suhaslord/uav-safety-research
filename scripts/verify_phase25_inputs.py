#!/usr/bin/env python3
"""Fail-closed inventory check for the Phase 25 protected inputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from phase25_lib import validate_phase25_inputs  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True, help="Frozen YOLO split root")
    parser.add_argument("--stress-root", type=Path, required=True, help="Frozen six-condition test root")
    parser.add_argument("--baseline-weights", type=Path, required=True)
    parser.add_argument("--phase23-weights", type=Path, required=True)
    parser.add_argument(
        "--protected-manifest",
        type=Path,
        default=ROOT / "results/phase25_failure_atlas/protected_test_manifest.csv",
    )
    args = parser.parse_args()

    try:
        inventory = validate_phase25_inputs(
            source_root=args.source_root,
            stress_root=args.stress_root,
            baseline_weights=args.baseline_weights,
            phase23_weights=args.phase23_weights,
            protected_manifest=args.protected_manifest,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"Phase 25 input gate: BLOCKED — {exc}", file=sys.stderr)
        return 2

    report = {
        "status": "verified",
        "frame_count": inventory["frame_count"],
        "condition_count": inventory["condition_count"],
        "frame_condition_count": inventory["frame_condition_count"],
        "sequence_counts": inventory["sequence_counts"],
        "manifest_sha256": inventory["manifest_sha256"],
        "baseline_weights_sha256": inventory["baseline_weights_sha256"],
        "phase23_weights_sha256": inventory["phase23_weights_sha256"],
        "input_lock_sha256": inventory["input_lock_sha256"],
        "baseline_actions_artifact_id": inventory["baseline_actions_artifact_id"],
        "baseline_actions_artifact_sha256": inventory["baseline_actions_artifact_sha256"],
        "hashed_data_files": len(inventory["inventory"]),
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
