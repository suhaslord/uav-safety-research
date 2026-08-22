#!/usr/bin/env python3
"""Extended diagnostics for the UNM Crazyflie Webots baseline.

This script never changes the Webots trajectory or the frozen Kalman-filter
assumptions from analyze_faults.py. It adds:
- estimator error time histories,
- noise/bias/dropout severity plots,
- a fixed-duration dropout timing sweep,
- normalized-innovation and covariance diagnostics,
- a generated research interpretation note.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from analyze_faults import (
    ACCEL_PROCESS_SIGMA_MPS2,
    BASE_SEED,
    INITIAL_POSITION_SIGMA_M,
    INITIAL_VELOCITY_SIGMA_MPS,
    POSITION_MEAS_SIGMA_M,
    load_baseline,
)

TURN_TIMES_S = np.array([10.0, 15.0, 20.0, 25.0])


def run_filter_diagnostics(t: np.ndarray, measurements: np.ndarray):
    initial = measurements[0] if np.isfinite(measurements[0]).all() else np.zeros(2)
    x = np.array([initial[0], initial[1], 0.0, 0.0], dtype=float)
    P = np.diag([
        INITIAL_POSITION_SIGMA_M**2,
        INITIAL_POSITION_SIGMA_M**2,
        INITIAL_VELOCITY_SIGMA_MPS**2,
        INITIAL_VELOCITY_SIGMA_MPS**2,
    ])
    H = np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]])
    R = np.eye(2) * POSITION_MEAS_SIGMA_M**2

    est = np.empty_like(measurements)
    est[0] = x[:2]
    innovation = np.full_like(measurements, np.nan)
    nis = np.full(len(t), np.nan)
    radial_sigma = np.zeros(len(t))
    radial_sigma[0] = math.sqrt(P[0, 0] + P[1, 1])

    for i in range(1, len(t)):
        dt = float(t[i] - t[i - 1])
        F = np.array([
            [1.0, 0.0, dt, 0.0],
            [0.0, 1.0, 0.0, dt],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ])
        q = ACCEL_PROCESS_SIGMA_MPS2**2
        dt2, dt3, dt4 = dt**2, dt**3, dt**4
        Q = q * np.array([
            [dt4 / 4, 0.0, dt3 / 2, 0.0],
            [0.0, dt4 / 4, 0.0, dt3 / 2],
            [dt3 / 2, 0.0, dt2, 0.0],
            [0.0, dt3 / 2, 0.0, dt2],
        ])

        x = F @ x
        P = F @ P @ F.T + Q

        z = measurements[i]
        if np.isfinite(z).all():
            y = z - H @ x
            S = H @ P @ H.T + R
            innovation[i] = y
            nis[i] = float(y.T @ np.linalg.inv(S) @ y)
            K = P @ H.T @ np.linalg.inv(S)
            x = x + K @ y
            P = (np.eye(4) - K @ H) @ P

        est[i] = x[:2]
        radial_sigma[i] = math.sqrt(P[0, 0] + P[1, 1])

    return est, innovation, nis, radial_sigma


def rolling_median(values: np.ndarray, window_samples: int) -> np.ndarray:
    out = np.full(len(values), np.nan)
    min_count = max(3, window_samples // 2)
    for i in range(len(values)):
        lo = max(0, i - window_samples + 1)
        window = values[lo:i + 1]
        finite = window[np.isfinite(window)]
        if len(finite) >= min_count:
            out[i] = float(np.median(finite))
    return out


def read_trial_metrics(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def severity_value(text: str) -> float:
    return float(text.split("_")[0])


def save_xy_plot(out: Path, t: np.ndarray, truth: np.ndarray):
    plt.figure(figsize=(7, 6))
    plt.plot(truth[:, 0], truth[:, 1])
    plt.scatter([truth[0, 0]], [truth[0, 1]], label="Start")
    plt.scatter([truth[-1, 0]], [truth[-1, 1]], label="End")
    plt.xlabel("x position (m)")
    plt.ylabel("y position (m)")
    plt.title("Genuine Webots Crazyflie baseline trajectory")
    plt.axis("equal")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out / "01_webots_xy_trajectory.png", dpi=180)
    plt.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("baseline_csv", type=Path)
    ap.add_argument("--results-dir", type=Path, required=True)
    args = ap.parse_args()
    args.results_dir.mkdir(parents=True, exist_ok=True)

    baseline = load_baseline(args.baseline_csv)
    t, truth = baseline.t, baseline.xy
    median_dt = float(np.median(np.diff(t)))
    rolling_samples = max(3, int(round(0.5 / median_dt)))

    cases = {"Nominal": truth.copy()}
    rng = np.random.default_rng(BASE_SEED)
    cases["Noise 0.32 m"] = truth + rng.normal(0.0, 0.32, size=truth.shape)
    bias = truth.copy()
    bias[(t >= 12.0) & (t < 16.0), 0] += 0.40
    cases["Bias +0.40 m"] = bias
    dropout = truth.copy()
    dropout[(t >= 12.0) & (t < 16.0)] = np.nan
    cases["Dropout 4.0 s"] = dropout

    diagnostics = {}
    for name, measurements in cases.items():
        est, innovation, nis, sigma = run_filter_diagnostics(t, measurements)
        diagnostics[name] = {
            "est": est,
            "innovation": innovation,
            "nis": nis,
            "sigma": sigma,
            "error": np.linalg.norm(est - truth, axis=1),
        }

    # Fixed 2 s dropout timing sweep.
    timing_rows = []
    for start in np.arange(6.0, 23.01, 0.5):
        duration = 2.0
        measurements = truth.copy()
        mask = (t >= start) & (t < start + duration)
        measurements[mask] = np.nan
        est, _, _, sigma = run_filter_diagnostics(t, measurements)
        error = np.linalg.norm(est - truth, axis=1)
        in_fault = (t >= start) & (t <= start + duration)
        crosses = bool(np.any((TURN_TIMES_S > start) & (TURN_TIMES_S < start + duration)))
        timing_rows.append({
            "start_s": float(start),
            "end_s": float(start + duration),
            "crosses_direction_change": int(crosses),
            "nearest_direction_change_from_start_s": float(np.min(np.abs(TURN_TIMES_S - start))),
            "fault_window_rmse_m": float(np.sqrt(np.mean(error[in_fault] ** 2))),
            "max_fault_error_m": float(np.max(error[in_fault])),
            "overall_rmse_m": float(np.sqrt(np.mean(error ** 2))),
            "max_position_sigma_m": float(np.max(sigma[in_fault])),
        })

    timing_path = args.results_dir / "dropout_timing_sweep_2s.csv"
    with timing_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(timing_rows[0]))
        writer.writeheader()
        writer.writerows(timing_rows)

    # Empirical no-false-positive detector thresholds from nominal post-settling data.
    nominal_roll = rolling_median(diagnostics["Nominal"]["nis"], rolling_samples)
    steady = (t >= 5.0) & np.isfinite(nominal_roll)
    nis_threshold = float(np.max(nominal_roll[steady]) * 1.20)
    sigma_threshold = float(np.max(diagnostics["Nominal"]["sigma"][t >= 5.0]) * 1.50)

    detector_rows = []
    for name, d in diagnostics.items():
        roll = rolling_median(d["nis"], rolling_samples)
        residual_hits = np.flatnonzero((t >= 5.0) & np.isfinite(roll) & (roll > nis_threshold))
        uncertainty_hits = np.flatnonzero((t >= 5.0) & (d["sigma"] > sigma_threshold))
        detector_rows.append({
            "case": name,
            "max_rolling_median_nis": float(np.nanmax(roll[t >= 5.0])),
            "first_residual_alert_s": float(t[residual_hits[0]]) if len(residual_hits) else float("nan"),
            "max_radial_position_sigma_m": float(np.max(d["sigma"][t >= 5.0])),
            "first_uncertainty_alert_s": float(t[uncertainty_hits[0]]) if len(uncertainty_hits) else float("nan"),
            "max_position_error_m": float(np.max(d["error"])),
        })

    detector_path = args.results_dir / "residual_uncertainty_detector.csv"
    with detector_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(detector_rows[0]))
        writer.writeheader()
        writer.writerows(detector_rows)

    save_xy_plot(args.results_dir, t, truth)

    plt.figure(figsize=(9, 5))
    for name, d in diagnostics.items():
        plt.plot(t, d["error"], label=name)
    plt.axvline(12.0, linestyle="--", label="Fault start")
    plt.axvline(16.0, linestyle="--", label="4 s fault end")
    plt.xlabel("time (s)")
    plt.ylabel("position estimation error (m)")
    plt.title("Estimator error time history")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(args.results_dir / "02_error_time_histories.png", dpi=180)
    plt.close()

    trials = read_trial_metrics(args.results_dir / "trial_metrics.csv")

    noise_groups = {}
    for row in trials:
        if row["fault_type"] == "noise":
            noise_groups.setdefault(severity_value(row["severity"]), []).append(float(row["estimator_rmse_m"]))
    xs = sorted(noise_groups)
    ys = [float(np.mean(noise_groups[x])) for x in xs]
    plt.figure(figsize=(7, 5))
    plt.plot(xs, ys, marker="o")
    plt.xlabel("Gaussian position-noise sigma (m)")
    plt.ylabel("mean estimator RMSE (m)")
    plt.title("Noise severity vs estimator RMSE")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(args.results_dir / "03_noise_severity_vs_rmse.png", dpi=180)
    plt.close()

    bias_rows = sorted(
        [(severity_value(r["severity"]), float(r["fault_window_estimator_rmse_m"]))
         for r in trials if r["fault_type"] == "bias"]
    )
    plt.figure(figsize=(7, 5))
    plt.plot([r[0] for r in bias_rows], [r[1] for r in bias_rows], marker="o")
    plt.xlabel("fixed +x position bias (m)")
    plt.ylabel("fault-window estimator RMSE (m)")
    plt.title("Bias severity vs fault-window RMSE")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(args.results_dir / "04_bias_severity_vs_rmse.png", dpi=180)
    plt.close()

    dropout_rows = sorted(
        [(severity_value(r["severity"]), float(r["max_estimator_error_m"]))
         for r in trials if r["fault_type"] == "dropout"]
    )
    plt.figure(figsize=(7, 5))
    plt.plot([r[0] for r in dropout_rows], [r[1] for r in dropout_rows], marker="o")
    plt.xlabel("dropout duration (s)")
    plt.ylabel("maximum estimator error (m)")
    plt.title("Original dropout duration sweep at t = 12 s")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(args.results_dir / "05_dropout_duration_vs_max_error.png", dpi=180)
    plt.close()

    plt.figure(figsize=(9, 5))
    plt.plot([r["start_s"] for r in timing_rows], [r["max_fault_error_m"] for r in timing_rows], marker="o", label="2 s dropout")
    for index, turn in enumerate(TURN_TIMES_S):
        plt.axvline(turn, linestyle="--", label="Direction change" if index == 0 else None)
    plt.xlabel("dropout start time (s)")
    plt.ylabel("maximum error during dropout (m)")
    plt.title("Same 2 s dropout, different timing")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(args.results_dir / "06_dropout_timing_vs_max_error.png", dpi=180)
    plt.close()

    plt.figure(figsize=(9, 5))
    for name in ["Nominal", "Noise 0.32 m", "Bias +0.40 m"]:
        roll = rolling_median(diagnostics[name]["nis"], rolling_samples)
        plt.plot(t, roll, label=name)
    plt.axhline(nis_threshold, linestyle="--", label="Empirical alert threshold")
    plt.axvline(12.0, linestyle="--")
    plt.axvline(16.0, linestyle="--")
    plt.yscale("log")
    plt.xlabel("time (s)")
    plt.ylabel("0.5 s rolling median NIS")
    plt.title("Residual-based fault indication")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(args.results_dir / "07_residual_nis_diagnostic.png", dpi=180)
    plt.close()

    plt.figure(figsize=(9, 5))
    plt.plot(t, diagnostics["Nominal"]["sigma"], label="Nominal")
    plt.plot(t, diagnostics["Dropout 4.0 s"]["sigma"], label="Dropout 4.0 s")
    plt.axhline(sigma_threshold, linestyle="--", label="Empirical alert threshold")
    plt.axvline(12.0, linestyle="--")
    plt.axvline(16.0, linestyle="--")
    plt.xlabel("time (s)")
    plt.ylabel("radial position sigma (m)")
    plt.title("Prediction uncertainty grows during measurement dropout")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(args.results_dir / "08_dropout_uncertainty_diagnostic.png", dpi=180)
    plt.close()

    by_start = {round(r["start_s"], 1): r for r in timing_rows}
    steady_starts = [7.0, 12.0, 17.0, 22.0]
    maneuver_starts = [9.5, 10.0, 14.5, 15.0, 19.5, 20.0]
    steady_mean = float(np.mean([by_start[s]["max_fault_error_m"] for s in steady_starts]))
    maneuver_mean = float(np.mean([by_start[s]["max_fault_error_m"] for s in maneuver_starts]))
    ratio = maneuver_mean / steady_mean

    detector_by_case = {r["case"]: r for r in detector_rows}
    lines = [
        "# Extended UNM Crazyflie / Webots analysis",
        "",
        "The original Webots trajectory and fixed Kalman-filter assumptions are unchanged. This layer adds diagnostics only.",
        "",
        "## Strongest new result: dropout timing matters",
        "",
        "A fixed 2.0 s position dropout was moved across the exact same saved Webots trajectory in 0.5 s increments.",
        "",
        f"- 7.0–9.0 s steady segment: max error **{by_start[7.0]['max_fault_error_m']:.4f} m**",
        f"- 12.0–14.0 s steady segment: max error **{by_start[12.0]['max_fault_error_m']:.4f} m**",
        f"- 9.5–11.5 s spanning the 10 s direction change: max error **{by_start[9.5]['max_fault_error_m']:.4f} m**",
        f"- 10.0–12.0 s starting at the new motion segment: max error **{by_start[10.0]['max_fault_error_m']:.4f} m**",
        f"- 15.0–17.0 s starting at a direction change: max error **{by_start[15.0]['max_fault_error_m']:.4f} m**",
        f"- 20.0–22.0 s starting at a direction change: max error **{by_start[20.0]['max_fault_error_m']:.4f} m**",
        "",
        f"Representative maneuver-adjacent windows averaged **{maneuver_mean:.4f} m** maximum error versus **{steady_mean:.4f} m** for representative steady windows, about **{ratio:.1f}× larger**.",
        "",
        "Interpretation: constant velocity predicts steady motion well. Near a commanded direction change, the velocity state is stale or still adapting, so prediction-only propagation can diverge rapidly.",
        "",
        "## Residual and uncertainty diagnostics",
        "",
        f"- Residual indicator: 0.5 s rolling median normalized innovation squared (NIS). Empirical threshold: **{nis_threshold:.3f}**.",
        f"- Uncertainty indicator: radial position standard deviation from the Kalman covariance. Empirical threshold: **{sigma_threshold:.4f} m**.",
        f"- Noise 0.32 m first residual alert: **{detector_by_case['Noise 0.32 m']['first_residual_alert_s']:.3f} s**.",
        f"- Bias +0.40 m first residual alert: **{detector_by_case['Bias +0.40 m']['first_residual_alert_s']:.3f} s**.",
        f"- Dropout 4.0 s first uncertainty alert: **{detector_by_case['Dropout 4.0 s']['first_uncertainty_alert_s']:.3f} s**.",
        "- Nominal produces no alert under either empirical threshold.",
        "",
        "Noise and bias can be indicated by residual disagreement because measurements still arrive. During dropout, innovations do not exist, so covariance growth is the useful reliability signal.",
        "",
        "## Guardrails",
        "",
        "These are simulation-only findings. The underlying trajectory is genuine Webots evidence. Faults and diagnostics are applied offline to that one saved trajectory for controlled comparison.",
        "",
    ]
    (args.results_dir / "EXTENDED_RESULTS.md").write_text("\n".join(lines), encoding="utf-8")

    print("UNM_EXTENDED_ANALYSIS_COMPLETE")
    print(f"steady 7-9 s max error: {by_start[7.0]['max_fault_error_m']:.6f} m")
    print(f"maneuver 10-12 s max error: {by_start[10.0]['max_fault_error_m']:.6f} m")
    print(f"NIS threshold: {nis_threshold:.6f}")
    print(f"sigma threshold: {sigma_threshold:.6f} m")


if __name__ == "__main__":
    main()
