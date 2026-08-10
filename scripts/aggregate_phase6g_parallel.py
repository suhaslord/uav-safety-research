from __future__ import annotations

from pathlib import Path
import argparse
import json

import pandas as pd

from run_phase6b_landing import summarize
from run_phase6g_development import paired_effects


EXPECTED_CONDITIONS = {"clean", "blur", "low_light", "occlusion", "mixed"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate parallel Phase 6G condition artifacts.")
    parser.add_argument("--downloads", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    paths = sorted(args.downloads.glob("phase6g-dev-*/episodes.csv"))
    if len(paths) != 5:
        raise ValueError(f"expected 5 condition artifacts, found {len(paths)}")

    raw = pd.concat([pd.read_csv(path) for path in paths], ignore_index=True, sort=False)
    conditions = set(raw["condition"].unique())
    if conditions != EXPECTED_CONDITIONS:
        raise ValueError(f"unexpected conditions: {sorted(conditions)}")
    counts = raw.groupby(["condition", "architecture"]).size()
    if not (counts == 50).all():
        raise ValueError(f"each condition/architecture must contain 50 episodes:\n{counts}")

    summary = summarize(raw)
    paired = paired_effects(raw)
    args.out.mkdir(parents=True, exist_ok=True)
    raw.to_csv(args.out / "episodes.csv", index=False)
    summary.to_csv(args.out / "summary.csv", index=False)
    paired.to_csv(args.out / "paired_effects.csv", index=False)
    (args.out / "run_metadata.json").write_text(json.dumps({
        "run_role": "development_parallel_replay_aggregate",
        "episode_seed_family": 838381,
        "calibration_seed": 616161,
        "conditions": sorted(EXPECTED_CONDITIONS),
        "episodes_per_condition_architecture": 50,
        "protocol": "docs/phase6g_landing_development.md",
        "replacement_reserved_unseen_seeds_not_used": [918271, 928271],
    }, indent=2), encoding="utf-8")
    (args.out / "summary.md").write_text(
        "# Phase 6G parallel development replay\n\n"
        "Deterministic condition-parallel replay of the preregistered `838381` matrix.\n\n"
        "## Summary\n\n" + summary.to_markdown(index=False)
        + "\n\n## Paired effects\n\n" + paired.to_markdown(index=False)
        + "\n",
        encoding="utf-8",
    )
    print(summary.to_string(index=False))
    print("\nPaired effects:")
    print(paired.to_string(index=False))


if __name__ == "__main__":
    main()
