from __future__ import annotations

from pathlib import Path
import argparse
import json

import numpy as np
import pandas as pd

from run_phase6b_landing import COMPONENT_COLUMNS, _episode_seeds, summarize
from uav_safety.image_perception import IMAGE_CONDITIONS
from uav_safety.image_temporal import fit_synthetic_calibrator
from uav_safety.phase6b_fusion import Phase6BComponentGateConfig
from uav_safety.phase6e_perception import fit_phase6e_component_calibrator
from uav_safety.simulator_image_phase6g import run_phase6g_episode
from uav_safety.simulator_image_v3 import run_image_episode


ARCHITECTURES = ("image_temporal", "image_aegis_v3", "image_aegis_phase6g")


def run_matrix(*, episodes: int, seed: int, calibration_seed: int) -> tuple[pd.DataFrame, object, object]:
    temporal = fit_synthetic_calibrator(
        seed=calibration_seed,
        samples_per_condition=180,
    )
    component = fit_phase6e_component_calibrator(
        seed=calibration_seed,
        samples_per_condition=300,
    )
    gate = Phase6BComponentGateConfig(
        lateral_confidence_threshold=0.80,
        altitude_confidence_threshold=0.80,
    )

    rows: list[dict] = []
    for condition_index, condition in enumerate(IMAGE_CONDITIONS):
        for episode_seed in _episode_seeds(seed, condition_index, episodes):
            for architecture in ARCHITECTURES:
                if architecture == "image_aegis_phase6g":
                    result = run_phase6g_episode(
                        episode_seed,
                        condition,
                        temporal,
                        component,
                        component_gate_cfg=gate,
                    )
                else:
                    result = run_image_episode(
                        episode_seed,
                        condition,
                        temporal,
                        architecture=architecture,
                    )
                row = result.to_dict()
                for column in COMPONENT_COLUMNS:
                    row.setdefault(column, np.nan)
                rows.append(row)
    return pd.DataFrame(rows), temporal, component


def paired_effects(raw: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for condition, group in raw.groupby("condition", sort=True):
        temporal = group[group["architecture"] == "image_temporal"].set_index("seed")
        phase6 = group[group["architecture"] == "image_aegis_v3"].set_index("seed")
        phase6g = group[group["architecture"] == "image_aegis_phase6g"].set_index("seed")
        common = temporal.index.intersection(phase6.index).intersection(phase6g.index)
        temporal = temporal.loc[common]
        phase6 = phase6.loc[common]
        phase6g = phase6g.loc[common]

        for comparison, candidate, reference in (
            ("phase6_vs_image_temporal", phase6, temporal),
            ("phase6g_vs_image_temporal", phase6g, temporal),
            ("phase6g_vs_phase6", phase6g, phase6),
        ):
            rows.append({
                "condition": condition,
                "comparison": comparison,
                "paired_episodes": len(common),
                "candidate_minus_reference_success_pp": 100.0 * float(candidate["success"].mean() - reference["success"].mean()),
                "candidate_minus_reference_unsafe_pp": 100.0 * float(candidate["unsafe_touchdown"].mean() - reference["unsafe_touchdown"].mean()),
                "candidate_minus_reference_abort_pp": 100.0 * float(candidate["aborted"].mean() - reference["aborted"].mean()),
                "candidate_minus_reference_timeout_pp": 100.0 * float((candidate["outcome"] == "timeout").mean() - (reference["outcome"] == "timeout").mean()),
                "reference_unsafe_rescued_to_candidate_success": int((reference["unsafe_touchdown"] & candidate["success"]).sum()),
                "reference_success_became_candidate_unsafe": int((reference["success"] & candidate["unsafe_touchdown"]).sum()),
                "reference_success_became_candidate_abort": int((reference["success"] & candidate["aborted"]).sum()),
                "reference_success_became_candidate_timeout": int((reference["success"] & (candidate["outcome"] == "timeout")).sum()),
                "reference_abort_became_candidate_success": int((reference["aborted"] & candidate["success"]).sum()),
                "reference_timeout_became_candidate_success": int(((reference["outcome"] == "timeout") & candidate["success"]).sum()),
            })
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run preregistered Phase 6G paired landing-development matrix.")
    parser.add_argument("--episodes", type=int, default=50)
    parser.add_argument("--seed", type=int, default=838381)
    parser.add_argument("--calibration-seed", type=int, default=616161)
    parser.add_argument("--out", type=Path, default=Path("results/phase6g_development"))
    args = parser.parse_args()

    if args.episodes != 50:
        raise ValueError("preregistered Phase 6G development requires exactly 50 episodes per condition/architecture")
    if args.seed != 838381:
        raise ValueError("preregistered Phase 6G development seed family is 838381")
    if args.calibration_seed != 616161:
        raise ValueError("preregistered Phase 6G calibration seed is 616161")

    raw, temporal, component = run_matrix(
        episodes=args.episodes,
        seed=args.seed,
        calibration_seed=args.calibration_seed,
    )
    summary = summarize(raw)
    paired = paired_effects(raw)

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    raw.to_csv(out / "episodes.csv", index=False)
    summary.to_csv(out / "summary.csv", index=False)
    paired.to_csv(out / "paired_effects.csv", index=False)
    (out / "temporal_calibrator.json").write_text(json.dumps(temporal.to_dict(), indent=2), encoding="utf-8")
    (out / "phase6e_component_calibrator.json").write_text(json.dumps(component.to_dict(), indent=2), encoding="utf-8")
    (out / "run_metadata.json").write_text(json.dumps({
        "run_role": "development",
        "scope": "simulation-only synthetic image landing episodes",
        "protocol": "docs/phase6g_landing_development.md",
        "episode_seed_family": args.seed,
        "calibration_seed": args.calibration_seed,
        "episodes_per_condition_architecture": args.episodes,
        "conditions": list(IMAGE_CONDITIONS),
        "architectures": list(ARCHITECTURES),
        "paired_episode_seeds": True,
        "phase6e_perception_frozen": True,
        "phase6e_perception_freeze": "docs/phase6e_perception_freeze.md",
        "component_thresholds": {"lateral": 0.80, "altitude": 0.80},
        "fusion": "Phase 6C z-only altitude fallback; no Phase 6D hard-alias rule",
        "historical_seen_heldout_seeds_do_not_reuse": [868686, 878787],
        "replacement_reserved_unseen_seeds_not_used": [918271, 928271],
    }, indent=2), encoding="utf-8")
    (out / "summary.md").write_text(
        "# Phase 6G paired landing-development matrix\n\n"
        "Simulation-only development result under the preregistered `838381` family. Final replacement held-out seeds are not used.\n\n"
        "## Summary\n\n" + summary.to_markdown(index=False)
        + "\n\n## Paired effects\n\n" + paired.to_markdown(index=False)
        + "\n",
        encoding="utf-8",
    )

    print(summary.to_string(index=False))
    print("\nPaired effects:")
    print(paired.to_string(index=False))
    print(f"\nSaved Phase 6G development matrix to {out.resolve()}")


if __name__ == "__main__":
    main()
