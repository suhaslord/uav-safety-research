from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import argparse
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from uav_safety.metrics import wilson_interval
from uav_safety.perception import PROFILES
from uav_safety.reference_estimator import ReferenceEstimatorConfig
from uav_safety.simulator import run_episode
from uav_safety.simulator_v2 import run_episode_v2
from uav_safety.simulator_v3 import run_episode_v3
from uav_safety.supervisor_v3 import SupervisorV3Config


ARCHITECTURES = ("baseline", "aegis_v1", "aegis_v2", "aegis_v3")


def run_comparison(episodes: int, seed: int, profiles: list[str]) -> pd.DataFrame:
    """Paired comparison using one episode seed across all architectures."""
    if episodes < 1:
        raise ValueError("episodes must be >= 1")

    seed_rng = np.random.default_rng(seed)
    rows: list[dict] = []

    for profile in profiles:
        episode_seeds = [int(seed_rng.integers(0, 2**31 - 1)) for _ in range(episodes)]
        for episode_seed in episode_seeds:
            runs = (
                ("baseline", run_episode(episode_seed, profile, supervised=False).to_dict()),
                ("aegis_v1", run_episode(episode_seed, profile, supervised=True).to_dict()),
                ("aegis_v2", run_episode_v2(episode_seed, profile).to_dict()),
                ("aegis_v3", run_episode_v3(episode_seed, profile).to_dict()),
            )
            for architecture, row in runs:
                row["architecture"] = architecture
                rows.append(row)

    return pd.DataFrame(rows)


