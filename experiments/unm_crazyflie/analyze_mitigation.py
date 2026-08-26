#!/usr/bin/env python3
"""Compare simple measurement-fault mitigation strategies on the frozen UNM Webots trajectory.

Strategies:
- baseline: unchanged Kalman update
- reject: skip a measurement update when its 2-DOF NIS exceeds a fixed 99.9% chi-square gate
- downweight: keep the measurement, but inflate R by 16x when the same gate fires

The underlying trajectory, CV process model, and fault matrix are unchanged.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from analyze_faults import (
    ACCEL_PROCESS_SIGMA_MPS2,
    BASE_SEED,
    INITIAL_POSITION_SIGMA_M,
    INITIAL_VELOCITY_SIGMA_MPS,
    POSITION_MEAS_SIGMA_M,
    load_baseline,
)

NIS_GATE_2DOF_999 = 13.815510557964274
DOWNWEIGHT_R_SCALE = 16.0


@dataclass
class RunResult:
    estimate: np.ndarray
    nis: np.ndarray
    alerts: int
    rejected: int
    downweighted: int


def run_filter(t: np.ndarray, measurements: np.ndarray, strategy: str) -> RunResult:
    if strategy not in {"baseline", "reject", "downweight"}:
        raise ValueError(f"unknown strategy: {strategy}")

    initial = measurements[0] if np.isfinite(measurements[0]).all() else np.zeros(2)
    x = np.array([initial[0], initial[1], 0.0, 0.0], dtype=float)
    P = np.diag([
        INITIAL_POSITION_SIGMA_M**2,
        INITIAL_POSITION_SIGMA_M**2,
        INITIAL_VELOCITY_SIGMA_MPS**2,
        INITIAL_VELOCITY_SIGMA_MPS**2,
    ])
    H = np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]])
    R0 = np.eye(2) * POSITION_MEAS_SIGMA_M**2

    est = np.empty_like(measurements)
    est[0] = x[:2]
    nis = np.full(len(t), np.nan)
    alerts = rejected = downweighted = 0

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
            S0 = H @ P @ H.T + R0
            current_nis = float(y.T @ np.linalg.inv(S0) @ y)
            nis[i] = current_nis
            flagged = current_nis > NIS_GATE_2DOF_999
            alerts += int(flagged)

            if strategy == "reject" and flagged:
                rejected += 1
            else:
                R = R0
                if strategy == "downweight" and flagged:
                    R = R0 * DOWNWEIGHT_R_SCALE
                    downweighted += 1
                S = H @ P @ H.T + R
                K = P @ H.T @ np.linalg.inv(S)
                x = x + K @ y
                P = (np.eye(4) - K @ H) @ P

        est[i] = x[:2]

    return RunResult(est, nis, alerts, rejected, downweighted)


def metrics(t: np.ndarray, truth: np.ndarray, result: RunResult, fault_start: float | None, fault_end: float | None) -> dict:
    err = np.linalg.norm(result.estimate - truth, axis=1)
    out = {
        "overall_rmse_m": float(np.sqrt(np.mean(err**2))),
        "max_error_m": float(np.max(err)),
        "alerts": result.alerts,
        "rejected": result.rejected,
        "downweighted": result.downweighted,
    }
    if fault_start is None or fault_end is None:
        out["fault_window_rmse_m"] = float("nan")
    else:
        mask = (t >= fault_start) & (t < fault_end)
        out["fault_window_rmse_m"] = float(np.sqrt(np.mean(err[mask] ** 2))) if np.any(mask) else float("nan")
    return out


def build_cases(t: np.ndarray, truth: np.ndarray):
    cases = [("nominal", "none", 0.0, truth.copy(), None, None, 0)]

    for sigma in (0.04, 0.08, 0.16, 0.32):
        for trial in range(30):
            rng = np.random.default_rng(BASE_SEED + int(sigma * 1000) * 100 + trial)
            z = truth + rng.normal(0.0, sigma, size=truth.shape)
            cases.append((f"noise_{sigma:.2f}_trial_{trial:02d}", "noise", sigma, z, 0.0, float(t[-1]) + 1e-9, trial))

    for bias in (0.05, 0.10, 0.20, 0.40):
        z = truth.copy()
        mask = (t >= 12.0) & (t < 16.0)
        z[mask, 0] += bias
        cases.append((f"bias_{bias:.2f}", "bias", bias, z, 12.0, 16.0, 0))

    for duration in (0.5, 1.0, 2.0, 4.0):
        z = truth.copy()
        mask = (t >= 12.0) & (t < 12.0 + duration)
        z[mask] = np.nan
        cases.append((f"dropout_{duration:.1f}", "dropout", duration, z, 12.0, 12.0 + duration, 0))
    return cases


def aggregate(rows: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        key = (r["fault_type"], float(r["severity"]), r["strategy"])
        groups.setdefault(key, []).append(r)
    out = []
    for (fault, severity, strategy), items in sorted(groups.items()):
        fault_values = [x["fault_window_rmse_m"] for x in items if np.isfinite(x["fault_window_rmse_m"])]
        out.append({
            "fault_type": fault,
            "severity": severity,
            "strategy": strategy,
            "trials": len(items),
            "mean_overall_rmse_m": float(np.mean([x["overall_rmse_m"] for x in items])),
            "mean_fault_window_rmse_m": float(np.mean(fault_values)) if fault_values else float("nan"),
            "mean_max_error_m": float(np.mean([x["max_error_m"] for x in items])),
            "mean_alerts": float(np.mean([x["alerts"] for x in items])),
            "mean_rejected": float(np.mean([x["rejected"] for x in items])),
            "mean_downweighted": float(np.mean([x["downweighted"] for x in items])),
        })
    return out


def write_summary(path: Path, agg: list[dict]) -> None:
    lookup = {(r["fault_type"], r["severity"], r["strategy"]): r for r in agg}
    lines = [
        "# UNM Crazyflie fault-mitigation comparison",
        "",
        "## Frozen design",
        "",
        f"- NIS gate: chi-square 2 DOF, 99.9% = `{NIS_GATE_2DOF_999:.6f}`.",
        "- Baseline: unchanged position Kalman update.",
        "- Reject: flagged measurements do not update the filter.",
        f"- Down-weight: flagged measurements use `{DOWNWEIGHT_R_SCALE:.0f}x` measurement covariance.",
        "- Same trajectory, CV model, and noise/bias/dropout severity matrix as the existing Webots benchmark.",
        "",
        "## Comparison",
        "",
        "| Fault | Severity | Baseline RMSE | Reject RMSE | Down-weight RMSE | Best |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for fault in ("noise", "bias", "dropout"):
        severities = sorted({r["severity"] for r in agg if r["fault_type"] == fault})
        for sev in severities:
            vals = {s: lookup[(fault, sev, s)]["mean_overall_rmse_m"] for s in ("baseline", "reject", "downweight")}
            best = min(vals, key=vals.get)
            lines.append(f"| {fault} | {sev:g} | {vals['baseline']:.6f} | {vals['reject']:.6f} | {vals['downweight']:.6f} | {best} |")
    lines += [
        "",
        "## Interpretation boundary",
        "",
        "Residual/NIS gating can mitigate *received but suspicious* measurements (noise/bias). It cannot directly mitigate a dropout because no measurement arrives to reject or down-weight; dropout performance is therefore expected to remain the same unless the process/uncertainty model or fallback estimator is changed.",
        "",
        "This remains a simulation-only Webots/offline-fault experiment and is not a real-aircraft safety claim.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("baseline_csv", type=Path)
    ap.add_argument("--results-dir", type=Path, required=True)
    args = ap.parse_args()
    args.results_dir.mkdir(parents=True, exist_ok=True)

    baseline = load_baseline(args.baseline_csv)
    t, truth = baseline.t, baseline.xy
    rows = []
    for case_name, fault_type, severity, z, start, end, trial in build_cases(t, truth):
        for strategy in ("baseline", "reject", "downweight"):
            result = run_filter(t, z, strategy)
            rows.append({
                "case": case_name,
                "fault_type": fault_type,
                "severity": float(severity),
                "trial": trial,
                "strategy": strategy,
                **metrics(t, truth, result, start, end),
            })

    detail = args.results_dir / "mitigation_trial_metrics.csv"
    with detail.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    agg = aggregate(rows)
    agg_path = args.results_dir / "mitigation_aggregate.csv"
    with agg_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(agg[0]))
        writer.writeheader()
        writer.writerows(agg)

    write_summary(args.results_dir / "MITIGATION_RESULTS.md", agg)
    print((args.results_dir / "MITIGATION_RESULTS.md").read_text())


if __name__ == "__main__":
    main()
