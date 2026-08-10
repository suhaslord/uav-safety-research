from __future__ import annotations

from pathlib import Path
import argparse
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from uav_safety.perception import PROFILES
from uav_safety.simulator import run_episode
from uav_safety.simulator_v2 import run_episode_v2


def run_comparison(episodes: int, seed: int, profiles: list[str]) -> pd.DataFrame:
    """Run a paired Baseline/V1/V2 comparison using identical episode seeds.

    Pairing matters: each architecture sees the same initial-state/random seed
    inside a profile, which reduces noise in architecture-to-architecture
    comparisons.
    """
    seed_rng = np.random.default_rng(seed)
    rows: list[dict] = []

    for profile in profiles:
        episode_seeds = [int(seed_rng.integers(0, 2**31 - 1)) for _ in range(episodes)]
        for episode_seed in episode_seeds:
            baseline = run_episode(episode_seed, profile, supervised=False).to_dict()
            baseline["architecture"] = "baseline"
            rows.append(baseline)

            v1 = run_episode(episode_seed, profile, supervised=True).to_dict()
            v1["architecture"] = "aegis_v1"
            rows.append(v1)

            v2 = run_episode_v2(episode_seed, profile).to_dict()
            v2["architecture"] = "aegis_v2"
            rows.append(v2)

    return pd.DataFrame(rows)


def summarize(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (profile, architecture), group in raw.groupby(["profile", "architecture"], sort=True):
        n = len(group)
        rows.append({
            "profile": profile,
            "architecture": architecture,
            "episodes": n,
            "success_rate": float(group["success"].mean()),
            "unsafe_touchdown_rate": float(group["unsafe_touchdown"].mean()),
            "abort_rate": float(group["aborted"].mean()),
            "timeout_rate": float((group["outcome"] == "timeout").mean()),
            "mean_final_x_error": float(group["final_x_error"].mean()),
            "mean_interventions": float(group["interventions"].mean()),
            "mean_max_risk": float(group["max_risk"].mean()),
        })
    return pd.DataFrame(rows)


def save(raw: pd.DataFrame, summary: pd.DataFrame, out: Path, seed: int) -> None:
    out.mkdir(parents=True, exist_ok=True)
    raw.to_csv(out / "episodes.csv", index=False)
    summary.to_csv(out / "summary.csv", index=False)
    (out / "run_metadata.json").write_text(json.dumps({
        "seed": seed,
        "episodes_total": int(len(raw)),
        "architectures": ["baseline", "aegis_v1", "aegis_v2"],
        "paired_seeds": True,
    }, indent=2), encoding="utf-8")

    display = summary.copy()
    for col in ["success_rate", "unsafe_touchdown_rate", "abort_rate", "timeout_rate"]:
        display[col] = display[col].map(lambda x: f"{x:.3f}")
    (out / "summary.md").write_text(
        "# Aegis V2 comparison\n\n"
        "Paired-seed comparison of baseline, Aegis V1, and Aegis V2.\n\n"
        + display.to_markdown(index=False)
        + "\n",
        encoding="utf-8",
    )

    _plot_metric(summary, "unsafe_touchdown_rate", "Unsafe touchdown rate", out / "unsafe_touchdown_rate.png")
    _plot_metric(summary, "success_rate", "Successful landing rate", out / "success_rate.png")
    _plot_metric(summary, "abort_rate", "Abort rate", out / "abort_rate.png")


def _plot_metric(summary: pd.DataFrame, metric: str, ylabel: str, path: Path) -> None:
    pivot = summary.pivot(index="profile", columns="architecture", values=metric)
    pivot.plot(kind="bar")
    plt.ylabel(ylabel)
    plt.xlabel("Perception profile")
    plt.ylim(0, 1)
    plt.title(f"{ylabel}: Baseline vs Aegis V1 vs Aegis V2")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Paired Aegis Baseline/V1/V2 benchmark.")
    parser.add_argument("--episodes", type=int, default=200, help="Episodes per profile for each architecture.")
    parser.add_argument("--seed", type=int, default=2027)
    parser.add_argument(
        "--profiles",
        nargs="+",
        default=list(PROFILES.keys()),
        choices=list(PROFILES.keys()),
    )
    parser.add_argument("--out", type=Path, default=Path("results/v2_comparison"))
    args = parser.parse_args()

    raw = run_comparison(args.episodes, args.seed, args.profiles)
    summary = summarize(raw)
    save(raw, summary, args.out, args.seed)
    print(summary.to_string(index=False))
    print(f"\nSaved V2 comparison to {args.out.resolve()}")


if __name__ == "__main__":
    main()
