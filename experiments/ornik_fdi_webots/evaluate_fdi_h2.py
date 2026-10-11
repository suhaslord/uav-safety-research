#!/usr/bin/env python3
"""Preregistered H2 stress evaluation of the unchanged H1 gyroscope rule.

No fitting or tuning. One detection per whole trajectory; six command seeds
are the independent clusters, even when scenarios and noise repeats exist.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import statistics
from pathlib import Path

SEEDS = (97, 101, 103, 107, 109, 113)
ONSETS = (8.0, 12.0)
FAULT_LOSSES = (0.5, 1.0)
NOISE_LEVELS = (0.0, 0.5)
THRESHOLD_P = 2.0
THRESHOLD_Q = 0.75
ALERT_STREAK = 3
POST_ONSET_WINDOW_S = 0.70
CENSOR_ALTITUDE_M = 0.50
BOOTSTRAP_SEED = 20261013
BOOTSTRAP_DRAWS = 2000
MOTOR_QUADRANTS = {(1, 1): 1, (1, -1): 2, (-1, -1): 3, (-1, 1): 4}
CLASSES = ("healthy", "motor_1", "motor_2", "motor_3", "motor_4")
PREMATURE_COLUMN = 5


def path_name(seed: int, onset: float, loss: float, motor: int) -> str:
    return f"seed{seed}_onset{int(onset)}_loss{int(loss * 100):03d}_motor{motor}.csv"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_checked(path: Path, seed: int, onset: float, loss: float, motor: int):
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) < (onset + 1.4) * 25:
        raise ValueError(f"Too few measurements in {path}")
    last_time = -1.0
    for idx, row in enumerate(rows):
        t = float(row["time_s"])
        values = (t, float(row["z_m"]), float(row["gyro_p_rps"]), float(row["gyro_q_rps"]))
        if not all(math.isfinite(v) for v in values) or t <= last_time:
            raise ValueError(f"Invalid timestamps or sensors in {path} at {idx}")
        if (int(row["seed"]), int(row["failed_motor"])) != (seed, motor):
            raise ValueError(f"Incorrect scenario metadata in {path}")
        if abs(float(row["fault_onset_s"]) - onset) > 1e-6 or abs(float(row["loss_fraction"]) - loss) > 1e-6:
            raise ValueError(f"Incorrect onset/severity metadata in {path}")
        if int(row["fault_active"]) != int(motor > 0 and t >= onset):
            raise ValueError(f"Incorrect actual fault activation in {path} at {idx}")
        last_time = t
    if last_time < onset + 1.4:
        raise ValueError(f"Truncated simulation in {path}")
    return rows


def gyro_decision(rows, seed, onset, loss, motor, noise_std):
    # Offline observation-only perturbation; dynamics/PID are unchanged.
    key = f"aegisland-h2-noise:v1:{seed}:{onset}:{loss}:{motor}:{noise_std}"
    rng_seed = int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:8], "big")
    rng = random.Random(rng_seed)
    streak = 0
    for row in rows:
        t = float(row["time_s"])
        if t > onset + POST_ONSET_WINDOW_S:
            break
        altitude = float(row["z_m"])
        if t >= onset and altitude < CENSOR_ALTITUDE_M:
            break
        p = float(row["gyro_p_rps"]) + (rng.gauss(0.0, noise_std) if noise_std else 0.0)
        q = float(row["gyro_q_rps"]) + (rng.gauss(0.0, noise_std) if noise_std else 0.0)
        streak = streak + 1 if abs(p) >= THRESHOLD_P and abs(q) >= THRESHOLD_Q else 0
        if streak >= ALERT_STREAK:
            predicted = MOTOR_QUADRANTS[(1 if p > 0 else -1, 1 if q > 0 else -1)]
            premature = bool(t < onset and motor != 0)
            return {
                "raw_prediction": predicted,
                "scored_prediction": PREMATURE_COLUMN if premature else predicted,
                "alert_time_s": t,
                "alert_altitude_m": altitude,
                "premature": premature,
            }
    return {
        "raw_prediction": 0, "scored_prediction": 0,
        "alert_time_s": None, "alert_altitude_m": None, "premature": False,
    }


def metric(records):
    matrix = [[0] * 6 for _ in range(5)]
    for r in records:
        matrix[r["truth_motor"]][r["scored_prediction"]] += 1
    if not all(sum(row) for row in matrix):
        raise ValueError("Missing true motor class in score set")
    recalls = [matrix[i][i] / sum(matrix[i]) for i in range(5)]
    fault = [r for r in records if r["truth_motor"] != 0]
    proper = [r for r in fault if r["scored_prediction"] == r["truth_motor"]]
    delay = [r["alert_time_s"] - r["onset_s"] for r in proper]
    return {
        "scenario_observations": len(records),
        "balanced_accuracy": sum(recalls) / 5,
        "class_recall": dict(zip(CLASSES, recalls)),
        "healthy_false_alert_rate": 1 - recalls[0],
        "fault_correct_isolation_rate": len(proper) / len(fault),
        "fault_detected_any_motor_rate": sum(r["scored_prediction"] in (1, 2, 3, 4) for r in fault) / len(fault),
        "premature_alert_count": sum(r["premature"] for r in fault),
        "median_correct_alert_delay_s": statistics.median(delay) if delay else None,
        "confusion_matrix_rows_truth_cols_healthy_m1_m2_m3_m4_premature": matrix,
    }


def cluster_bootstrap(records):
    by_seed = {seed: [r for r in records if r["seed"] == seed] for seed in SEEDS}
    if any(len(rs) != 2 * 5 for rs in by_seed.values()):
        raise ValueError("Primary H2 strata must contain both onsets and five classes per seed")
    rng = random.Random(BOOTSTRAP_SEED)
    values = []
    for _ in range(BOOTSTRAP_DRAWS):
        selected = [row for _ in SEEDS for row in by_seed[rng.choice(SEEDS)]]
        values.append(metric(selected)["balanced_accuracy"])
    values.sort()
    def percentile(p):
        pos = p * (len(values) - 1)
        idx = int(pos)
        return values[idx] + (values[min(idx + 1, len(values) - 1)] - values[idx]) * (pos - idx)
    return {
        "cluster_unit": "complete command seed (both onsets, all five conditions)",
        "clusters": len(SEEDS),
        "draws": BOOTSTRAP_DRAWS,
        "random_seed": BOOTSTRAP_SEED,
        "percentile_95_interval": [percentile(.025), percentile(.975)],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    expected = {path_name(s, o, 0, 0) for s in SEEDS for o in ONSETS}
    expected |= {path_name(s, o, loss, motor)
                 for s in SEEDS for o in ONSETS for loss in FAULT_LOSSES for motor in range(1, 5)}
    seen = {path.name for path in args.raw_dir.glob("*.csv")}
    if seen != expected or len(expected) != 108:
        raise ValueError(f"Expected 108 complete unique raw traces; missing={sorted(expected - seen)}; unexpected={sorted(seen - expected)}")

    raw = {}
    manifest = []
    for seed in SEEDS:
        for onset in ONSETS:
            cases = [(0.0, 0)] + [(loss, motor) for loss in FAULT_LOSSES for motor in range(1, 5)]
            for loss, motor in cases:
                filename = path_name(seed, onset, loss, motor)
                path = args.raw_dir / filename
                rows = read_checked(path, seed, onset, loss, motor)
                raw[(seed, onset, loss, motor)] = rows
                manifest.append({"filename": filename, "sha256": sha256(path),
                                 "measurements": len(rows), "seed": seed,
                                 "onset_s": onset, "loss_fraction": loss, "motor": motor})

    decisions = []
    for seed in SEEDS:
        for onset in ONSETS:
            for loss in FAULT_LOSSES:
                for noise_std in NOISE_LEVELS:
                    for motor in range(5):
                        actual_loss = loss if motor else 0.0
                        rows = raw[(seed, onset, actual_loss, motor)]
                        decision = gyro_decision(rows, seed, onset, actual_loss, motor, noise_std)
                        decisions.append({"seed": seed, "onset_s": onset,
                                          "loss_fraction": loss, "noise_std_rps": noise_std,
                                          "truth_motor": motor, **decision})
    if len(decisions) != 240:
        raise ValueError("Expected 240 repeated scenario-observations")

    primary = [r for r in decisions if r["loss_fraction"] == 0.5 and r["noise_std_rps"] == 0.5]
    if len(primary) != 60:
        raise ValueError("Primary comparison has missing scenarios")
    primary_stats = metric(primary)
    factorial = []
    for onset in ONSETS:
        for loss in FAULT_LOSSES:
            for noise in NOISE_LEVELS:
                group = [r for r in decisions if
                         (r["onset_s"], r["loss_fraction"], r["noise_std_rps"]) == (onset, loss, noise)]
                if len(group) != 30:
                    raise ValueError("Missing factorial cell")
                factorial.append({"onset_s": onset, "loss_fraction": loss, "noise_std_rps": noise,
                                  **metric(group)})

    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "scenario_predictions.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(decisions[0]))
        writer.writeheader()
        writer.writerows(decisions)
    result = {
        "status": "within_simulator_h2_stress_test",
        "primary_condition": "50 percent actuator output loss, offline gyro Gaussian sigma=0.5 rad/s, pooled onsets 8 and 12 seconds",
        "primary_metric": "five-class balanced accuracy, one classification per seed × onset × condition",
        "primary_result": primary_stats,
        "primary_cluster_interval": cluster_bootstrap(primary),
        "factorial_results": factorial,
        "always_healthy_balanced_accuracy": 0.2,
        "fresh_command_seeds": SEEDS,
        "onsets_s": ONSETS, "fault_loss_fractions": FAULT_LOSSES,
        "offline_gyro_noise_std_rps": NOISE_LEVELS,
        "physical_simulations": len(manifest),
        "repeated_scenario_observations": len(decisions),
        "simulation_only": True,
        "threshold_frozen_from_h1": True,
        "real_flight_safety_claim": False,
        "git_sha": os.environ.get("GITHUB_SHA", "local-uncommitted"),
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "evaluator_sha256": sha256(Path(__file__)),
        "input_manifest": manifest,
        "caveats": [
            "One simulator and one vehicle plant; changed timing and partial loss are in-model stressors, not external validation.",
            "Six fresh command seeds are six independent motion clusters; 240 conditions are repeated measurements, not independent experiments.",
            "Noise is applied offline only to gyro p and q; flight dynamics and PID use unchanged ground-truth simulated gyro.",
            "Thresholds/sign mapping developed on prior H1 pilot; no fitting or retuning using H2 outcomes.",
            "No physical flight, intervention, recovery, or real-world safety guarantee.",
        ],
    }
    (args.output_dir / "h2_results.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"primary_balanced_accuracy": primary_stats["balanced_accuracy"],
                      "primary_confusion": primary_stats["confusion_matrix_rows_truth_cols_healthy_m1_m2_m3_m4_premature"],
                      "ci": result["primary_cluster_interval"]["percentile_95_interval"],
                      "simulations": len(manifest)}, indent=2))


if __name__ == "__main__":
    main()
