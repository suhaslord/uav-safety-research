from __future__ import annotations

from pathlib import Path
import argparse

import pandas as pd

from uav_safety.config import SimConfig


def analyze(episodes: pd.DataFrame) -> pd.DataFrame:
    cfg = SimConfig()
    rows: list[dict] = []
    for (condition, architecture), group in episodes.groupby(["condition", "architecture"], sort=True):
        unsafe = group[group["unsafe_touchdown"]]
        rows.append({
            "condition": condition,
            "architecture": architecture,
            "episodes": len(group),
            "unsafe_touchdowns": len(unsafe),
            "lateral_failures": int((unsafe["final_x_error"] > cfg.touchdown_x_tolerance).sum()),
            "horizontal_speed_failures": int((unsafe["final_vx"].abs() > cfg.touchdown_vx_limit).sum()),
            "vertical_speed_failures": int((unsafe["final_vz"].abs() > cfg.touchdown_vz_limit).sum()),
            "mean_unsafe_x_error": float(unsafe["final_x_error"].mean()) if len(unsafe) else 0.0,
            "mean_unsafe_abs_vx": float(unsafe["final_vx"].abs().mean()) if len(unsafe) else 0.0,
            "mean_unsafe_abs_vz": float(unsafe["final_vz"].abs().mean()) if len(unsafe) else 0.0,
        })
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Decompose Phase 6 unsafe touchdowns by failed safety criterion.")
    parser.add_argument("--results", type=Path, default=Path("results/phase6_image_landing"))
    args = parser.parse_args()

    episodes_path = args.results / "episodes.csv"
    if not episodes_path.exists():
        raise FileNotFoundError(f"Missing {episodes_path}")

    episodes = pd.read_csv(episodes_path)
    analysis = analyze(episodes)
    analysis.to_csv(args.results / "failure_decomposition.csv", index=False)
    (args.results / "failure_decomposition.md").write_text(
        "# Phase 6 touchdown failure decomposition\n\n"
        "Counts are not mutually exclusive: one unsafe touchdown may violate more "
        "than one simulated touchdown criterion.\n\n"
        + analysis.to_markdown(index=False)
        + "\n",
        encoding="utf-8",
    )
    print(analysis.to_string(index=False))


if __name__ == "__main__":
    main()
