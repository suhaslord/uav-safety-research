#!/usr/bin/env python3
"""Frozen trajectory-level generalization test for the AegisLand Webots motor FDI pilot.

No results are claimed unless Webots creates all registered trajectories and this
script completes. Import the original pilot model unchanged; do not tune on test.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from collections import Counter
from pathlib import Path

import numpy as np
from train_pilot import (
    CLASS_NAMES, FEATURES, WINDOW_LENGTH, fit_mlp, load_trace,
    predict, score, sha256, windows,
)

TRAIN_SEEDS = (11, 23, 29, 31)
DEVELOPMENT_SEEDS = (41, 43)
TEST_SEEDS = (47, 53, 59, 61, 67, 71, 73, 79)
GROUPS = {"train": TRAIN_SEEDS, "development": DEVELOPMENT_SEEDS, "test": TEST_SEEDS}
FAULT_ONSET_S = 10.0
EVALUATION_START_S = 12.0  # deliberately excludes ambiguous onset windows
EVALUATION_END_S = 22.0
MODEL_SEED = 20261011
BOOTSTRAP_SEED = 20261012
BOOTSTRAP_DRAWS = 2000
COMMAND_FEATURES = tuple(range(6, len(FEATURES)))


def ensure_complete_files(input_dir: Path):
    expected = {(seed, motor) for seeds in GROUPS.values() for seed in seeds for motor in range(5)}
    seen = {}
    for path in sorted(input_dir.glob("*.csv")):
        seed, motor, values, labels, times = load_trace(path)
        key = (seed, motor)
        if key not in expected or key in seen:
            raise ValueError(f"Unexpected or duplicate seed/motor: {key} in {path.name}")
        if len(times) < 2 or not np.all(np.diff(times) > 0):
            raise ValueError(f"Non-increasing timestamps in {path}")
        if times[-1] < EVALUATION_END_S:
            raise ValueError(f"Trace ends before evaluation period: {path}")
        if np.any(labels[times < FAULT_ONSET_S] != 0):
            raise ValueError(f"Fault label appears before 10 seconds: {path}")
        if motor == 0 and np.any(labels != 0):
            raise ValueError(f"Healthy trace contains fault labels: {path}")
        if motor != 0 and np.any(labels[times >= FAULT_ONSET_S] != motor):
            raise ValueError(f"Wrong fault label after onset: {path}")
        seen[key] = (path, values, labels, times)
    if set(seen) != expected:
        raise ValueError(f"Missing {sorted(expected - set(seen))}; found {len(seen)} of {len(expected)}")
    return seen


def select_columns(x: np.ndarray, command_only: bool):
    if not command_only:
        return x
    return x.reshape(len(x), WINDOW_LENGTH, len(FEATURES))[:, :, COMMAND_FEATURES].reshape(len(x), -1)


def train_detector(traces, command_only: bool):
    xs, ys = [], []
    for seed in TRAIN_SEEDS:
        for motor in range(5):
            path, values, labels, times = traces[(seed, motor)]
            x, y, _, _ = windows(values, labels, times, path.name)
            xs.append(select_columns(x, command_only))
            ys.append(y)
    x = np.concatenate(xs)
    y = np.concatenate(ys)
    if len(set(y.tolist())) != 5:
        raise ValueError("Missing training class")
    mean = x.mean(axis=0)
    std = x.std(axis=0)
    std[std < 1e-6] = 1.0
    normalized = ((x - mean) / std).astype(np.float32)
    params = fit_mlp(normalized, y, seed=MODEL_SEED, epochs=80, batch_size=64, hidden=24)
    return mean, std, params


def classify_trace(trace, detector, command_only: bool):
    path, values, labels, times = trace
    x, y, ends, _ = windows(values, labels, times, path.name)
    window_mask = (ends >= EVALUATION_START_S) & (ends <= EVALUATION_END_S)
    if not window_mask.any():
        raise ValueError(f"No scored windows in {path}")
    x = select_columns(x[window_mask], command_only)
    mean, std, params = detector
    pred = predict(params, ((x - mean) / std).astype(np.float32))
    if not np.isin(pred, np.arange(5)).all():
        raise ValueError("Invalid predicted class")
    # Predeclared majority vote; exact ties resolve to lower indexed class.
    return int(np.argmax(np.bincount(pred, minlength=5))), int(len(pred))


def metric(rows, pred_field):
    y = np.asarray([row["failed_motor"] for row in rows], dtype=np.int64)
    p = np.asarray([row[pred_field] for row in rows], dtype=np.int64)
    return score(y, p)


def cluster_bootstrap(test_rows, pred_field):
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    seeds = np.asarray(TEST_SEEDS)
    by_seed = {seed: [row for row in test_rows if row["seed"] == seed] for seed in TEST_SEEDS}
    if any(len(group) != 5 for group in by_seed.values()):
        raise ValueError("Every test seed must contain five paired motor conditions")
    values = []
    for _ in range(BOOTSTRAP_DRAWS):
        picked = rng.choice(seeds, size=len(seeds), replace=True)
        sample = [row for seed in picked for row in by_seed[int(seed)]]
        values.append(metric(sample, pred_field)["balanced_accuracy"])
    return {
        "unit": "command_seed_cluster (five paired motor conditions each)",
        "seed_clusters": len(TEST_SEEDS),
        "draws": BOOTSTRAP_DRAWS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "percentile_95_interval": [
            float(np.percentile(values, 2.5)),
            float(np.percentile(values, 97.5)),
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    traces = ensure_complete_files(args.input_dir)
    full = train_detector(traces, command_only=False)
    commands = train_detector(traces, command_only=True)
    # Archive the exact trained weights and train-only normalization statistics.
    np.savez_compressed(
        args.output_dir / "frozen_models.npz",
        full_mean=full[0], full_std=full[1],
        full_w1=full[2][0], full_b1=full[2][1],
        full_w2=full[2][2], full_b2=full[2][3],
        commands_mean=commands[0], commands_std=commands[1],
        commands_w1=commands[2][0], commands_b1=commands[2][1],
        commands_w2=commands[2][2], commands_b2=commands[2][3],
    )
    records = []
    provenance = []
    for group, seeds in GROUPS.items():
        for seed in seeds:
            for motor in range(5):
                trace = traces[(seed, motor)]
                full_pred, count = classify_trace(trace, full, False)
                command_pred, n_commands = classify_trace(trace, commands, True)
                if count != n_commands:
                    raise ValueError("Inconsistent evaluation window count")
                records.append({
                    "split": group, "seed": seed, "failed_motor": motor,
                    "full_prediction": full_pred,
                    "command_only_prediction": command_pred,
                    "always_healthy_prediction": 0,
                    "scored_windows": count,
                })
                provenance.append({
                    "split": group, "seed": seed, "motor": motor,
                    "path": trace[0].name, "sha256": sha256(trace[0]),
                    "samples": len(trace[2]),
                })
    test_rows = [r for r in records if r["split"] == "test"]
    dev_rows = [r for r in records if r["split"] == "development"]
    if len(test_rows) != 5 * len(TEST_SEEDS):
        raise ValueError("Unexpected test-trace count")
    heldout = {}
    for field in ("full_prediction", "command_only_prediction", "always_healthy_prediction"):
        heldout[field] = {
            "trajectory_level": metric(test_rows, field),
            "seed_cluster_bootstrap": cluster_bootstrap(test_rows, field),
        }
    report = {
        "status": "simulation_only_independent_command_seed_holdout",
        "research_question": "Does a single-motor fault classifier transfer to unseen commanded motions in the same Webots plant?",
        "independent_physical_dataset": False,
        "paper_reproduction": False,
        "real_flight_safety_evidence": False,
        "validation_tuned_on_test": False,
        "model": "Original one-hidden-layer NumPy pilot MLP; unchanged recipe",
        "train_seeds": list(TRAIN_SEEDS),
        "development_seeds": list(DEVELOPMENT_SEEDS),
        "protected_test_seeds": list(TEST_SEEDS),
        "training_seed": MODEL_SEED,
        "fault_onset_seconds": FAULT_ONSET_S,
        "post_onset_evaluation_seconds": [EVALUATION_START_S, EVALUATION_END_S],
        "decision_rule": "one majority-voted class per complete trajectory; ties choose lowest index",
        "primary_metric": "test trajectory-level five-class balanced accuracy",
        "test_seed_clusters": len(TEST_SEEDS),
        "test_trajectories": len(test_rows),
        "holdout": heldout,
        "development_descriptive_only": {
            "full": metric(dev_rows, "full_prediction"),
            "command_only": metric(dev_rows, "command_only_prediction"),
        },
        "git_sha": os.environ.get("GITHUB_SHA", "local-uncommitted"),
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "frozen_models_sha256": sha256(args.output_dir / "frozen_models.npz"),
        "pilot_training_script_sha256": sha256(Path(__file__).with_name("train_pilot.py")),
        "evaluation_script_sha256": sha256(Path(__file__)),
        "input_manifest": provenance,
        "limits": [
            "Eight test motion seeds give a wide uncertainty interval; seed-level rather than window-level replication.",
            "Only a single plant, simulator, full motor loss at one onset time, and fixed command distribution.",
            "No tests of smaller partial loss, fault onset jitter, controller recovery, or physical flight.",
            "The command-only ablation checks for a possible command-signature shortcut.",
            "No threshold or classifier selection uses protected test data.",
        ],
    }
    with (args.output_dir / "trajectory_predictions.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)
    (args.output_dir / "heldout_metrics.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": report["status"],
        "test_trajectories": len(test_rows),
        "full_model_balanced_accuracy": heldout["full_prediction"]["trajectory_level"]["balanced_accuracy"],
        "command_only_balanced_accuracy": heldout["command_only_prediction"]["trajectory_level"]["balanced_accuracy"],
        "always_healthy_balanced_accuracy": heldout["always_healthy_prediction"]["trajectory_level"]["balanced_accuracy"],
    }, indent=2))


if __name__ == "__main__":
    main()
