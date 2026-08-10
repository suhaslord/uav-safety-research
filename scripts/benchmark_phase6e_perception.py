from __future__ import annotations

from pathlib import Path
import argparse
import json

import numpy as np
import pandas as pd

from uav_safety.image_perception import IMAGE_CONDITIONS
from uav_safety.image_temporal import Phase6LandingPadRenderer
from uav_safety.phase6e_perception import (
    Phase6ERobustPadEstimator,
    fit_phase6e_component_calibrator,
)
from uav_safety.selective_confidence_v2 import (
    SharpnessAwarePadEstimator,
    fit_component_calibrator,
)


ALTITUDES_M = (
    0.08, 0.12, 0.18, 0.25, 0.40, 0.60, 0.80, 1.20,
    2.00, 3.00, 4.00, 5.00, 6.00, 7.00, 8.00,
)
Z_TOLERANCE_M = 0.85
X_TOLERANCE_M = 0.30
P_THRESHOLD = 0.80


def main() -> None:
    parser = argparse.ArgumentParser(description="Perception-only Phase 6E validation against the historical Phase 6 estimator.")
    parser.add_argument("--samples", type=int, default=40)
    parser.add_argument("--seed", type=int, default=697431)
    parser.add_argument("--calibration-seed", type=int, default=616161)
    parser.add_argument("--out", type=Path, default=Path("results/phase6e_perception_validation"))
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    renderer = Phase6LandingPadRenderer()
    old_estimator = SharpnessAwarePadEstimator()
    new_estimator = Phase6ERobustPadEstimator()
    old_calibrator = fit_component_calibrator(seed=args.calibration_seed, samples_per_condition=280)
    new_calibrator = fit_phase6e_component_calibrator(seed=args.calibration_seed, samples_per_condition=300)

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

                for revision, estimator, calibrator in (
                    ("phase6", old_estimator, old_calibrator),
                    ("phase6e", new_estimator, new_calibrator),
                ):
                    measurement = estimator.estimate(frame)
                    p_x, p_z = calibrator.probabilities(measurement)
                    x_error = abs(measurement.x_m - x_true) if measurement.valid else np.inf
                    z_error = abs(measurement.z_m - true_z) if measurement.valid else np.inf
                    rows.append({
                        "revision": revision,
                        "condition": condition,
                        "true_z_m": true_z,
                        "x_true_m": x_true,
                        "frame_seed": frame_seed,
                        "valid": measurement.valid,
                        "measured_x_m": measurement.x_m if measurement.valid else np.nan,
                        "measured_z_m": measurement.z_m if measurement.valid else np.nan,
                        "abs_x_error_m": x_error,
                        "abs_z_error_m": z_error,
                        "x_good": bool(measurement.valid and x_error <= X_TOLERANCE_M),
                        "z_good": bool(measurement.valid and z_error <= Z_TOLERANCE_M),
                        "p_x_good": p_x,
                        "p_z_good": p_z,
                        "x_selected": bool(p_x >= P_THRESHOLD),
                        "z_selected": bool(p_z >= P_THRESHOLD),
                        "selected_pixels": measurement.selected_pixels,
                        "bbox_width_px": measurement.bbox_width_px,
                    })

    raw = pd.DataFrame(rows)

    summary_rows: list[dict] = []
    for (revision, condition), group in raw.groupby(["revision", "condition"], sort=True):
        z_selected = group["z_selected"]
        x_selected = group["x_selected"]
        z_bad = ~group["z_good"]
        x_bad = ~group["x_good"]
        summary_rows.append({
            "revision": revision,
            "condition": condition,
            "frames": len(group),
            "x_good_rate": float(group["x_good"].mean()),
            "z_good_rate": float(group["z_good"].mean()),
            "mean_abs_x_error_m": float(group["abs_x_error_m"].replace(np.inf, np.nan).mean()),
            "mean_abs_z_error_m": float(group["abs_z_error_m"].replace(np.inf, np.nan).mean()),
            "x_coverage_at_080": float(x_selected.mean()),
            "z_coverage_at_080": float(z_selected.mean()),
            "x_selected_bad_rate": float(x_bad[x_selected].mean()) if x_selected.any() else np.nan,
            "z_selected_bad_rate": float(z_bad[z_selected].mean()) if z_selected.any() else np.nan,
            "x_bad_rejection_recall": float((~x_selected)[x_bad].mean()) if x_bad.any() else np.nan,
            "z_bad_rejection_recall": float((~z_selected)[z_bad].mean()) if z_bad.any() else np.nan,
        })
    summary = pd.DataFrame(summary_rows)

    cell = (
        raw.groupby(["revision", "condition", "true_z_m"], sort=True)
        .agg(
            frames=("frame_seed", "size"),
            z_good_rate=("z_good", "mean"),
            mean_abs_z_error_m=("abs_z_error_m", lambda s: float(s.replace(np.inf, np.nan).mean())),
            p95_abs_z_error_m=("abs_z_error_m", lambda s: float(s.replace(np.inf, np.nan).quantile(0.95))),
            mean_p_z_good=("p_z_good", "mean"),
            z_coverage_at_080=("z_selected", "mean"),
        )
        .reset_index()
    )

    near = cell[cell["true_z_m"] <= 0.40].copy()
    high = cell[cell["true_z_m"] >= 6.0].copy()

    args.out.mkdir(parents=True, exist_ok=True)
    raw.to_csv(args.out / "frames.csv", index=False)
    summary.to_csv(args.out / "summary.csv", index=False)
    cell.to_csv(args.out / "altitude_cells.csv", index=False)
    near.to_csv(args.out / "near_ground_cells.csv", index=False)
    high.to_csv(args.out / "high_altitude_cells.csv", index=False)
    (args.out / "run_metadata.json").write_text(json.dumps({
        "run_role": "perception_development_validation",
        "scope": "static synthetic images only; no landing controller or supervisor",
        "validation_seed": args.seed,
        "calibration_seed": args.calibration_seed,
        "phase6e_rule": "use p30 background if median > 0.5*p90, else historical median",
        "phase6e_calibration_altitude_bands_m": [[0.08,0.50],[0.50,2.0],[2.0,4.0],[4.0,6.0],[6.0,8.0]],
        "component_selection_threshold": 0.80,
        "historical_seen_heldout_seeds_do_not_reuse": [868686, 878787],
        "replacement_reserved_unseen_seeds_not_used": [918271, 928271],
    }, indent=2), encoding="utf-8")
    (args.out / "summary.md").write_text(
        "# Phase 6E perception-only validation\n\n"
        "The Phase 6E robust-background rule was fixed before this validation seed was run. No landing controller, supervisor, or replacement held-out seed is used.\n\n"
        "## Condition summary\n\n" + summary.to_markdown(index=False)
        + "\n\n## Near-ground cells\n\n" + near.to_markdown(index=False)
        + "\n\n## High-altitude cells\n\n" + high.to_markdown(index=False)
        + "\n",
        encoding="utf-8",
    )

    print(summary.to_string(index=False))
    print("\nNear-ground cells:")
    print(near.to_string(index=False))
    print("\nHigh-altitude cells:")
    print(high.to_string(index=False))
    print(f"\nSaved Phase 6E perception validation to {args.out.resolve()}")


if __name__ == "__main__":
    main()
