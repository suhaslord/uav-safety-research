from __future__ import annotations

from pathlib import Path
import argparse

import numpy as np
import pandas as pd

from uav_safety.image_perception import IMAGE_CONDITIONS
from uav_safety.image_temporal import Phase6LandingPadRenderer
from uav_safety.selective_confidence_v2 import SharpnessAwarePadEstimator, fit_component_calibrator


ALTITUDES_M = (
    0.08, 0.12, 0.18, 0.25, 0.40, 0.60, 0.80, 1.20,
    2.00, 3.00, 4.00, 5.00, 6.00, 7.00, 8.00,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Perception-only Phase 6 altitude scale-response benchmark.")
    parser.add_argument("--samples", type=int, default=40, help="samples per condition/altitude cell")
    parser.add_argument("--seed", type=int, default=687431)
    parser.add_argument("--calibration-seed", type=int, default=616161)
    parser.add_argument("--out", type=Path, default=Path("results/phase6_altitude_response"))
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    renderer = Phase6LandingPadRenderer()
    estimator = SharpnessAwarePadEstimator()
    calibrator = fit_component_calibrator(seed=args.calibration_seed, samples_per_condition=280)

    rows: list[dict] = []
    for condition in IMAGE_CONDITIONS:
        for true_z in ALTITUDES_M:
            for _ in range(args.samples):
                x_true = float(rng.uniform(-1.5, 1.5))
                frame_seed = int(rng.integers(0, 2**31 - 1))
                frame = renderer.render(
                    x_offset_m=x_true,
                    altitude_m=true_z,
                    rng=np.random.default_rng(frame_seed),
                    condition=condition,
                    severity=1.0,
                )
                m = estimator.estimate(frame)
                p_x, p_z = calibrator.probabilities(m)
                rows.append({
                    "condition": condition,
                    "true_z_m": true_z,
                    "x_true_m": x_true,
                    "frame_seed": frame_seed,
                    "valid": m.valid,
                    "measured_z_m": m.z_m if m.valid else np.nan,
                    "abs_z_error_m": abs(m.z_m - true_z) if m.valid else np.nan,
                    "measured_x_m": m.x_m if m.valid else np.nan,
                    "abs_x_error_m": abs(m.x_m - x_true) if m.valid else np.nan,
                    "bbox_width_px": m.bbox_width_px,
                    "selected_pixels": m.selected_pixels,
                    "raw_confidence": m.raw_confidence,
                    "geometry_score": m.geometry_score,
                    "contrast": m.contrast,
                    "sharpness_score": m.sharpness_score,
                    "scale_quantization_bin_width_m": m.scale_quantization_bin_width_m,
                    "p_x_good": p_x,
                    "p_z_good": p_z,
                })

    raw = pd.DataFrame(rows)
    summary = (
        raw.groupby(["condition", "true_z_m"], sort=True)
        .agg(
            samples=("frame_seed", "size"),
            valid_rate=("valid", "mean"),
            median_measured_z_m=("measured_z_m", "median"),
            mean_abs_z_error_m=("abs_z_error_m", "mean"),
            p95_abs_z_error_m=("abs_z_error_m", lambda s: s.quantile(0.95)),
            median_bbox_width_px=("bbox_width_px", "median"),
            median_selected_pixels=("selected_pixels", "median"),
            mean_p_z_good=("p_z_good", "mean"),
            fraction_p_z_below_080=("p_z_good", lambda s: float((s < 0.80).mean())),
            median_scale_quantization_bin_width_m=("scale_quantization_bin_width_m", "median"),
        )
        .reset_index()
    )
    summary["median_z_bias_m"] = summary["median_measured_z_m"] - summary["true_z_m"]

    # A compact observability table highlights where image scale ceases to be
    # one-to-one or confidence correctly identifies the loss of information.
    nominal = summary[summary["condition"].isin(["clean", "blur"])].copy()

    args.out.mkdir(parents=True, exist_ok=True)
    raw.to_csv(args.out / "frames.csv", index=False)
    summary.to_csv(args.out / "summary.csv", index=False)
    nominal.to_csv(args.out / "clean_blur_summary.csv", index=False)
    (args.out / "summary.md").write_text(
        "# Phase 6 perception-only altitude response\n\n"
        "This benchmark does not run the landing controller or supervisor. It maps the synthetic renderer/estimator scale response against known simulator altitude. Replacement held-out seeds are not used.\n\n"
        "## Clean and blur response\n\n" + nominal.to_markdown(index=False)
        + "\n\n## All conditions\n\n" + summary.to_markdown(index=False)
        + "\n",
        encoding="utf-8",
    )

    print(nominal.to_string(index=False))
    print(f"\nSaved perception-only altitude response to {args.out.resolve()}")


if __name__ == "__main__":
    main()
