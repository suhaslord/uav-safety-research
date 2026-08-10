from __future__ import annotations

from pathlib import Path
import argparse
import json

import numpy as np
import pandas as pd

from uav_safety.image_perception import IMAGE_CONDITIONS
from uav_safety.image_temporal import Phase6LandingPadRenderer
from uav_safety.selective_confidence_v2 import (
    SharpnessAwarePadEstimator,
    altitude_observability_cap,
    altitude_scale_bin_width_m,
    fit_component_calibrator,
)


THRESHOLDS = (0.40, 0.50, 0.60, 0.70, 0.80, 0.90)


def run_frames(*, sequences: int, frames: int, seed: int, calibration_seed: int, calibration_samples: int):
    calibrator = fit_component_calibrator(
        seed=calibration_seed,
        samples_per_condition=calibration_samples,
    )
    renderer = Phase6LandingPadRenderer()
    estimator = SharpnessAwarePadEstimator()
    rng = np.random.default_rng(seed)
    rows = []

    for condition in IMAGE_CONDITIONS:
        for sequence_id in range(sequences):
            x0 = float(rng.uniform(-2.5, 2.5))
            vx = float(rng.uniform(-0.12, 0.12))
            z0 = float(rng.uniform(4.2, 5.8))
            descent_rate = float(rng.uniform(0.38, 0.62))
            phase = float(rng.uniform(0.0, 2 * np.pi))
            severity = float(rng.uniform(0.75, 1.35))

            for frame_index in range(frames):
                t = 0.05 * frame_index
                x_true = float(x0 + vx * t + 0.10 * np.sin(0.7 * t + phase))
                z_true = float(max(0.25, z0 - descent_rate * t))
                frame_seed = int(rng.integers(0, 2**31 - 1))
                frame = renderer.render(
                    x_true,
                    z_true,
                    np.random.default_rng(frame_seed),
                    condition,
                    severity,
                )
                m = estimator.estimate(frame)
                learned_px, learned_pz = calibrator.learned_probabilities(m)
                px, pz = calibrator.probabilities(m)
                z_cap = altitude_observability_cap(m, calibrator.tolerance_z_m)
                z_bin_width = altitude_scale_bin_width_m(m)
                x_error = abs(m.x_m - x_true) if m.valid else np.inf
                z_error = abs(m.z_m - z_true) if m.valid else np.inf
                rows.append({
                    "condition": condition,
                    "sequence_id": sequence_id,
                    "frame_index": frame_index,
                    "valid": bool(m.valid),
                    "p_x_good": px,
                    "p_z_good": pz,
                    "learned_p_x_good": learned_px,
                    "learned_p_z_good": learned_pz,
                    "altitude_observability_cap": z_cap,
                    "altitude_scale_bin_width_m": z_bin_width,
                    "observability_cap_active": bool(pz + 1e-12 < learned_pz),
                    "joint_lower_bound": calibrator.joint_probability_lower_bound(m),
                    "x_good": bool(m.valid and x_error <= calibrator.tolerance_x_m),
                    "z_good": bool(m.valid and z_error <= calibrator.tolerance_z_m),
                    "joint_good": bool(
                        m.valid
                        and x_error <= calibrator.tolerance_x_m
                        and z_error <= calibrator.tolerance_z_m
                    ),
                    "x_error_m": x_error if np.isfinite(x_error) else np.nan,
                    "z_error_m": z_error if np.isfinite(z_error) else np.nan,
                    "raw_confidence": m.raw_confidence,
                    "geometry_score": m.geometry_score,
                    "sharpness_score": m.sharpness_score,
                    "measured_z_m": m.z_m,
                    "bbox_width_px": m.bbox_width_px,
                    "contrast": m.contrast,
                })
    return pd.DataFrame(rows), calibrator


