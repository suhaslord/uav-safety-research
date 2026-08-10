from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

import pandas as pd

EXPECTED_PROFILES = {"clean", "blur", "low_light", "occlusion", "mixed"}
EXPECTED_ARCHITECTURES = {"baseline", "aegis_v1", "aegis_v2", "aegis_v3"}
RATE_OUTCOMES = {"success", "unsafe_touchdown", "safe_abort", "timeout"}


def fail(message: str) -> None:
    raise ValueError(message)


def validate(out: Path, expected_seed: int, expected_episodes: int) -> None:
    episodes_path = out / "episodes.csv"
    summary_path = out / "summary.csv"
    paired_path = out / "paired_effects.csv"
    metadata_path = out / "run_metadata.json"

    for path in (episodes_path, summary_path, paired_path, metadata_path):
        if not path.exists():
            fail(f"missing required output: {path}")

    raw = pd.read_csv(episodes_path)
    summary = pd.read_csv(summary_path)
    paired = pd.read_csv(paired_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    if metadata.get("seed") != expected_seed:
        fail(f"metadata seed {metadata.get('seed')} != expected {expected_seed}")

    if metadata.get("paired_seeds") is not True:
        fail("metadata does not confirm paired seeds")

    if metadata.get("v3_reference_rng_isolated") is not True:
        fail("metadata does not confirm isolated V3 reference RNG")

    profiles = set(raw["profile"].unique())
    architectures = set(raw["architecture"].unique())
    if profiles != EXPECTED_PROFILES:
        fail(f"profiles mismatch: {profiles}")
    if architectures != EXPECTED_ARCHITECTURES:
        fail(f"architectures mismatch: {architectures}")

    expected_rows = len(EXPECTED_PROFILES) * len(EXPECTED_ARCHITECTURES) * expected_episodes
    if len(raw) != expected_rows:
        fail(f"episodes.csv has {len(raw)} rows; expected {expected_rows}")

    required_cols = {
        "seed", "profile", "architecture", "outcome", "success",
        "unsafe_touchdown", "aborted", "final_x_error", "interventions",
    }
    missing = required_cols - set(raw.columns)
    if missing:
        fail(f"episodes.csv missing columns: {sorted(missing)}")

    if raw[list(required_cols)].isna().any().any():
        fail("required episode fields contain NaN values")

    unknown_outcomes = set(raw["outcome"].unique()) - RATE_OUTCOMES
    if unknown_outcomes:
        fail(f"unexpected outcomes: {unknown_outcomes}")

    counts = raw.groupby(["profile", "architecture"]).size()
    bad_counts = counts[counts != expected_episodes]
    if not bad_counts.empty:
        fail(f"incorrect episode counts per cell:\n{bad_counts}")

    # Each architecture in a profile must use the same paired seed set.
    for profile in EXPECTED_PROFILES:
        groups = raw[raw["profile"] == profile].groupby("architecture")
        seed_sets = {arch: set(g["seed"].astype(int)) for arch, g in groups}
        first = next(iter(seed_sets.values()))
        for arch, seeds in seed_sets.items():
            if seeds != first:
                fail(f"paired seed mismatch for {profile}/{arch}")
            if len(seeds) != expected_episodes:
                fail(f"duplicate episode seeds in {profile}/{arch}")

    expected_summary_rows = len(EXPECTED_PROFILES) * len(EXPECTED_ARCHITECTURES)
    if len(summary) != expected_summary_rows:
        fail(f"summary.csv has {len(summary)} rows; expected {expected_summary_rows}")

    if set(summary["profile"]) != EXPECTED_PROFILES:
        fail("summary.csv profile set mismatch")
    if set(summary["architecture"]) != EXPECTED_ARCHITECTURES:
        fail("summary.csv architecture set mismatch")

    if set(paired["profile"]) != EXPECTED_PROFILES or len(paired) != len(EXPECTED_PROFILES):
        fail("paired_effects.csv must contain exactly one row per profile")

    # Internal consistency: success, unsafe, abort, and timeout should partition episodes.
    outcome_flags = (
        raw["success"].astype(int)
        + raw["unsafe_touchdown"].astype(int)
        + raw["aborted"].astype(int)
        + (raw["outcome"] == "timeout").astype(int)
    )
    if not (outcome_flags == 1).all():
        fail("episode outcome flags do not form a one-of-four partition")

    print("V3 frozen result validation: PASS")
    print(f"  seed: {expected_seed}")
    print(f"  episodes per cell: {expected_episodes}")
    print(f"  total rows: {len(raw)}")
    print(f"  profiles: {', '.join(sorted(EXPECTED_PROFILES))}")
    print(f"  architectures: {', '.join(sorted(EXPECTED_ARCHITECTURES))}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a frozen Aegis V3 benchmark output directory.")
    parser.add_argument("--out", type=Path, default=Path("results/v3_frozen"))
    parser.add_argument("--seed", type=int, default=424242)
    parser.add_argument("--episodes", type=int, default=500)
    args = parser.parse_args()

    try:
        validate(args.out, args.seed, args.episodes)
    except Exception as exc:
        print(f"V3 frozen result validation: FAIL\n{exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
