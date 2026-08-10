from __future__ import annotations

from pathlib import Path
import argparse
import json

import numpy as np
import pandas as pd

from uav_safety.image_perception import IMAGE_CONDITIONS
from uav_safety.image_temporal import (
    CalibratedTemporalImagePipeline,
    Phase6LandingPadRenderer,
    Phase6PadEstimator,
    fit_synthetic_calibrator,
)
from uav_safety.selective_confidence import (
    ContextualTemporalImagePipeline,
    fit_contextual_calibrator,
)


def run_benchmark(*, sequences: int, frames: int, seed: int, calibration_seed: int, calibration_samples: int):
    scalar_cal = fit_synthetic_calibrator(seed=calibration_seed, samples_per_condition=calibration_samples)
    contextual_cal = fit_contextual_calibrator(seed=calibration_seed, samples_per_condition=calibration_samples)
    renderer = Phase6LandingPadRenderer()
    estimator = Phase6PadEstimator()
    root_rng = np.random.default_rng(seed)
    rows = []

    for condition in IMAGE_CONDITIONS:
        for sequence_id in range(sequences):
            scalar = CalibratedTemporalImagePipeline(scalar_cal)
            contextual = ContextualTemporalImagePipeline(contextual_cal)
            x0 = float(root_rng.uniform(-2.5, 2.5))
            vx = float(root_rng.uniform(-0.12, 0.12))
            z0 = float(root_rng.uniform(4.2, 5.6))
            descent_rate = float(root_rng.uniform(0.38, 0.62))
            phase = float(root_rng.uniform(0.0, 2 * np.pi))
            severity = float(root_rng.uniform(0.80, 1.30))

            for frame_index in range(frames):
                t = frame_index * scalar.cfg.dt
                x_true = float(x0 + vx * t + 0.10 * np.sin(0.7 * t + phase))
                z_true = float(max(0.25, z0 - descent_rate * t))
                frame_seed = int(root_rng.integers(0, 2**31 - 1))
                image = renderer.render(
                    x_true,
                    z_true,
                    np.random.default_rng(frame_seed),
                    condition,
                    severity,
                )
                m = estimator.estimate(image)
                xerr = abs(m.x_m - x_true) if m.valid else np.inf
                zerr = abs(m.z_m - z_true) if m.valid else np.inf
                good = bool(m.valid and xerr <= scalar_cal.tolerance_x_m and zerr <= scalar_cal.tolerance_z_m)

                for name, pipeline in (("scalar", scalar), ("contextual", contextual)):
                    obs, diag = pipeline.update(image)
                    rows.append({
                        "condition": condition,
                        "sequence_id": sequence_id,
                        "frame_index": frame_index,
                        "calibrator": name,
                        "good": good,
                        "bad": not good,
                        "abstained": bool(diag.abstained),
                        "calibrated_confidence": float(diag.calibrated_confidence),
                        "raw_confidence": float(diag.raw_confidence),
                        "geometry_score": float(diag.geometry_score),
                        "raw_x_error_m": xerr if np.isfinite(xerr) else np.nan,
                        "raw_z_error_m": zerr if np.isfinite(zerr) else np.nan,
                        "filtered_x_error_m": abs(obs.x - x_true),
                        "filtered_z_error_m": abs(obs.z - z_true),
                    })
    return pd.DataFrame(rows), scalar_cal, contextual_cal


def _ece(group: pd.DataFrame, bins: int = 10) -> float:
    if group.empty:
        return float("nan")
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = len(group)
    ece = 0.0
    for i in range(bins):
        idx = (group["calibrated_confidence"] >= edges[i]) & (
            group["calibrated_confidence"] <= edges[i + 1] if i == bins - 1
            else group["calibrated_confidence"] < edges[i + 1]
        )
        b = group[idx]
        if len(b):
            ece += len(b) / total * abs(float(b["calibrated_confidence"].mean()) - float(b["good"].mean()))
    return float(ece)


def summarize(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (condition, calibrator), group in raw.groupby(["condition", "calibrator"], sort=True):
        bad = group[group["bad"]]
        good = group[group["good"]]
        accepted = group[~group["abstained"]]
        rows.append({
            "condition": condition,
            "calibrator": calibrator,
            "frames": len(group),
            "coverage": float((~group["abstained"]).mean()),
            "abstention_rate": float(group["abstained"].mean()),
            "bad_frame_rate": float(group["bad"].mean()),
            "bad_frame_abstention_recall": float(bad["abstained"].mean()) if len(bad) else 0.0,
            "good_frame_false_abstention_rate": float(good["abstained"].mean()) if len(good) else 0.0,
            "accepted_bad_rate": float(accepted["bad"].mean()) if len(accepted) else np.nan,
            "calibration_ece": _ece(group),
            "accepted_raw_x_mae_m": float(accepted["raw_x_error_m"].mean()) if len(accepted) else np.nan,
            "accepted_raw_z_mae_m": float(accepted["raw_z_error_m"].mean()) if len(accepted) else np.nan,
            "accepted_filtered_x_mae_m": float(accepted["filtered_x_error_m"].mean()) if len(accepted) else np.nan,
            "accepted_filtered_z_mae_m": float(accepted["filtered_z_error_m"].mean()) if len(accepted) else np.nan,
        })
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="Compare scalar and contextual Phase 6 confidence calibration.")
    parser.add_argument("--sequences", type=int, default=12)
    parser.add_argument("--frames", type=int, default=90)
    parser.add_argument("--seed", type=int, default=646464)
    parser.add_argument("--calibration-seed", type=int, default=616161)
    parser.add_argument("--calibration-samples", type=int, default=180)
    parser.add_argument("--out", type=Path, default=Path("results/phase6_confidence_ablation"))
    args = parser.parse_args()
    if args.seed == args.calibration_seed:
        raise ValueError("benchmark and calibration seeds must differ")

    raw, scalar_cal, contextual_cal = run_benchmark(
        sequences=args.sequences,
        frames=args.frames,
        seed=args.seed,
        calibration_seed=args.calibration_seed,
        calibration_samples=args.calibration_samples,
    )
    summary = summarize(raw)
    args.out.mkdir(parents=True, exist_ok=True)
    raw.to_csv(args.out / "frames.csv", index=False)
    summary.to_csv(args.out / "summary.csv", index=False)
    (args.out / "scalar_calibrator.json").write_text(json.dumps(scalar_cal.to_dict(), indent=2), encoding="utf-8")
    (args.out / "contextual_calibrator.json").write_text(json.dumps(contextual_cal.to_dict(), indent=2), encoding="utf-8")
    (args.out / "summary.md").write_text(
        "# Phase 6 confidence ablation\n\n"
        "Both pipelines see identical synthetic frames. `bad_frame_abstention_recall` measures rejection of estimates outside the predefined x/z calibration tolerances; `accepted_bad_rate` measures the residual bad-frame fraction after abstention.\n\n"
        + summary.to_markdown(index=False)
        + "\n",
        encoding="utf-8",
    )
    print(summary.to_string(index=False))
    print(f"\nSaved confidence ablation to {args.out.resolve()}")


if __name__ == "__main__":
    main()
