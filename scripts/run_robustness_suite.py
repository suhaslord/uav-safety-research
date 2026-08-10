from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import argparse
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from uav_safety.metrics import wilson_interval
from uav_safety.robustness import SCENARIO_BUILDERS, RobustnessScenario, get_scenarios
from uav_safety.simulator import run_episode
from uav_safety.simulator_v2 import run_episode_v2
from uav_safety.simulator_v3 import run_episode_v3
from uav_safety.supervisor_v3 import SupervisorV3Config


ARCHITECTURES = ("baseline", "aegis_v2", "aegis_v3")
DEFAULT_SEED_FAMILIES = (515151, 626262, 737373, 848484, 959595)


def _episode_seeds(family_seed: int, scenario_index: int, episodes: int) -> list[int]:
    rng = np.random.default_rng(np.random.SeedSequence([family_seed, scenario_index, 5050]))
    return [int(rng.integers(0, 2**31 - 1)) for _ in range(episodes)]


def _run_one(
    architecture: str,
    episode_seed: int,
    scenario: RobustnessScenario,
) -> dict:
    label = scenario.name
    if architecture == "baseline":
        result = run_episode(
            episode_seed,
            label,
            supervised=False,
            perception_profile=scenario.perception_profile,
        )
    elif architecture == "aegis_v2":
        result = run_episode_v2(
            episode_seed,
            label,
            perception_profile=scenario.perception_profile,
        )
    elif architecture == "aegis_v3":
        result = run_episode_v3(
            episode_seed,
            label,
            perception_profile=scenario.perception_profile,
            ref_cfg=scenario.reference_config,
        )
    else:
        raise ValueError(f"Unknown architecture: {architecture}")

    row = result.to_dict()
    row["architecture"] = architecture
    return row


def run_axis(
    axis: str,
    episodes: int,
    seed: int,
    seed_families: tuple[int, ...] = DEFAULT_SEED_FAMILIES,
) -> pd.DataFrame:
    if episodes < 1:
        raise ValueError("episodes must be >= 1")

    scenarios = get_scenarios(axis)
    families = seed_families if axis == "seed_families" else (seed,)
    rows: list[dict] = []

    for family_seed in families:
        for scenario_index, scenario in enumerate(scenarios):
            seeds = _episode_seeds(family_seed, scenario_index, episodes)
            for episode_seed in seeds:
                for architecture in ARCHITECTURES:
                    row = _run_one(architecture, episode_seed, scenario)
                    row.update({
                        "axis": axis,
                        "scenario": scenario.name,
                        "level": scenario.level,
                        "family_seed": family_seed,
                    })
                    rows.append(row)

    return pd.DataFrame(rows)


def summarize(raw: pd.DataFrame) -> pd.DataFrame:
    group_cols = ["axis", "scenario", "level", "family_seed", "architecture"]
    rows: list[dict] = []

    for keys, group in raw.groupby(group_cols, sort=True, dropna=False):
        axis, scenario, level, family_seed, architecture = keys
        n = len(group)
        successes = int(group["success"].sum())
        unsafe = int(group["unsafe_touchdown"].sum())
        aborts = int(group["aborted"].sum())
        success_ci = wilson_interval(successes, n)
        unsafe_ci = wilson_interval(unsafe, n)
        abort_ci = wilson_interval(aborts, n)

        rows.append({
            "axis": axis,
            "scenario": scenario,
            "level": level,
            "family_seed": int(family_seed),
            "architecture": architecture,
            "episodes": n,
            "success_rate": successes / n,
            "success_ci_low": success_ci[0],
            "success_ci_high": success_ci[1],
            "unsafe_touchdown_rate": unsafe / n,
            "unsafe_ci_low": unsafe_ci[0],
            "unsafe_ci_high": unsafe_ci[1],
            "abort_rate": aborts / n,
            "abort_ci_low": abort_ci[0],
            "abort_ci_high": abort_ci[1],
            "timeout_rate": float((group["outcome"] == "timeout").mean()),
            "mean_final_x_error": float(group["final_x_error"].mean()),
            "mean_interventions": float(group["interventions"].mean()),
        })

    return pd.DataFrame(rows)


