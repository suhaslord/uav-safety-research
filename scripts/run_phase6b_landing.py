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
from uav_safety.phase6b_fusion import Phase6BComponentGateConfig
from uav_safety.selective_confidence_v2 import fit_component_calibrator
from uav_safety.simulator_image_phase6b import run_phase6b_episode
from uav_safety.simulator_image_v3 import run_image_episode


ARCHITECTURES = ("image_temporal", "image_aegis_v3", "image_aegis_phase6b")
COMPONENT_COLUMNS = (
    "lateral_component_abstentions",
    "lateral_component_abstention_rate",
    "altitude_component_abstentions",
    "altitude_component_abstention_rate",
    "lateral_reference_takeovers",
    "altitude_reference_takeovers",
    "unresolved_component_frames",
    "mean_p_x_good",
    "mean_p_z_good",
)


def _episode_seeds(seed: int, condition_index: int, episodes: int) -> list[int]:
    rng = np.random.default_rng(np.random.SeedSequence([seed, condition_index, 6060]))
    return [int(rng.integers(0, 2**31 - 1)) for _ in range(episodes)]


def run_comparison(
    *,
    episodes: int,
    seed: int,
    calibration_seed: int,
    temporal_calibration_samples: int,
    component_calibration_samples: int,
    severity: float,
    gate_cfg: Phase6BComponentGateConfig,
) -> tuple[pd.DataFrame, object, object]:
    temporal_calibrator = fit_synthetic_calibrator(
        seed=calibration_seed,
        samples_per_condition=temporal_calibration_samples,
    )
    component_calibrator = fit_component_calibrator(
        seed=calibration_seed,
        samples_per_condition=component_calibration_samples,
    )

    rows: list[dict] = []
    for condition_index, condition in enumerate(IMAGE_CONDITIONS):
        for episode_seed in _episode_seeds(seed, condition_index, episodes):
            for architecture in ARCHITECTURES:
                if architecture == "image_aegis_phase6b":
                    result = run_phase6b_episode(
                        episode_seed,
                        condition,
                        temporal_calibrator,
                        component_calibrator,
                        severity=severity,
                        component_gate_cfg=gate_cfg,
                    )
                else:
                    result = run_image_episode(
                        episode_seed,
                        condition,
                        temporal_calibrator,
                        architecture=architecture,
                        severity=severity,
                    )
                row = result.to_dict()
                for column in COMPONENT_COLUMNS:
                    row.setdefault(column, np.nan)
                rows.append(row)

    return pd.DataFrame(rows), temporal_calibrator, component_calibrator


