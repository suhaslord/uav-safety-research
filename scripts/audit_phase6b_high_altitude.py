from __future__ import annotations

from pathlib import Path
import argparse

import numpy as np
import pandas as pd

from uav_safety.image_perception import IMAGE_CONDITIONS
from uav_safety.image_temporal import Phase6LandingPadRenderer
from uav_safety.selective_confidence_v2 import (
    SharpnessAwarePadEstimator,
    fit_component_calibrator,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Phase 6B component confidence in the high-altitude landing domain.")
    parser.add_argument("--samples", type=int, default=400)
    parser.add_argument("--seed", type=int, default=666666)
    parser.add_argument("--calibration-seed", type=int, default=616161)
    parser.add_argument("--calibration-samples", type=int, default=280)
    parser.add_argument("--threshold", type=float, default=0.80)
    parser.add_argument("--z-min", type=float, default=5.8)
    parser.add_argument("--z-max", type=float, default=8.0)
    parser.add_argument("--out", type=Path, default=Path("results/phase6b_high_altitude_audit"))
    args = parser.parse_args()

    if args.seed == args.calibration_seed:
        raise ValueError("audit and calibration seeds must differ")
    if not args.z_min < args.z_max:
        raise ValueError("z-min must be below z-max")

    calibrator = fit_component_calibrator(
        seed=args.calibration_seed,
        samples_per_condition=args.calibration_samples,
    )
    renderer = Phase6LandingPadRenderer()
    estimator = SharpnessAwarePadEstimator()
    rng = np.random.default_rng(args.seed)
    rows = []

    for condition in IMAGE_CONDITIONS:
        for _ in range(args.samples):
            x_true = float(rng.uniform(-3.0, 3.0))
            z_true = float(rng.uniform(args.z_min, args.z_max))
            severity = float(rng.uniform(0.75, 1.35))
            frame_seed = int(rng.integers(0, 2**31 - 1))
            frame = renderer.render(
                x_true,
                z_true,
                np.random.default_rng(frame_seed),
                condition,
                severity,
            )
            m = estimator.estimate(frame)
            px, pz = calibrator.probabilities(m)
            x_good = bool(m.valid and abs(m.x_m - x_true) <= calibrator.tolerance_x_m)
            z_good = bool(m.valid and abs(m.z_m - z_true) <= calibrator.tolerance_z_m)
            rows.append({
                "condition": condition,
                "p_x_good": px,
                "p_z_good": pz,
                "x_good": x_good,
                "z_good": z_good,
                "x_selected": px >= args.threshold,
                "z_selected": pz >= args.threshold,
                "sharpness_score": m.sharpness_score,
                "measured_z_m": m.z_m,
                "true_z_m": z_true,
            })

    raw = pd.DataFrame(rows)
    summary_rows = []
    for condition, group in raw.groupby("condition", sort=True):
        x_bad = group[~group["x_good"]]
        z_bad = group[~group["z_good"]]
        x_sel = group[group["x_selected"]]
        z_sel = group[group["z_selected"]]
        summary_rows.append({
            "condition": condition,
            "frames": len(group),
            "x_good_rate": float(group["x_good"].mean()),
            "z_good_rate": float(group["z_good"].mean()),
            "mean_p_x_good": float(group["p_x_good"].mean()),
            "mean_p_z_good": float(group["p_z_good"].mean()),
            "x_coverage_at_threshold": float(group["x_selected"].mean()),
            "z_coverage_at_threshold": float(group["z_selected"].mean()),
            "x_selected_bad_rate": float((~x_sel["x_good"]).mean()) if len(x_sel) else np.nan,
            "z_selected_bad_rate": float((~z_sel["z_good"]).mean()) if len(z_sel) else np.nan,
            "x_bad_rejection_recall": float((x_bad["p_x_good"] < args.threshold).mean()) if len(x_bad) else 0.0,
            "z_bad_rejection_recall": float((z_bad["p_z_good"] < args.threshold).mean()) if len(z_bad) else 0.0,
        })

    summary = pd.DataFrame(summary_rows)
    args.out.mkdir(parents=True, exist_ok=True)
    raw.to_csv(args.out / "frames.csv", index=False)
    summary.to_csv(args.out / "summary.csv", index=False)
    (args.out / "summary.md").write_text(
        "# Phase 6B high-altitude confidence audit\n\n"
        f"Synthetic frames are restricted to z in [{args.z_min}, {args.z_max}] m. "
        f"The frozen development component threshold is {args.threshold:.2f}.\n\n"
        + summary.to_markdown(index=False)
        + "\n",
        encoding="utf-8",
    )
    print(summary.to_string(index=False))
    print(f"\nSaved high-altitude audit to {args.out.resolve()}")


if __name__ == "__main__":
    main()
