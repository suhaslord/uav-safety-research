from __future__ import annotations

from pathlib import Path
import argparse
import json

import numpy as np
import pandas as pd

from uav_safety.image_perception import IMAGE_CONDITIONS
from uav_safety.image_temporal import Phase6LandingPadRenderer
from uav_safety.metrics import wilson_interval
from uav_safety.phase6e_perception import Phase6ERobustPadEstimator, fit_phase6e_component_calibrator


ALTITUDES_M = (
    0.08, 0.12, 0.18, 0.25, 0.40, 0.60, 0.80, 1.20,
    2.00, 3.00, 4.00, 5.00, 6.00, 7.00, 8.00,
)
CONFIRMATION_SEEDS = (737431, 747432, 757432)
X_TOLERANCE_M = 0.30
Z_TOLERANCE_M = 0.85
SELECTION_THRESHOLD = 0.80
CATASTROPHIC_Z_ERROR_M = 2.0


def wilson_upper(bad: int, total: int) -> float:
    if total <= 0:
        return float("nan")
    return float(wilson_interval(bad, total)[1])


def main() -> None:
    parser = argparse.ArgumentParser(description="Run preregistered Phase 6E perception-only confirmation.")
    parser.add_argument("--samples", type=int, default=40)
    parser.add_argument("--calibration-seed", type=int, default=616161)
    parser.add_argument("--out", type=Path, default=Path("results/phase6e_perception_confirmation"))
    args = parser.parse_args()

    if args.samples != 40:
        raise ValueError("preregistered Phase 6E confirmation requires exactly 40 frames per condition/altitude cell")

    renderer = Phase6LandingPadRenderer()
    estimator = Phase6ERobustPadEstimator()
    calibrator = fit_phase6e_component_calibrator(
        seed=args.calibration_seed,
        samples_per_condition=300,
    )

    rows: list[dict] = []
    for confirmation_seed in CONFIRMATION_SEEDS:
        rng = np.random.default_rng(confirmation_seed)
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
                    p_x, p_z = calibrator.probabilities(measurement)
                    x_error = abs(measurement.x_m - x_true) if measurement.valid else np.inf
                    z_error = abs(measurement.z_m - true_z) if measurement.valid else np.inf
                    rows.append({
                        "confirmation_seed": confirmation_seed,
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
                        "x_selected": bool(p_x >= SELECTION_THRESHOLD),
                        "z_selected": bool(p_z >= SELECTION_THRESHOLD),
                        "selected_pixels": measurement.selected_pixels,
                        "bbox_width_px": measurement.bbox_width_px,
                    })

    raw = pd.DataFrame(rows)

    condition_rows: list[dict] = []
    for condition, group in raw.groupby("condition", sort=True):
        x_selected = group["x_selected"]
        z_selected = group["z_selected"]
        x_bad_selected = int((x_selected & ~group["x_good"]).sum())
        z_bad_selected = int((z_selected & ~group["z_good"]).sum())
        x_selected_n = int(x_selected.sum())
        z_selected_n = int(z_selected.sum())
        condition_rows.append({
            "condition": condition,
            "frames": len(group),
            "x_good_rate": float(group["x_good"].mean()),
            "z_good_rate": float(group["z_good"].mean()),
            "x_coverage": float(x_selected.mean()),
            "z_coverage": float(z_selected.mean()),
            "x_selected_bad_count": x_bad_selected,
            "x_selected_count": x_selected_n,
            "x_selected_bad_rate": x_bad_selected / max(1, x_selected_n),
            "x_selected_bad_wilson_upper": wilson_upper(x_bad_selected, x_selected_n),
            "z_selected_bad_count": z_bad_selected,
            "z_selected_count": z_selected_n,
            "z_selected_bad_rate": z_bad_selected / max(1, z_selected_n),
            "z_selected_bad_wilson_upper": wilson_upper(z_bad_selected, z_selected_n),
            "mean_abs_x_error_m": float(group["abs_x_error_m"].replace(np.inf, np.nan).mean()),
            "mean_abs_z_error_m": float(group["abs_z_error_m"].replace(np.inf, np.nan).mean()),
        })
    condition_summary = pd.DataFrame(condition_rows)

    seed_rows: list[dict] = []
    for (confirmation_seed, condition), group in raw.groupby(["confirmation_seed", "condition"], sort=True):
        x_selected = group["x_selected"]
        z_selected = group["z_selected"]
        x_bad_selected = int((x_selected & ~group["x_good"]).sum())
        z_bad_selected = int((z_selected & ~group["z_good"]).sum())
        x_selected_n = int(x_selected.sum())
        z_selected_n = int(z_selected.sum())
        seed_rows.append({
            "confirmation_seed": confirmation_seed,
            "condition": condition,
            "frames": len(group),
            "x_selected_count": x_selected_n,
            "x_selected_bad_count": x_bad_selected,
            "x_selected_bad_wilson_upper": wilson_upper(x_bad_selected, x_selected_n),
            "z_selected_count": z_selected_n,
            "z_selected_bad_count": z_bad_selected,
            "z_selected_bad_wilson_upper": wilson_upper(z_bad_selected, z_selected_n),
            "x_coverage": float(x_selected.mean()),
            "z_coverage": float(z_selected.mean()),
        })
    seed_summary = pd.DataFrame(seed_rows)

    criteria_rows: list[dict] = []
    for _, row in condition_summary.iterrows():
        condition = row["condition"]
        criteria_rows.extend([
            {
                "criterion": "x_selected_risk_wilson_upper_le_0.20",
                "condition": condition,
                "value": float(row["x_selected_bad_wilson_upper"]),
                "limit": 0.20,
                "pass": bool(row["x_selected_bad_wilson_upper"] <= 0.20),
            },
            {
                "criterion": "z_selected_risk_wilson_upper_le_0.20",
                "condition": condition,
                "value": float(row["z_selected_bad_wilson_upper"]),
                "limit": 0.20,
                "pass": bool(row["z_selected_bad_wilson_upper"] <= 0.20),
            },
            {
                "criterion": "x_coverage_ge_0.50",
                "condition": condition,
                "value": float(row["x_coverage"]),
                "limit": 0.50,
                "pass": bool(row["x_coverage"] >= 0.50),
            },
            {
                "criterion": "z_coverage_ge_0.50",
                "condition": condition,
                "value": float(row["z_coverage"]),
                "limit": 0.50,
                "pass": bool(row["z_coverage"] >= 0.50),
            },
        ])

    near = raw[raw["true_z_m"] <= 0.25]
    for condition, group in near.groupby("condition", sort=True):
        value = float(group["z_good"].mean())
        criteria_rows.append({
            "criterion": "near_ground_z_good_rate_ge_0.95",
            "condition": condition,
            "value": value,
            "limit": 0.95,
            "pass": bool(value >= 0.95),
        })

    selected_catastrophic = raw[raw["z_selected"] & (raw["abs_z_error_m"] > CATASTROPHIC_Z_ERROR_M)]
    criteria_rows.append({
        "criterion": "selected_catastrophic_z_error_count_eq_0",
        "condition": "all",
        "value": int(len(selected_catastrophic)),
        "limit": 0,
        "pass": bool(len(selected_catastrophic) == 0),
    })

    for condition in ("blur", "mixed"):
        high = raw[(raw["condition"] == condition) & (raw["true_z_m"] >= 6.0)]
        bad = high[~high["z_good"]]
        rejection = float((~bad["z_selected"]).mean()) if len(bad) else 1.0
        criteria_rows.append({
            "criterion": "high_altitude_bad_z_rejection_ge_0.95",
            "condition": condition,
            "value": rejection,
            "limit": 0.95,
            "pass": bool(rejection >= 0.95),
        })

    per_seed_x_max = float(seed_summary["x_selected_bad_wilson_upper"].max())
    per_seed_z_max = float(seed_summary["z_selected_bad_wilson_upper"].max())
    criteria_rows.extend([
        {
            "criterion": "per_seed_condition_x_selected_risk_max_le_0.20",
            "condition": "all",
            "value": per_seed_x_max,
            "limit": 0.20,
            "pass": bool(per_seed_x_max <= 0.20),
        },
        {
            "criterion": "per_seed_condition_z_selected_risk_max_le_0.20",
            "condition": "all",
            "value": per_seed_z_max,
            "limit": 0.20,
            "pass": bool(per_seed_z_max <= 0.20),
        },
    ])

    criteria = pd.DataFrame(criteria_rows)
    all_pass = bool(criteria["pass"].all())

    args.out.mkdir(parents=True, exist_ok=True)
    raw.to_csv(args.out / "frames.csv", index=False)
    condition_summary.to_csv(args.out / "condition_summary.csv", index=False)
    seed_summary.to_csv(args.out / "seed_summary.csv", index=False)
    criteria.to_csv(args.out / "criteria.csv", index=False)
    selected_catastrophic.to_csv(args.out / "selected_catastrophic_z_errors.csv", index=False)
    (args.out / "confirmation_result.json").write_text(json.dumps({
        "phase6e_perception_confirmation_pass": all_pass,
        "confirmation_seeds": list(CONFIRMATION_SEEDS),
        "calibration_seed": args.calibration_seed,
        "frames_per_seed": len(IMAGE_CONDITIONS) * len(ALTITUDES_M) * args.samples,
        "total_unique_rendered_frames": len(CONFIRMATION_SEEDS) * len(IMAGE_CONDITIONS) * len(ALTITUDES_M) * args.samples,
        "selection_threshold": SELECTION_THRESHOLD,
        "protocol": "docs/phase6e_perception_confirmation.md",
        "historical_seen_heldout_seeds_do_not_reuse": [868686, 878787],
        "replacement_reserved_unseen_seeds_not_used": [918271, 928271],
    }, indent=2), encoding="utf-8")
    (args.out / "summary.md").write_text(
        "# Phase 6E perception confirmation\n\n"
        "Three-seed, perception-only confirmation using criteria committed before execution. No landing controller/supervisor or final held-out seed is used.\n\n"
        "## Condition summary\n\n" + condition_summary.to_markdown(index=False)
        + "\n\n## Criteria\n\n" + criteria.to_markdown(index=False)
        + "\n\n**Overall pass:** " + str(all_pass) + "\n",
        encoding="utf-8",
    )

    print(condition_summary.to_string(index=False))
    print("\nCriteria:")
    print(criteria.to_string(index=False))
    print(f"\nOverall Phase 6E perception confirmation pass: {all_pass}")

    if not all_pass:
        raise SystemExit("Phase 6E perception confirmation did not satisfy preregistered criteria")


if __name__ == "__main__":
    main()
