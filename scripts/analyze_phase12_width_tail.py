from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scripts import run_phase12_adaptive_normalized_conformal as v1
    from scripts import run_phase12_adaptive_normalized_conformal_v2 as v2
except ModuleNotFoundError:
    import run_phase12_adaptive_normalized_conformal as v1
    import run_phase12_adaptive_normalized_conformal_v2 as v2

SEEN_ROLES = {
    "scale_fit": (v1.SCALE_FIT_SEED, v1.SCALE_FIT_FAMILIES, v1.SCALE_FIT_DOMAINS, v1.SCALE_FIT_STRATA),
    "calibration_a": (v1.CAL_A_SEED, v1.CAL_A_FAMILIES, v1.CAL_A_DOMAINS, v1.CAL_A_STRATA),
    "calibration_b": (v1.CAL_B_SEED, v1.CAL_B_FAMILIES, v1.CAL_B_DOMAINS, v1.CAL_B_STRATA),
    "development": (v1.DEV_SEED, v1.DEV_FAMILIES, v1.DEV_DOMAINS, v1.DEV_STRATA),
}
FORBIDDEN_SEEDS = {858858, 869869, v1.TRANSFER_SEED, v1.VALIDATION_SEED, v1.FINAL_SEED}


def _spearman(x: np.ndarray, y: np.ndarray) -> float:
    mask = np.isfinite(x) & np.isfinite(y)
    if int(mask.sum()) < 3:
        return float("nan")
    return float(pd.Series(x[mask]).rank(method="average").corr(pd.Series(y[mask]).rank(method="average")))


def _halfwidth(df: pd.DataFrame, candidate: dict[str, object], axis: str = "lateral") -> np.ndarray:
    groups = v1.p11._groups(df).astype(str).to_numpy()
    scales = v2._scale_values(df, candidate["scale_models"], axis)
    radii = candidate["robust_normalized_radii"]
    multipliers = np.asarray([float(radii[g][axis]["0.95"]) for g in groups], dtype=float)
    return scales * multipliers


def _feature_arrays(df: pd.DataFrame, candidate: dict[str, object]) -> dict[str, np.ndarray]:
    innov_scale = max(float(candidate["innovation_scales"]["lateral"]), 1e-12)
    features = {
        "severity": df["severity"].to_numpy(float),
        "normalized_anchor_innovation_lateral": df["p9_anchor_innovation_lateral_abs"].to_numpy(float) / innov_scale,
        "lateral_gain": df["p9_lateral_gain"].to_numpy(float),
        "lateral_slope_cap_utilization": df["p9_lateral_slope_cap_utilization"].to_numpy(float),
        "continuity_horizon": df["p9_continuity_horizon"].to_numpy(float),
    }
    return features


def _quartile_summary(feature: np.ndarray, error: np.ndarray, hw: np.ndarray) -> list[dict[str, float | int]]:
    mask = np.isfinite(feature) & np.isfinite(error) & np.isfinite(hw)
    if int(mask.sum()) < 40 or np.unique(feature[mask]).size < 4:
        return []
    f = feature[mask]
    e = error[mask]
    w = hw[mask]
    edges = np.unique(np.quantile(f, [0.0, 0.25, 0.50, 0.75, 1.0]))
    if len(edges) < 3:
        return []
    bins = np.digitize(f, edges[1:-1], right=True)
    out = []
    for b in range(len(edges) - 1):
        m = bins == b
        if int(m.sum()) == 0:
            continue
        p95e = float(np.percentile(e[m], 95))
        p95w = float(np.percentile(w[m], 95))
        out.append({
            "rows": int(m.sum()),
            "feature_min": float(np.min(f[m])),
            "feature_max": float(np.max(f[m])),
            "p95_error": p95e,
            "p95_halfwidth": p95w,
            "coverage95": float(np.mean(e[m] <= w[m])),
            "width_over_error": p95w / p95e if p95e > 0 else float("nan"),
        })
    return out


