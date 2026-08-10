from __future__ import annotations

from pathlib import Path
import argparse
import json

import numpy as np
import pandas as pd

from run_phase6b_landing import _episode_seeds, run_comparison as run_phase6b_comparison, summarize
from uav_safety.image_perception import IMAGE_CONDITIONS
from uav_safety.image_temporal import fit_synthetic_calibrator
from uav_safety.phase6b_fusion import Phase6BComponentGateConfig
from uav_safety.selective_confidence_v2 import fit_component_calibrator
from uav_safety.simulator_image_phase6c import run_phase6c_episode


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulation-only paired Phase 6C development matrix.")
    parser.add_argument("--episodes", type=int, default=30)
    parser.add_argument("--seed", type=int, default=626262)
    parser.add_argument("--calibration-seed", type=int, default=616161)
    parser.add_argument("--out", type=Path, default=Path("results/phase6c_development"))
    args = parser.parse_args()

    gate = Phase6BComponentGateConfig(
        lateral_confidence_threshold=0.80,
        altitude_confidence_threshold=0.80,
    )

    # Reuse the established synthetic Phase 6B comparison unchanged.
    raw, _, _ = run_phase6b_comparison(
        episodes=args.episodes,
        seed=args.seed,
        calibration_seed=args.calibration_seed,
        temporal_calibration_samples=180,
        component_calibration_samples=280,
        severity=1.0,
        gate_cfg=gate,
    )

    temporal = fit_synthetic_calibrator(seed=args.calibration_seed, samples_per_condition=180)
    component = fit_component_calibrator(seed=args.calibration_seed, samples_per_condition=280)

    phase6c_rows: list[dict] = []
    for condition_index, condition in enumerate(IMAGE_CONDITIONS):
        for episode_seed in _episode_seeds(args.seed, condition_index, args.episodes):
            result = run_phase6c_episode(
                episode_seed,
                condition,
                temporal,
                component,
                component_gate_cfg=gate,
            )
            phase6c_rows.append(result.to_dict())

    raw = pd.concat([raw, pd.DataFrame(phase6c_rows)], ignore_index=True, sort=False)
    summary = summarize(raw)

    paired_rows: list[dict] = []
    for condition, group in raw.groupby("condition", sort=True):
        c = group[group["architecture"] == "image_aegis_phase6c"].set_index("seed")
        for label, reference_name in (
            ("phase6c_vs_image_temporal", "image_temporal"),
            ("phase6c_vs_phase6", "image_aegis_v3"),
            ("phase6c_vs_phase6b", "image_aegis_phase6b"),
        ):
            r = group[group["architecture"] == reference_name].set_index("seed")
            common = c.index.intersection(r.index)
            cc = c.loc[common]
            rr = r.loc[common]
            paired_rows.append({
                "condition": condition,
                "comparison": label,
                "paired_episodes": len(common),
                "candidate_minus_reference_success_pp": 100 * float(cc["success"].mean() - rr["success"].mean()),
                "candidate_minus_reference_unsafe_pp": 100 * float(cc["unsafe_touchdown"].mean() - rr["unsafe_touchdown"].mean()),
                "candidate_minus_reference_timeout_pp": 100 * float((cc["outcome"] == "timeout").mean() - (rr["outcome"] == "timeout").mean()),
                "reference_success_became_candidate_unsafe": int((rr["success"] & cc["unsafe_touchdown"]).sum()),
                "reference_success_became_candidate_timeout": int((rr["success"] & (cc["outcome"] == "timeout")).sum()),
                "reference_unsafe_rescued_to_candidate_success": int((rr["unsafe_touchdown"] & cc["success"]).sum()),
            })
    paired = pd.DataFrame(paired_rows)

    args.out.mkdir(parents=True, exist_ok=True)
    raw.to_csv(args.out / "episodes.csv", index=False)
    summary.to_csv(args.out / "summary.csv", index=False)
    paired.to_csv(args.out / "paired_effects.csv", index=False)
    (args.out / "run_metadata.json").write_text(json.dumps({
        "run_role": "development",
        "scope": "simulation-only synthetic image sequences",
        "episode_seed": args.seed,
        "calibration_seed": args.calibration_seed,
        "paired_episode_seeds": True,
        "component_thresholds": {"lateral": 0.80, "altitude": 0.80},
        "phase6c_delta": "altitude fallback changes position only and preserves the established simulated vertical-rate estimate",
        "reserved_unseen_seeds_not_used": [868686, 878787],
    }, indent=2), encoding="utf-8")

    print(summary.to_string(index=False))
    print("\nPhase 6C paired effects:")
    print(paired.to_string(index=False))
    print(f"\nSaved simulation-only development matrix to {args.out.resolve()}")


if __name__ == "__main__":
    main()
