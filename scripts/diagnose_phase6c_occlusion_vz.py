from __future__ import annotations

from pathlib import Path
import argparse

import numpy as np
import pandas as pd

from uav_safety.image_temporal import fit_synthetic_calibrator
from uav_safety.phase6b_fusion import Phase6BComponentGateConfig
from uav_safety.selective_confidence_v2 import fit_component_calibrator
from uav_safety.simulator_image_phase6b import run_phase6b_episode
from uav_safety.simulator_image_phase6c import run_phase6c_episode


def summarize_trace(name: str, result, trace: list[dict]) -> tuple[dict, pd.DataFrame]:
    df = pd.DataFrame(trace)
    near = df[df["true_z_before"] <= 1.20].copy()
    if near.empty:
        near = df.copy()

    def mae(column: str) -> float:
        return float(np.mean(np.abs(near[column] - near["true_vz_before"])))

    summary = {
        "revision": name,
        "outcome": result.outcome,
        "duration_s": result.duration_s,
        "final_vz": result.final_vz,
        "near_ground_frames": len(near),
        "near_ground_image_vz_mae": mae("image_vz"),
        "near_ground_control_vz_mae": mae("control_vz"),
        "near_ground_reference_vz_mae": mae("reference_vz"),
        "near_ground_altitude_takeovers": int(near["altitude_reference_takeover"].sum()),
        "near_ground_lateral_takeovers": int(near["lateral_reference_takeover"].sum()),
        "near_ground_mean_p_z_good": float(near["p_z_good"].mean()),
        "near_ground_mean_image_vz": float(near["image_vz"].mean()),
        "near_ground_mean_reference_vz": float(near["reference_vz"].mean()),
        "near_ground_mean_true_vz": float(near["true_vz_before"].mean()),
    }
    return summary, near


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulation-only Phase 6C occlusion vertical-rate trace audit.")
    parser.add_argument("--seed", type=int, default=1033307971)
    parser.add_argument("--calibration-seed", type=int, default=616161)
    parser.add_argument("--out", type=Path, default=Path("results/phase6c_occlusion_vz_diagnostic"))
    args = parser.parse_args()

    temporal = fit_synthetic_calibrator(seed=args.calibration_seed, samples_per_condition=180)
    component = fit_component_calibrator(seed=args.calibration_seed, samples_per_condition=280)
    gate = Phase6BComponentGateConfig(lateral_confidence_threshold=0.80, altitude_confidence_threshold=0.80)

    b_result, b_trace = run_phase6b_episode(
        args.seed, "occlusion", temporal, component,
        component_gate_cfg=gate, return_trace=True,
    )
    c_result, c_trace = run_phase6c_episode(
        args.seed, "occlusion", temporal, component,
        component_gate_cfg=gate, return_trace=True,
    )

    b_summary, b_near = summarize_trace("phase6b", b_result, b_trace)
    c_summary, c_near = summarize_trace("phase6c", c_result, c_trace)
    summary = pd.DataFrame([b_summary, c_summary])

    keep = [
        "t", "true_z_before", "true_vz_before", "image_z", "image_vz",
        "control_z", "control_vz", "reference_z", "reference_vz",
        "p_z_good", "altitude_component_abstained", "altitude_reference_takeover",
        "reference_fresh", "reference_age_steps", "risk", "decision",
    ]
    b_near = b_near[keep].copy()
    b_near.insert(0, "revision", "phase6b")
    c_near = c_near[keep].copy()
    c_near.insert(0, "revision", "phase6c")
    near = pd.concat([b_near, c_near], ignore_index=True)

    args.out.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.out / "summary.csv", index=False)
    near.to_csv(args.out / "near_ground_trace.csv", index=False)
    (args.out / "summary.md").write_text(
        "# Phase 6C occlusion vertical-rate diagnostic\n\n"
        "Development-only replay of already-seen seed 1033307971.\n\n"
        + summary.to_markdown(index=False)
        + "\n\n## Final 20 near-ground rows\n\n"
        + near.groupby("revision", group_keys=False).tail(20).to_markdown(index=False)
        + "\n",
        encoding="utf-8",
    )

    print(summary.to_string(index=False))
    print("\nFinal 20 near-ground rows per revision:")
    print(near.groupby("revision", group_keys=False).tail(20).to_string(index=False))


if __name__ == "__main__":
    main()
