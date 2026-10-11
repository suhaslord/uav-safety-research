#!/usr/bin/env python3
"""Generate the *unexecuted* R1 partial-motor-effectiveness challenge manifest.

This planning utility does not run Webots, inspect protected traces, score a
detector, or change the frozen FDI-H1 experiment. It fixes the scenario set
before the next research study begins.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HISTORICAL_SEEDS = (11, 23, 29, 31, 41, 47, 53, 59, 61, 67, 71, 73, 79, 83)
NEW_SEEDS = (89, 97, 101, 103, 107, 109, 113, 127)
FAULT_ONSET_S = 10.0
EARLY_CENSOR_S = 10.70
PINNED_CRAZYFLIE_COMMIT = "7e93752dbc803af2488c1db46bb79b3da55f5d8c"
PINNED_WEBOTS_DIGEST = (
    "cyberbotics/webots@sha256:"
    "f0023e30daf38b172e4e6ad24ed345909bcd9551df34d63d824e121a7cebf099"
)


def planned_scenarios():
    """One healthy control, four full losses, four half-losses per seed."""
    if len(NEW_SEEDS) != 8 or len(set(NEW_SEEDS)) != 8:
        raise ValueError("R1 must have eight unique command-seed clusters")
    if not set(NEW_SEEDS).isdisjoint(HISTORICAL_SEEDS):
        raise ValueError("R1 command seeds overlap the historical/protected data")
    result = []
    for seed in NEW_SEEDS:
        result.append({
            "case_id": f"r1_seed{seed}_healthy",
            "command_seed": seed,
            "condition": "healthy",
            "failed_motor": 0,
            "retained_motor_fraction": 1.0,
            "fault_onset_s": FAULT_ONSET_S,
            "gyro_noise_std_rad_per_s": 0.0,
        })
        for condition, retained in (("full_loss", 0.0), ("partial_50pct", 0.5)):
            for motor in range(1, 5):
                result.append({
                    "case_id": f"r1_seed{seed}_{condition}_motor{motor}",
                    "command_seed": seed,
                    "condition": condition,
                    "failed_motor": motor,
                    "retained_motor_fraction": retained,
                    "fault_onset_s": FAULT_ONSET_S,
                    "gyro_noise_std_rad_per_s": 0.0,
                })
    validate_scenarios(result)
    return result


def validate_scenarios(records):
    """Reject swapped labels, missing motor pairs, duplicate cases or new seeds."""
    expected = {
        (seed, condition, motor, retained)
        for seed in NEW_SEEDS
        for condition, motors, retained in (
            ("healthy", (0,), 1.0),
            ("full_loss", (1, 2, 3, 4), 0.0),
            ("partial_50pct", (1, 2, 3, 4), 0.5),
        )
        for motor in motors
    }
    if len(records) != 72 or len({r.get("case_id") for r in records}) != 72:
        raise ValueError("R1 must specify exactly 72 uniquely named scenarios")
    observed = {
        (r.get("command_seed"), r.get("condition"), r.get("failed_motor"),
         r.get("retained_motor_fraction"))
        for r in records
    }
    if observed != expected:
        raise ValueError("R1 scenario labels, seeds, or effectiveness matrix drifted")
    for r in records:
        if r.get("fault_onset_s") != FAULT_ONSET_S or r.get("gyro_noise_std_rad_per_s") != 0.0:
            raise ValueError("R1 permits no timing or noise perturbations")
        expected_id = (
            f"r1_seed{r['command_seed']}_healthy" if r["condition"] == "healthy"
            else f"r1_seed{r['command_seed']}_{r['condition']}_motor{r['failed_motor']}"
        )
        if r.get("case_id") != expected_id:
            raise ValueError("R1 scenario identifier differs from canonical name")
    return True


def make_manifest():
    evaluator = Path(__file__).with_name("evaluate_fdi_early.py")
    evaluator_bytes = evaluator.read_bytes()
    return {
        "schema": "aegisland.fdi.r1.design-only.v1",
        "status": "unexecuted_design_not_simulation_results",
        "parent_study": "FDI-H1, draft PR #175; frozen before R1",
        "interpretation": "One simulator, exploratory partial actuator fault challenge; no flight-safety claim",
        "source_study_historical_seeds_excluded": list(HISTORICAL_SEEDS),
        "new_independent_command_seeds": list(NEW_SEEDS),
        "command_seed_clusters": len(NEW_SEEDS),
        "scenarios": 72,
        "healthy_scenarios": 8,
        "full_loss_scenarios": 32,
        "partial_50pct_scenarios": 32,
        "frozen_early_detector_source_sha256": hashlib.sha256(evaluator_bytes).hexdigest(),
        "pinned_crazyflie_commit": PINNED_CRAZYFLIE_COMMIT,
        "pinned_webots_image_digest": PINNED_WEBOTS_DIGEST,
        "fault_onset_s": FAULT_ONSET_S,
        "evaluation_time_limit_s": EARLY_CENSOR_S,
        "planned_cases": planned_scenarios(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="New JSON file only; refusing overwrite preserves the initial plan")
    args = parser.parse_args()
    manifest = make_manifest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents an accidental edit to a supposedly frozen design.
    with args.output.open("x", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
        fh.write("\n")
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(f"R1 DESIGN ONLY: {len(manifest['planned_cases'])} scenarios; SHA-256 {digest}")


if __name__ == "__main__":
    main()
