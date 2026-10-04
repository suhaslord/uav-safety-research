#!/usr/bin/env python3
"""Publish a small website record from sealed research artifacts, never new inference."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "results/research_revalidation_2026_10_03"
OUT = ROOT / "deploy/vercel/data/research-revalidation.json"
FIGURE = ROOT / "deploy/vercel/media/research-revalidation-occlusion.png"
SCIENTIFIC_REVISION = "db7aca05382f608cbe021cabb5c32862123c7633"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> bytes:
    manifest = json.loads((RESULT / "frozen_manifest.json").read_text(encoding="utf-8"))
    names = ["results/research_revalidation_2026_10_03/replay_receipt.json",
             "results/research_revalidation_2026_10_03/controlled_occlusion/analysis.json",
             "results/research_revalidation_2026_10_03/controlled_occlusion/controlled_occlusion.png",
             "results/research_revalidation_2026_10_03/paired_clean_vs_stressed.csv",
             "docs/phase26_admission_execution_lock.json", "pyproject.toml"]
    hashes = {name: digest(ROOT / name) for name in names}
    if any(value != manifest["files_sha256"][name] for name, value in hashes.items()):
        raise ValueError("Sealed research inputs changed; publish a separately reviewed revision")
    replay = json.loads((RESULT / "replay_receipt.json").read_text(encoding="utf-8"))
    occlusion = json.loads((RESULT / "controlled_occlusion/analysis.json").read_text(encoding="utf-8"))
    admission = json.loads((ROOT / "docs/phase26_admission_execution_lock.json").read_text(encoding="utf-8"))
    if replay["status"] != "PASS" or replay["comparison"] != "EXACT_MATCH" or not all(replay["frozen_tables_byte_identical"].values()):
        raise ValueError("Original-model replay is not verified")
    if occlusion["artifact_replay"]["status"] != "PASS" or occlusion["detector_inference_run"] is not False:
        raise ValueError("This publication requires the saved-artifact occlusion replay")
    if admission["admitted_datasets"] or admission["detector_test_inference_authorized"] is not False:
        raise ValueError("No independent dataset/result is admitted by this publication")
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    payload = {"schema": "aegisland.website-revalidation.v1", "version": version,
               "scientific_revision": SCIENTIFIC_REVISION,
               "frozen_manifest_sha256": digest(RESULT / "frozen_manifest.json"),
               "source_sha256": hashes, "source_frames": occlusion["source_frames"],
               "capture_sequences": occlusion["capture_sequences"],
               "phase23": {k: replay[k] for k in ["comparison", "phase23_cells_checked", "maximum_absolute_delta", "runtime", "checkpoint_sha256", "baseline_checkpoint_sha256", "protected_manifest_sha256", "source_archive_sha256", "cross_model_transition_counts", "clean_stressed_pair_count"]},
               "controlled_occlusion": {k: occlusion[k] for k in ["recovery_source_commit", "inference_freeze_commit", "detector_inference_run", "baseline_failures_before_added_occlusion", "clean_successes", "first_observed_loss_counts_among_clean_successes", "frames_with_later_recovery", "dose_response", "by_sequence", "limitations"]},
               "phase26": {"status": "NO_DATASET_ADMITTED", "test_inference_authorized": False,
                           "near_distance_argument": admission["screening"]["near_distance_argument"],
                           "minimum_accepted_dhash_distance": admission["screening"]["minimum_accepted_dhash_distance"]},
               "scope": "Retrospective KIOS research release candidate. Occlusion is saved-artifact replay, not new detector inference. No independent data, final v1.0 tag, end-to-end controller validation or flight certification."}
    return (json.dumps(payload, indent=2, allow_nan=False) + "\n").encode()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Read-only freshness check")
    args = parser.parse_args()
    payload = build()
    source_figure = RESULT / "controlled_occlusion/controlled_occlusion.png"
    if args.check:
        if not OUT.exists() or OUT.read_bytes() != payload or not FIGURE.exists() or FIGURE.read_bytes() != source_figure.read_bytes():
            raise SystemExit("Website research record/figure is stale; run this builder after reviewing the sealed inputs")
        print("Website research record and original figure: PASS")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_bytes(payload)
        FIGURE.parent.mkdir(parents=True, exist_ok=True)
        FIGURE.write_bytes(source_figure.read_bytes())
        print(f"Published {len(payload)} bytes and the unmodified evidence figure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
