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
from uav_safety.phase6d_fusion import Phase6DConsistencyConfig
from uav_safety.selective_confidence_v2 import fit_component_calibrator
from uav_safety.simulator_image_phase6c import run_phase6c_episode
from uav_safety.simulator_image_phase6d import run_phase6d_episode


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulation-only paired Phase 6D development matrix.")
    parser.add_argument("--episodes", type=int, default=30)
    parser.add_argument("--seed", type=int, default=626262)
    parser.add_argument("--calibration-seed", type=int, default=616161)
    parser.add_argument("--out", type=Path, default=Path("results/phase6d_development"))
    args = parser.parse_args()

    gate = Phase6BComponentGateConfig(
        lateral_confidence_threshold=0.80,
        altitude_confidence_threshold=0.80,
    )
    consistency = Phase6DConsistencyConfig(
        altitude_disagreement_sigma_threshold=3.0,
        min_combined_altitude_sigma_m=0.20,
    )

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

    extra_rows: list[dict] = []
    for condition_index, condition in enumerate(IMAGE_CONDITIONS):
        for episode_seed in _episode_seeds(args.seed, condition_index, args.episodes):
            c = run_phase6c_episode(
                episode_seed,
                condition,
                temporal,
                component,
                component_gate_cfg=gate,
            )
            d = run_phase6d_episode(
                episode_seed,
                condition,
                temporal,
                component,
                component_gate_cfg=gate,
                consistency_cfg=consistency,
            )
            extra_rows.extend((c.to_dict(), d.to_dict()))

    raw = pd.concat([raw, pd.DataFrame(extra_rows)], ignore_index=True, sort=False)
    summary = summarize(raw)

    paired_rows: list[dict] = []
    for condition, group in raw.groupby("condition", sort=True):
        d = group[group["architecture"] == "image_aegis_phase6d"].set_index("seed")
        for label, reference_name in (
            ("phase6d_vs_image_temporal", "image_temporal"),
            ("phase6d_vs_phase6", "image_aegis_v3"),
            ("phase6d_vs_phase6b", "image_aegis_phase6b"),
            ("phase6d_vs_phase6c", "image_aegis_phase6c"),
        ):
            r = group[group["architecture"] == reference_name].set_index("seed")
            common = d.index.intersection(r.index)
            dd = d.loc[common]
            rr = r.loc[common]
            paired_rows.append({
                "condition": condition,
                "comparison": label,
                "paired_episodes": len(common),
                "candidate_minus_reference_success_pp": 100 * float(dd["success"].mean() - rr["success"].mean()),
                "candidate_minus_reference_unsafe_pp": 100 * float(dd["unsafe_touchdown"].mean() - rr["unsafe_touchdown"].mean()),
                "candidate_minus_reference_timeout_pp": 100 * float((dd["outcome"] == "timeout").mean() - (rr["outcome"] == "timeout").mean()),
                "reference_unsafe_rescued_to_candidate_success": int((rr["unsafe_touchdown"] & dd["success"]).sum()),
                "reference_success_became_candidate_unsafe": int((rr["success"] & dd["unsafe_touchdown"]).sum()),
                "reference_success_became_candidate_abort": int((rr["success"] & dd["aborted"]).sum()),
                "reference_success_became_candidate_timeout": int((rr["success"] & (dd["outcome"] == "timeout")).sum()),
            })
    paired = pd.DataFrame(paired_rows)

    d_only = raw[raw["architecture"] == "image_aegis_phase6d"].copy()
    alias_summary = d_only.groupby("condition", sort=True).agg(
        episodes=("seed", "size"),
        episodes_with_hard_alias=("hard_altitude_alias_frames", lambda s: int((pd.to_numeric(s, errors="coerce") > 0).sum())),
        mean_hard_alias_frames=("hard_altitude_alias_frames", "mean"),
        max_hard_alias_frames=("hard_altitude_alias_frames", "max"),
        mean_altitude_disagreement_sigma=("mean_altitude_disagreement_sigma", "mean"),
    ).reset_index()
    alias_summary["episode_hard_alias_rate"] = alias_summary["episodes_with_hard_alias"] / alias_summary["episodes"]

    args.out.mkdir(parents=True, exist_ok=True)
    raw.to_csv(args.out / "episodes.csv", index=False)
    summary.to_csv(args.out / "summary.csv", index=False)
    paired.to_csv(args.out / "paired_effects.csv", index=False)
    alias_summary.to_csv(args.out / "alias_summary.csv", index=False)
    (args.out / "run_metadata.json").write_text(json.dumps({
        "run_role": "development",
        "scope": "simulation-only synthetic image sequences",
        "episode_seed": args.seed,
        "calibration_seed": args.calibration_seed,
        "paired_episode_seeds": True,
        "component_thresholds": {"lateral": 0.80, "altitude": 0.80},
        "altitude_consistency": {"sigma_threshold": 3.0, "min_combined_sigma_m": 0.20},
        "threshold_selection": "0.80/0.80 inherited unchanged from Phase 6B; 3-sigma consistency rule selected before the Phase 6D landing matrix",
        "phase6d_delta": "soft altitude uncertainty preserves Phase 6 vz; hard >3-sigma image/reference altitude contradiction also blends reference vz",
        "historical_seen_heldout_seeds_do_not_reuse": [868686, 878787],
        "replacement_reserved_unseen_seeds_not_used": [918271, 928271],
        "integrity_note": "docs/research_integrity_recovery.md",
    }, indent=2), encoding="utf-8")
    (args.out / "summary.md").write_text(
        "# Phase 6D paired development simulation\n\n"
        "This is development evidence only. Replacement reserved held-out seeds 918271 and 928271 are not used.\n\n"
        "## Landing summary\n\n" + summary.to_markdown(index=False)
        + "\n\n## Phase 6D paired effects\n\n" + paired.to_markdown(index=False)
        + "\n\n## Hard-altitude-alias activity\n\n" + alias_summary.to_markdown(index=False)
        + "\n",
        encoding="utf-8",
    )

    print(summary.to_string(index=False))
    print("\nPhase 6D paired effects:")
    print(paired.to_string(index=False))
    print("\nPhase 6D hard-alias activity:")
    print(alias_summary.to_string(index=False))
    print(f"\nSaved Phase 6D development matrix to {args.out.resolve()}")


if __name__ == "__main__":
    main()