def paired_effects(raw: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    key_cols = ["axis", "scenario", "level", "family_seed"]

    for keys, group in raw.groupby(key_cols, sort=True, dropna=False):
        axis, scenario, level, family_seed = keys
        baseline = group[group["architecture"] == "baseline"].set_index("seed")
        v2 = group[group["architecture"] == "aegis_v2"].set_index("seed")
        v3 = group[group["architecture"] == "aegis_v3"].set_index("seed")
        common = baseline.index.intersection(v2.index).intersection(v3.index)
        baseline = baseline.loc[common]
        v2 = v2.loc[common]
        v3 = v3.loc[common]

        rows.append({
            "axis": axis,
            "scenario": scenario,
            "level": level,
            "family_seed": int(family_seed),
            "episodes": len(common),
            "v3_minus_baseline_success_pp": 100 * float(v3["success"].mean() - baseline["success"].mean()),
            "v3_minus_baseline_unsafe_pp": 100 * float(v3["unsafe_touchdown"].mean() - baseline["unsafe_touchdown"].mean()),
            "v3_minus_v2_success_pp": 100 * float(v3["success"].mean() - v2["success"].mean()),
            "v3_minus_v2_unsafe_pp": 100 * float(v3["unsafe_touchdown"].mean() - v2["unsafe_touchdown"].mean()),
            "baseline_unsafe_rescued_to_v3_success": int((baseline["unsafe_touchdown"] & v3["success"]).sum()),
            "baseline_success_became_v3_unsafe": int((baseline["success"] & v3["unsafe_touchdown"]).sum()),
            "v2_unsafe_rescued_to_v3_success": int((v2["unsafe_touchdown"] & v3["success"]).sum()),
            "v2_success_became_v3_unsafe": int((v2["success"] & v3["unsafe_touchdown"]).sum()),
        })

    return pd.DataFrame(rows)


def aggregate_seed_families(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty or summary["axis"].iloc[0] != "seed_families":
        return pd.DataFrame()

    cols = ["success_rate", "unsafe_touchdown_rate", "abort_rate", "mean_interventions"]
    agg = (
        summary.groupby(["scenario", "architecture"], as_index=False)[cols]
        .agg(["mean", "std", "min", "max"])
    )
    agg.columns = ["_".join(col).strip("_") for col in agg.columns.to_flat_index()]
    return agg


def save_axis(
    raw: pd.DataFrame,
    summary: pd.DataFrame,
    paired: pd.DataFrame,
    axis: str,
    out: Path,
    seed: int,
    episodes: int,
) -> None:
    out.mkdir(parents=True, exist_ok=True)
    raw.to_csv(out / "episodes.csv", index=False)
    summary.to_csv(out / "summary.csv", index=False)
    paired.to_csv(out / "paired_effects.csv", index=False)

    scenarios = get_scenarios(axis)
    metadata = {
        "axis": axis,
        "episodes_per_scenario_architecture_family": episodes,
        "top_level_seed": seed,
        "seed_families": list(DEFAULT_SEED_FAMILIES) if axis == "seed_families" else [seed],
        "architectures": list(ARCHITECTURES),
        "paired_episode_seeds": True,
        "v3_reference_rng_isolated": True,
        "v3_supervisor_config": asdict(SupervisorV3Config()),
        "scenarios": [scenario.metadata() for scenario in scenarios],
    }
    (out / "run_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    display_cols = [
        "scenario", "level", "family_seed", "architecture", "episodes",
        "success_rate", "unsafe_touchdown_rate", "abort_rate", "mean_interventions",
    ]
    (out / "summary.md").write_text(
        f"# Aegis V3 robustness: {axis}\n\n"
        "This is a simulation-only post-freeze robustness study. The frozen V3 "
        "algorithm is evaluated without retuning.\n\n"
        + summary[display_cols].to_markdown(index=False)
        + "\n\n## Paired effects\n\n"
        + paired.to_markdown(index=False)
        + "\n",
        encoding="utf-8",
    )

    if axis == "seed_families":
        aggregate = aggregate_seed_families(summary)
        aggregate.to_csv(out / "family_aggregate.csv", index=False)

    _plot(summary, "unsafe_touchdown_rate", "Unsafe touchdown rate", out / "unsafe_rate.png")
    _plot(summary, "success_rate", "Success rate", out / "success_rate.png")
    _plot(summary, "abort_rate", "Abort rate", out / "abort_rate.png")


def _plot(summary: pd.DataFrame, metric: str, ylabel: str, path: Path) -> None:
    data = summary.copy()
    if data["axis"].iloc[0] == "seed_families":
        plot_data = (
            data.groupby(["family_seed", "architecture"], as_index=False)[metric]
            .mean()
            .pivot(index="family_seed", columns="architecture", values=metric)
        )
        xlabel = "Unseen seed family"
    else:
        plot_data = data.pivot(index="scenario", columns="architecture", values=metric)
        xlabel = "Stress scenario"

    plot_data.plot(kind="bar")
    plt.ylabel(ylabel)
    plt.xlabel(xlabel)
    plt.ylim(0, 1)
    plt.title(f"{ylabel}: robustness study")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def print_compact(summary: pd.DataFrame, paired: pd.DataFrame) -> None:
    cols = [
        "scenario", "level", "family_seed", "architecture", "episodes",
        "success_rate", "unsafe_touchdown_rate", "abort_rate", "mean_interventions",
    ]
    print(summary[cols].to_string(index=False))
    print("\nPaired V3 effects (percentage points):")
    print(paired.to_string(index=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Post-freeze Aegis V3 robustness suite.")
    parser.add_argument(
        "--axis",
        choices=[*SCENARIO_BUILDERS.keys(), "all"],
        default="seed_families",
    )
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--seed", type=int, default=515151)
    parser.add_argument("--out", type=Path, default=Path("results/robustness"))
    args = parser.parse_args()

    axes = list(SCENARIO_BUILDERS.keys()) if args.axis == "all" else [args.axis]

    for axis in axes:
        axis_out = args.out / axis
        raw = run_axis(axis, args.episodes, args.seed)
        summary = summarize(raw)
        paired = paired_effects(raw)
        save_axis(raw, summary, paired, axis, axis_out, args.seed, args.episodes)
        print(f"\n=== {axis} ===")
        print_compact(summary, paired)
        print(f"Saved to {axis_out.resolve()}")


if __name__ == "__main__":
    main()
