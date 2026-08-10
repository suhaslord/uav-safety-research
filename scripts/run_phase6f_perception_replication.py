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
from uav_safety.phase6f_perception import Phase6FDistributionAwarePadEstimator, fit_phase6f_component_calibrator


ALTITUDES_M = (
    0.08, 0.12, 0.18, 0.25, 0.40, 0.60, 0.80, 1.20,
    2.00, 3.00, 4.00, 5.00, 6.00, 7.00, 8.00,
)
REPLICATION_SEEDS = (707431, 717431, 727431)
X_TOLERANCE_M = 0.30
Z_TOLERANCE_M = 0.85
SELECTION_THRESHOLD = 0.80
CATASTROPHIC_Z_ERROR_M = 2.0


def _wilson_upper(bad: int, total: int) -> float:
    if total <= 0:
        return float("nan")
    return float(wilson_interval(bad, total)[1])


def main() -> None:
    parser = argparse.ArgumentParser(description="Run preregistered Phase 6F perception-only replication.")
    parser.add_argument("--samples", type=int, default=40)
    parser.add_argument("--calibration-seed", type=int, default=616161)
    parser.add_argument("--out", type=Path, default=Path("results/phase6f_perception_replication"))
    args = parser.parse_args()

    if args.samples != 40:
        raise ValueError("preregistered Phase 6F replication requires exactly 40 frames per condition/altitude cell")

    renderer = Phase6LandingPadRenderer()
    estimators = {
        "phase6e": Phase6ERobustPadEstimator(),
        "phase6f": Phase6FDistributionAwarePadEstimator(),
    }
    calibrators = {
        "phase6e": fit_phase6e_component_calibrator(seed=args.calibration_seed, samples_per_condition=300),
        "phase6f": fit_phase6f_component_calibrator(seed=args.calibration_seed, samples_per_condition=300),
    }

    rows: list[dict] = []
    for replication_seed in REPLICATION_SEEDS:
        rng = np.random.default_rng(replication_seed)
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
                    for revision in ("phase6e", "phase6f"):
                        measurement = estimators[revision].estimate(frame)
                        p_x, p_z = calibrators[revision].probabilities(measurement)
                        x_error = abs(measurement.x_m - x_true) if measurement.valid else np.inf
                        z_error = abs(measurement.z_m - true_z) if measurement.valid else np.inf
                        rows.append({
                            "replication_seed": replication_seed,
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
                            "x_selected": bool(p_x >= SELECTION_THRESHOLD),
                            "z_selected": bool(p_z >= SELECTION_THRESHOLD),
                            "selected_pixels": measurement.selected_pixels,
                            "bbox_width_px": measurement.bbox_width_px,
                        })

    raw = pd.DataFrame(rows)

    condition_rows: list[dict] = []
    for (revision, condition), group in raw.groupby(["revision", "condition"], sort=True):
        x_selected = group["x_selected"]
        z_selected = group["z_selected"]
        x_bad_selected = int((x_selected & ~group["x_good"]).sum())
        z_bad_selected = int((z_selected & ~group["z_good"]).sum())
        x_selected_n = int(x_selected.sum())
        z_selected_n = int(z_selected.sum())
        condition_rows.append({
            "revision": revision,
            "condition": condition,
            "frames": len(group),
            "x_good_rate": float(group["x_good"].mean()),
            "z_good_rate": float(group["z_good"].mean()),
            "x_coverage": float(x_selected.mean()),
            "z_coverage": float(z_selected.mean()),
            "x_selected_bad_count": x_bad_selected,
            "x_selected_count": x_selected_n,
            "x_selected_bad_rate": x_bad_selected / max(1, x_selected_n),
            "x_selected_bad_wilson_upper": _wilson_upper(x_bad_selected, x_selected_n),
            "z_selected_bad_count": z_bad_selected,
            "z_selected_count": z_selected_n,
            "z_selected_bad_rate": z_bad_selected / max(1, z_selected_n),
            "z_selected_bad_wilson_upper": _wilson_upper(z_bad_selected, z_selected_n),
            "mean_abs_x_error_m": float(group["abs_x_error_m"].replace(np.inf, np.nan).mean()),
            "mean_abs_z_error_m": float(group["abs_z_error_m"].replace(np.inf, np.nan).mean()),
        })
    condition_summary = pd.DataFrame(condition_rows)

    criteria_rows: list[dict] = []
    phase6e_summary = condition_summary[condition_summary["revision"] == "phase6e"].set_index("condition")
    phase6f_summary = condition_summary[condition_summary["revision"] == "phase6f"].set_index("condition")

    for condition in IMAGE_CONDITIONS:
        e = phase6e_summary.loc[condition]
        f = phase6f_summary.loc[condition]
        criteria_rows.extend([
            {
                "criterion": "x_selected_risk_wilson_upper_le_0.20",
                "condition": condition,
                "value": float(f["x_selected_bad_wilson_upper"]),
                "limit": 0.20,
                "pass": bool(f["x_selected_bad_wilson_upper"] <= 0.20),
            },
            {
                "criterion": "z_selected_risk_wilson_upper_le_0.20",
                "condition": condition,
                "value": float(f["z_selected_bad_wilson_upper"]),
                "limit": 0.20,
                "pass": bool(f["z_selected_bad_wilson_upper"] <= 0.20),
            },
            {
                "criterion": "x_coverage_loss_vs_phase6e_le_0.05",
                "condition": condition,
                "value": float(e["x_coverage"] - f["x_coverage"]),
                "limit": 0.05,
                "pass": bool(f["x_coverage"] >= e["x_coverage"] - 0.05),
            },
            {
                "criterion": "z_coverage_loss_vs_phase6e_le_0.05",
                "condition": condition,
                "value": float(e["z_coverage"] - f["z_coverage"]),
                "limit": 0.05,
                "pass": bool(f["z_coverage"] >= e["z_coverage"] - 0.05),
            },
        ])

    fraw = raw[raw["revision"] == "phase6f"].copy()
    near = fraw[fraw["true_z_m"] <= 0.25]
    for condition, group in near.groupby("condition", sort=True):
        z_good_rate = float(group["z_good"].mean())
        criteria_rows.append({
            "criterion": "near_ground_z_good_rate_ge_0.95",
            "condition": condition,
            "value": z_good_rate,
            "limit": 0.95,
            "pass": bool(z_good_rate >= 0.95),
        })

    selected_catastrophic = fraw[fraw["z_selected"] & (fraw["abs_z_error_m"] > CATASTROPHIC_Z_ERROR_M)]
    criteria_rows.append({
        "criterion": "selected_catastrophic_z_error_count_eq_0",
        "condition": "all",
        "value": int(len(selected_catastrophic)),
        "limit": 0,
        "pass": bool(len(selected_catastrophic) == 0),
    })

    for condition in ("blur", "mixed"):
        high = fraw[(fraw["condition"] == condition) & (fraw["true_z_m"] >= 6.0)]
        bad = high[~high["z_good"]]
        rejection = float((~bad["z_selected"]).mean()) if len(bad) else 1.0
        criteria_rows.append({
            "criterion": "high_altitude_bad_z_rejection_ge_0.95",
            "condition": condition,
            "value": rejection,
            "limit": 0.95,
            "pass": bool(rejection >= 0.95),
        })

    criteria = pd.DataFrame(criteria_rows)
    all_pass = bool(criteria["pass"].all())

    seed_summary = (
        raw.groupby(["replication_seed", "revision", "condition"], sort=True)
        .agg(
            frames=("frame_seed", "size"),
            x_good_rate=("x_good", "mean"),
            z_good_rate=("z_good", "mean"),
            x_coverage=("x_selected", "mean"),
            z_coverage=("z_selected", "mean"),
        )
        .reset_index()
    )

    args.out.mkdir(parents=True, exist_ok=True)
    raw.to_csv(args.out / "frames.csv", index=False)
    condition_summary.to_csv(args.out / "condition_summary.csv", index=False)
    seed_summary.to_csv(args.out / "seed_summary.csv", index=False)
    criteria.to_csv(args.out / "criteria.csv", index=False)
    selected_catastrophic.to_csv(args.out / "selected_catastrophic_z_errors.csv", index=False)
    (args.out / "replication_result.json").write_text(json.dumps({
        "phase6f_perception_replication_pass": all_pass,
        "replication_seeds": list(REPLICATION_SEEDS),
        "calibration_seed": args.calibration_seed,
        "frames_per_seed": len(IMAGE_CONDITIONS) * len(ALTITUDES_M) * args.samples,
        "total_unique_rendered_frames": len(REPLICATION_SEEDS) * len(IMAGE_CONDITIONS) * len(ALTITUDES_M) * args.samples,
        "phase6f_rule": "use p30 only when median > (p30+p90)/2",
        "selection_threshold": SELECTION_THRESHOLD,
        "historical_seen_heldout_seeds_do_not_reuse": [868686, 878787],
        "replacement_reserved_unseen_seeds_not_used": [918271, 928271],
        "protocol": "docs/phase6f_perception_replication.md",
    }, indent=2), encoding="utf-8")
    (args.out / "summary.md").write_text(
        "# Phase 6F perception replication\n\n"
        "Three-seed, perception-only replication using preregistered acceptance criteria. No landing controller/supervisor or final held-out seed is used.\n\n"
        "## Condition summary\n\n" + condition_summary.to_markdown(index=False)
        + "\n\n## Criteria\n\n" + criteria.to_markdown(index=False)
        + "\n\n**Overall pass:** " + str(all_pass) + "\n",
        encoding="utf-8",
    )

    print(condition_summary.to_string(index=False))
    print("\nCriteria:")
    print(criteria.to_string(index=False))
    print(f"\nOverall Phase 6F perception replication pass: {all_pass}")

    if not all_pass:
        raise SystemExit("Phase 6F perception replication did not satisfy preregistered criteria")


if __name__ == "__main__":
    main()
