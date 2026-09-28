"""Replay the frozen V3 benchmark and verify Model VASE preserves its results.

The VASE wrapper is intentionally a no-op orchestration change. Categorical
episode outcomes and paired transitions must match exactly; floating-point
measurements allow only 1e-13 absolute/relative tolerance for runtime-level
rounding differences.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_v3_comparison import paired_effects, run_comparison, summarize
from uav_safety.perception import PROFILES


FROZEN = ROOT / "results/v3_frozen"
TOLERANCE = 1e-13


def compare_tables(label: str, actual: pd.DataFrame, expected: pd.DataFrame) -> float:
    if list(actual.columns) != list(expected.columns):
        raise AssertionError(f"{label}: column mismatch")
    if len(actual) != len(expected):
        raise AssertionError(f"{label}: row count {len(actual)} != {len(expected)}")

    max_delta = 0.0
    for column in actual.columns:
        left = actual[column]
        right = expected[column]
        if pd.api.types.is_numeric_dtype(left) and pd.api.types.is_numeric_dtype(right):
            a = left.to_numpy(dtype=float, na_value=np.nan)
            b = right.to_numpy(dtype=float, na_value=np.nan)
            finite = np.isfinite(a) & np.isfinite(b)
            if np.any(finite):
                max_delta = max(max_delta, float(np.max(np.abs(a[finite] - b[finite]))))
            if not np.allclose(a, b, rtol=TOLERANCE, atol=TOLERANCE, equal_nan=True):
                raise AssertionError(f"{label}: numeric mismatch in {column}")
        else:
            a = left.fillna("<NA>").astype(str).to_numpy()
            b = right.fillna("<NA>").astype(str).to_numpy()
            if not np.array_equal(a, b):
                raise AssertionError(f"{label}: categorical mismatch in {column}")
    print(f"{label}: {len(actual)} rows match (maximum numeric delta {max_delta:.3g})")
    return max_delta


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=500, help="Episodes per profile; frozen benchmark uses 500.")
    parser.add_argument("--seed", type=int, default=424242, help="Frozen benchmark seed.")
    parser.add_argument("--replay-dir", type=Path, help="Compare a prior output directory instead of rerunning the 10,000 episodes.")
    args = parser.parse_args()
    if args.episodes != 500 or args.seed != 424242:
        raise SystemExit("This parity check is bound to the committed frozen run: --episodes 500 --seed 424242")

    replay_dir = args.replay_dir
    if replay_dir is None:
        replay = run_comparison(args.episodes, args.seed, list(PROFILES))
        replay_summary = summarize(replay)
        replay_pairs = paired_effects(replay)
    else:
        metadata = pd.read_json(replay_dir / "run_metadata.json", typ="series")
        if int(metadata["seed"]) != args.seed or int(metadata["episodes_total"]) != 10000:
            raise SystemExit("Replay metadata does not identify the frozen 10,000-row run at seed 424242")
        replay = pd.read_csv(replay_dir / "episodes.csv")
        replay_summary = pd.read_csv(replay_dir / "summary.csv")
        replay_pairs = pd.read_csv(replay_dir / "paired_effects.csv")

    frozen_episodes = pd.read_csv(FROZEN / "episodes.csv")
    compare_tables("episode outcomes", replay, frozen_episodes)

    frozen_summary = pd.read_csv(FROZEN / "summary.csv")
    compare_tables("summary metrics", replay_summary, frozen_summary)

    frozen_pairs = pd.read_csv(FROZEN / "paired_effects.csv")
    compare_tables("paired effects", replay_pairs, frozen_pairs)

    print("Model VASE frozen V3 parity: PASS")
    print("10,000 episode outcomes and all published comparisons reproduced.")


if __name__ == "__main__":
    main()
