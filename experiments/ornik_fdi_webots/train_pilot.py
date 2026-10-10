#!/usr/bin/env python3
"""Fit and score a small trajectory-held-out NumPy MLP for the Webots pilot."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path

import numpy as np

WINDOW_LENGTH = 100
WINDOW_STRIDE = 20
FEATURES = (
    "x_m", "y_m", "z_m", "gyro_p_rps", "gyro_q_rps", "gyro_r_rps",
    "cmd_m1", "cmd_m2", "cmd_m3", "cmd_m4",
)
TRAIN_SEEDS = {11, 23}
HOLDOUT_SEED = 47
CLASS_NAMES = ["healthy", "motor_1", "motor_2", "motor_3", "motor_4"]


def load_trace(path: Path):
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) < WINDOW_LENGTH:
        raise ValueError(f"{path.name} has only {len(rows)} rows; needs {WINDOW_LENGTH} samples")
    seed = int(rows[0]["seed"])
    motor = int(rows[0]["failed_motor"])
    if any(int(row["seed"]) != seed or int(row["failed_motor"]) != motor for row in rows):
        raise ValueError(f"{path.name} changes seed or fault label within a trajectory")
    values = np.asarray([[float(row[name]) for name in FEATURES] for row in rows], dtype=np.float32)
    labels = np.asarray([
        int(row["failed_motor"]) if int(row["fault_active"]) else 0
        for row in rows
    ], dtype=np.int64)
    times = np.asarray([float(row["time_s"]) for row in rows], dtype=np.float64)
    if not np.isfinite(values).all() or not np.isfinite(times).all():
        raise ValueError(f"{path.name} contains a non-finite input")
    return seed, motor, values, labels, times


def windows(values, labels, times, path_name):
    xs, ys, ends = [], [], []
    for end in range(WINDOW_LENGTH - 1, len(values), WINDOW_STRIDE):
        xs.append(values[end - WINDOW_LENGTH + 1:end + 1].reshape(-1))
        ys.append(labels[end])
        ends.append(times[end])
    return np.asarray(xs, dtype=np.float32), np.asarray(ys, dtype=np.int64), np.asarray(ends), path_name


def softmax(logits):
    shifted = logits - logits.max(axis=1, keepdims=True)
    exps = np.exp(shifted)
    return exps / exps.sum(axis=1, keepdims=True)


def fit_mlp(x_train, y_train, seed=20261010, epochs=80, batch_size=64, hidden=24):
    rng = np.random.default_rng(seed)
    input_size, class_count = x_train.shape[1], len(CLASS_NAMES)
    w1 = rng.normal(0.0, np.sqrt(2.0 / input_size), (input_size, hidden)).astype(np.float32)
    b1 = np.zeros(hidden, dtype=np.float32)
    w2 = rng.normal(0.0, np.sqrt(2.0 / hidden), (hidden, class_count)).astype(np.float32)
    b2 = np.zeros(class_count, dtype=np.float32)
    params = [w1, b1, w2, b2]
    first = [np.zeros_like(p) for p in params]
    second = [np.zeros_like(p) for p in params]
    step = 0
    lr, beta1, beta2, eps = 0.001, 0.9, 0.999, 1e-8

    for _ in range(epochs):
        order = rng.permutation(len(y_train))
        for start in range(0, len(order), batch_size):
            idx = order[start:start + batch_size]
            xb, yb = x_train[idx], y_train[idx]
            z1 = xb @ w1 + b1
            h1 = np.maximum(z1, 0.0)
            probs = softmax(h1 @ w2 + b2)
            probs[np.arange(len(yb)), yb] -= 1.0
            probs /= max(1, len(yb))
            dw2 = h1.T @ probs
            db2 = probs.sum(axis=0)
            dz1 = (probs @ w2.T) * (z1 > 0.0)
            dw1 = xb.T @ dz1
            db1 = dz1.sum(axis=0)
            step += 1
            for p, g, m, v in zip(params, [dw1, db1, dw2, db2], first, second):
                m *= beta1
                m += (1.0 - beta1) * g
                v *= beta2
                v += (1.0 - beta2) * np.square(g)
                m_hat = m / (1.0 - beta1 ** step)
                v_hat = v / (1.0 - beta2 ** step)
                p -= lr * m_hat / (np.sqrt(v_hat) + eps)
    return params


def predict(params, x):
    w1, b1, w2, b2 = params
    return np.argmax(np.maximum(x @ w1 + b1, 0.0) @ w2 + b2, axis=1)


def score(y_true, y_pred):
    count = len(CLASS_NAMES)
    matrix = np.zeros((count, count), dtype=np.int64)
    for truth, pred in zip(y_true, y_pred):
        matrix[int(truth), int(pred)] += 1
    recalls = [
        float(matrix[i, i] / matrix[i].sum()) if matrix[i].sum() else None
        for i in range(count)
    ]
    f1s = []
    for i in range(count):
        tp = matrix[i, i]
        fp = matrix[:, i].sum() - tp
        fn = matrix[i, :].sum() - tp
        denom = 2 * tp + fp + fn
        f1s.append(float(2 * tp / denom) if denom else None)
    available = [value for value in recalls if value is not None]
    macro_f1 = [value for value in f1s if value is not None]
    return {
        "window_accuracy": float(np.mean(y_true == y_pred)),
        "balanced_accuracy": float(np.mean(available)) if available else None,
        "macro_f1": float(np.mean(macro_f1)) if macro_f1 else None,
        "class_recall": dict(zip(CLASS_NAMES, recalls)),
        "class_f1": dict(zip(CLASS_NAMES, f1s)),
        "confusion_matrix_rows_truth_cols_prediction": matrix.tolist(),
    }


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    train_x, train_y, holdout_x, holdout_y = [], [], [], []
    holdout_rows = []
    manifest = []
    for path in sorted(args.input_dir.glob("*.csv")):
        seed, motor, values, labels, times = load_trace(path)
        x, y, t, _ = windows(values, labels, times, path.name)
        if seed in TRAIN_SEEDS:
            train_x.append(x)
            train_y.append(y)
            split = "train"
        elif seed == HOLDOUT_SEED:
            holdout_x.append(x)
            holdout_y.append(y)
            holdout_rows.extend((path.name, float(end_time)) for end_time in t)
            split = "heldout_trajectory"
        else:
            raise ValueError(f"unregistered seed {seed} in {path.name}")
        manifest.append({
            "file": path.name,
            "sha256": sha256(path),
            "seed": seed,
            "failed_motor": motor,
            "rows": len(values),
            "windows": len(x),
            "split": split,
            "first_time_s": float(times[0]),
            "last_time_s": float(times[-1]),
        })

    expected = {(seed, motor) for seed in (11, 23, 47) for motor in range(5)}
    observed = {(item["seed"], item["failed_motor"]) for item in manifest}
    if observed != expected or len(manifest) != len(expected):
        raise ValueError(f"expected 15 unique seed/motor traces, found {len(manifest)}")
    x_train = np.concatenate(train_x)
    y_train = np.concatenate(train_y)
    x_holdout = np.concatenate(holdout_x)
    y_holdout = np.concatenate(holdout_y)
    if len(set(y_train.tolist())) != len(CLASS_NAMES) or len(set(y_holdout.tolist())) != len(CLASS_NAMES):
        raise ValueError("training and held-out trajectories must each cover all five classes")

    mean = x_train.mean(axis=0)
    scale = x_train.std(axis=0)
    scale[scale < 1e-6] = 1.0
    normalized_train = ((x_train - mean) / scale).astype(np.float32)
    normalized_holdout = ((x_holdout - mean) / scale).astype(np.float32)
    params = fit_mlp(normalized_train, y_train)
    predictions = predict(params, normalized_holdout)
    metrics = score(y_holdout, predictions)

    np.savez_compressed(
        args.output_dir / "pilot_detector.npz",
        mean=mean, scale=scale, w1=params[0], b1=params[1], w2=params[2], b2=params[3],
    )
    with (args.output_dir / "heldout_window_predictions.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "trace_file", "window_end_time_s", "truth", "prediction",
            "truth_name", "prediction_name",
        ])
        writer.writerows([
            (trace, f"{time_s:.6f}", int(truth), int(pred),
             CLASS_NAMES[int(truth)], CLASS_NAMES[int(pred)])
            for (trace, time_s), truth, pred in zip(holdout_rows, y_holdout, predictions)
        ])
    model_path = args.output_dir / "pilot_detector.npz"
    result = {
        "status": "exploratory_pilot_only",
        "paper_reproduction": False,
        "physical_hardware_used": False,
        "controller_recovery_evaluated": False,
        "px4_or_gazebo_evaluated": False,
        "window_length_samples": WINDOW_LENGTH,
        "window_stride_samples": WINDOW_STRIDE,
        "feature_order_per_sample": list(FEATURES),
        "classes": CLASS_NAMES,
        "training_seeds": sorted(TRAIN_SEEDS),
        "heldout_seed": HOLDOUT_SEED,
        "training_random_seed": 20261010,
        "network": {"hidden_units": 24, "epochs": 80, "batch_size": 64, "optimizer": "Adam", "learning_rate": 0.001},
        "fault_onset_s": 10.0,
        "bitcraze_repository": "https://github.com/bitcraze/crazyflie-simulation",
        "bitcraze_commit": "7e93752dbc803af2488c1db46bb79b3da55f5d8c",
        "webots_image": "cyberbotics/webots:R2025a-ubuntu22.04",
        "training_windows": len(y_train),
        "heldout_windows": len(y_holdout),
        "training_class_counts": {CLASS_NAMES[i]: int((y_train == i).sum()) for i in range(len(CLASS_NAMES))},
        "heldout_class_counts": {CLASS_NAMES[i]: int((y_holdout == i).sum()) for i in range(len(CLASS_NAMES))},
        "metrics": metrics,
        "trajectories": manifest,
        "model_sha256": sha256(model_path),
        "git_sha": os.environ.get("GITHUB_SHA", "local-uncommitted"),
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
    }
    (args.output_dir / "pilot_metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    summary = [
        "# Hardware-free actuator FDI pilot results",
        "",
        "**Exploratory software pilot only. This is not a reproduction of Garg et al., a PX4/Gazebo result, or a safety claim.**",
        "",
        f"- Training windows: {len(y_train)} from complete trajectories with seeds {sorted(TRAIN_SEEDS)}.",
        f"- Held-out windows: {len(y_holdout)} from complete trajectories with seed {HOLDOUT_SEED}.",
        f"- Window accuracy: {metrics['window_accuracy']:.3f}.",
        f"- Balanced accuracy: {metrics['balanced_accuracy']:.3f}.",
        f"- Macro F1: {metrics['macro_f1']:.3f}.",
        "- The held-out set contains only one trajectory per class and adjacent windows overlap. Do not interpret these metrics as a generalization estimate.",
        "",
        "See `pilot_metrics.json` for per-class counts, confusion matrix, seeds, model/source hashes, and full run settings.",
    ]
    (args.output_dir / "RESULTS.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("\n".join(summary))


if __name__ == "__main__":
    main()
