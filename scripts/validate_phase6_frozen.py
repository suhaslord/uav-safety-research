from __future__ import annotations

from pathlib import Path
import argparse
import json

import pandas as pd

from uav_safety.image_perception import IMAGE_CONDITIONS
from run_phase6_image_landing import ARCHITECTURES, PHASE6_ALGORITHM_FREEZE_COMMIT


REQUIRED_COLUMNS = {
    "seed",
    "condition",
    "architecture",
    "outcome",
    "success",
    "unsafe_touchdown",
    "aborted",
    "frames",
    "image_abstentions",
    "image_abstention_rate",
    "final_x_error",
    "final_vx",
    "final_vz",
}


def _as_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    normalized = series.astype(str).str.strip().str.lower()
    if not normalized.isin({"true", "false", "1", "0"}).all():
        raise ValueError(f"Boolean column contains unexpected values: {sorted(normalized.unique())}")
    return normalized.isin({"true", "1"})


def validate(out: Path, seed: int, episodes: int, calibration_seed: int) -> list[str]:
    errors: list[str] = []
    episodes_path = out / "episodes.csv"
    summary_path = out / "summary.csv"
    paired_path = out / "paired_effects.csv"
    metadata_path = out / "run_metadata.json"
    calibrator_path = out / "calibrator.json"

    for path in (episodes_path, summary_path, paired_path, metadata_path, calibrator_path):
        if not path.exists():
            errors.append(f"missing required file: {path.name}")
    if errors:
        return errors

    raw = pd.read_csv(episodes_path)
    summary = pd.read_csv(summary_path)
    paired = pd.read_csv(paired_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    missing_columns = sorted(REQUIRED_COLUMNS - set(raw.columns))
    if missing_columns:
        errors.append(f"episodes.csv missing columns: {missing_columns}")
        return errors

    expected_rows = len(IMAGE_CONDITIONS) * len(ARCHITECTURES) * episodes
    if len(raw) != expected_rows:
        errors.append(f"expected {expected_rows} episode rows, found {len(raw)}")

    conditions = set(raw["condition"].unique())
    if conditions != set(IMAGE_CONDITIONS):
        errors.append(f"condition set mismatch: {sorted(conditions)}")

    architectures = set(raw["architecture"].unique())
    if architectures != set(ARCHITECTURES):
        errors.append(f"architecture set mismatch: {sorted(architectures)}")

    group_sizes = raw.groupby(["condition", "architecture"], dropna=False).size()
    if len(group_sizes) != len(IMAGE_CONDITIONS) * len(ARCHITECTURES):
        errors.append("missing one or more condition/architecture cells")
    bad_sizes = group_sizes[group_sizes != episodes]
    if len(bad_sizes):
        errors.append(f"incorrect cell sizes: {bad_sizes.to_dict()}")

    duplicates = raw.duplicated(subset=["condition", "architecture", "seed"])
    if duplicates.any():
        errors.append(f"duplicate condition/architecture/seed rows: {int(duplicates.sum())}")

    for condition in IMAGE_CONDITIONS:
        sets = []
        for architecture in ARCHITECTURES:
            cell = raw[(raw["condition"] == condition) & (raw["architecture"] == architecture)]
            sets.append(set(int(v) for v in cell["seed"]))
        if len(sets) != 2 or sets[0] != sets[1]:
            errors.append(f"paired episode seeds do not match for {condition}")
        if len(sets[0]) != episodes:
            errors.append(f"expected {episodes} unique paired seeds for {condition}, found {len(sets[0])}")

    success = _as_bool(raw["success"])
    unsafe = _as_bool(raw["unsafe_touchdown"])
    aborted = _as_bool(raw["aborted"])
    timeout = raw["outcome"].astype(str).eq("timeout")
    outcome_count = success.astype(int) + unsafe.astype(int) + aborted.astype(int) + timeout.astype(int)
    if not outcome_count.eq(1).all():
        errors.append(f"outcome flags are not mutually exclusive/exhaustive for {int((outcome_count != 1).sum())} rows")

    if not raw.loc[success, "outcome"].astype(str).eq("success").all():
        errors.append("success flag disagrees with outcome label")
    if not raw.loc[unsafe, "outcome"].astype(str).eq("unsafe_touchdown").all():
        errors.append("unsafe_touchdown flag disagrees with outcome label")
    if not raw.loc[aborted, "outcome"].astype(str).eq("safe_abort").all():
        errors.append("aborted flag disagrees with outcome label")

    numeric_required = [
        "seed", "frames", "image_abstentions", "image_abstention_rate",
        "final_x_error", "final_vx", "final_vz",
    ]
    if raw[numeric_required].isna().any().any():
        errors.append("required episode numeric fields contain NaN")
    if ((raw["image_abstention_rate"] < 0) | (raw["image_abstention_rate"] > 1)).any():
        errors.append("image_abstention_rate outside [0, 1]")
    if (raw["image_abstentions"] > raw["frames"]).any():
        errors.append("image_abstentions exceeds frames")

    expected_summary_rows = len(IMAGE_CONDITIONS) * len(ARCHITECTURES)
    if len(summary) != expected_summary_rows:
        errors.append(f"expected {expected_summary_rows} summary rows, found {len(summary)}")
    if len(paired) != len(IMAGE_CONDITIONS):
        errors.append(f"expected {len(IMAGE_CONDITIONS)} paired-effect rows, found {len(paired)}")
    if "paired_episodes" in paired.columns and not paired["paired_episodes"].eq(episodes).all():
        errors.append("paired_effects.csv does not report the expected paired episode count")

    metadata_checks = {
        "run_role": "frozen",
        "phase6_algorithm_freeze_commit": PHASE6_ALGORITHM_FREEZE_COMMIT,
        "evaluation_seed": seed,
        "calibration_seed": calibration_seed,
        "episodes_per_condition_architecture": episodes,
        "paired_episode_seeds": True,
        "image_rng_isolated": True,
        "reference_rng_isolated": True,
    }
    for key, expected in metadata_checks.items():
        if metadata.get(key) != expected:
            errors.append(f"metadata {key!r}: expected {expected!r}, found {metadata.get(key)!r}")

    if seed == calibration_seed:
        errors.append("evaluation seed equals calibration seed")

    if metadata.get("conditions") != list(IMAGE_CONDITIONS):
        errors.append("metadata conditions do not match frozen condition order")
    if metadata.get("architectures") != list(ARCHITECTURES):
        errors.append("metadata architectures do not match frozen architecture order")

    config = metadata.get("configuration")
    if not isinstance(config, dict):
        errors.append("metadata is missing the configuration snapshot")
    else:
        required_config_blocks = {
            "simulation", "controller", "temporal_image", "robust_velocity",
            "phase6_fusion", "frozen_v3_supervisor", "reference_estimator", "renderer",
        }
        missing_blocks = sorted(required_config_blocks - set(config))
        if missing_blocks:
            errors.append(f"configuration snapshot missing blocks: {missing_blocks}")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the frozen Phase 6 image-to-Aegis result bundle.")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--episodes", type=int, required=True)
    parser.add_argument("--calibration-seed", type=int, default=616161)
    args = parser.parse_args()

    errors = validate(args.out, args.seed, args.episodes, args.calibration_seed)
    if errors:
        print("Phase 6 frozen validation: FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    expected_rows = len(IMAGE_CONDITIONS) * len(ARCHITECTURES) * args.episodes
    print("Phase 6 frozen validation: PASS")
    print(f"evaluation seed: {args.seed}")
    print(f"calibration seed: {args.calibration_seed}")
    print(f"episodes per condition/architecture cell: {args.episodes}")
    print(f"total episode rows: {expected_rows}")
    print(f"algorithm freeze commit: {PHASE6_ALGORITHM_FREEZE_COMMIT}")


if __name__ == "__main__":
    main()
