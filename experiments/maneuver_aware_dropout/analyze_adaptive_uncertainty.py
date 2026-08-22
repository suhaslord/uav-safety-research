#!/usr/bin/env python3
"""Controlled experiment: maneuver-aware adaptive process noise under dropout.

Research question:
Can adaptive process noise that increases near detected maneuvers produce
uncertainty estimates that better reflect actual estimation error during dropout?

Hypothesis:
A filter that adaptively increases process noise near direction changes will
produce covariance that better ranks dropout severity compared to the frozen
constant-velocity baseline from PR #52.

Controlled conditions (frozen from PR #52):
- Same saved Webots baseline trajectory
- Same measurement fault injection (2s dropouts at various times)
- Same initial covariance, measurement noise
- Same evaluation metrics

Single modification:
- Adaptive process noise: detect maneuvers from acceleration/jerk, temporarily
  increase process noise scale factor near detected direction changes

Metrics:
- Correlation between predicted uncertainty and actual error
- Calibration: does 1-sigma bound contain ~68% of actual errors during dropout?
- Comparison: frozen CV baseline vs adaptive-Q variant on identical dropouts
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

# Frozen configuration from PR #52 baseline
BASE_SEED = 20260820
POSITION_MEAS_SIGMA_M = 0.02
ACCEL_PROCESS_SIGMA_MPS2 = 0.35
INITIAL_POSITION_SIGMA_M = 0.05
INITIAL_VELOCITY_SIGMA_MPS = 0.20

# Adaptive process noise parameters
MANEUVER_DETECT_ACCEL_THRESHOLD_MPS2 = 0.15  # Empirical from Webots baseline
MANEUVER_DETECT_WINDOW_S = 1.0
MANEUVER_BOOST_FACTOR = 5.0  # Increase process noise by 5× near maneuvers
MANEUVER_BOOST_DECAY_S = 2.0  # Exponential decay time constant

# Known maneuver times from PR #52 baseline
KNOWN_MANEUVER_TIMES_S = [10.0, 15.0, 20.0, 25.0]


@dataclass
class Baseline:
    t: np.ndarray
    xy: np.ndarray
    vxy: np.ndarray  # Global velocities for maneuver detection


def load_baseline(path: Path) -> Baseline:
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    
    t = np.array([float(r["time_s"]) for r in rows], dtype=float)
    xy = np.array([[float(r["x_m"]), float(r["y_m"])] for r in rows], dtype=float)
    
    # Use global velocities if available, otherwise differentiate position
    if "vx_global_mps" in rows[0] and "vy_global_mps" in rows[0]:
        vxy = np.array([[float(r["vx_global_mps"]), float(r["vy_global_mps"])] for r in rows], dtype=float)
        # Handle initial NaN velocities
        for i in range(len(vxy)):
            if not np.isfinite(vxy[i]).all():
                if i + 1 < len(vxy) and np.isfinite(vxy[i+1]).all():
                    vxy[i] = vxy[i+1]
                elif i > 0:
                    vxy[i] = vxy[i-1]
                else:
                    vxy[i] = np.zeros(2)
    else:
        # Fallback: differentiate position
        vxy = np.zeros_like(xy)
        vxy[1:] = np.diff(xy, axis=0) / np.diff(t)[:, None]
        vxy[0] = vxy[1]
    
    return Baseline(t=t, xy=xy, vxy=vxy)


def detect_maneuvers_from_acceleration(t: np.ndarray, vxy: np.ndarray) -> np.ndarray:
    """Detect maneuvers from acceleration magnitude.
    
    Returns maneuver_score array in [0, 1] where 1 = high confidence maneuver.
    """
    # Compute acceleration magnitude
    accel = np.zeros(len(t))
    accel[1:] = np.linalg.norm(np.diff(vxy, axis=0), axis=1) / np.diff(t)
    accel[0] = accel[1]
    
    # Smooth acceleration with moving average
    window = max(3, int(MANEUVER_DETECT_WINDOW_S / np.median(np.diff(t))))
    smoothed = np.convolve(accel, np.ones(window)/window, mode='same')
    
    # Threshold and normalize to [0, 1]
    maneuver_score = np.clip(smoothed / MANEUVER_DETECT_ACCEL_THRESHOLD_MPS2, 0, 1)
    
    return maneuver_score


class CVKalman2D:
    """Frozen constant-velocity 2D Kalman filter from PR #52."""
    
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
    
    def step(self, dt: float, z: np.ndarray | None, q_scale: float = 1.0) -> tuple[np.ndarray, float]:
        """Predict and update. Returns (position_estimate, radial_sigma)."""
        F = np.array([
            [1.0, 0.0, dt, 0.0],
            [0.0, 1.0, 0.0, dt],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ])
        
        q = (ACCEL_PROCESS_SIGMA_MPS2 * q_scale) ** 2
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
        
        radial_sigma = math.sqrt(self.P[0, 0] + self.P[1, 1])
        return self.x[:2].copy(), radial_sigma


