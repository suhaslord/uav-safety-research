#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BASE_SEED = 20260820
POSITION_MEAS_SIGMA_M = 0.02
ACCEL_PROCESS_SIGMA_MPS2 = 0.35
INITIAL_POSITION_SIGMA_M = 0.05
INITIAL_VELOCITY_SIGMA_MPS = 0.20
TURN_TIMES = np.array([10.0, 15.0, 20.0, 25.0])
NOISE_LEVELS = [0.04, 0.08, 0.16, 0.32]
BIAS_LEVELS = [0.05, 0.10, 0.20, 0.40]
DROPOUT_DURATIONS = [0.5, 1.0, 2.0, 4.0]
N_NOISE_TRIALS = 30


def load(path: Path):
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    t = np.array([float(r["time_s"]) for r in rows])
    xy = np.array([[float(r["x_m"]), float(r["y_m"])] for r in rows])
    return t, xy


def run_diag(t: np.ndarray, measurements: np.ndarray):
    initial = measurements[0] if np.isfinite(measurements[0]).all() else np.zeros(2)
    x = np.array([initial[0], initial[1], 0.0, 0.0])
    P = np.diag([
        INITIAL_POSITION_SIGMA_M**2,
        INITIAL_POSITION_SIGMA_M**2,
        INITIAL_VELOCITY_SIGMA_MPS**2,
        INITIAL_VELOCITY_SIGMA_MPS**2,
    ])
    H = np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]])
    R = np.eye(2) * POSITION_MEAS_SIGMA_M**2
    nis = np.full(len(t), np.nan)
    sigma = np.zeros(len(t))
    est = np.empty_like(measurements)
    sigma[0] = math.sqrt(P[0, 0] + P[1, 1])
    est[0] = x[:2]

    for i in range(1, len(t)):
        dt = float(t[i] - t[i - 1])
        q = ACCEL_PROCESS_SIGMA_MPS2**2
        F = np.array([
            [1.0, 0.0, dt, 0.0],
            [0.0, 1.0, 0.0, dt],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ])
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
            nis[i] = float(y.T @ np.linalg.inv(S) @ y)
            K = P @ H.T @ np.linalg.inv(S)
            x = x + K @ y
            P = (np.eye(4) - K @ H) @ P

        est[i] = x[:2]
        sigma[i] = math.sqrt(P[0, 0] + P[1, 1])

    return est, nis, sigma


