from __future__ import annotations

from pathlib import Path
import argparse

import numpy as np
import pandas as pd

from uav_safety.image_temporal import fit_synthetic_calibrator
from uav_safety.phase6b_fusion import Phase6BComponentGateConfig
from uav_safety.phase6d_fusion import Phase6DConsistencyConfig
from uav_safety.selective_confidence_v2 import fit_component_calibrator
from uav_safety.simulator_image_phase6d import run_phase6d_episode


CASES = (
    ("clean", 1783909939, "representative clean development episode with frequent Phase 6D hard-alias flags"),
    ("blur", 163593717, "worst blur development episode by hard-alias frame count"),
    ("occlusion", 1033307971, "known near-ground visual altitude-teleport development case"),
)


def effective_combined_sigma(frame: pd.DataFrame) -> pd.Series:
    residual = (frame["image_z"] - frame["reference_z"]).abs()
    score = pd.to_numeric(frame["altitude_disagreement_sigma"], errors="coerce")
    out = residual / score.replace(0.0, np.nan)
    return out.fillna(0.0)


def altitude_band(z: float) -> str:
    if z <= 0.5:
        return "0-0.5m"
    if z <= 1.2:
        return "0.5-1.2m"
    if z <= 3.0:
        return "1.2-3m"
    if z <= 5.0:
        return "3-5m"
    return ">5m"