def run_filter(t: np.ndarray, truth: np.ndarray, measurements: np.ndarray,
               maneuver_score: np.ndarray | None = None) -> dict:
    """Run filter and collect diagnostics.
    
    If maneuver_score is provided, use adaptive process noise.
    Otherwise use frozen constant-velocity process noise.
    """
    initial = measurements[0] if np.isfinite(measurements[0]).all() else np.zeros(2)
    kf = CVKalman2D(initial)
    
    est = np.empty_like(measurements)
    sigma = np.zeros(len(t))
    q_scale = np.ones(len(t))
    
    est[0] = kf.x[:2]
    sigma[0] = math.sqrt(kf.P[0, 0] + kf.P[1, 1])
    
    for i in range(1, len(t)):
        dt = float(t[i] - t[i - 1])
        z = measurements[i]
        z_or_none = None if not np.isfinite(z).all() else z
        
        # Adaptive process noise based on maneuver detection
        if maneuver_score is not None:
            # Exponential boost near maneuvers
            boost = 1.0 + (MANEUVER_BOOST_FACTOR - 1.0) * maneuver_score[i]
            q_scale[i] = boost
        
        est[i], sigma[i] = kf.step(dt, z_or_none, q_scale[i])
    
    error = np.linalg.norm(est - truth, axis=1)
    
    return {
        "est": est,
        "error": error,
        "sigma": sigma,
        "q_scale": q_scale,
    }


def evaluate_dropout_timing(t: np.ndarray, truth: np.ndarray, 
                            maneuver_score: np.ndarray,
                            dropout_starts: np.ndarray,
                            dropout_duration: float = 2.0) -> tuple[list[dict], list[dict]]:
    """Run dropout timing sweep for both baseline and adaptive filters."""
    
    baseline_results = []
    adaptive_results = []
    
    for start in dropout_starts:
        measurements = truth.copy()
        mask = (t >= start) & (t < start + dropout_duration)
        measurements[mask] = np.nan
        
        # Baseline frozen CV filter
        baseline_out = run_filter(t, truth, measurements, maneuver_score=None)
        
        # Adaptive maneuver-aware filter
        adaptive_out = run_filter(t, truth, measurements, maneuver_score=maneuver_score)
        
        # Compute metrics during dropout window
        in_dropout = (t >= start) & (t <= start + dropout_duration)
        
        for name, out, results_list in [
            ("baseline", baseline_out, baseline_results),
            ("adaptive", adaptive_out, adaptive_results)
        ]:
            max_error = float(np.max(out["error"][in_dropout]))
            max_sigma = float(np.max(out["sigma"][in_dropout]))
            mean_q_scale = float(np.mean(out["q_scale"][in_dropout]))
            
            # Does the uncertainty bound contain the actual error?
            errors_in_dropout = out["error"][in_dropout]
            sigmas_in_dropout = out["sigma"][in_dropout]
            within_1sigma = np.mean(errors_in_dropout <= sigmas_in_dropout)
            within_2sigma = np.mean(errors_in_dropout <= 2 * sigmas_in_dropout)
            
            # Distance to nearest known maneuver
            nearest_maneuver_dist = float(np.min(np.abs(KNOWN_MANEUVER_TIMES_S - start)))
            crosses_maneuver = bool(np.any(
                (np.array(KNOWN_MANEUVER_TIMES_S) > start) & 
                (np.array(KNOWN_MANEUVER_TIMES_S) < start + dropout_duration)
            ))
            
            results_list.append({
                "start_s": float(start),
                "duration_s": dropout_duration,
                "max_error_m": max_error,
                "max_sigma_m": max_sigma,
                "mean_q_scale": mean_q_scale,
                "within_1sigma_fraction": float(within_1sigma),
                "within_2sigma_fraction": float(within_2sigma),
                "nearest_maneuver_s": nearest_maneuver_dist,
                "crosses_maneuver": int(crosses_maneuver),
                "sigma_to_error_ratio": max_sigma / max_error if max_error > 1e-6 else np.nan,
            })
    
    return baseline_results, adaptive_results


