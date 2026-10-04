#!/usr/bin/env python3
"""Verify the prospective admission execution lock; never certify a dataset by pixels alone."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "docs/phase26_admission_execution_lock.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_lock(path: Path = LOCK) -> dict:
    lock = json.loads(path.read_text(encoding="utf-8"))
    if lock["status"] != "FROZEN_NEXT_CANDIDATE_ADMISSION" or lock["admitted_datasets"] != []:
        raise ValueError("This lock freezes admission methods, not an independent-validation result")
    for name, expected in lock["frozen_files_sha256"].items():
        target = (ROOT / name).resolve()
        if not target.is_relative_to(ROOT.resolve()) or digest(target) != expected:
            raise ValueError(f"Frozen admission method changed: {name}")
    spec = lock["screening"]
    if spec["near_distance_argument"] != 9 or spec["minimum_accepted_dhash_distance"] != 10:
        raise ValueError("The execution threshold must reject distances <= 9, matching the frozen >= 10 separation rule")
    if spec["kios_reference_count"] != 422 or lock["detector_test_inference_authorized"] is not False:
        raise ValueError("Independent validation is not authorized by this method-only lock")
    return {"status": "PASS", "lock_sha256": digest(path), "admission_status": "NO_DATASET_ADMITTED",
            "test_inference_authorized": False, "frozen_files_checked": len(lock["frozen_files_sha256"]),
            "scope": "Admission protocol/method integrity only; no dataset or detector results authenticated by this check."}


def verify_screen(screen: dict) -> dict:
    """Fail closed on the automated part; a passing screen still requires human review."""
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    spec = lock["screening"]
    reasons = []
    if screen.get("status") != "screened_pending_provenance_ontology_rights_review" or screen.get("reasons"):
        reasons.append("automated_screen_not_clear")
    if screen.get("reference_archive_sha256") != spec["kios_reference_archive_sha256"] or screen.get("reference_count") != 422:
        reasons.append("full_kios_reference_not_authenticated")
    if screen.get("near_match_threshold_dhash") != 9 or screen.get("exact_overlaps") or screen.get("near_match_flags"):
        reasons.append("duplicate_or_distance_gate_not_clear")
    images = screen.get("images", [])
    if len(images) != screen.get("candidate_count") or len(images) < spec["minimum_total_frames"]:
        reasons.append("insufficient_or_incomplete_frame_inventory")
    if len({r.get("session_id") for r in images if r.get("session_id")}) < spec["minimum_capture_sessions"]:
        reasons.append("insufficient_capture_sessions")
    if not any(r.get("target_count") == 0 for r in images):
        reasons.append("negative_frame_inventory_missing")
    if not screen.get("dev_count") or not screen.get("test_count"):
        reasons.append("separate_development_and_test_required")
    return {"status": "BLOCKED" if reasons else "SCREENED_REQUIRES_DOCUMENTED_HUMAN_REVIEWS",
            "admitted": False, "test_inference_authorized": False, "reasons": reasons,
            "pending_reviews": lock["required_documented_reviews_before_admission"]}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--screen", type=Path, help="Optional saved candidate screen; never promotes it to admission")
    args = p.parse_args()
    report = verify_lock()
    if args.screen:
        report["candidate"] = verify_screen(json.loads(args.screen.read_text(encoding="utf-8")))
    print(json.dumps(report, indent=2))
    return 2 if report.get("candidate", {}).get("status") == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