def _ece(group: pd.DataFrame, prob_col: str, label_col: str, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = len(group)
    result = 0.0
    for i in range(bins):
        idx = (group[prob_col] >= edges[i]) & (
            group[prob_col] <= edges[i + 1] if i == bins - 1
            else group[prob_col] < edges[i + 1]
        )
        bucket = group[idx]
        if len(bucket):
            result += len(bucket) / total * abs(float(bucket[prob_col].mean()) - float(bucket[label_col].mean()))
    return float(result)


def calibration_summary(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for condition, group in raw.groupby("condition", sort=True):
        rows.append({
            "condition": condition,
            "frames": len(group),
            "x_good_rate": float(group["x_good"].mean()),
            "z_good_rate": float(group["z_good"].mean()),
            "joint_good_rate": float(group["joint_good"].mean()),
            "mean_p_x_good": float(group["p_x_good"].mean()),
            "mean_p_z_good": float(group["p_z_good"].mean()),
            "mean_learned_p_z_good": float(group["learned_p_z_good"].mean()),
            "mean_altitude_observability_cap": float(group["altitude_observability_cap"].mean()),
            "observability_cap_active_rate": float(group["observability_cap_active"].mean()),
            "x_ece": _ece(group, "p_x_good", "x_good"),
            "z_ece": _ece(group, "p_z_good", "z_good"),
            "mean_sharpness": float(group["sharpness_score"].mean()),
        })
    return pd.DataFrame(rows)


def risk_coverage(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for condition, group in raw.groupby("condition", sort=True):
        for threshold in THRESHOLDS:
            x_selected = group[group["p_x_good"] >= threshold]
            z_selected = group[group["p_z_good"] >= threshold]
            joint_selected = group[
                (group["p_x_good"] >= threshold) & (group["p_z_good"] >= threshold)
            ]
            rows.append({
                "condition": condition,
                "threshold": threshold,
                "x_coverage": len(x_selected) / len(group),
                "x_selected_bad_rate": float((~x_selected["x_good"]).mean()) if len(x_selected) else np.nan,
                "z_coverage": len(z_selected) / len(group),
                "z_selected_bad_rate": float((~z_selected["z_good"]).mean()) if len(z_selected) else np.nan,
                "joint_coverage": len(joint_selected) / len(group),
                "joint_selected_bad_rate": float((~joint_selected["joint_good"]).mean()) if len(joint_selected) else np.nan,
                "x_bad_rejection_recall": float((group.loc[~group["x_good"], "p_x_good"] < threshold).mean()) if (~group["x_good"]).any() else 0.0,
                "z_bad_rejection_recall": float((group.loc[~group["z_good"], "p_z_good"] < threshold).mean()) if (~group["z_good"]).any() else 0.0,
            })
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="Evaluate Phase 6B component confidence calibration and observability.")
    parser.add_argument("--sequences", type=int, default=20)
    parser.add_argument("--frames", type=int, default=100)
    parser.add_argument("--seed", type=int, default=656565)
    parser.add_argument("--calibration-seed", type=int, default=616161)
    parser.add_argument("--calibration-samples", type=int, default=260)
    parser.add_argument("--out", type=Path, default=Path("results/phase6b_component_calibration"))
    args = parser.parse_args()
    if args.seed == args.calibration_seed:
        raise ValueError("benchmark and calibration seeds must differ")

    raw, calibrator = run_frames(
        sequences=args.sequences,
        frames=args.frames,
        seed=args.seed,
        calibration_seed=args.calibration_seed,
        calibration_samples=args.calibration_samples,
    )
    summary = calibration_summary(raw)
    curves = risk_coverage(raw)

    args.out.mkdir(parents=True, exist_ok=True)
    raw.to_csv(args.out / "frames.csv", index=False)
    summary.to_csv(args.out / "calibration_summary.csv", index=False)
    curves.to_csv(args.out / "risk_coverage.csv", index=False)
    (args.out / "calibrator.json").write_text(json.dumps(calibrator.to_dict(), indent=2), encoding="utf-8")
    (args.out / "summary.md").write_text(
        "# Phase 6B component-confidence benchmark\n\n"
        "Lateral and altitude reliability are calibrated separately. Final altitude confidence is the learned probability capped by the synthetic renderer's scale observability. Risk/coverage is reported over fixed probability thresholds.\n\n"
        "## Calibration\n\n"
        + summary.to_markdown(index=False)
        + "\n\n## Risk / coverage\n\n"
        + curves.to_markdown(index=False)
        + "\n",
        encoding="utf-8",
    )

    print("Calibration summary:")
    print(summary.to_string(index=False))
    print("\nRisk / coverage:")
    print(curves.to_string(index=False))
    print(f"\nSaved Phase 6B calibration benchmark to {args.out.resolve()}")


if __name__ == "__main__":
    main()
