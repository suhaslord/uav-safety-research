#!/usr/bin/env python3
"""Read-only, scoped 1.0.0rc1 artifact validation; no inference or dataset admission.

The manifest freezes exact bytes, not a digital signature or a claim that every
historical experiment has been rerun. Use a full-history checkout.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from scripts import build_failure_atlas_data, reproduce_release
from scripts.verify_phase23_research_replay import authenticate_recovery, clean_stress_pairs, read_rows, TABLES, RECOVERED_PATHS
from scripts.verify_phase22_occlusion_v2 import verify as verify_occlusion
from scripts.verify_phase26_admission_protocol import verify_lock

RESULT = ROOT / "results/research_revalidation_2026_10_03"
MANIFEST = RESULT / "frozen_manifest.json"
VERSION = "1.0.0rc1"
SCOPE = "retrospective_original_detector_and_controlled_occlusion_plus_prospective_admission_methods"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def repository_state() -> dict:
    return {"head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())}


def frozen_paths() -> list[str]:
    fixed = [".gitattributes", "CITATION.cff", "README.md", "REPRODUCE.md", "pyproject.toml",
             "paper/README.md", "paper/detector_revalidation_report.md", "docs/citation_provenance.md",
             "docs/research_revalidation_2026_10_03.md", "docs/model_vase.md",
             "docs/phase26_admission_execution_lock.json", "docs/phase25_input_lock.json",
             "scripts/verify_phase23_research_replay.py", "scripts/summarize_controlled_occlusion.py",
             "scripts/verify_phase26_admission_protocol.py", "scripts/validate_research_release.py",
             "scripts/reproduce_release.py", "scripts/build_failure_atlas_data.py",
             "scripts/verify_model_vase_parity.py", "scripts/phase22_representation_transform.py",
             "tests/conftest.py", "tests/test_research_revalidation.py",
             "deploy/vercel/failure-atlas-data.json", "deploy/vercel/failure-atlas.html",
             "deploy/vercel/failure-atlas.js", "deploy/vercel/model-vase.html",
             "deploy/vercel/model-vase-evidence.js"]
    paths = set(fixed) | set(RECOVERED_PATHS)
    lock = json.loads((ROOT / "docs/phase26_admission_execution_lock.json").read_text())
    paths.update(lock["frozen_files_sha256"])
    for directory in ["src", "results/phase25_baseline_diagnostic", "results/phase25_failure_atlas",
                      "results/phase22_occlusion_original_recovery", "results/phase22_occlusion_v2",
                      "results/phase23_robust_detector", "results/v3_frozen", "results/research_revalidation_2026_10_03"]:
        for path in (ROOT / directory).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and path != MANIFEST:
                paths.add(path.relative_to(ROOT).as_posix())
    # Freeze the actual method adapters and their CLI schemas, not weights/private imagery.
    for name in ["phase25_lib.py", "verify_phase25_inputs.py", "run_phase25_frame_audit.py", "analyze_phase25_failures.py",
                 "run_phase22_occlusion_v2.py", "verify_phase22_occlusion_v2.py", "build_model_vase_data.py"]:
        path = ROOT / "scripts" / name
        if path.exists(): paths.add(path.relative_to(ROOT).as_posix())
    return sorted(paths)


def create_manifest() -> dict:
    if MANIFEST.exists():
        raise ValueError("The frozen manifest already exists; do not overwrite it")
    record = {"schema": "aegisland.research-release-candidate.v1", "version": VERSION, "scope": SCOPE,
              "created_at_utc": datetime.now(timezone.utc).isoformat(), "source_base_commit": repository_state()["head"],
              "status": "FROZEN_RELEASE_CANDIDATE", "inference_replayed_by_this_manifest": False,
              "independent_dataset_admitted": False, "tag_or_doi_created": False,
              "files_sha256": {name: sha(ROOT / name) for name in frozen_paths()}}
    MANIFEST.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    return record


def verify_manifest(path: Path = MANIFEST) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    if record["schema"] != "aegisland.research-release-candidate.v1" or record["version"] != VERSION or record["scope"] != SCOPE:
        raise ValueError("Manifest version/scope is not this release candidate")
    if record["status"] != "FROZEN_RELEASE_CANDIDATE" or record["independent_dataset_admitted"] is not False:
        raise ValueError("Retrospective evidence must not be relabeled independent validation")
    if not record["files_sha256"]:
        raise ValueError("Empty frozen artifact inventory")
    for name, expected in record["files_sha256"].items():
        target = (ROOT / name).resolve()
        if not target.is_relative_to(ROOT.resolve()) or not target.is_file() or sha(target) != expected:
            raise ValueError(f"Frozen artifact changed or escaped the repository: {name}")
    if path == MANIFEST and set(record["files_sha256"]) != set(frozen_paths()):
        raise ValueError("Frozen artifact inventory changed")
    return record


def verify(allow_dirty: bool = False) -> dict:
    state = repository_state()
    if state["dirty"] and not allow_dirty:
        raise ValueError("Release validation requires a clean committed checkout")
    manifest = verify_manifest()
    receipt = json.loads((RESULT / "replay_receipt.json").read_text())
    if receipt["status"] != "PASS" or receipt["comparison"] != "EXACT_MATCH" or receipt["phase23_cells_checked"] != 24 or receipt["maximum_absolute_delta"] != 0:
        raise ValueError("Original Phase 23 aggregate replay is not exact")
    frozen = ROOT / "results/phase25_failure_atlas"
    if set(receipt["replay_table_sha256"]) != set(TABLES) or not all(receipt["frozen_tables_byte_identical"].values()):
        raise ValueError("Original prediction-table identity is incomplete")
    for name, expected in receipt["replay_table_sha256"].items():
        if sha(frozen / name) != expected: raise ValueError("Original replay table changed: " + name)
    source = authenticate_recovery()
    if source != receipt["controlled_occlusion_recovery_files"]:
        raise ValueError("Controlled-occlusion recovery provenance changed")
    pairs = clean_stress_pairs(read_rows(frozen / "frame_condition_metrics.csv"), read_rows(frozen / "protected_test_manifest.csv"))
    buf = io.StringIO(newline="")
    # Match the receipt writer's canonical CSV bytes; never rewrite retained pairs.
    writer = csv.DictWriter(buf, fieldnames=list(pairs[0]), lineterminator="\r\n")
    writer.writeheader(); writer.writerows(pairs)
    pair_path = RESULT / "paired_clean_vs_stressed.csv"
    if len(pairs) != 860 or sha(pair_path) != receipt["paired_clean_vs_stressed_sha256"] or buf.getvalue().encode() != pair_path.read_bytes():
        raise ValueError("Within-model clean/stress pairs do not replay")
    baseline = reproduce_release.verify()
    if baseline["status"] != "committed_phase25a_verified":
        raise ValueError("Phase 25A hashes or generated site snapshots failed")
    occlusion = verify_occlusion(ROOT / "results/phase22_occlusion_v2")
    if occlusion["status"] != "PASS" or not occlusion["freeze_commit_locally_verified"]:
        raise ValueError("Controlled v2 freeze/saved predictions need a full-history verified checkout")
    admission = verify_lock()
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    if project["version"] != VERSION or f'version: "{VERSION}"' not in (ROOT / "CITATION.cff").read_text():
        raise ValueError("Software and citation candidate versions disagree")
    return {"status": "PASS_SCOPED_RELEASE_CANDIDATE", "version": VERSION, "scope": SCOPE,
            "repository": state, "frozen_files_checked": len(manifest["files_sha256"]), "manifest_sha256": sha(MANIFEST),
            "phase23_aggregate_cells_exact": 24, "prediction_tables_byte_identical": 4,
            "within_model_pairs_replayed": len(pairs), "original_recovery_files_authenticated": len(source),
            "phase25a": baseline["status"], "controlled_occlusion": occlusion, "phase26": admission,
            "site_snapshot": "PASS_generated_from_authenticated_tables",
            "inputs_replayed": False, "tag_or_doi_created": False, "final_v1_0_tag_validated": False,
            "limits": ["Artifact replay is not a new model/input inference run.",
                       "Independent dataset, detector/controller composition and flight validation are absent.",
                       "All historical Monte Carlo phases are not rerun by this scoped command.",
                       "Final v1.0 publication needs an explicit final version/tag and applicable external rights."]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create-manifest", action="store_true", help="Initial freeze only; refuses overwrite")
    parser.add_argument("--allow-dirty", action="store_true", help="Development checks only; reports actual dirty state")
    args = parser.parse_args()
    if args.create_manifest: create_manifest()
    print(json.dumps(verify(args.allow_dirty), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
