from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import argparse
import json
import os

import numpy as np
import pandas as pd

from uav_safety.dynamics_phase7 import Phase7DynamicsConfig
from uav_safety.image_perception import IMAGE_CONDITIONS
from uav_safety.image_temporal import fit_synthetic_calibrator
from uav_safety.metrics import wilson_interval
from uav_safety.phase6b_fusion import Phase6BComponentGateConfig
from uav_safety.phase7_faults import FaultScenario, Phase7FaultConfig
from uav_safety.phase7_reference import Phase7SensorStackConfig
from uav_safety.provenance import write_result_manifest
from uav_safety.selective_confidence_v2 import fit_component_calibrator
from uav_safety.simulator_phase7 import PLANT_MODELS, run_phase7_episode
from uav_safety.supervisor_v3 import SupervisorV3Config


DEFAULT_CONDITIONS = ("clean", "low_light", "occlusion", "mixed")
DEFAULT_FAULTS = tuple(s.value for s in FaultScenario)


def _episode_seeds(seed: int, condition_index: int, fault_index: int, episodes: int) -> list[int]:
    rng = np.random.default_rng(np.random.SeedSequence([seed, condition_index, fault_index, 7007]))
    return [int(rng.integers(0, 2**31 - 1)) for _ in range(episodes)]