def summarize(raw: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for (condition, architecture), group in raw.groupby(["condition", "architecture"], sort=True):
        n = len(group)
        success_n = int(group["success"].sum())
        unsafe_n = int(group["unsafe_touchdown"].sum())
        abort_n = int(group["aborted"].sum())
        success_ci = wilson_interval(success_n, n)
        unsafe_ci = wilson_interval(unsafe_n, n)
        abort_ci = wilson_interval(abort_n, n)

        def mean_or_nan(column: str) -> float:
            values = pd.to_numeric(group[column], errors="coerce")
            return float(values.mean()) if values.notna().any() else np.nan

        rows.append({
            "condition": condition,
            "architecture": architecture,
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
            "mean_image_abstention_rate": float(group["image_abstention_rate"].mean()),
            "mean_lateral_component_abstention_rate": mean_or_nan("lateral_component_abstention_rate"),
            "mean_altitude_component_abstention_rate": mean_or_nan("altitude_component_abstention_rate"),
            "mean_lateral_reference_takeovers": mean_or_nan("lateral_reference_takeovers"),
            "mean_altitude_reference_takeovers": mean_or_nan("altitude_reference_takeovers"),
            "mean_unresolved_component_frames": mean_or_nan("unresolved_component_frames"),
            "mean_p_x_good": mean_or_nan("mean_p_x_good"),
            "mean_p_z_good": mean_or_nan("mean_p_z_good"),
            "mean_interventions": float(group["interventions"].mean()),
            "mean_final_x_error": float(group["final_x_error"].mean()),
            "mean_abs_final_vx": float(group["final_vx"].abs().mean()),
            "mean_abs_final_vz": float(group["final_vz"].abs().mean()),
        })
    return pd.DataFrame(rows)


def paired_effects(raw: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for condition, group in raw.groupby("condition", sort=True):
        baseline = group[group["architecture"] == "image_temporal"].set_index("seed")
        old = group[group["architecture"] == "image_aegis_v3"].set_index("seed")
        new = group[group["architecture"] == "image_aegis_phase6b"].set_index("seed")
        common = baseline.index.intersection(old.index).intersection(new.index)
        baseline = baseline.loc[common]
        old = old.loc[common]
        new = new.loc[common]

        for comparison, reference in (
            ("phase6_vs_image_temporal", baseline),
            ("phase6b_vs_image_temporal", baseline),
            ("phase6b_vs_phase6", old),
        ):
            candidate = old if comparison == "phase6_vs_image_temporal" else new
            rows.append({
                "condition": condition,
                "comparison": comparison,
                "paired_episodes": len(common),
                "candidate_minus_reference_success_pp": 100 * float(candidate["success"].mean() - reference["success"].mean()),
                "candidate_minus_reference_unsafe_pp": 100 * float(candidate["unsafe_touchdown"].mean() - reference["unsafe_touchdown"].mean()),
                "reference_unsafe_rescued_to_candidate_success": int((reference["unsafe_touchdown"] & candidate["success"]).sum()),
                "reference_success_became_candidate_unsafe": int((reference["success"] & candidate["unsafe_touchdown"]).sum()),
                "reference_success_became_candidate_abort": int((reference["success"] & candidate["aborted"]).sum()),
                "reference_abort_became_candidate_success": int((reference["aborted"] & candidate["success"]).sum()),
            })
    return pd.DataFrame(rows)


def save_results(
    raw: pd.DataFrame,
    summary: pd.DataFrame,
    paired: pd.DataFrame,
    temporal_calibrator,
    component_calibrator,
    gate_cfg: Phase6BComponentGateConfig,
    out: Path,
    args,
) -> None:
    out.mkdir(parents=True, exist_ok=True)
    raw.to_csv(out / "episodes.csv", index=False)
    summary.to_csv(out / "summary.csv", index=False)
    paired.to_csv(out / "paired_effects.csv", index=False)
    (out / "temporal_calibrator.json").write_text(
        json.dumps(temporal_calibrator.to_dict(), indent=2), encoding="utf-8"
    )
    (out / "component_calibrator.json").write_text(
        json.dumps(component_calibrator.to_dict(), indent=2), encoding="utf-8"
    )
    (out / "run_metadata.json").write_text(json.dumps({
        "run_role": args.run_role,
        "episode_seed": args.seed,
        "calibration_seed": args.calibration_seed,
        "episodes_per_condition_architecture": args.episodes,
        "temporal_calibration_samples_per_condition": args.temporal_calibration_samples,
        "component_calibration_samples_per_condition": args.component_calibration_samples,
        "severity": args.severity,
        "architectures": list(ARCHITECTURES),
        "conditions": list(IMAGE_CONDITIONS),
        "paired_episode_seeds": True,
        "phase6b_component_gate": asdict(gate_cfg),
        "threshold_selection": "0.80/0.80 selected from predeclared Phase 6B development risk-coverage grid before Phase 6B landing runs",
        "historical_phase6_frozen_landing_seed": 747474,
        "historical_phase6_frozen_selective_seed": 757575,
        "scope": "simulation-only synthetic image sequences",
    }, indent=2), encoding="utf-8")
    (out / "summary.md").write_text(
        "# Phase 6B paired landing comparison\n\n"
        "Phase 6B is evaluated as a new revision. The historical Phase 6 frozen result is not overwritten. "
        "All architectures in this bundle use identical paired episode seeds.\n\n"
        "## Summary\n\n"
        + summary.to_markdown(index=False)
        + "\n\n## Paired effects\n\n"
        + paired.to_markdown(index=False)
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare original Phase 6 and component-selective Phase 6B Aegis landing.")
    parser.add_argument("--episodes", type=int, default=30)
    parser.add_argument("--seed", type=int, default=626262)
    parser.add_argument("--calibration-seed", type=int, default=616161)
    parser.add_argument("--temporal-calibration-samples", type=int, default=180)
    parser.add_argument("--component-calibration-samples", type=int, default=280)
    parser.add_argument("--severity", type=float, default=1.0)
    parser.add_argument("--lateral-threshold", type=float, default=0.80)
    parser.add_argument("--altitude-threshold", type=float, default=0.80)
    parser.add_argument("--run-role", choices=("development", "frozen"), default="development")
    parser.add_argument("--out", type=Path, default=Path("results/phase6b_development"))
    args = parser.parse_args()

    if args.episodes < 1:
        raise ValueError("episodes must be >= 1")
    if args.seed == args.calibration_seed:
        raise ValueError("episode and calibration seeds must differ")
    if not 0.0 <= args.lateral_threshold <= 1.0 or not 0.0 <= args.altitude_threshold <= 1.0:
        raise ValueError("component thresholds must lie in [0,1]")

    gate_cfg = Phase6BComponentGateConfig(
        lateral_confidence_threshold=args.lateral_threshold,
        altitude_confidence_threshold=args.altitude_threshold,
    )
    raw, temporal_calibrator, component_calibrator = run_comparison(
        episodes=args.episodes,
        seed=args.seed,
        calibration_seed=args.calibration_seed,
        temporal_calibration_samples=args.temporal_calibration_samples,
        component_calibration_samples=args.component_calibration_samples,
        severity=args.severity,
        gate_cfg=gate_cfg,
    )
    summary = summarize(raw)
    paired = paired_effects(raw)
    save_results(
        raw,
        summary,
        paired,
        temporal_calibrator,
        component_calibrator,
        gate_cfg,
        args.out,
        args,
    )

    print(summary.to_string(index=False))
    print("\nPaired effects:")
    print(paired.to_string(index=False))
    print(f"\nSaved Phase 6B comparison to {args.out.resolve()}")


if __name__ == "__main__":
    main()
