from __future__ import annotations

from math import sqrt
import pandas as pd


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total == 0:
        return (0.0, 0.0)
    p = successes / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    margin = (z / denom) * sqrt((p * (1 - p) / total) + (z * z / (4 * total * total)))
    return max(0.0, center - margin), min(1.0, center + margin)


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    group_cols = ["profile", "supervised"]
    for (profile, supervised), g in df.groupby(group_cols, sort=True):
        n = len(g)
        success_count = int(g["success"].sum())
        unsafe_count = int(g["unsafe_touchdown"].sum())
        abort_count = int(g["aborted"].sum())

        success_ci = wilson_interval(success_count, n)
        unsafe_ci = wilson_interval(unsafe_count, n)

        rows.append({
            "profile": profile,
            "controller": "supervised" if supervised else "baseline",
            "episodes": n,
            "success_rate": success_count / n,
            "success_ci_low": success_ci[0],
            "success_ci_high": success_ci[1],
            "unsafe_touchdown_rate": unsafe_count / n,
            "unsafe_ci_low": unsafe_ci[0],
            "unsafe_ci_high": unsafe_ci[1],
            "abort_rate": abort_count / n,
            "mean_final_x_error": g["final_x_error"].mean(),
            "mean_interventions": g["interventions"].mean(),
            "mean_max_risk": g["max_risk"].mean(),
        })
    return pd.DataFrame(rows)