def summarize(raw: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    grouped = raw.groupby(["condition", "fault_scenario", "plant_model"], sort=True)
    for (condition, fault, plant_model), group in grouped:
        n = len(group)
        success_n = int(group["success"].sum())
        unsafe_n = int(group["unsafe_touchdown"].sum())
        abort_n = int(group["aborted"].sum())
        timeout_n = int((group["outcome"] == "timeout").sum())
        success_ci = wilson_interval(success_n, n)
        unsafe_ci = wilson_interval(unsafe_n, n)
        abort_ci = wilson_interval(abort_n, n)
        timeout_ci = wilson_interval(timeout_n, n)
        rows.append({
            "condition": condition,
            "fault_scenario": fault,
            "plant_model": plant_model,
            "episodes": n,
            "success_rate": success_n / n,
            "success_ci_low": success_ci[0],
            "success_ci_high": success_ci[1],
            "unsafe_touchdown_rate": unsafe_n / n,
            "unsafe_ci_low": unsafe_ci[0],
            "unsafe_ci_high": unsafe_ci[1],
            "abort_rate": abort_n / n,
            "abort_ci_low": abort_ci[0],
            "abort_ci_high": abort_ci[1],
            "timeout_rate": timeout_n / n,
            "timeout_ci_low": timeout_ci[0],
            "timeout_ci_high": timeout_ci[1],
            "mean_shared_dropout_event_rate": float(group["shared_dropout_event_rate"].mean()),
            "mean_image_drop_rate": float(group["image_drop_rate"].mean()),
            "mean_reference_available_rate": float(group["reference_available_rate"].mean()),
            "mean_reference_delivery_rate": float(group["reference_delivery_rate"].mean()),
            "mean_reference_latency_steps": float(group["mean_reference_latency_steps"].mean()),
            "mean_delivered_transport_latency_steps": float(group["mean_delivered_transport_latency_steps"].mean()),
            "mean_reference_age_steps": float(group["mean_reference_age_steps"].mean()),
            "mean_max_reference_age_steps": float(group["max_reference_age_steps"].mean()),
            "mean_max_abs_reference_bias_x_m": float(group["max_abs_reference_bias_x_m"].mean()),
            "mean_max_abs_shared_vision_bias_x_m": float(group["max_abs_shared_vision_bias_x_m"].mean()),
            "mean_lateral_component_abstention_rate": float(group["lateral_component_abstention_rate"].mean()),
            "mean_altitude_component_abstention_rate": float(group["altitude_component_abstention_rate"].mean()),
            "mean_interventions": float(group["mean_interventions"].mean()),
            "mean_final_x_error": float(group["final_x_error"].mean()),
            "mean_abs_final_vx": float(group["final_vx"].abs().mean()),
            "mean_abs_final_vz": float(group["final_vz"].abs().mean()),
        })
    return pd.DataFrame(rows)


def paired_plant_effects(raw: pd.DataFrame) -> pd.DataFrame:
    """Summarize paired outcome changes caused only by the stronger plant."""
    rows: list[dict] = []
    if set(raw["plant_model"].unique()) != {"legacy", "phase7"}:
        return pd.DataFrame(rows)

    for (condition, fault), group in raw.groupby(["condition", "fault_scenario"], sort=True):
        legacy = group[group["plant_model"] == "legacy"].set_index("seed")
        stronger = group[group["plant_model"] == "phase7"].set_index("seed")
        common = legacy.index.intersection(stronger.index)
        if len(common) == 0:
            continue
        legacy = legacy.loc[common]
        stronger = stronger.loc[common]
        rows.append({
            "condition": condition,
            "fault_scenario": fault,
            "paired_episodes": int(len(common)),
            "phase7_minus_legacy_success_pp": float(100.0 * (stronger["success"].mean() - legacy["success"].mean())),
            "phase7_minus_legacy_unsafe_pp": float(100.0 * (stronger["unsafe_touchdown"].mean() - legacy["unsafe_touchdown"].mean())),
            "legacy_success_became_phase7_failure": int((legacy["success"] & ~stronger["success"]).sum()),
            "legacy_unsafe_became_phase7_success": int((legacy["unsafe_touchdown"] & stronger["success"]).sum()),
        })
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Phase 7 simulation-only external-validity stress tests."
    )
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--seed", type=int, default=979797)
    parser.add_argument("--calibration-seed", type=int, default=616161)
    parser.add_argument("--temporal-calibration-samples", type=int, default=180)
    parser.add_argument("--component-calibration-samples", type=int, default=280)
    parser.add_argument("--severity", type=float, default=1.0)
    parser.add_argument("--conditions", nargs="+", default=list(DEFAULT_CONDITIONS))
    parser.add_argument("--faults", nargs="+", default=list(DEFAULT_FAULTS))
    parser.add_argument("--plants", nargs="+", default=list(PLANT_MODELS))
    parser.add_argument("--out", type=Path, default=Path("results/phase7_development"))
    args = parser.parse_args()

    if args.episodes < 1:
        raise ValueError("episodes must be >= 1")
    if args.seed == args.calibration_seed:
        raise ValueError("episode and calibration seeds must differ")

    conditions = tuple(args.conditions)
    unknown_conditions = set(conditions) - set(IMAGE_CONDITIONS)
    if unknown_conditions:
        raise ValueError(f"unknown conditions: {sorted(unknown_conditions)}")
    faults = tuple(FaultScenario(value) for value in args.faults)
    plants = tuple(args.plants)
    unknown_plants = set(plants) - set(PLANT_MODELS)
    if unknown_plants:
        raise ValueError(f"unknown plant models: {sorted(unknown_plants)}")

    temporal_calibrator = fit_synthetic_calibrator(
        seed=args.calibration_seed,
        samples_per_condition=args.temporal_calibration_samples,
    )
    component_calibrator = fit_component_calibrator(
        seed=args.calibration_seed,
        samples_per_condition=args.component_calibration_samples,
    )

    rows: list[dict] = []
    for condition_index, condition in enumerate(conditions):
        for fault_index, fault in enumerate(faults):
            episode_seeds = _episode_seeds(args.seed, condition_index, fault_index, args.episodes)
            for episode_seed in episode_seeds:
                for plant_model in plants:
                    result = run_phase7_episode(
                        episode_seed,
                        condition,
                        temporal_calibrator,
                        component_calibrator,
                        fault_scenario=fault,
                        plant_model=plant_model,
                        severity=args.severity,
                    )
                    rows.append(result.to_dict())

    raw = pd.DataFrame(rows)
    summary = summarize(raw)
    plant_effects = paired_plant_effects(raw)
    args.out.mkdir(parents=True, exist_ok=True)
    raw.to_csv(args.out / "episodes.csv", index=False)
    summary.to_csv(args.out / "summary.csv", index=False)
    plant_effects.to_csv(args.out / "paired_plant_effects.csv", index=False)

    git_sha = os.environ.get("GITHUB_SHA", "unknown-local-worktree")
    (args.out / "git_sha.txt").write_text(git_sha + "\n", encoding="utf-8")

    metadata = {
        "run_role": "development_external_validity_factorial",
        "git_sha": git_sha,
        "episode_seed": args.seed,
        "episode_seed_status": "development_seen",
        "calibration_seed": args.calibration_seed,
        "episodes_per_condition_fault_plant": args.episodes,
        "conditions": list(conditions),
        "fault_scenarios": [f.value for f in faults],
        "plant_models": list(plants),
        "paired_plant_episode_seeds": True,
        "severity": args.severity,
        "sensor_stack": asdict(Phase7SensorStackConfig()),
        "sensor_transport_model": "scheduled_delivery_queue_v1",
        "sensor_rng_model": "channel_isolated_time_indexed_v1",
        "reference_lateral_freshness_model": "gnss_delivery_only_v1",
        "shared_dropout_model": "single_common_event_blackout_v1",
        "fault_model": asdict(Phase7FaultConfig()),
        "phase7_dynamics": asdict(Phase7DynamicsConfig()),
        "component_gate": asdict(Phase6BComponentGateConfig()),
        "supervisor": asdict(SupervisorV3Config()),
        "historical_phase6b_frozen_commit": "b4e9838555e935a5ec42690495315473629b58f6",
        "scope": "simulation-only external-validity stress study; not physical-flight validation",
        "interpretation": "The legacy-vs-Phase7 plant pairing isolates plant-model sensitivity while holding the new sensing/fault assumptions and episode seed fixed. Sensor RNG streams are channel-isolated and time-indexed; lateral freshness requires a newly delivered GNSS-like update; shared dropout uses one common same-frame outage event. This remains development evidence and does not overwrite frozen Phase 6B.",
    }
    (args.out / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )
    (args.out / "summary.md").write_text(
        "# Phase 7 external-validity development benchmark\n\n"
        "The same sensor/fault episode seeds are paired across the historical and stronger Phase 7 plant models so sensing/fault robustness can be separated from plant-model sensitivity. This is development evidence only.\n\n"
        + f"Executable commit: `{git_sha}`\n\n"
        + summary.to_markdown(index=False)
        + "\n\n## Paired plant effects\n\n"
        + plant_effects.to_markdown(index=False)
        + "\n",
        encoding="utf-8",
    )

    dashboard_bundle = {
        "schema": "aegisland.phase7.dashboard-bundle.v1",
        "metadata": metadata,
        "summary": summary.to_dict(orient="records"),
        "paired_plant_effects": plant_effects.to_dict(orient="records"),
    }
    (args.out / "dashboard_bundle.json").write_text(
        json.dumps(dashboard_bundle, indent=2),
        encoding="utf-8",
    )

    write_result_manifest(
        args.out,
        [
            "episodes.csv",
            "summary.csv",
            "paired_plant_effects.csv",
            "git_sha.txt",
            "run_metadata.json",
            "summary.md",
            "dashboard_bundle.json",
        ],
        schema="aegisland.phase7.result-bundle.v1",
        extra={
            "git_sha": git_sha,
            "episode_seed": args.seed,
            "calibration_seed": args.calibration_seed,
            "run_role": "development_external_validity_factorial",
        },
    )

    print(summary.to_string(index=False))
    if not plant_effects.empty:
        print("\nPaired plant effects:\n")
        print(plant_effects.to_string(index=False))
    print(f"\nSaved Phase 7 development benchmark to {args.out.resolve()}")


if __name__ == "__main__":
    main()
