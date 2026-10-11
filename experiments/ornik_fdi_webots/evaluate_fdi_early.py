#!/usr/bin/env python3
"""Frozen pre-contact motor-fault rule for the AegisLand Webots feasibility study.

The rule was informed by the *earlier pilot* (seeds 11,23,47). Those
seeds are excluded from the eight independent command-seed test clusters.
No physical-aircraft, hardware-validation, or flight-safety claim.
"""
import argparse
import csv
import hashlib
import json
import math
import os
import random
import statistics
from pathlib import Path

SOURCE_SEEDS = (11, 23, 29, 31)
DEV_SEEDS = (41, 47)
TEST_SEEDS = (53, 59, 61, 67, 71, 73, 79, 83)
ALL_SEEDS = SOURCE_SEEDS + DEV_SEEDS + TEST_SEEDS
FAULT_ONSET = 10.0
CENSOR_TIME = 10.70
CENSOR_ALTITUDE = 0.50
THRESHOLD_P = 2.0
THRESHOLD_Q = 0.75
PERSISTENCE = 3
QUADRANT = {(1, 1): 1, (1, -1): 2, (-1, -1): 3, (-1, 1): 4}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_trace(path, seed, motor):
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) < 700:
        raise ValueError(f"Incomplete trace: {path} ({len(rows)} samples)")
    last = -float("inf")
    for n, row in enumerate(rows):
        t = float(row["time_s"])
        if not math.isfinite(t) or t <= last:
            raise ValueError(f"Nonmonotonic timestamp: {path} row {n}")
        if any(not math.isfinite(float(row[field]))
               for field in ("z_m", "gyro_p_rps", "gyro_q_rps")):
            raise ValueError(f"Nonfinite sensor in {path} row {n}")
        if int(row["seed"]) != seed or int(row["failed_motor"]) != motor:
            raise ValueError(f"Scenario label changed in {path}")
        if int(row["fault_active"]) != int(motor > 0 and t >= FAULT_ONSET):
            raise ValueError(f"Incorrect fault onset in {path} row {n}")
        last = t
    if last < 22.0:
        raise ValueError(f"Trace ended too early: {path}")
    return rows


def early_decision(rows):
    """First causal gyro alert wins; altitude is an evaluation censor only."""
    streak = 0
    for row in rows:
        t = float(row["time_s"])
        z = float(row["z_m"])
        if t > CENSOR_TIME or (t >= FAULT_ONSET and z < CENSOR_ALTITUDE):
            break
        p = float(row["gyro_p_rps"])
        q = float(row["gyro_q_rps"])
        streak = streak + 1 if abs(p) >= THRESHOLD_P and abs(q) >= THRESHOLD_Q else 0
        if streak >= PERSISTENCE:
            return {"prediction": QUADRANT[(1 if p > 0 else -1, 1 if q > 0 else -1)],
                    "alert_time_s": t, "alert_altitude_m": z,
                    "false_alert_before_onset": t < FAULT_ONSET}
    return {"prediction": 0, "alert_time_s": None, "alert_altitude_m": None,
            "false_alert_before_onset": False}


def metrics(records):
    c = [[0 for _ in range(5)] for _ in range(5)]
    for row in records:
        c[row["motor"]][row["prediction"]] += 1
    if not all(sum(row) for row in c):
        raise ValueError("All five conditions must occur in the score set")
    recalls = [c[i][i] / sum(c[i]) for i in range(5)]
    fault_records = [r for r in records if r["motor"] > 0]
    correct_delays = [r["alert_time_s"] - FAULT_ONSET for r in fault_records
                      if r["motor"] == r["prediction"] and r["alert_time_s"] is not None
                      and r["alert_time_s"] >= FAULT_ONSET]
    return {"trajectories": len(records),
            "balanced_accuracy": sum(recalls) / 5,
            "healthy_false_alarm_rate": 1 - recalls[0],
            "fault_detection_rate": sum(r["prediction"] != 0 for r in fault_records)/len(fault_records),
            "correct_fault_isolation_rate": sum(r["prediction"] == r["motor"] for r in fault_records)/len(fault_records),
            "median_correct_detection_latency_s": statistics.median(correct_delays) if correct_delays else None,
            "class_recall": dict(zip(("healthy", "motor_1", "motor_2", "motor_3", "motor_4"), recalls)),
            "confusion_matrix_rows_true_cols_predicted": c}


