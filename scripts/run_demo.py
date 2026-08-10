from pathlib import Path
import sys

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uav_safety.simulator import run_episode


def main() -> None:
    seed = 42
    profile = "mixed"

    baseline, baseline_trace = run_episode(seed, profile, supervised=False, return_trace=True)
    guarded, guarded_trace = run_episode(seed, profile, supervised=True, return_trace=True)

    print("BASELINE")
    print(baseline)
    print("\nSUPERVISED")
    print(guarded)

    out = ROOT / "results" / "demo"
    out.mkdir(parents=True, exist_ok=True)

    for name, trace in [("baseline", baseline_trace), ("supervised", guarded_trace)]:
        df = pd.DataFrame(trace)
        df.to_csv(out / f"{name}_trace.csv", index=False)

        plt.figure(figsize=(7, 4))
        plt.plot(df["x"], df["z"], label=name)
        plt.axvline(0, linestyle="--", linewidth=1)
        plt.xlabel("Horizontal offset x")
        plt.ylabel("Altitude z")
        plt.title(f"{name.title()} trajectory — {profile} perception")
        plt.legend()
        plt.tight_layout()
        plt.savefig(out / f"{name}_trajectory.png", dpi=180)
        plt.close()

    print(f"\nSaved demo traces and plots to {out}")


if __name__ == "__main__":
    main()
