#!/usr/bin/env python3
"""Audit the *scope* of AegisLand's public claims from committed evidence.

This checks archived arithmetic and dataset admission only. It is not model
inference, the Phase 25 top-box replay, or an independent performance result.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


class EvidenceError(ValueError):
    """An archived claim cannot be reconciled with its declared evidence."""


def audit(paired: dict, admission: dict) -> dict:
    """Return a conservative, provenance-linked snapshot or fail closed."""
    if paired.get("status") != "PASS" or paired.get("phase") != "phase25":
        raise EvidenceError("Phase 25 paired evidence is absent or not PASS")
    counts = paired.get("counts")
    if not isinstance(counts, dict):
        raise EvidenceError("Missing paired count table")
    keys = ("recovered", "regressed", "both_pass", "both_fail", "total_views")
    if any(type(counts.get(k)) is not int or counts[k] < 0 for k in keys):
        raise EvidenceError("Missing or invalid paired integer counts")
    if counts["total_views"] == 0 or sum(counts[k] for k in keys[:-1]) != counts["total_views"]:
        raise EvidenceError("Paired outcome counts do not reconcile")
    rates = paired.get("rates", {})
    n = counts["total_views"]
    expected_base = (counts["regressed"] + counts["both_pass"]) / n
    expected_new = (counts["recovered"] + counts["both_pass"]) / n
    expected_delta = expected_new - expected_base
    expected_rates = {
        "baseline_success_rate": expected_base,
        "phase23_success_rate": expected_new,
        "success_rate_delta": expected_delta,
    }
    for key, expected in expected_rates.items():
        value = rates.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or abs(value - expected) > 1e-9:
            raise EvidenceError(f"Contradictory paired rate: {key}")

    candidates = admission.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise EvidenceError("Missing independent dataset admission candidates")
    if any(type(item) is not dict or type(item.get("admitted")) is not bool for item in candidates):
        raise EvidenceError("Dataset candidate is missing explicit admission status")
    admitted = [item["name"] for item in candidates if item["admitted"]]
    if admitted:
        raise EvidenceError(
            "External dataset admission changed; rewrite/revalidate the historical showcase: "
            + ", ".join(admitted)
        )
    overlap = next((item for item in candidates
                    if item.get("name") == "KIOS 2022 Archive"), None)
    if overlap is None or overlap.get("overlap_count") != 422:
        raise EvidenceError("Historical KIOS 2022/2024 overlap evidence changed")

    return {
        "research_focus": "landing-perception reliability, not physical flight safety",
        "phase25": {
            "evidence_role": "retrospective_previously_used_frames",
            "paired_image_views": n,
            "recovered": counts["recovered"],
            "regressed": counts["regressed"],
            "both_pass": counts["both_pass"],
            "both_fail": counts["both_fail"],
            "baseline_any_match_success_rate": expected_base,
            "phase23_any_match_success_rate": expected_new,
            "independent_new_holdout": False,
            "source": "results/phase25_failure_atlas/paired_analysis_summary.json",
        },
        "phase26": {
            "external_dataset_admitted": False,
            "candidates_in_historical_admission_record": len(candidates),
            "known_KIOS_2022_byte_duplicates": overlap["overlap_count"],
            "threshold_frozen_for_new_external_test": False,
            "independent_test_result_available": False,
            "source": "docs/phase26_admission_report.json",
        },
        "cannot_claim": [
            "new independent real-image generalization performance",
            "a calibrated probability of safe landing",
            "physical flight safety or certification",
            "an integrated Model VASE flight-controller experiment",
        ],
        "scope": "archived count/admission consistency only; no top-box replay or inference",
    }


def load_snapshot(repo_root: Path) -> dict:
    paths = (
        repo_root / "results/phase25_failure_atlas/paired_analysis_summary.json",
        repo_root / "docs/phase26_admission_report.json",
    )
    try:
        paired, admission = (json.loads(path.read_text(encoding="utf-8")) for path in paths)
    except (OSError, ValueError) as exc:
        raise EvidenceError(f"Unable to load committed evidence: {exc}") from exc
    return audit(paired, admission)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    try:
        snapshot = load_snapshot(args.repo_root)
    except EvidenceError as exc:
        parser.exit(status=2, message=f"SHOWCASE EVIDENCE REJECTED: {exc}\n")
    content = json.dumps(snapshot, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(content, encoding="utf-8")
    else:
        print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