def bootstrap_test(records):
    by_seed = {seed: [r for r in records if r["seed"] == seed] for seed in TEST_SEEDS}
    if any(len(x) != 5 for x in by_seed.values()):
        raise ValueError("Expected five paired conditions per protected seed")
    rng = random.Random(20261012)
    values = []
    for _ in range(2000):
        picked = [item for __ in TEST_SEEDS
                  for item in by_seed[rng.choice(TEST_SEEDS)]]
        values.append(metrics(picked)["balanced_accuracy"])
    values.sort()
    def pct(p):
        index = p * (len(values) - 1)
        lo = int(index)
        weight = index - lo
        return values[lo] * (1 - weight) + values[min(lo + 1, len(values) - 1)] * weight
    return {"independent_units": "eight command-seed clusters; five paired scenarios each",
            "bootstrap_draws": 2000, "random_seed": 20261012,
            "percentile_95_interval": [pct(.025), pct(.975)]}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-dir", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()
    expected = {f"seed{s}_motor{m}.csv" for s in ALL_SEEDS for m in range(5)}
    seen = {path.name for path in args.input_dir.glob("*.csv")}
    if seen != expected:
        raise ValueError(f"Expected exactly 70 files; missing={sorted(expected-seen)}, extra={sorted(seen-expected)}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    decisions, input_manifest = [], []
    for seed in ALL_SEEDS:
        split = ("protected_test" if seed in TEST_SEEDS else
                 ("development" if seed in DEV_SEEDS else "source_development"))
        for motor in range(5):
            path = args.input_dir / f"seed{seed}_motor{motor}.csv"
            raw = load_trace(path, seed, motor)
            decisions.append(dict(split=split, seed=seed, motor=motor, **early_decision(raw)))
            input_manifest.append({"file": path.name, "rows": len(raw), "sha256": sha256(path), "split": split})
    with (args.output_dir / "trajectory_decisions.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(decisions[0]))
        writer.writeheader()
        writer.writerows(decisions)
    protected = [x for x in decisions if x["split"] == "protected_test"]
    dev = [x for x in decisions if x["split"] != "protected_test"]
    if len(protected) != 40:
        raise ValueError("Protected split must contain 40 independent-scenario trajectories")
    result = {
        "status": "simulation_only_pre_contact_fault_isolation",
        "research_question": "Can a causal gyro-sign rule isolate complete motor loss on unseen command seeds before simulated impact?",
        "pilot_informed_rule_not_preregistered_before_original_pilot": True,
        "pilot_exposure_seeds": [11, 23, 47],
        "source_development_seeds": list(SOURCE_SEEDS),
        "development_seeds": list(DEV_SEEDS),
        "protected_test_seeds": list(TEST_SEEDS),
        "protected_test_trajectories": len(protected),
        "primary_metric": "five-class trajectory-level balanced accuracy",
        "predefined_rule": {
            "input": "gyro_p_rps and gyro_q_rps only",
            "p_abs_threshold_rad_per_s": THRESHOLD_P,
            "q_abs_threshold_rad_per_s": THRESHOLD_Q,
            "consecutive_alert_samples": PERSISTENCE,
            "quadrant_mapping": {str(k): v for k, v in QUADRANT.items()},
            "fault_onset_s": FAULT_ONSET,
            "time_censor_s": CENSOR_TIME,
            "altitude_censor_m": CENSOR_ALTITUDE,
            "first_alarm_wins": True},
        "protected_result": metrics(protected),
        "protected_seed_cluster_bootstrap": bootstrap_test(protected),
        "development_descriptive_result": metrics(dev),
        "always_healthy_balanced_accuracy": 0.2,
        "git_sha": os.environ.get("GITHUB_SHA", "local-uncommitted"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "analysis_script_sha256": sha256(Path(__file__)),
        "input_manifest": input_manifest,
        "limitations": [
            "Only one simulator, one vehicle plant and complete motor shutdown at a known fixed onset.",
            "Thresholds and mapping informed by earlier 15-trajectory pilot (seeds 11, 23, 47); those excluded from protected set.",
            "Late unrealistic simulator telemetry is deliberately excluded, not evidence of correct late-stage flight dynamics.",
            "No new vehicle, noise perturbations, controller recovery, flight testing or flight safety claims.",
            "Eight independent seed clusters give limited statistical power; windows/samples are not independent trials."]}
    (args.output_dir / "heldout_results.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"test_trajectories": len(protected),
                      "balanced_accuracy": result["protected_result"]["balanced_accuracy"],
                      "bootstrap_interval": result["protected_seed_cluster_bootstrap"]["percentile_95_interval"]}, indent=2))


if __name__ == "__main__":
    main()
