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
    parser = argparse.ArgumentParser(description="Inspect Phase 6 development episode failure mechanisms.")
    parser.add_argument("--condition", choices=IMAGE_CONDITIONS, default="clean")
    parser.add_argument("--episodes", type=int, default=2)
    parser.add_argument("--seed", type=int, default=626262)
    parser.add_argument("--episode-seed", type=int, default=None)
    parser.add_argument("--calibration-seed", type=int, default=616161)
    parser.add_argument("--calibration-samples", type=int, default=60)
    parser.add_argument("--architecture", choices=("image_temporal", "image_aegis_v3"), default="image_aegis_v3")
    args = parser.parse_args()

    calibrator = fit_synthetic_calibrator(
        seed=args.calibration_seed,
        samples_per_condition=args.calibration_samples,
    )

    seeds = [args.episode_seed] if args.episode_seed is not None else episode_seeds(args.seed, args.condition, args.episodes)
    for episode_seed in seeds:
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

        near_touchdown = [r for r in trace if r["true_z_before"] <= 1.0]
        if near_touchdown:
            true_vx = np.asarray([r["true_vx_before"] for r in near_touchdown])
            image_vx = np.asarray([r["image_vx"] for r in near_touchdown])
            control_vx = np.asarray([r["control_vx"] for r in near_touchdown])
            robust_target = np.asarray([r["robust_vx_target"] for r in near_touchdown])
            print("near-ground frames:", len(near_touchdown))
            print("near-ground true vx MAE vs image:", round(float(np.mean(np.abs(image_vx - true_vx))), 4))
            print("near-ground true vx MAE vs control:", round(float(np.mean(np.abs(control_vx - true_vx))), 4))
            print("near-ground true vx MAE vs robust target:", round(float(np.mean(np.abs(robust_target - true_vx))), 4))
            print("last 8 frames: t z true_vx image_vx control_vx robust_target quality true_x control_x")
            for r in near_touchdown[-8:]:
                print(
                    f"{r['t']:.2f} {r['true_z_before']:.3f} {r['true_vx_before']:+.3f} "
                    f"{r['image_vx']:+.3f} {r['control_vx']:+.3f} {r['robust_vx_target']:+.3f} "
                    f"{r['velocity_quality']:.3f} {r['true_x_before']:+.3f} {r['control_x']:+.3f}"
                )


if __name__ == "__main__":
    main()
