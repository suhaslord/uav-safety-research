from __future__ import annotations

from pathlib import Path
import argparse
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from uav_safety.image_perception import IMAGE_CONDITIONS
from uav_safety.image_temporal import (
    CalibratedTemporalImagePipeline,
    Phase6LandingPadRenderer,
    Phase6PadEstimator,
    fit_synthetic_calibrator,
)


def run_benchmark(
    *,
    sequences_per_condition: int,
    frames_per_sequence: int,
    seed: int,
    calibration_seed: int,
    calibration_samples: int,
) -> pd.DataFrame:
    calibrator = fit_synthetic_calibrator(
        seed=calibration_seed,
        samples_per_condition=calibration_samples,
    )
    renderer = Phase6LandingPadRenderer()
    estimator = Phase6PadEstimator()
    root_rng = np.random.default_rng(seed)
    rows: list[dict] = []

    for condition in IMAGE_CONDITIONS:
        for sequence_id in range(sequences_per_condition):
            pipeline = CalibratedTemporalImagePipeline(calibrator)
            x0 = float(root_rng.uniform(-2.5, 2.5))
            vx = float(root_rng.uniform(-0.12, 0.12))
            z0 = float(root_rng.uniform(4.2, 5.6))
            descent_rate = float(root_rng.uniform(0.38, 0.62))
            phase = float(root_rng.uniform(0.0, 2 * np.pi))
            severity = float(root_rng.uniform(0.80, 1.30))

            for frame_index in range(frames_per_sequence):
                t = frame_index * pipeline.cfg.dt
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

                raw = estimator.estimate(image)
                obs, diag = pipeline.update(image)
                raw_x_error = abs(raw.x_m - x_true) if raw.valid else np.inf
                raw_z_error = abs(raw.z_m - z_true) if raw.valid else np.inf
                raw_bad = bool(
                    not raw.valid
                    or raw_x_error > calibrator.tolerance_x_m
                    or raw_z_error > calibrator.tolerance_z_m
                )

                rows.append({
                    "condition": condition,
                    "sequence_id": sequence_id,
                    "frame_index": frame_index,
                    "severity": severity,
                    "raw_valid": raw.valid,
                    "raw_confidence": raw.raw_confidence,
                    "calibrated_confidence": diag.calibrated_confidence,
                    "geometry_score": raw.geometry_score,
                    "raw_x_error_m": raw_x_error if np.isfinite(raw_x_error) else np.nan,
                    "raw_z_error_m": raw_z_error if np.isfinite(raw_z_error) else np.nan,
                    "raw_bad": raw_bad,
                    "abstained": diag.abstained,
                    "reacquired": diag.reacquired,
                    "filtered_x_error_m": abs(obs.x - x_true),
                    "filtered_z_error_m": abs(obs.z - z_true),
                    "filtered_dropped": obs.dropped,
                })

    return pd.DataFrame(rows)


def summarize(raw: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for condition, group in raw.groupby("condition", sort=True):
        bad = group[group["raw_bad"]]
        good = group[~group["raw_bad"]]
        accepted = group[~group["abstained"]]
        rejected = group[group["abstained"]]
        rows.append({
            "condition": condition,
            "frames": len(group),
            "coverage": float((~group["abstained"]).mean()),
            "abstention_rate": float(group["abstained"].mean()),
            "raw_bad_rate": float(group["raw_bad"].mean()),
            "bad_frame_abstention_recall": float(bad["abstained"].mean()) if len(bad) else 0.0,
            "good_frame_false_abstention_rate": float(good["abstained"].mean()) if len(good) else 0.0,
            "accepted_raw_x_mae_m": float(accepted["raw_x_error_m"].mean()) if len(accepted) else np.nan,
            "rejected_raw_x_mae_m": float(rejected["raw_x_error_m"].mean()) if len(rejected) else np.nan,
            "accepted_filtered_x_mae_m": float(accepted["filtered_x_error_m"].mean()) if len(accepted) else np.nan,
            "all_filtered_x_mae_m": float(group["filtered_x_error_m"].mean()),
            "all_filtered_z_mae_m": float(group["filtered_z_error_m"].mean()),
            "reacquisitions": int(group["reacquired"].sum()),
        })
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure Phase 6 temporal abstention selectivity on held-out synthetic sequences.")
    parser.add_argument("--sequences", type=int, default=20)
    parser.add_argument("--frames", type=int, default=100)
    parser.add_argument("--seed", type=int, default=636363)
    parser.add_argument("--calibration-seed", type=int, default=616161)
    parser.add_argument("--calibration-samples", type=int, default=180)
    parser.add_argument("--out", type=Path, default=Path("results/phase6_selective_perception"))
    args = parser.parse_args()

    if args.sequences < 1 or args.frames < 2:
        raise ValueError("sequences must be >= 1 and frames >= 2")
    if args.seed == args.calibration_seed:
        raise ValueError("sequence and calibration seeds must differ")

    raw = run_benchmark(
        sequences_per_condition=args.sequences,
        frames_per_sequence=args.frames,
        seed=args.seed,
        calibration_seed=args.calibration_seed,
        calibration_samples=args.calibration_samples,
    )
    summary = summarize(raw)
    args.out.mkdir(parents=True, exist_ok=True)
    raw.to_csv(args.out / "frames.csv", index=False)
    summary.to_csv(args.out / "summary.csv", index=False)
    (args.out / "summary.md").write_text(
        "# Phase 6 selective-perception benchmark\n\n"
        "`bad_frame_abstention_recall` is the fraction of frame-level estimates "
        "outside the calibration error tolerances that the temporal pipeline "
        "rejected. `good_frame_false_abstention_rate` measures unnecessary "
        "rejection of estimates inside those tolerances.\n\n"
        + summary.to_markdown(index=False)
        + "\n",
        encoding="utf-8",
    )
    (args.out / "run_metadata.json").write_text(json.dumps({
        "sequence_seed": args.seed,
        "calibration_seed": args.calibration_seed,
        "sequences_per_condition": args.sequences,
        "frames_per_sequence": args.frames,
        "conditions": list(IMAGE_CONDITIONS),
        "scope": "simulation-only temporal synthetic image perception",
    }, indent=2), encoding="utf-8")

    plot = summary.set_index("condition")[["raw_bad_rate", "abstention_rate", "bad_frame_abstention_recall"]]
    plot.plot(kind="bar")
    plt.ylabel("Rate")
    plt.xlabel("Image condition")
    plt.ylim(0, 1)
    plt.title("Phase 6 selective perception")
    plt.tight_layout()
    plt.savefig(args.out / "selectivity.png", dpi=180)
    plt.close()

    print(summary.to_string(index=False))
    print(f"\nSaved selective-perception results to {args.out.resolve()}")


if __name__ == "__main__":
    main()
