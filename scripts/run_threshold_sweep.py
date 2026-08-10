from pathlib import Path
import argparse
import sys

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uav_safety.config import SupervisorConfig
from uav_safety.experiment import run_monte_carlo


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep supervisor thresholds.")
    parser.add_argument("--episodes", type=int, default=60)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--profile", default="occlusion")
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "threshold_sweep")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    rows = []

    hold_values = [0.58, 0.64, 0.70, 0.76]
    abort_values = [0.82, 0.88, 0.94]

    for hold in hold_values:
        for abort in abort_values:
            if abort <= hold:
                continue
            cfg = SupervisorConfig(hold_risk=hold, abort_risk=abort)
            _, summary = run_monte_carlo(args.episodes, args.seed, sup_cfg=cfg)
            cell = summary[
                (summary["profile"] == args.profile)
                & (summary["controller"] == "supervised")
            ].iloc[0]
            rows.append({
                "hold_risk": hold,
                "abort_risk": abort,
                "success_rate": cell["success_rate"],
                "unsafe_touchdown_rate": cell["unsafe_touchdown_rate"],
                "abort_rate": cell["abort_rate"],
                "mean_interventions": cell["mean_interventions"],
            })

    df = pd.DataFrame(rows)
    df.to_csv(args.out / "threshold_sweep.csv", index=False)

    plt.figure(figsize=(7, 5))
    scatter = plt.scatter(
        df["unsafe_touchdown_rate"],
        df["success_rate"],
        s=80,
        c=df["abort_rate"],
    )
    for _, row in df.iterrows():
        plt.annotate(
            f"H{row.hold_risk:.2f}/A{row.abort_risk:.2f}",
            (row.unsafe_touchdown_rate, row.success_rate),
            fontsize=7,
            xytext=(4, 4),
            textcoords="offset points",
        )
    plt.xlabel("Unsafe touchdown rate (lower is better)")
    plt.ylabel("Successful landing rate (higher is better)")
    plt.title(f"Safety–availability frontier: {args.profile}")
    plt.colorbar(scatter, label="Abort rate")
    plt.tight_layout()
    plt.savefig(args.out / "safety_availability_frontier.png", dpi=180)
    plt.close()

    print(df.to_string(index=False))
    print(f"\nSaved sweep to {args.out}")


if __name__ == "__main__":
    main()