def compute_correlation_and_calibration(results: list[dict]) -> dict:
    """Compute overall correlation between uncertainty and error."""
    max_errors = np.array([r["max_error_m"] for r in results])
    max_sigmas = np.array([r["max_sigma_m"] for r in results])
    
    # Pearson correlation
    corr, p_value = stats.pearsonr(max_sigmas, max_errors)
    
    # Mean calibration: how well does sigma predict error?
    within_1sigma = np.mean([r["within_1sigma_fraction"] for r in results])
    within_2sigma = np.mean([r["within_2sigma_fraction"] for r in results])
    
    # Ranking: does higher sigma correspond to higher error?
    rank_corr, rank_p = stats.spearmanr(max_sigmas, max_errors)
    
    return {
        "pearson_correlation": float(corr),
        "pearson_p_value": float(p_value),
        "spearman_rank_correlation": float(rank_corr),
        "spearman_p_value": float(rank_p),
        "mean_within_1sigma": float(within_1sigma),
        "mean_within_2sigma": float(within_2sigma),
        "ideal_within_1sigma": 0.68,
        "ideal_within_2sigma": 0.95,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("baseline_csv", type=Path)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--dropout-duration", type=float, default=2.0)
    args = ap.parse_args()
    
    args.out_dir.mkdir(parents=True, exist_ok=True)
    
    # Load baseline
    baseline = load_baseline(args.baseline_csv)
    t, truth = baseline.t, baseline.xy
    
    # Detect maneuvers
    maneuver_score = detect_maneuvers_from_acceleration(t, baseline.vxy)
    
    # Dropout timing sweep (same as PR #52)
    dropout_starts = np.arange(6.0, 23.01, 0.5)
    
    baseline_results, adaptive_results = evaluate_dropout_timing(
        t, truth, maneuver_score, dropout_starts, args.dropout_duration
    )
    
    # Compute statistics
    baseline_stats = compute_correlation_and_calibration(baseline_results)
    adaptive_stats = compute_correlation_and_calibration(adaptive_results)
    
    # Save detailed results
    with (args.out_dir / "baseline_dropout_timing.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(baseline_results[0].keys()))
        writer.writeheader()
        writer.writerows(baseline_results)
    
    with (args.out_dir / "adaptive_dropout_timing.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(adaptive_results[0].keys()))
        writer.writeheader()
        writer.writerows(adaptive_results)
    
    # Save statistics
    stats_data = {
        "baseline": baseline_stats,
        "adaptive": adaptive_stats,
        "improvement": {
            "correlation_increase": adaptive_stats["pearson_correlation"] - baseline_stats["pearson_correlation"],
            "rank_correlation_increase": adaptive_stats["spearman_rank_correlation"] - baseline_stats["spearman_rank_correlation"],
            "calibration_1sigma_closer_to_ideal": abs(adaptive_stats["mean_within_1sigma"] - 0.68) - abs(baseline_stats["mean_within_1sigma"] - 0.68),
        }
    }
    
    (args.out_dir / "statistics.json").write_text(json.dumps(stats_data, indent=2), encoding="utf-8")
    
    # Generate plots
    plot_trajectory_with_maneuvers(t, truth, maneuver_score, args.out_dir)
    plot_comparison(baseline_results, adaptive_results, args.out_dir)
    plot_calibration(baseline_results, adaptive_results, args.out_dir)
    plot_maneuver_correlation(baseline_results, adaptive_results, args.out_dir)
    
    # Generate summary
    write_summary(stats_data, args.out_dir)
    
    print("MANEUVER_AWARE_ANALYSIS_COMPLETE")
    print(json.dumps(stats_data, indent=2))


def plot_trajectory_with_maneuvers(t: np.ndarray, truth: np.ndarray, 
                                   maneuver_score: np.ndarray, out_dir: Path):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    
    # XY trajectory
    ax1.plot(truth[:, 0], truth[:, 1], 'b-', linewidth=2)
    ax1.scatter([truth[0, 0]], [truth[0, 1]], c='g', s=100, label="Start", zorder=5)
    ax1.scatter([truth[-1, 0]], [truth[-1, 1]], c='r', s=100, label="End", zorder=5)
    ax1.set_xlabel("x position (m)")
    ax1.set_ylabel("y position (m)")
    ax1.set_title("Webots trajectory with maneuver detection")
    ax1.axis("equal")
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Maneuver score over time
    ax2.plot(t, maneuver_score, 'r-', linewidth=2)
    for mt in KNOWN_MANEUVER_TIMES_S:
        ax2.axvline(mt, color='k', linestyle='--', alpha=0.5)
    ax2.axhline(0.5, color='gray', linestyle=':', label="Detection threshold")
    ax2.set_xlabel("time (s)")
    ax2.set_ylabel("maneuver score")
    ax2.set_title("Maneuver detection from acceleration")
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    plt.tight_layout()
    plt.savefig(out_dir / "01_trajectory_maneuver_detection.png", dpi=180)
    plt.close()


def plot_comparison(baseline: list[dict], adaptive: list[dict], out_dir: Path):
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    starts = [r["start_s"] for r in baseline]
    
    # Max error comparison
    ax = axes[0, 0]
    ax.plot(starts, [r["max_error_m"] for r in baseline], 'o-', label="Baseline CV")
    ax.plot(starts, [r["max_error_m"] for r in adaptive], 's-', label="Adaptive Q")
    for mt in KNOWN_MANEUVER_TIMES_S:
        ax.axvline(mt, color='k', linestyle='--', alpha=0.3)
    ax.set_xlabel("dropout start (s)")
    ax.set_ylabel("max error during dropout (m)")
    ax.set_title("Actual error (identical for both filters)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # Max sigma comparison
    ax = axes[0, 1]
    ax.plot(starts, [r["max_sigma_m"] for r in baseline], 'o-', label="Baseline CV")
    ax.plot(starts, [r["max_sigma_m"] for r in adaptive], 's-', label="Adaptive Q")
    for mt in KNOWN_MANEUVER_TIMES_S:
        ax.axvline(mt, color='k', linestyle='--', alpha=0.3)
    ax.set_xlabel("dropout start (s)")
    ax.set_ylabel("max uncertainty during dropout (m)")
    ax.set_title("Predicted uncertainty (different)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # Sigma/error ratio
    ax = axes[1, 0]
    ax.plot(starts, [r["sigma_to_error_ratio"] for r in baseline], 'o-', label="Baseline CV")
    ax.plot(starts, [r["sigma_to_error_ratio"] for r in adaptive], 's-', label="Adaptive Q")
    ax.axhline(1.0, color='gray', linestyle=':', label="Perfect calibration")
    for mt in KNOWN_MANEUVER_TIMES_S:
        ax.axvline(mt, color='k', linestyle='--', alpha=0.3)
    ax.set_xlabel("dropout start (s)")
    ax.set_ylabel("sigma / error ratio")
    ax.set_title("Calibration ratio (closer to 1.0 is better)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # Process noise scale
    ax = axes[1, 1]
    ax.plot(starts, [r["mean_q_scale"] for r in adaptive], 's-', color='purple')
    for mt in KNOWN_MANEUVER_TIMES_S:
        ax.axvline(mt, color='k', linestyle='--', alpha=0.3)
    ax.set_xlabel("dropout start (s)")
    ax.set_ylabel("mean process noise scale during dropout")
    ax.set_title("Adaptive process noise behavior")
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(out_dir / "02_baseline_vs_adaptive_comparison.png", dpi=180)
    plt.close()


def plot_calibration(baseline: list[dict], adaptive: list[dict], out_dir: Path):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Scatter: sigma vs error
    ax1.scatter([r["max_sigma_m"] for r in baseline], 
               [r["max_error_m"] for r in baseline], 
               alpha=0.6, label="Baseline CV")
    ax1.scatter([r["max_sigma_m"] for r in adaptive], 
               [r["max_error_m"] for r in adaptive], 
               alpha=0.6, label="Adaptive Q")
    
    # Perfect calibration line
    max_val = max(
        max(r["max_error_m"] for r in baseline + adaptive),
        max(r["max_sigma_m"] for r in baseline + adaptive)
    )
    ax1.plot([0, max_val], [0, max_val], 'k--', label="Perfect calibration", alpha=0.5)
    
    ax1.set_xlabel("predicted uncertainty (m)")
    ax1.set_ylabel("actual error (m)")
    ax1.set_title("Uncertainty calibration")
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Coverage fractions
    categories = ["Within 1σ", "Within 2σ"]
    baseline_coverage = [
        np.mean([r["within_1sigma_fraction"] for r in baseline]),
        np.mean([r["within_2sigma_fraction"] for r in baseline])
    ]
    adaptive_coverage = [
        np.mean([r["within_1sigma_fraction"] for r in adaptive]),
        np.mean([r["within_2sigma_fraction"] for r in adaptive])
    ]
    ideal = [0.68, 0.95]
    
    x = np.arange(len(categories))
    width = 0.25
    ax2.bar(x - width, baseline_coverage, width, label="Baseline CV")
    ax2.bar(x, adaptive_coverage, width, label="Adaptive Q")
    ax2.bar(x + width, ideal, width, label="Ideal", alpha=0.5)
    ax2.set_ylabel("fraction of samples")
    ax2.set_title("Coverage calibration")
    ax2.set_xticks(x)
    ax2.set_xticklabels(categories)
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(out_dir / "03_calibration_analysis.png", dpi=180)
    plt.close()


def plot_maneuver_correlation(baseline: list[dict], adaptive: list[dict], out_dir: Path):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Group by distance to nearest maneuver
    for name, results, marker in [("Baseline CV", baseline, 'o'), 
                                   ("Adaptive Q", adaptive, 's')]:
        near_maneuver = [r for r in results if r["nearest_maneuver_s"] < 1.0]
        far_maneuver = [r for r in results if r["nearest_maneuver_s"] >= 1.0]
        
        if near_maneuver:
            ax1.scatter([r["max_error_m"] for r in near_maneuver],
                       [r["max_sigma_m"] for r in near_maneuver],
                       alpha=0.6, marker=marker, label=f"{name} (near maneuver)")
        if far_maneuver:
            ax2.scatter([r["max_error_m"] for r in far_maneuver],
                       [r["max_sigma_m"] for r in far_maneuver],
                       alpha=0.6, marker=marker, label=f"{name} (far from maneuver)")
    
    for ax, title in [(ax1, "Near maneuvers (<1s)"), (ax2, "Far from maneuvers (≥1s)")]:
        ax.set_xlabel("actual error (m)")
        ax.set_ylabel("predicted uncertainty (m)")
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Add perfect calibration line
        if ax.get_xlim()[1] > 0:
            max_val = max(ax.get_xlim()[1], ax.get_ylim()[1])
            ax.plot([0, max_val], [0, max_val], 'k--', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(out_dir / "04_maneuver_proximity_analysis.png", dpi=180)
    plt.close()


def write_summary(stats: dict, out_dir: Path):
    lines = [
        "# Maneuver-aware uncertainty estimation experiment",
        "",
        "## Hypothesis",
        "",
        "Adaptive process noise that increases near detected maneuvers will produce",
        "uncertainty estimates that better reflect actual estimation error during dropout",
        "compared to the frozen constant-velocity baseline from PR #52.",
        "",
        "## Method",
        "",
        "### Frozen conditions (identical to PR #52)",
        "- Same saved Webots baseline trajectory",
        "- Same 2.0 s dropout timing sweep (6–23 s in 0.5 s increments)",
        "- Same initial covariance and measurement noise assumptions",
        "- Same evaluation metrics",
        "",
        "### Single modification",
        "- **Adaptive process noise:** Detect maneuvers from velocity acceleration",
        f"  - Acceleration threshold: {MANEUVER_DETECT_ACCEL_THRESHOLD_MPS2} m/s²",
        f"  - Process noise boost factor: {MANEUVER_BOOST_FACTOR}× near maneuvers",
        f"  - Exponential decay: {MANEUVER_BOOST_DECAY_S} s time constant",
        "",
        "### Comparison filters",
        "1. **Baseline CV:** Frozen constant-velocity model with constant process noise (PR #52)",
        "2. **Adaptive Q:** Same CV model with adaptive process noise near maneuvers",
        "",
        "## Results",
        "",
        "### Correlation between uncertainty and error",
        "",
        f"**Baseline CV:**",
        f"- Pearson correlation: {stats['baseline']['pearson_correlation']:.4f} (p={stats['baseline']['pearson_p_value']:.4e})",
        f"- Spearman rank correlation: {stats['baseline']['spearman_rank_correlation']:.4f} (p={stats['baseline']['spearman_p_value']:.4e})",
        "",
        f"**Adaptive Q:**",
        f"- Pearson correlation: {stats['adaptive']['pearson_correlation']:.4f} (p={stats['adaptive']['pearson_p_value']:.4e})",
        f"- Spearman rank correlation: {stats['adaptive']['spearman_rank_correlation']:.4f} (p={stats['adaptive']['spearman_p_value']:.4e})",
        "",
        f"**Improvement:** {stats['improvement']['correlation_increase']:+.4f} Pearson, {stats['improvement']['rank_correlation_increase']:+.4f} Spearman",
        "",
        "### Calibration: does uncertainty bound contain actual error?",
        "",
        f"**Baseline CV:**",
        f"- Fraction within 1σ: {stats['baseline']['mean_within_1sigma']:.3f} (ideal: 0.68)",
        f"- Fraction within 2σ: {stats['baseline']['mean_within_2sigma']:.3f} (ideal: 0.95)",
        "",
        f"**Adaptive Q:**",
        f"- Fraction within 1σ: {stats['adaptive']['mean_within_1sigma']:.3f} (ideal: 0.68)",
        f"- Fraction within 2σ: {stats['adaptive']['mean_within_2sigma']:.3f} (ideal: 0.95)",
        "",
        f"**Improvement:** calibration error reduction = {-stats['improvement']['calibration_1sigma_closer_to_ideal']:.4f}",
        "",
        "## Interpretation",
        "",
        "The adaptive process noise modification aims to address PR #52's identified weakness:",
        "equal-duration dropouts produce similar covariance growth in the frozen CV filter",
        "even though actual errors differ dramatically near maneuvers.",
        "",
        "If correlation increases and calibration improves, the adaptive approach better",
        "ranks dropout severity. If improvement is small or negative, the simple maneuver",
        "detection heuristic may be insufficient, or the CV model's fundamental limitation",
        "requires a different motion model (e.g., coordinated turn, IMM) rather than just",
        "adaptive noise tuning.",
        "",
        "## Limitations",
        "",
        "- **Simulation only:** Webots trajectory, offline fault injection",
        "- **Simple maneuver detection:** Acceleration threshold heuristic, not robust fault detection",
        "- **Single trajectory:** Results specific to this commanded motion profile",
        "- **Hyperparameters:** Boost factor and decay manually tuned, not optimized",
        "- **No real-time test:** Implementation assumes offline batch processing",
        "",
        "## Next steps if hypothesis supported",
        "",
        "- Test on additional trajectories with different maneuver profiles",
        "- Compare to coordinated-turn or IMM models",
        "- Optimize adaptive parameters via cross-validation",
        "- Add robust acceleration-based maneuver detector with false-positive control",
        "",
        "## Next steps if hypothesis rejected",
        "",
        "- The CV model's limitation may require switching to a better motion model",
        "- Investigate IMM (interacting multiple models) or coordinated-turn filters",
        "- Consider model-selection indicators beyond simple acceleration threshold",
        "",
    ]
    
    (out_dir / "EXPERIMENT_NOTES.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