def summarize(raw: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for (profile, architecture), group in raw.groupby(["profile", "architecture"], sort=True):
        n = len(group)
        success_count = int(group["success"].sum())
        unsafe_count = int(group["unsafe_touchdown"].sum())
        abort_count = int(group["aborted"].sum())
        success_ci = wilson_interval(success_count, n)
        unsafe_ci = wilson_interval(unsafe_count, n)
        abort_ci = wilson_interval(abort_count, n)

        row = {
            "profile": profile,
            "architecture": architecture,
            "episodes": n,
            "success_rate": success_count / n,
            "success_ci_low": success_ci[0],
            "success_ci_high": success_ci[1],
            "unsafe_touchdown_rate": unsafe_count / n,
            "unsafe_ci_low": unsafe_ci[0],
            "unsafe_ci_high": unsafe_ci[1],
            "abort_rate": abort_count / n,
            "abort_ci_low": abort_ci[0],
            "abort_ci_high": abort_ci[1],
            "timeout_rate": float((group["outcome"] == "timeout").mean()),
            "mean_final_x_error": float(group["final_x_error"].mean()),
            "mean_interventions": float(group["interventions"].mean()),
            "mean_max_risk": float(group["max_risk"].mean()),
        }

        if "final_bias_estimate_x" in group.columns and architecture == "aegis_v3":
            row.update({
                "mean_final_bias_estimate_x": float(group["final_bias_estimate_x"].mean()),
                "mean_final_bias_confidence": float(group["final_bias_confidence"].mean()),
                "mean_normalized_disagreement": float(group["mean_normalized_disagreement"].mean()),
                "mean_reference_weight": float(group["mean_reference_weight"].mean()),
            })
        else:
            row.update({
                "mean_final_bias_estimate_x": np.nan,
                "mean_final_bias_confidence": np.nan,
                "mean_normalized_disagreement": np.nan,
                "mean_reference_weight": np.nan,
            })
        rows.append(row)

    return pd.DataFrame(rows)


def paired_effects(raw: pd.DataFrame) -> pd.DataFrame:
    """Report paired V3 deltas so aggregate rates do not hide episode swaps."""
    rows: list[dict] = []
    for profile, group in raw.groupby("profile", sort=True):
        base = group[group["architecture"] == "baseline"].set_index("seed")
        v2 = group[group["architecture"] == "aegis_v2"].set_index("seed")
        v3 = group[group["architecture"] == "aegis_v3"].set_index("seed")
        common = base.index.intersection(v2.index).intersection(v3.index)
        base = base.loc[common]
        v2 = v2.loc[common]
        v3 = v3.loc[common]

        rows.append({
            "profile": profile,
            "episodes": len(common),
            "v3_minus_baseline_success_pp": 100.0 * float(v3["success"].mean() - base["success"].mean()),
            "v3_minus_baseline_unsafe_pp": 100.0 * float(v3["unsafe_touchdown"].mean() - base["unsafe_touchdown"].mean()),
            "v3_minus_v2_success_pp": 100.0 * float(v3["success"].mean() - v2["success"].mean()),
            "v3_minus_v2_unsafe_pp": 100.0 * float(v3["unsafe_touchdown"].mean() - v2["unsafe_touchdown"].mean()),
            "baseline_unsafe_rescued_to_v3_success": int((base["unsafe_touchdown"] & v3["success"]).sum()),
            "baseline_success_became_v3_unsafe": int((base["success"] & v3["unsafe_touchdown"]).sum()),
            "v2_unsafe_rescued_to_v3_success": int((v2["unsafe_touchdown"] & v3["success"]).sum()),
            "v2_success_became_v3_unsafe": int((v2["success"] & v3["unsafe_touchdown"]).sum()),
        })
    return pd.DataFrame(rows)


def save_outputs(
    raw: pd.DataFrame,
    summary: pd.DataFrame,
    paired: pd.DataFrame,
    out: Path,
    seed: int,
) -> None:
    out.mkdir(parents=True, exist_ok=True)
    raw.to_csv(out / "episodes.csv", index=False)
    summary.to_csv(out / "summary.csv", index=False)
    paired.to_csv(out / "paired_effects.csv", index=False)

    metadata = {
        "seed": seed,
        "episodes_total": int(len(raw)),
        "architectures": list(ARCHITECTURES),
        "paired_seeds": True,
        "v3_reference_rng_isolated": True,
        "v3_supervisor_config": asdict(SupervisorV3Config()),
        "v3_reference_config": asdict(ReferenceEstimatorConfig()),
    }
    (out / "run_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    display = summary.copy()
    rate_cols = [
        "success_rate", "success_ci_low", "success_ci_high",
        "unsafe_touchdown_rate", "unsafe_ci_low", "unsafe_ci_high",
        "abort_rate", "abort_ci_low", "abort_ci_high", "timeout_rate",
    ]
    for col in rate_cols:
        display[col] = display[col].map(lambda x: f"{x:.3f}")

    (out / "summary.md").write_text(
        "# Aegis V3 comparison\n\n"
        "Paired-seed simulation comparison of baseline, Aegis V1, V2, and V3. "
        "V3 uses an imperfect independent reference-estimator RNG stream that does not alter vision/wind randomness.\n\n"
        + display.to_markdown(index=False)
        + "\n\n## Paired effects\n\n"
        + paired.to_markdown(index=False)
        + "\n",
        encoding="utf-8",
    )

    _plot_metric(summary, "unsafe_touchdown_rate", "Unsafe touchdown rate", out / "unsafe_touchdown_rate.png")
    _plot_metric(summary, "success_rate", "Successful landing rate", out / "success_rate.png")
    _plot_metric(summary, "abort_rate", "Abort rate", out / "abort_rate.png")
    _plot_metric(summary, "mean_interventions", "Mean interventions", out / "mean_interventions.png", unit_interval=False)


def _plot_metric(
    summary: pd.DataFrame,
    metric: str,
    ylabel: str,
    path: Path,
    unit_interval: bool = True,
) -> None:
    pivot = summary.pivot(index="profile", columns="architecture", values=metric)
    pivot.plot(kind="bar")
    plt.ylabel(ylabel)
    plt.xlabel("Perception profile")
    if unit_interval:
        plt.ylim(0, 1)
    plt.title(f"{ylabel}: Baseline vs Aegis V1/V2/V3")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Paired Aegis Baseline/V1/V2/V3 simulation benchmark.")
    parser.add_argument("--episodes", type=int, default=30, help="Episodes per profile for each architecture.")
    parser.add_argument("--seed", type=int, default=3031, help="Top-level benchmark seed.")
    parser.add_argument(
        "--profiles",
        nargs="+",
        default=list(PROFILES.keys()),
        choices=list(PROFILES.keys()),
    )
    parser.add_argument("--out", type=Path, default=Path("results/v3_comparison"))
    args = parser.parse_args()

    raw = run_comparison(args.episodes, args.seed, args.profiles)
    summary = summarize(raw)
    paired = paired_effects(raw)
    save_outputs(raw, summary, paired, args.out, args.seed)

    cols = [
        "profile", "architecture", "episodes", "success_rate",
        "unsafe_touchdown_rate", "abort_rate", "timeout_rate",
        "mean_final_x_error", "mean_interventions",
    ]
    print(summary[cols].to_string(index=False))
    print("\nPaired V3 effects (percentage points):")
    print(paired.to_string(index=False))
    print(f"\nSaved V3 comparison to {args.out.resolve()}")


if __name__ == "__main__":
    main()