def rolling_median(values: np.ndarray, window_samples: int) -> np.ndarray:
    out = np.full(len(values), np.nan)
    min_count = max(3, window_samples // 2)
    for i in range(len(values)):
        window = values[max(0, i - window_samples + 1):i + 1]
        finite = window[np.isfinite(window)]
        if len(finite) >= min_count:
            out[i] = float(np.median(finite))
    return out


def first_time(t: np.ndarray, mask: np.ndarray) -> float:
    inds = np.flatnonzero(mask)
    return float(t[inds[0]]) if len(inds) else float("nan")


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: float) -> str:
    return "n/a" if not math.isfinite(float(value)) else f"{float(value):.3f}"


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Validate frozen residual/uncertainty fault indicators on a Webots baseline."
    )
    ap.add_argument("baseline_csv", type=Path)
    ap.add_argument("--results-dir", type=Path, required=True)
    args = ap.parse_args()
    out = args.results_dir
    out.mkdir(parents=True, exist_ok=True)

    t, truth = load(args.baseline_csv)
    dt = float(np.median(np.diff(t)))
    rolling_samples = max(3, int(round(0.5 / dt)))
    _, nominal_nis, nominal_sigma = run_diag(t, truth.copy())
    nominal_roll = rolling_median(nominal_nis, rolling_samples)
    armed = (t >= 5.0) & np.isfinite(nominal_roll)

    # Freeze thresholds using only the nominal baseline. Never retune per fault.
    nis_threshold = float(np.max(nominal_roll[armed]) * 1.20)
    sigma_threshold = float(np.max(nominal_sigma[t >= 5.0]) * 1.50)

    noise_trials = []
    for severity in NOISE_LEVELS:
        for trial in range(N_NOISE_TRIALS):
            rng = np.random.default_rng(BASE_SEED + trial)
            measurements = truth + rng.normal(0.0, severity, size=truth.shape)
            _, nis, _ = run_diag(t, measurements)
            roll = rolling_median(nis, rolling_samples)
            hit_mask = (t >= 5.0) & np.isfinite(roll) & (roll > nis_threshold)
            first_alert = first_time(t, hit_mask)
            noise_trials.append({
                "fault_type": "noise",
                "severity_m_sigma": severity,
                "trial": trial,
                "detected": int(math.isfinite(first_alert)),
                "first_alert_s": first_alert,
                "latency_after_arming_s": first_alert - 5.0 if math.isfinite(first_alert) else float("nan"),
                "max_rolling_median_nis": float(np.nanmax(roll[t >= 5.0])),
            })
    write_csv(out / "noise_detection_trials.csv", noise_trials)

    noise_summary = []
    for severity in NOISE_LEVELS:
        rows = [r for r in noise_trials if r["severity_m_sigma"] == severity]
        detections = [r for r in rows if r["detected"]]
        latencies = [r["latency_after_arming_s"] for r in detections]
        noise_summary.append({
            "severity_m_sigma": severity,
            "trials": len(rows),
            "detections": len(detections),
            "detection_rate": len(detections) / len(rows),
            "median_latency_after_arming_s": float(np.median(latencies)) if latencies else float("nan"),
            "p95_latency_after_arming_s": float(np.percentile(latencies, 95)) if latencies else float("nan"),
            "median_max_rolling_nis": float(np.median([r["max_rolling_median_nis"] for r in rows])),
        })
    write_csv(out / "noise_detection_summary.csv", noise_summary)

    bias_rows = []
    for severity in BIAS_LEVELS:
        measurements = truth.copy()
        measurements[(t >= 12.0) & (t < 16.0), 0] += severity
        _, nis, _ = run_diag(t, measurements)
        roll = rolling_median(nis, rolling_samples)
        hit_mask = (t >= 12.0) & np.isfinite(roll) & (roll > nis_threshold)
        first_alert = first_time(t, hit_mask)
        bias_rows.append({
            "severity_m": severity,
            "detected": int(math.isfinite(first_alert)),
            "first_alert_s": first_alert,
            "latency_s": first_alert - 12.0 if math.isfinite(first_alert) else float("nan"),
            "max_rolling_median_nis": float(np.nanmax(roll[(t >= 12.0) & (t < 16.0)])),
        })
    write_csv(out / "bias_detection.csv", bias_rows)

    dropout_rows = []
    for duration in DROPOUT_DURATIONS:
        measurements = truth.copy()
        measurements[(t >= 12.0) & (t < 12.0 + duration)] = np.nan
        _, _, sigma = run_diag(t, measurements)
        hit_mask = (t >= 12.0) & (sigma > sigma_threshold)
        first_alert = first_time(t, hit_mask)
        dropout_rows.append({
            "duration_s": duration,
            "detected": int(math.isfinite(first_alert) and first_alert <= 12.0 + duration + 1e-9),
            "first_alert_s": first_alert,
            "latency_s": first_alert - 12.0 if math.isfinite(first_alert) else float("nan"),
            "max_sigma_during_dropout_m": float(np.max(sigma[(t >= 12.0) & (t < 12.0 + duration)])),
        })
    write_csv(out / "dropout_detection.csv", dropout_rows)

    nominal_hits = (t >= 5.0) & np.isfinite(nominal_roll) & (nominal_roll > nis_threshold)
    false_positive_rows = []
    for turn in TURN_TIMES:
        window = (t >= turn - 0.75) & (t <= turn + 0.75) & np.isfinite(nominal_roll)
        values = nominal_roll[window]
        false_positive_rows.append({
            "direction_change_s": turn,
            "samples_in_window": int(np.sum(window)),
            "alerts_in_window": int(np.sum(nominal_hits & window)),
            "max_rolling_median_nis": float(np.max(values)),
            "threshold": nis_threshold,
            "margin_to_threshold": nis_threshold - float(np.max(values)),
        })
    write_csv(out / "nominal_direction_change_false_positives.csv", false_positive_rows)

    total_armed = int(np.sum((t >= 5.0) & np.isfinite(nominal_roll)))
    total_false_positives = int(np.sum(nominal_hits))

    plt.figure(figsize=(7, 4.5))
    plt.plot(
        [r["severity_m_sigma"] for r in noise_summary],
        [r["detection_rate"] for r in noise_summary],
        marker="o",
    )
    plt.ylim(-0.05, 1.05)
    plt.xlabel("Gaussian position noise sigma (m)")
    plt.ylabel("detection rate (30 trials)")
    plt.title("Residual indicator detection vs noise severity")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out / "noise_detection_rate.png", dpi=180)
    plt.close()

    plt.figure(figsize=(7, 4.5))
    plt.plot(
        [r["severity_m"] for r in bias_rows],
        [r["latency_s"] if math.isfinite(r["latency_s"]) else np.nan for r in bias_rows],
        marker="o",
    )
    plt.xlabel("fixed +x bias (m)")
    plt.ylabel("first-alert latency (s)")
    plt.title("Residual indicator latency vs bias severity")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out / "bias_detection_latency.png", dpi=180)
    plt.close()

    plt.figure(figsize=(9, 4.8))
    plt.plot(t, nominal_roll, label="Nominal rolling median NIS")
    plt.axhline(nis_threshold, linestyle="--", label="Alert threshold")
    for index, turn in enumerate(TURN_TIMES):
        plt.axvline(turn, linestyle=":", label="Direction change" if index == 0 else None)
    plt.xlabel("time (s)")
    plt.ylabel("0.5 s rolling median NIS")
    plt.title("No-fault maneuver false-positive audit")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out / "nominal_false_positive_audit.png", dpi=180)
    plt.close()

    lines = [
        "# Fault-indicator validation on the frozen Webots Crazyflie trajectory",
        "",
        "**Scope:** offline measurement-fault validation on the exact 1,000-sample Webots baseline from the reviewed PR. This is simulation evidence, not physical-flight evidence.",
        "",
        "## Frozen detector definition",
        "",
        f"- Residual indicator: 0.5 s rolling median NIS; threshold = 1.20 × maximum nominal post-settling value = **{nis_threshold:.6f}**.",
        f"- Dropout indicator: radial position sigma; threshold = 1.50 × maximum nominal post-settling value = **{sigma_threshold:.6f} m**.",
        "- Thresholds were not retuned by fault severity.",
        "",
        "## Noise detection",
        "",
        "| sigma (m) | detected / 30 | rate | median latency after 5 s arming | p95 latency |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in noise_summary:
        lines.append(
            f"| {row['severity_m_sigma']:.2f} | {row['detections']} / {row['trials']} | "
            f"{100 * row['detection_rate']:.1f}% | {fmt(row['median_latency_after_arming_s'])} s | "
            f"{fmt(row['p95_latency_after_arming_s'])} s |"
        )
    lines += [
        "",
        "Noise is present for the entire run in the original experiment, so latency is measured from the detector arming time at 5 s rather than from a later injection onset.",
        "",
        "## Bias detection",
        "",
        "| bias (m) | detected | latency from 12 s onset | max rolling NIS in fault window |",
        "|---:|---:|---:|---:|",
    ]
    for row in bias_rows:
        lines.append(
            f"| {row['severity_m']:.2f} | {'yes' if row['detected'] else 'no'} | "
            f"{fmt(row['latency_s'])} s | {row['max_rolling_median_nis']:.3f} |"
        )
    lines += [
        "",
        "## Dropout detection",
        "",
        "| dropout duration | detected during dropout | latency | max radial sigma during dropout |",
        "|---:|---:|---:|---:|",
    ]
    for row in dropout_rows:
        lines.append(
            f"| {row['duration_s']:.1f} s | {'yes' if row['detected'] else 'no'} | "
            f"{fmt(row['latency_s'])} s | {row['max_sigma_during_dropout_m']:.4f} m |"
        )
    lines += [
        "",
        "## False positives on normal direction changes",
        "",
        f"- Overall nominal post-settling false positives: **{total_false_positives}/{total_armed} samples ({100 * total_false_positives / total_armed:.3f}%)**.",
        "- Direction-change neighborhoods use ±0.75 s around the commanded turns.",
        "",
        "| turn time | alerts | max rolling NIS | threshold margin |",
        "|---:|---:|---:|---:|",
    ]
    for row in false_positive_rows:
        lines.append(
            f"| {row['direction_change_s']:.1f} s | {row['alerts_in_window']} / {row['samples_in_window']} | "
            f"{row['max_rolling_median_nis']:.3f} | {row['margin_to_threshold']:.3f} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "- The frozen indicator is strongest for large measurement noise/bias and for dropout; weak faults that stay below threshold are expected misses rather than silently being counted as successes.",
        "- Normal commanded turns on this one frozen no-fault trajectory do not trigger the residual threshold. Because the threshold was calibrated from this same nominal trajectory, that is an **in-sample false-positive check**, not a general false-alarm guarantee.",
        "- The most important next validation is a second no-fault trajectory with different turn timing/speeds, with thresholds frozen from this baseline. That would convert the current in-sample false-positive result into a genuine holdout check.",
        "- Only after that holdout should mitigation (rejecting/down-weighting suspect measurements) be compared against the unchanged filter.",
    ]
    (out / "INDICATOR_VALIDATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