def summarize_case(condition: str, seed: int, note: str, trace: pd.DataFrame, outcome: str) -> dict:
    trace = trace.copy()
    trace["image_z_abs_error"] = (trace["image_z"] - trace["true_z_before"]).abs()
    trace["reference_z_abs_error"] = (trace["reference_z"] - trace["true_z_before"]).abs()
    trace["image_reference_abs_residual"] = (trace["image_z"] - trace["reference_z"]).abs()
    trace["effective_combined_sigma"] = effective_combined_sigma(trace)
    trace["true_altitude_band"] = trace["true_z_before"].map(altitude_band)
    flagged = trace[trace["hard_altitude_alias"]].copy()

    if flagged.empty:
        return {
            "condition": condition,
            "seed": seed,
            "note": note,
            "outcome": outcome,
            "frames": len(trace),
            "hard_alias_frames": 0,
        }

    return {
        "condition": condition,
        "seed": seed,
        "note": note,
        "outcome": outcome,
        "frames": len(trace),
        "hard_alias_frames": len(flagged),
        "hard_alias_rate": len(flagged) / len(trace),
        "flagged_mean_true_z": float(flagged["true_z_before"].mean()),
        "flagged_median_true_z": float(flagged["true_z_before"].median()),
        "flagged_mean_image_z_error": float(flagged["image_z_abs_error"].mean()),
        "flagged_median_image_z_error": float(flagged["image_z_abs_error"].median()),
        "flagged_p95_image_z_error": float(flagged["image_z_abs_error"].quantile(0.95)),
        "flagged_mean_reference_z_error": float(flagged["reference_z_abs_error"].mean()),
        "flagged_median_reference_z_error": float(flagged["reference_z_abs_error"].median()),
        "flagged_mean_image_reference_residual": float(flagged["image_reference_abs_residual"].mean()),
        "flagged_mean_effective_combined_sigma": float(flagged["effective_combined_sigma"].mean()),
        "flagged_mean_disagreement_sigma": float(flagged["altitude_disagreement_sigma"].mean()),
        "flagged_mean_p_z_good": float(flagged["p_z_good"].mean()),
        "flagged_reference_fresh_rate": float(flagged["reference_fresh"].mean()),
        "flagged_mean_reference_age_steps": float(flagged["reference_age_steps"].mean()),
        "flagged_temporal_abstention_rate": float(flagged["temporal_abstained"].mean()),
        "flagged_image_better_than_reference_rate": float((flagged["image_z_abs_error"] < flagged["reference_z_abs_error"]).mean()),
        "flagged_reference_better_than_image_rate": float((flagged["reference_z_abs_error"] < flagged["image_z_abs_error"]).mean()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose Phase 6D hard-alias false positives on already-seen synthetic development episodes.")
    parser.add_argument("--calibration-seed", type=int, default=616161)
    parser.add_argument("--out", type=Path, default=Path("results/phase6d_alias_false_positive_diagnostic"))
    args = parser.parse_args()

    temporal = fit_synthetic_calibrator(seed=args.calibration_seed, samples_per_condition=180)
    component = fit_component_calibrator(seed=args.calibration_seed, samples_per_condition=280)
    gate = Phase6BComponentGateConfig(lateral_confidence_threshold=0.80, altitude_confidence_threshold=0.80)
    consistency = Phase6DConsistencyConfig(
        altitude_disagreement_sigma_threshold=3.0,
        min_combined_altitude_sigma_m=0.20,
    )

    summaries: list[dict] = []
    traces: list[pd.DataFrame] = []
    flagged_tables: list[pd.DataFrame] = []

    for condition, seed, note in CASES:
        result, rows = run_phase6d_episode(
            seed,
            condition,
            temporal,
            component,
            component_gate_cfg=gate,
            consistency_cfg=consistency,
            return_trace=True,
        )
        trace = pd.DataFrame(rows)
        trace.insert(0, "case_note", note)
        trace.insert(0, "seed", seed)
        trace.insert(0, "condition", condition)
        trace["image_z_abs_error"] = (trace["image_z"] - trace["true_z_before"]).abs()
        trace["reference_z_abs_error"] = (trace["reference_z"] - trace["true_z_before"]).abs()
        trace["image_reference_abs_residual"] = (trace["image_z"] - trace["reference_z"]).abs()
        trace["effective_combined_sigma"] = effective_combined_sigma(trace)
        trace["true_altitude_band"] = trace["true_z_before"].map(altitude_band)
        traces.append(trace)
        flagged_tables.append(trace[trace["hard_altitude_alias"]].copy())
        summaries.append(summarize_case(condition, seed, note, trace, result.outcome))

    all_trace = pd.concat(traces, ignore_index=True)
    flagged = pd.concat(flagged_tables, ignore_index=True)
    summary = pd.DataFrame(summaries)

    band_summary = (
        flagged.groupby(["condition", "true_altitude_band"], observed=False)
        .agg(
            flagged_frames=("t", "size"),
            mean_image_z_error=("image_z_abs_error", "mean"),
            mean_reference_z_error=("reference_z_abs_error", "mean"),
            mean_residual=("image_reference_abs_residual", "mean"),
            mean_effective_combined_sigma=("effective_combined_sigma", "mean"),
            mean_reference_age_steps=("reference_age_steps", "mean"),
            reference_fresh_rate=("reference_fresh", "mean"),
        )
        .reset_index()
    )

    worst_flagged = (
        flagged.sort_values(["condition", "image_z_abs_error"], ascending=[True, False])
        .groupby("condition", group_keys=False)
        .head(20)
    )

    args.out.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.out / "case_summary.csv", index=False)
    band_summary.to_csv(args.out / "flagged_by_altitude_band.csv", index=False)
    flagged.to_csv(args.out / "flagged_frames.csv", index=False)
    all_trace.to_csv(args.out / "all_trace.csv", index=False)
    worst_flagged.to_csv(args.out / "worst_flagged_frames.csv", index=False)

    (args.out / "diagnostic.md").write_text(
        "# Phase 6D hard-alias detector diagnostic\n\n"
        "All seeds are already-seen development episodes. No replacement held-out seed is used. "
        "This diagnostic evaluates the detector against simulator ground truth and does not tune landing outcomes.\n\n"
        "## Case summary\n\n" + summary.to_markdown(index=False)
        + "\n\n## Flagged frames by true-altitude band\n\n" + band_summary.to_markdown(index=False)
        + "\n\n## Worst flagged frames by image altitude error\n\n" + worst_flagged.to_markdown(index=False)
        + "\n",
        encoding="utf-8",
    )

    print(summary.to_string(index=False))
    print("\nFlagged by altitude band:")
    print(band_summary.to_string(index=False))
    print("\nWorst flagged frames:")
    print(worst_flagged.to_string(index=False))


if __name__ == "__main__":
    main()