def _summarize_role(df: pd.DataFrame, candidate: dict[str, object]) -> dict[str, object]:
    available = v1.p11._available(df)
    d = df[available].copy()
    d["phase12_group"] = v1.p11._groups(d).astype(str)
    err = d["p14_lateral_abs_error_m"].to_numpy(float)
    hw = _halfwidth(d, candidate)
    features = _feature_arrays(d, candidate)

    groups: dict[str, object] = {}
    for group in v1.GROUPS:
        m = d["phase12_group"].to_numpy(str) == group
        ge = err[m]
        gw = hw[m]
        groups[group] = {
            "rows": int(m.sum()),
            "p95_error": float(np.percentile(ge, 95)),
            "p95_halfwidth": float(np.percentile(gw, 95)),
            "coverage95": float(np.mean(ge <= gw)),
            "median_halfwidth": float(np.median(gw)),
            "max_halfwidth": float(np.max(gw)),
        }

    p95w = float(np.percentile(hw, 95))
    top_width = hw >= p95w
    p95e = float(np.percentile(err, 95))
    top_error = err >= p95e
    top_group_counts = pd.Series(d.loc[top_width, "phase12_group"]).value_counts().to_dict()

    continuity = d["phase12_group"].isin({v1.p11.GROUP_H3, v1.p11.GROUP_H45, v1.p11.GROUP_H67}).to_numpy()
    ce = err[continuity]
    cw = hw[continuity]
    cfeatures = {name: values[continuity] for name, values in features.items()}
    feature_stats = {}
    for name, values in cfeatures.items():
        feature_stats[name] = {
            "spearman_abs_error": _spearman(values, ce),
            "spearman_halfwidth": _spearman(values, cw),
            "quartiles": _quartile_summary(values, ce, cw),
        }

    return {
        "rows": int(len(d)),
        "overall_p95_error": p95e,
        "overall_p95_halfwidth": p95w,
        "overall_width_over_error": p95w / p95e,
        "groups": groups,
        "top5_width_group_counts": {str(k): int(v) for k, v in top_group_counts.items()},
        "top5_width_rows": int(top_width.sum()),
        "top5_error_rows": int(top_error.sum()),
        "top5_width_error_overlap_rows": int(np.sum(top_width & top_error)),
        "top5_width_error_overlap_fraction": float(np.sum(top_width & top_error) / max(1, top_width.sum())),
        "continuity_feature_stats": feature_stats,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Phase 12 permanently-seen width-tail diagnostics")
    p.add_argument("--predecessor", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--git-sha")
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    if any(seed in FORBIDDEN_SEEDS for seed, *_ in SEEN_ROLES.values()):
        raise RuntimeError("forbidden evidence seed configured in Phase 12 forensic roles")

    candidate = v2._build_candidate(args.predecessor, args.git_sha)
    results: dict[str, object] = {
        "schema": "aegisland.phase12.width-tail-forensics.v1",
        "scientific_git_sha": args.git_sha,
        "simulation_only": True,
        "development_only": True,
        "forbidden_seeds_untouched": sorted(FORBIDDEN_SEEDS),
        "candidate_schema": candidate["schema"],
        "candidate_method": candidate["method"],
        "calibration_95_environment_dominance": {},
        "roles": {},
    }

    for group in v1.GROUPS:
        a = float(candidate["normalized_radii_calibration_a"][group]["lateral"]["0.95"])
        b = float(candidate["normalized_radii_calibration_b"][group]["lateral"]["0.95"])
        results["calibration_95_environment_dominance"][group] = {
            "calibration_a": a,
            "calibration_b": b,
            "max_over_min": max(a, b) / min(a, b),
            "dominant": "a" if a >= b else "b",
        }

    for role, (seed, families, domains, strata) in SEEN_ROLES.items():
        frame = v1._event(f"phase12_forensics_{role}", seed, families, domains, strata, candidate)
        results["roles"][role] = _summarize_role(frame, candidate)

    path = args.out / "phase12_width_tail_forensics.json"
    path.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "schema": results["schema"],
        "development_width_over_error": results["roles"]["development"]["overall_width_over_error"],
        "development_top5_width_group_counts": results["roles"]["development"]["top5_width_group_counts"],
        "development_top5_width_error_overlap_fraction": results["roles"]["development"]["top5_width_error_overlap_fraction"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
