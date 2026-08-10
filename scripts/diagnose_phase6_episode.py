from __future__ import annotations

import argparse
from collections import Counter

import numpy as np

from uav_safety.image_perception import IMAGE_CONDITIONS
from uav_safety.image_temporal import fit_synthetic_calibrator
from uav_safety.simulator_image_v3 import run_image_episode


def episode_seeds(seed: int, condition: str, episodes: int) -> list[int]:
    condition_index = IMAGE_CONDITIONS.index(condition)
    rng = np.random.default_rng(np.random.SeedSequence([seed, condition_index, 6060]))
    return [int(rng.integers(0, 2**31 - 1)) for _ in range(episodes)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect Phase 6 image abstention causes for development episodes.")
    parser.add_argument("--condition", choices=IMAGE_CONDITIONS, default="clean")
    parser.add_argument("--episodes", type=int, default=2)
    parser.add_argument("--seed", type=int, default=626262)
    parser.add_argument("--calibration-seed", type=int, default=616161)
    parser.add_argument("--calibration-samples", type=int, default=60)
    parser.add_argument("--architecture", choices=("image_temporal", "image_aegis_v3"), default="image_aegis_v3")
    args = parser.parse_args()

    calibrator = fit_synthetic_calibrator(
        seed=args.calibration_seed,
        samples_per_condition=args.calibration_samples,
    )

    for episode_seed in episode_seeds(args.seed, args.condition, args.episodes):
        result, trace = run_image_episode(
            episode_seed,
            args.condition,
            calibrator,
            architecture=args.architecture,
            return_trace=True,
        )
        reasons = Counter(row["abstain_reason"] for row in trace if row["abstained"])
        abstained = [row for row in trace if row["abstained"]]
        accepted = [row for row in trace if not row["abstained"]]

        print("\n=== episode", episode_seed, "===")
        print("outcome:", result.outcome)
        print("frames:", result.frames)
        print("abstention_rate:", round(result.image_abstention_rate, 4))
        print("final_x_error:", round(result.final_x_error, 4))
        print("final_vx/vz:", round(result.final_vx, 4), round(result.final_vz, 4))
        print("abstention_reasons:", dict(reasons))
        if abstained:
            print("abstained true-z range:", round(min(r["true_z"] for r in abstained), 3), "to", round(max(r["true_z"] for r in abstained), 3))
            print("mean abstained innovation:", round(float(np.mean([r["innovation_score"] for r in abstained])), 3))
            print("mean abstained raw/cal conf:", round(float(np.mean([r["raw_confidence"] for r in abstained])), 3), round(float(np.mean([r["calibrated_confidence"] for r in abstained])), 3))
            print("mean abstained geometry:", round(float(np.mean([r["geometry_score"] for r in abstained])), 3))
        if accepted:
            print("accepted true-z range:", round(min(r["true_z"] for r in accepted), 3), "to", round(max(r["true_z"] for r in accepted), 3))
            print("mean accepted innovation:", round(float(np.mean([r["innovation_score"] for r in accepted])), 3))


if __name__ == "__main__":
    main()
