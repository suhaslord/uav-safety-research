from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import argparse
import json

import numpy as np
import pandas as pd

from uav_safety.image_perception import IMAGE_CONDITIONS
from uav_safety.image_temporal import fit_synthetic_calibrator
from uav_safety.metrics import wilson_interval
from uav_safety.phase7_faults import FaultScenario
from uav_safety.phase7_reference import Phase7SensorStackConfig
from uav_safety.selective_confidence_v2 import fit_component_calibrator
from uav_safety.simulator_phase7 import run_phase7_episode


DEFAULT_CONDITIONS = ("clean", "low_light", "occlusion", "mixed")
DEFAULT_FAULTS = tuple(s.value for s in FaultScenario)


def _episode_seeds(seed: int, condition_index: int, fault_index: int, episodes: int) -> list[int]:
    rng = np.random.default_rng(np.random.SeedSequence([seed, condition_index, fault_index, 7007]))
    return [int(rng.integers(0, 2**31 - 1)) for _ in range(episodes)]


def summarize(raw: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for (condition, fault), group in raw.groupby(["condition", "fault_scenario"], sort=True):
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
            "mean_reference_available_rate": float(group["reference_available_rate"].mean()),
            "mean_reference_latency_steps": float(group["mean_reference_latency_steps"].mean()),
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Phase 7 simulation-only external-validity stress tests."
    )
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--seed", type=int, default=979797)
    parser.add_argument("--calibration-seed", type=int, default=616161)
    parser.add_argument("--temporal-calibration-samples", type=int, default=180)
    parser.add_argument("--component-calibration-samples", type=int, default=280)
    parser.add_argument("--severity", type=float, default=1.0)
    parser.add_argument("--conditions", nargs="+", default=list(DEFAULT_CONDITIONS))
    parser.add_argument("--faults", nargs="+", default=list(DEFAULT_FAULTS))
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
            for episode_seed in _episode_seeds(args.seed, condition_index, fault_index, args.episodes):
                result = run_phase7_episode(
                    episode_seed,
                    condition,
                    temporal_calibrator,
                    component_calibrator,
                    fault_scenario=fault,
                    severity=args.severity,
                )
                rows.append(result.to_dict())

    raw = pd.DataFrame(rows)
    summary = summarize(raw)
    args.out.mkdir(parents=True, exist_ok=True)
    raw.to_csv(args.out / "episodes.csv", index=False)
    summary.to_csv(args.out / "summary.csv", index=False)
    (args.out / "run_metadata.json").write_text(
        json.dumps({
            "run_role": "development_external_validity",
            "episode_seed": args.seed,
            "calibration_seed": args.calibration_seed,
            "episodes_per_condition_fault": args.episodes,
            "conditions": list(conditions),
            "fault_scenarios": [f.value for f in faults],
            "severity": args.severity,
            "sensor_stack": asdict(Phase7SensorStackConfig()),
            "historical_phase6b_frozen_commit": "b4e9838555e935a5ec42690495315473629b58f6",
            "scope": "simulation-only external-validity stress study; not physical-flight validation",
            "interpretation": "Phase 7 intentionally changes the sensing and plant assumptions, so direct percentage comparisons to frozen Phase 6B are distribution-shift diagnostics rather than a rerun of the frozen experiment.",
        }, indent=2),
        encoding="utf-8",
    )
    (args.out / "summary.md").write_text(
        "# Phase 7 external-validity development benchmark\n\n"
        "This benchmark changes the simulated sensing and plant assumptions. It does not overwrite the frozen Phase 6B result.\n\n"
        + summary.to_markdown(index=False)
        + "\n",
        encoding="utf-8",
    )

    print(summary.to_string(index=False))
    print(f"\nSaved Phase 7 development benchmark to {args.out.resolve()}")


if __name__ == "__main__":
    main()
