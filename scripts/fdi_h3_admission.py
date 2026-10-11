#!/usr/bin/env python3
"""Reject incomplete or contaminated candidate manifests for H3 cross-dynamics research.

The script validates documented prerequisites but CANNOT establish physical
simulation independence. A human reviewer still must verify source provenance.
It never executes a simulator, detector, or protected-holdout evaluation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

PREVIOUSLY_USED = frozenset(
    (11, 23, 29, 31, 41, 47, 53, 59, 61, 67, 71, 73, 79, 83,
     89, 97, 101, 103, 107, 109, 113, 127)
)
H1_MOTOR_MAP = {"++": 1, "+-": 2, "--": 3, "-+": 4}


def validate(manifest):
    issues = []
    def check(ok, failure):
        if not ok:
            issues.append(failure)

    check(isinstance(manifest, dict), "manifest must be an object")
    if not isinstance(manifest, dict):
        return issues
    check(manifest.get("study_id") == "FDI-H3", "study_id must be FDI-H3")
    engine = manifest.get("engine", {})
    if not isinstance(engine, dict):
        engine = {}
    identifier = engine.get("implementation", "")
    check(isinstance(identifier, str) and len(identifier.strip()) > 7, "engine implementation identity missing")
    check(engine.get("dynamics_family") not in (None, "", "bitcraze-webots", "same-webots-plant"),
          "a candidate independent dynamics family is required; original Webots is not eligible")
    origin = engine.get("source_url", "")
    check(isinstance(origin, str) and origin.startswith("https://"), "engine source URL missing")
    source_sha = engine.get("commit_sha", "")
    check(isinstance(source_sha, str) and bool(re.fullmatch(r"[0-9a-fA-F]{40}", source_sha)),
          "engine source 40-char Git SHA missing")
    digest = engine.get("runtime_digest", "")
    check(isinstance(digest, str) and bool(re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest)),
          "container/runtime sha256 digest missing")
    independence = engine.get("independence_evidence_url", "")
    check(isinstance(independence, str) and independence.startswith("https://"),
          "source-level independence evidence missing; parameter shifts alone do not qualify")

    interface = manifest.get("interface", {})
    if not isinstance(interface, dict):
        interface = {}
    check(interface.get("gyro_units") == "rad/s", "gyro p/q must use rad/s")
    check(interface.get("gyro_axes") == ["body_roll_rate_p", "body_pitch_rate_q"],
          "gyro axes must be frozen as body roll and pitch rates")
    check(interface.get("motor_order") == [1, 2, 3, 4], "motor ordering must be frozen as 1–4")
    check(interface.get("motor_quadrant_map") == H1_MOTOR_MAP,
          "frozen H1 quadrant mapping differs; do not tune on protected evaluation")
    dt = interface.get("sample_period_s")
    check(isinstance(dt, (float, int)) and not isinstance(dt, bool) and 0 < dt <= 0.1,
          "document plausible sample period (0, 0.1] s")
    check(isinstance(interface.get("altitude_reference"), str) and len(interface["altitude_reference"].strip()) > 5,
          "document altitude frame")
    check(isinstance(interface.get("contact_indicator"), str) and bool(interface["contact_indicator"].strip()),
          "document simulator contact detection")

    method = manifest.get("method", {})
    if not isinstance(method, dict):
        method = {}
    check(method.get("threshold_p_radps") == 2.0 and method.get("threshold_q_radps") == 0.75 and
          method.get("consecutive_samples") == 3, "historical detector thresholds/persistence must not change")
    check(method.get("speed_retentions") == [0.0, 0.5, 0.8],
          "predeclared motor speed retention set must be [0,0.5,0.8]")
    check(method.get("injection_site") == "simulated_actuator_model", "fault must be injected in simulator motor model")
    check(method.get("online_gyro_noise") is True, "online measurement perturbation must be documented")
    check(isinstance(method.get("online_gyro_noise_spec_url"), str) and method["online_gyro_noise_spec_url"].startswith("https://"),
          "online noise implementation evidence URL required")

    splits = manifest.get("splits", {})
    if not isinstance(splits, dict):
        splits = {}
    development, protected = splits.get("development_seeds"), splits.get("protected_seeds")
    for label, seeds in (("development", development), ("protected", protected)):
        check(isinstance(seeds, list) and all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in seeds),
              f"{label} seeds must be a list of nonnegative integers")
        if isinstance(seeds, list):
            check(len(seeds) == len(set(map(str, seeds))), f"{label} seeds must not contain duplicates")
            check(not set(v for v in seeds if isinstance(v, int)).intersection(PREVIOUSLY_USED),
                  f"{label} contains known H1/H2 seeds")
    if isinstance(protected, list):
        check(len(protected) >= 12, "at least 12 independent protected command seeds required")
    if isinstance(development, list) and isinstance(protected, list):
        check(not set(development).intersection(protected), "development/protected seed leakage")

    for name in ("development_protocol_url", "protected_protocol_url", "manifest_archive_url"):
        url = manifest.get(name)
        check(isinstance(url, str) and url.startswith("https://"),
              f"missing immutable public reference: {name}")
    return issues


def evaluate_file(path):
    raw = Path(path).read_bytes()
    manifest = json.loads(raw)
    problems = validate(manifest)
    return {
        "study": "FDI-H3",
        "preflight_version": "1.0",
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "status": "REJECTED" if problems else "READY_FOR_INDEPENDENT_SOURCE_REVIEW",
        "can_claim_h3_results": False,
        "independent_dynamics_verified": False,
        "issues": problems,
        "note": "Manifest completeness is not scientific admission; external source verification is mandatory.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_manifest", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    result = evaluate_file(args.candidate_manifest)
    text = json.dumps(result, indent=2) + "\n"
    print(text, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    raise SystemExit(0 if result["status"] == "READY_FOR_INDEPENDENT_SOURCE_REVIEW" else 2)


if __name__ == "__main__":
    main()
