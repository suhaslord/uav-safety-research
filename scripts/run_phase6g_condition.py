from __future__ import annotations

from pathlib import Path
import argparse
import json

import numpy as np
import pandas as pd

from run_phase6b_landing import COMPONENT_COLUMNS, _episode_seeds, summarize
from run_phase6g_development import paired_effects
from uav_safety.image_perception import IMAGE_CONDITIONS
from uav_safety.image_temporal import fit_synthetic_calibrator
from uav_safety.phase6b_fusion import Phase6BComponentGateConfig
from uav_safety.phase6e_perception import fit_phase6e_component_calibrator
from uav_safety.simulator_image_phase6g import run_phase6g_episode
from uav_safety.simulator_image_v3 import run_image_episode


ARCHITECTURES = ("image_temporal", "image_aegis_v3", "image_aegis_phase6g")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one condition of the preregistered Phase 6G development matrix.")
    parser.add_argument("--condition", choices=IMAGE_CONDITIONS, required=True)
    parser.add_argument("--episodes", type=int, default=50)
    parser.add_argument("--seed", type=int, default=838381)
    parser.add_argument("--calibration-seed", type=int, default=616161)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    if args.episodes != 50 or args.seed != 838381 or args.calibration_seed != 616161:
        raise ValueError("runner is locked to the preregistered 50-episode 838381/616161 matrix")

    temporal = fit_synthetic_calibrator(seed=args.calibration_seed, samples_per_condition=180)
    component = fit_phase6e_component_calibrator(seed=args.calibration_seed, samples_per_condition=300)
    gate = Phase6BComponentGateConfig(lateral_confidence_threshold=0.80, altitude_confidence_threshold=0.80)
    condition_index = IMAGE_CONDITIONS.index(args.condition)

    rows: list[dict] = []
    for episode_seed in _episode_seeds(args.seed, condition_index, args.episodes):
        for architecture in ARCHITECTURES:
            if architecture == "image_aegis_phase6g":
                result = run_phase6g_episode(
                    episode_seed,
                    args.condition,
                    temporal,
                    component,
                    component_gate_cfg=gate,
                )
            else:
                result = run_image_episode(
                    episode_seed,
                    args.condition,
                    temporal,
                    architecture=architecture,
                )
            row = result.to_dict()
            for column in COMPONENT_COLUMNS:
                row.setdefault(column, np.nan)
            rows.append(row)

    raw = pd.DataFrame(rows)
    summary = summarize(raw)
    paired = paired_effects(raw)

    args.out.mkdir(parents=True, exist_ok=True)
    raw.to_csv(args.out / "episodes.csv", index=False)
    summary.to_csv(args.out / "summary.csv", index=False)
    paired.to_csv(args.out / "paired_effects.csv", index=False)
    (args.out / "run_metadata.json").write_text(json.dumps({
        "run_role": "development_parallel_replay",
        "condition": args.condition,
        "episode_seed_family": args.seed,
        "calibration_seed": args.calibration_seed,
        "episodes_per_architecture": args.episodes,
        "architectures": list(ARCHITECTURES),
        "paired_episode_seeds": True,
        "protocol": "docs/phase6g_landing_development.md",
        "replacement_reserved_unseen_seeds_not_used": [918271, 928271],
    }, indent=2), encoding="utf-8")

    print(summary.to_string(index=False))
    print("\nPaired effects:")
    print(paired.to_string(index=False))


if __name__ == "__main__":
    main()
