#!/usr/bin/env python3
"""Offline single-fault resilience study on one genuine Webots baseline.

The same baseline, constant-velocity Kalman filter, initial covariance,
process/measurement covariance, fault window, and random seed policy are used
for every case. Only one degradation mechanism changes at a time.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

NOISE_SIGMAS_M = [0.04, 0.08, 0.16, 0.32]
BIAS_MAGNITUDES_M = [0.05, 0.10, 0.20, 0.40]
DROPOUT_DURATIONS_S = [0.5, 1.0, 2.0, 4.0]
N_NOISE_TRIALS = 30
FAULT_START_S = 12.0
BASE_SEED = 20260820

# Fixed filter assumptions.
POSITION_MEAS_SIGMA_M = 0.02
ACCEL_PROCESS_SIGMA_MPS2 = 0.35
INITIAL_POSITION_SIGMA_M = 0.05
INITIAL_VELOCITY_SIGMA_MPS = 0.20


@dataclass
class Baseline:
    t: np.ndarray
    xy: np.ndarray
    source_sha256: str


def rmse(err: np.ndarray) -> float:
    if err.size == 0:
        return float("nan")
    return float(np.sqrt(np.mean(np.sum(np.square(err), axis=1))))


def load_baseline(path: Path) -> Baseline:
    required = {"time_s", "x_m", "y_m"}
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) < 100:
        raise ValueError(f"baseline has only {len(rows)} rows; expected >= 100")
    if not required.issubset(rows[0]):
        raise ValueError(f"baseline missing columns: {sorted(required - set(rows[0]))}")

    t = np.array([float(r["time_s"]) for r in rows], dtype=float)
    xy = np.array([[float(r["x_m"]), float(r["y_m"])] for r in rows], dtype=float)

    if not np.isfinite(t).all() or not np.isfinite(xy).all():
        raise ValueError("baseline contains non-finite values")
    if not np.all(np.diff(t) > 0):
        raise ValueError("timestamps are not strictly increasing")

    path_extent = float(np.max(np.linalg.norm(xy - xy[0], axis=1)))
    if path_extent < 0.25:
        raise ValueError(f"baseline lateral path extent {path_extent:.3f} m is too small")

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return Baseline(t=t, xy=xy, source_sha256=digest)


class CVKalman2D:
    def __init__(self, x0: np.ndarray):
        self.x = np.array([x0[0], x0[1], 0.0, 0.0], dtype=float)
        self.P = np.diag([
            INITIAL_POSITION_SIGMA_M**2,
            INITIAL_POSITION_SIGMA_M**2,
            INITIAL_VELOCITY_SIGMA_MPS**2,
            INITIAL_VELOCITY_SIGMA_MPS**2,
        ])
        self.H = np.array([[1.0, 0.0, 0.0, 0.0],
                           [0.0, 1.0, 0.0, 0.0]])
        self.R = np.eye(2) * POSITION_MEAS_SIGMA_M**2

    def step(self, dt: float, z: np.ndarray | None) -> np.ndarray:
        F = np.array([
            [1.0, 0.0, dt, 0.0],
            [0.0, 1.0, 0.0, dt],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ])
        q = ACCEL_PROCESS_SIGMA_MPS2**2
        dt2, dt3, dt4 = dt**2, dt**3, dt**4
        Q = q * np.array([
            [dt4/4, 0.0, dt3/2, 0.0],
            [0.0, dt4/4, 0.0, dt3/2],
            [dt3/2, 0.0, dt2, 0.0],
            [0.0, dt3/2, 0.0, dt2],
        ])

        self.x = F @ self.x
        self.P = F @ self.P @ F.T + Q

        if z is not None:
            innovation = z - self.H @ self.x
            S = self.H @ self.P @ self.H.T + self.R
            K = self.P @ self.H.T @ np.linalg.inv(S)
            self.x = self.x + K @ innovation
            I = np.eye(4)
            self.P = (I - K @ self.H) @ self.P

        return self.x[:2].copy()


def run_filter(t: np.ndarray, measurements: np.ndarray) -> np.ndarray:
    kf = CVKalman2D(measurements[0] if np.isfinite(measurements[0]).all() else np.zeros(2))
    est = np.empty_like(measurements)
    est[0] = kf.x[:2]
    for i in range(1, len(t)):
        dt = float(t[i] - t[i - 1])
        z = measurements[i]
        z_or_none = None if not np.isfinite(z).all() else z
        est[i] = kf.step(dt, z_or_none)
    return est


def recovery_time(t: np.ndarray, err_norm: np.ndarray, fault_end: float, threshold_m: float = 0.10,
                  dwell_s: float = 0.5) -> float:
    after = np.flatnonzero(t >= fault_end)
    if len(after) == 0:
        return float("nan")
    for idx in after:
        end_t = t[idx] + dwell_s
        j = np.searchsorted(t, end_t, side="left")
        if j >= len(t):
            break
        if np.all(err_norm[idx:j+1] <= threshold_m):
            return float(t[idx] - fault_end)
    return float("nan")


def case_metrics(t, truth, measurements, est, fault_start, fault_end):
    est_err = est - truth
    meas_valid = np.isfinite(measurements).all(axis=1)
    meas_err = measurements[meas_valid] - truth[meas_valid]
    in_fault = (t >= fault_start) & (t <= fault_end)
    return {
        "measurement_rmse_m": rmse(meas_err),
        "measurement_coverage": float(np.mean(meas_valid)),
        "estimator_rmse_m": rmse(est_err),
        "fault_window_estimator_rmse_m": rmse(est_err[in_fault]),
        "max_estimator_error_m": float(np.max(np.linalg.norm(est_err, axis=1))),
        "recovery_time_s": recovery_time(
            t, np.linalg.norm(est_err, axis=1), fault_end
        ),
    }


def inject_noise(truth, sigma, seed):
    rng = np.random.default_rng(seed)
    return truth + rng.normal(0.0, sigma, size=truth.shape)


def inject_bias(t, truth, magnitude):
    out = truth.copy()
    mask = (t >= FAULT_START_S) & (t < FAULT_START_S + 4.0)
    # Fixed +x bias so direction is identical across severity values.
    out[mask, 0] += magnitude
    return out, FAULT_START_S + 4.0


def inject_dropout(t, truth, duration):
    out = truth.copy()
    mask = (t >= FAULT_START_S) & (t < FAULT_START_S + duration)
    out[mask] = np.nan
    return out, FAULT_START_S + duration


def write_summary(path: Path, records: list[dict]):
    fieldnames = [
        "fault_type", "severity", "trial",
        "measurement_rmse_m", "measurement_coverage", "estimator_rmse_m",
        "fault_window_estimator_rmse_m", "max_estimator_error_m",
        "recovery_time_s",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def aggregate(records):
    grouped = {}
    for r in records:
        key = (r["fault_type"], r["severity"])
        grouped.setdefault(key, []).append(r)
    output = []
    for (fault_type, severity), group in sorted(grouped.items()):
        def mean_key(k):
            vals = [float(g[k]) for g in group if math.isfinite(float(g[k]))]
            return float(np.mean(vals)) if vals else float("nan")
        output.append({
            "fault_type": fault_type,
            "severity": severity,
            "trials": len(group),
            "measurement_rmse_m_mean": mean_key("measurement_rmse_m"),
            "measurement_coverage_mean": mean_key("measurement_coverage"),
            "estimator_rmse_m_mean": mean_key("estimator_rmse_m"),
            "fault_window_estimator_rmse_m_mean": mean_key("fault_window_estimator_rmse_m"),
            "max_estimator_error_m_mean": mean_key("max_estimator_error_m"),
            "recovery_time_s_mean": mean_key("recovery_time_s"),
        })
    return output


def write_report(path: Path, metadata: dict, agg: list[dict]):
    lines = [
        "# UNM Crazyflie / Webots single-fault results",
        "",
        "This report is generated from one genuine Webots baseline trajectory. The same",
        "baseline and the same 2D constant-velocity Kalman-filter configuration are reused",
        "for every case. Only one measurement degradation changes at a time.",
        "",
        f"- Baseline SHA-256: `{metadata['baseline_sha256']}`",
        f"- Samples: {metadata['samples']}",
        f"- Duration: {metadata['duration_s']:.3f} s",
        f"- Lateral path extent: {metadata['path_extent_m']:.3f} m",
        f"- Fault start: {metadata['fault_start_s']:.1f} s",
        "",
        "## Aggregate metrics",
        "",
        "| Fault | Severity | Trials | Measurement coverage | Estimator RMSE (m) | Fault-window estimator RMSE (m) | Max estimator error (m) | Recovery time (s) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in agg:
        def fnum(v, digits=4):
            v = float(v)
            return "n/a" if not math.isfinite(v) else f"{v:.{digits}f}"
        lines.append(
            f"| {row['fault_type']} | {row['severity']} | {row['trials']} | "
            f"{fnum(row['measurement_coverage_mean'], 3)} | "
            f"{fnum(row['estimator_rmse_m_mean'])} | "
            f"{fnum(row['fault_window_estimator_rmse_m_mean'])} | "
            f"{fnum(row['max_estimator_error_m_mean'])} | "
            f"{fnum(row['recovery_time_s_mean'], 3)} |"
        )
    lines += [
        "",
        "## Interpretation guardrails",
        "",
        "- These are **simulation results**, not physical-flight results.",
        "- The position faults are injected offline into the Webots position trace; the underlying trajectory is unchanged.",
        "- Noise is zero-mean Gaussian position noise. Bias is a fixed +x offset during a 4 s fault window.",
        "- Dropout means the filter receives no position update during the dropout window and only predicts forward.",
        "- A lower estimator RMSE is better. Recovery time is the first time after the fault ends that position error stays at or below 0.10 m for 0.5 s.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("baseline_csv", type=Path)
    ap.add_argument("--out-dir", type=Path, default=Path("unm_results"))
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    baseline = load_baseline(args.baseline_csv)
    t, truth = baseline.t, baseline.xy
    records = []

    # Nominal: no injected degradation.
    nominal_est = run_filter(t, truth.copy())
    nominal = case_metrics(t, truth, truth.copy(), nominal_est, t[0], t[-1])
    records.append({"fault_type": "nominal", "severity": "0", "trial": 0, **nominal})

    for sigma in NOISE_SIGMAS_M:
        for trial in range(N_NOISE_TRIALS):
            measurements = inject_noise(truth, sigma, BASE_SEED + trial)
            est = run_filter(t, measurements)
            m = case_metrics(t, truth, measurements, est, t[0], t[-1])
            records.append({
                "fault_type": "noise",
                "severity": f"{sigma:.3f}_m_sigma",
                "trial": trial,
                **m,
            })

    for magnitude in BIAS_MAGNITUDES_M:
        measurements, fault_end = inject_bias(t, truth, magnitude)
        est = run_filter(t, measurements)
        m = case_metrics(t, truth, measurements, est, FAULT_START_S, fault_end)
        records.append({
            "fault_type": "bias",
            "severity": f"{magnitude:.3f}_m",
            "trial": 0,
            **m,
        })

    for duration in DROPOUT_DURATIONS_S:
        measurements, fault_end = inject_dropout(t, truth, duration)
        est = run_filter(t, measurements)
        m = case_metrics(t, truth, measurements, est, FAULT_START_S, fault_end)
        records.append({
            "fault_type": "dropout",
            "severity": f"{duration:.1f}_s",
            "trial": 0,
            **m,
        })

    write_summary(args.out_dir / "trial_metrics.csv", records)
    agg = aggregate(records)
    (args.out_dir / "aggregate.json").write_text(json.dumps(agg, indent=2) + "\n", encoding="utf-8")

    metadata = {
        "baseline_sha256": baseline.source_sha256,
        "samples": int(len(t)),
        "duration_s": float(t[-1] - t[0]),
        "path_extent_m": float(np.max(np.linalg.norm(truth - truth[0], axis=1))),
        "fault_start_s": FAULT_START_S,
        "noise_sigmas_m": NOISE_SIGMAS_M,
        "bias_magnitudes_m": BIAS_MAGNITUDES_M,
        "dropout_durations_s": DROPOUT_DURATIONS_S,
        "noise_trials_per_level": N_NOISE_TRIALS,
        "base_seed": BASE_SEED,
        "filter": {
            "model": "2D constant-velocity Kalman filter",
            "position_measurement_sigma_m": POSITION_MEAS_SIGMA_M,
            "acceleration_process_sigma_mps2": ACCEL_PROCESS_SIGMA_MPS2,
            "initial_position_sigma_m": INITIAL_POSITION_SIGMA_M,
            "initial_velocity_sigma_mps": INITIAL_VELOCITY_SIGMA_MPS,
        },
    }
    (args.out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    write_report(args.out_dir / "RESULTS.md", metadata, agg)

    print("UNM_ANALYSIS_COMPLETE")
    print(json.dumps(metadata, indent=2))
    for row in agg:
        print(row)


if __name__ == "__main__":
    main()
