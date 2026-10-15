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
import math
import re
from pathlib import Path
from urllib.parse import urlsplit

PREVIOUSLY_USED = frozenset(
    (11, 23, 29, 31, 41, 47, 53, 59, 61, 67, 71, 73, 79, 83,
     89, 97, 101, 103, 107, 109, 113, 127)
)
H1_MOTOR_MAP = {"++": 1, "+-": 2, "--": 3, "-+": 4}


def _is_https_evidence_url(value):
    """Require a usable HTTPS origin and reject non-string/offline evidence."""
    if not isinstance(value, str) or any(ch.isspace() for ch in value):
        return False
    try:
        parsed = urlsplit(value)
        return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password
    except ValueError:
        return False


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
    dynamics_family = engine.get("dynamics_family")
    check(isinstance(dynamics_family, str) and len(dynamics_family.strip()) > 7 and
          dynamics_family.strip().lower() not in ("bitcraze-webots", "same-webots-plant"),
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

    license_id = engine.get("license")
    check(isinstance(license_id, str) and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+-]{1,99}", license_id)),
          "engine.license must name a reviewable SPDX license identifier")

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
    check(isinstance(dt, (float, int)) and not isinstance(dt, bool) and math.isfinite(dt) and 0 < dt <= 0.1,
          "document finite sample period (0, 0.1] s")
    check(isinstance(interface.get("altitude_reference"), str) and len(interface["altitude_reference"].strip()) > 5,
          "document altitude frame")
    check(isinstance(interface.get("contact_indicator"), str) and bool(interface["contact_indicator"].strip()),
          "document simulator contact detection")

    for key in ("gyro_axis_mapping_evidence_url", "motor_index_mapping_evidence_url",
                "applied_actuator_observation_evidence_url"):
        check(_is_https_evidence_url(interface.get(key)), f"interface.{key} must provide an HTTPS evidence URL")

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

    for key in ("simulator_fault_injection_evidence_url", "online_noise_runtime_evidence_url"):
        check(_is_https_evidence_url(method.get(key)), f"method.{key} must provide an HTTPS evidence URL")

    splits = manifest.get("splits", {})
    if not isinstance(splits, dict):
        splits = {}
    development, protected = splits.get("development_seeds"), splits.get("protected_seeds")
    valid_splits = {}
    for label, seeds in (("development", development), ("protected", protected)):
        # Never create a set from unvalidated external JSON. The old implementation
        # could raise TypeError for a list containing a dictionary or list.
        valid = (isinstance(seeds, list) and
                 all(type(value) is int and value >= 0 for value in seeds))
        check(valid, f"{label} seeds must be a list of nonnegative integers")
        if not valid:
            continue
        check(len(seeds) == len(set(seeds)), f"{label} seeds must not contain duplicates")
        check(not set(seeds).intersection(PREVIOUSLY_USED), f"{label} contains known H1/H2 seeds")
        valid_splits[label] = seeds
    if "development" in valid_splits:
        check(bool(valid_splits["development"]), "a separate nonempty development split is required")
    if "protected" in valid_splits:
        check(len(valid_splits["protected"]) >= 12,
              "at least 12 independent protected command seeds required")
    if len(valid_splits) == 2:
        check(not set(valid_splits["development"]).intersection(valid_splits["protected"]),
              "development/protected seed leakage")

    check(splits.get("protected_holdout_status") == "sealed_unscored",
          "protected holdout must remain sealed_unscored before independent-source review")
    freeze_hash = splits.get("protected_holdout_freeze_sha256")
    check(isinstance(freeze_hash, str) and bool(re.fullmatch(r"[0-9a-fA-F]{64}", freeze_hash)),
          "protected holdout freeze SHA-256 must be present and well-formed")

    for name in ("development_protocol_url", "protected_protocol_url", "manifest_archive_url"):
        url = manifest.get(name)
        check(isinstance(url, str) and url.startswith("https://"),
              f"missing immutable public reference: {name}")
    return issues


def evaluate_file(path):
    raw = Path(path).read_bytes()
    try:
        manifest = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"Candidate manifest is not valid UTF-8 JSON: {exc}") from exc
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
