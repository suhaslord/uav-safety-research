from __future__ import annotations

from pathlib import Path
import argparse

import numpy as np
import pandas as pd

from uav_safety.image_perception import IMAGE_CONDITIONS
from uav_safety.image_temporal import Phase6LandingPadRenderer
from uav_safety.phase6_scale_censor import analyze_scale_censor
from uav_safety.selective_confidence_v2 import SharpnessAwarePadEstimator, fit_component_calibrator


ALTITUDES_M = (
    0.08, 0.12, 0.18, 0.25, 0.40, 0.60, 0.80, 1.20,
    2.00, 3.00, 4.00, 5.00, 6.00, 7.00, 8.00,
)
Z_ERROR_TOLERANCE_M = 0.85
P_Z_THRESHOLD = 0.80


def _safe_rate(mask: pd.Series) -> float:
    return float(mask.mean()) if len(mask) else float("nan")


def main() -> None:
    parser = argparse.ArgumentParser(description="Perception-only benchmark for Phase 6 field-of-view scale censoring.")
    parser.add_argument("--samples", type=int, default=40)
    parser.add_argument("--seed", type=int, default=687431)
    parser.add_argument("--calibration-seed", type=int, default=616161)
    parser.add_argument("--out", type=Path, default=Path("results/phase6_scale_censor"))
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
                measurement = estimator.estimate(frame)
                _, p_z = calibrator.probabilities(measurement)
                censor = analyze_scale_censor(frame)
                z_error = abs(measurement.z_m - true_z) if measurement.valid else np.inf
                bad_z = bool((not measurement.valid) or z_error > Z_ERROR_TOLERANCE_M)
                soft_low_confidence = bool(p_z < P_Z_THRESHOLD)
                hard_censored = bool(censor.scale_censored)
                if hard_censored:
                    state = "hard_censored"
                elif soft_low_confidence:
                    state = "soft_low_pz"
                else:
                    state = "nominal"

                rows.append({
                    "condition": condition,
                    "true_z_m": true_z,
                    "x_true_m": x_true,
                    "frame_seed": frame_seed,
                    "valid": measurement.valid,
                    "measured_z_m": measurement.z_m if measurement.valid else np.nan,
                    "abs_z_error_m": z_error,
                    "bad_z": bad_z,
                    "p_z_good": p_z,
                    "soft_low_confidence": soft_low_confidence,
                    "scale_censored": hard_censored,
                    "phase6e_perception_state": state,
                    "border_foreground_pixels": censor.border_foreground_pixels,
                    "border_foreground_fraction": censor.border_foreground_fraction,
                    "touched_sides": censor.touched_sides,
                    "total_foreground_pixels": censor.total_foreground_pixels,
                    "bbox_width_px": measurement.bbox_width_px,
                    "selected_pixels": measurement.selected_pixels,
                })

    raw = pd.DataFrame(rows)

    cell_rows: list[dict] = []
    for (condition, true_z), group in raw.groupby(["condition", "true_z_m"], sort=True):
        bad = group["bad_z"]
        censored = group["scale_censored"]
        low_pz = group["soft_low_confidence"]
        cell_rows.append({
            "condition": condition,
            "true_z_m": true_z,
            "samples": len(group),
            "bad_z_rate": _safe_rate(bad),
            "scale_censored_rate": _safe_rate(censored),
            "low_pz_rate": _safe_rate(low_pz),
            "hard_censor_bad_z_precision": _safe_rate(group.loc[censored, "bad_z"]) if censored.any() else np.nan,
            "bad_z_censor_recall": _safe_rate(group.loc[bad, "scale_censored"]) if bad.any() else np.nan,
            "mean_p_z_good": float(group["p_z_good"].mean()),
            "median_abs_z_error_m": float(group["abs_z_error_m"].replace(np.inf, np.nan).median()),
            "p95_abs_z_error_m": float(group["abs_z_error_m"].replace(np.inf, np.nan).quantile(0.95)),
            "median_border_foreground_pixels": float(group["border_foreground_pixels"].median()),
        })
    cells = pd.DataFrame(cell_rows)

    state_summary = (
        raw.groupby(["condition", "phase6e_perception_state"], sort=True)
        .agg(
            frames=("frame_seed", "size"),
            bad_z_rate=("bad_z", "mean"),
            mean_abs_z_error_m=("abs_z_error_m", lambda s: float(s.replace(np.inf, np.nan).mean())),
            p95_abs_z_error_m=("abs_z_error_m", lambda s: float(s.replace(np.inf, np.nan).quantile(0.95))),
            mean_p_z_good=("p_z_good", "mean"),
            mean_border_foreground_pixels=("border_foreground_pixels", "mean"),
        )
        .reset_index()
    )

    global_rows: list[dict] = []
    for condition, group in raw.groupby("condition", sort=True):
        bad = group["bad_z"]
        censored = group["scale_censored"]
        hard_or_soft = censored | group["soft_low_confidence"]
        global_rows.append({
            "condition": condition,
            "frames": len(group),
            "bad_z_rate": _safe_rate(bad),
            "scale_censored_rate": _safe_rate(censored),
            "bad_z_censor_recall": _safe_rate(group.loc[bad, "scale_censored"]) if bad.any() else np.nan,
            "hard_censor_bad_z_precision": _safe_rate(group.loc[censored, "bad_z"]) if censored.any() else np.nan,
            "bad_z_detected_by_censor_or_low_pz_recall": _safe_rate(hard_or_soft[bad]) if bad.any() else np.nan,
            "good_z_flagged_by_censor_or_low_pz_rate": _safe_rate(hard_or_soft[~bad]) if (~bad).any() else np.nan,
        })
    overall = pd.DataFrame(global_rows)

    args.out.mkdir(parents=True, exist_ok=True)
    raw.to_csv(args.out / "frames.csv", index=False)
    cells.to_csv(args.out / "altitude_cells.csv", index=False)
    state_summary.to_csv(args.out / "state_summary.csv", index=False)
    overall.to_csv(args.out / "condition_summary.csv", index=False)
    (args.out / "summary.md").write_text(
        "# Phase 6 field-of-view scale censor benchmark\n\n"
        "Perception-only development benchmark. It uses simulator ground truth to evaluate whether explicit image-boundary censoring separates out-of-FOV scale measurements from ordinary low-confidence scale uncertainty. No landing controller/supervisor and no replacement held-out seed are used.\n\n"
        "## Condition summary\n\n" + overall.to_markdown(index=False)
        + "\n\n## Perception-state summary\n\n" + state_summary.to_markdown(index=False)
        + "\n\n## Altitude cells\n\n" + cells.to_markdown(index=False)
        + "\n",
        encoding="utf-8",
    )

    print(overall.to_string(index=False))
    print("\nPerception-state summary:")
    print(state_summary.to_string(index=False))
    print("\nClean/blur altitude cells:")
    print(cells[cells["condition"].isin(["clean", "blur"])].to_string(index=False))
    print(f"\nSaved perception-only scale-censor benchmark to {args.out.resolve()}")


if __name__ == "__main__":
    main()
