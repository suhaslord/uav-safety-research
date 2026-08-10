from __future__ import annotations

from pathlib import Path
import argparse
import json

import pandas as pd

from run_phase6b_landing import _episode_seeds
from uav_safety.image_perception import IMAGE_CONDITIONS
from uav_safety.image_temporal import fit_synthetic_calibrator
from uav_safety.phase6b_fusion import Phase6BComponentGateConfig
from uav_safety.phase6d_fusion import Phase6DConsistencyConfig
from uav_safety.selective_confidence_v2 import fit_component_calibrator
from uav_safety.simulator_image_phase6d import run_phase6d_episode


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulation-only Phase 6D candidate development run for one condition.")
    parser.add_argument("--condition", choices=IMAGE_CONDITIONS, required=True)
    parser.add_argument("--episodes", type=int, default=30)
    parser.add_argument("--seed", type=int, default=626262)
    parser.add_argument("--calibration-seed", type=int, default=616161)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    gate = Phase6BComponentGateConfig(
        lateral_confidence_threshold=0.80,
        altitude_confidence_threshold=0.80,
    )
    consistency = Phase6DConsistencyConfig(
        altitude_disagreement_sigma_threshold=3.0,
        min_combined_altitude_sigma_m=0.20,
    )
    temporal = fit_synthetic_calibrator(seed=args.calibration_seed, samples_per_condition=180)
    component = fit_component_calibrator(seed=args.calibration_seed, samples_per_condition=280)

    condition_index = IMAGE_CONDITIONS.index(args.condition)
    rows: list[dict] = []
    for episode_seed in _episode_seeds(args.seed, condition_index, args.episodes):
        result = run_phase6d_episode(
            episode_seed,
            args.condition,
            temporal,
            component,
            component_gate_cfg=gate,
            consistency_cfg=consistency,
        )
        rows.append(result.to_dict())

    df = pd.DataFrame(rows)
    summary = pd.DataFrame([{
        "condition": args.condition,
        "episodes": len(df),
        "success_rate": float(df["success"].mean()),
        "unsafe_touchdown_rate": float(df["unsafe_touchdown"].mean()),
        "abort_rate": float(df["aborted"].mean()),
        "timeout_rate": float((df["outcome"] == "timeout").mean()),
        "episodes_with_hard_alias": int((df["hard_altitude_alias_frames"] > 0).sum()),
        "episode_hard_alias_rate": float((df["hard_altitude_alias_frames"] > 0).mean()),
        "mean_hard_alias_frames": float(df["hard_altitude_alias_frames"].mean()),
        "max_hard_alias_frames": int(df["hard_altitude_alias_frames"].max()),
        "mean_final_x_error": float(df["final_x_error"].mean()),
        "mean_abs_final_vx": float(df["final_vx"].abs().mean()),
        "mean_abs_final_vz": float(df["final_vz"].abs().mean()),
    }])

    args.out.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out / "episodes.csv", index=False)
    summary.to_csv(args.out / "summary.csv", index=False)
    (args.out / "run_metadata.json").write_text(json.dumps({
        "run_role": "development_candidate_only",
        "scope": "simulation-only synthetic image sequences",
        "condition": args.condition,
        "episode_seed": args.seed,
        "calibration_seed": args.calibration_seed,
        "episodes": args.episodes,
        "component_thresholds": {"lateral": 0.80, "altitude": 0.80},
        "altitude_consistency": {"sigma_threshold": 3.0, "min_combined_sigma_m": 0.20},
        "historical_seen_heldout_seeds_do_not_reuse": [868686, 878787],
        "replacement_reserved_unseen_seeds_not_used": [918271, 928271],
        "integrity_note": "docs/research_integrity_recovery.md",
    }, indent=2), encoding="utf-8")

    print(summary.to_string(index=False))
    print(f"Saved candidate-only result to {args.out.resolve()}")


if __name__ == "__main__":
    main()
