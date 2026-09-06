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

CANDIDATE_SCHEMA = "aegisland.phase12.adaptive-normalized-conformal.candidate.v3"
METHOD = "continuity_lateral_innovation_residual_normalized_robust_conformal"
RELIABILITY_GROUPS = (v1.p11.GROUP_H3, v1.p11.GROUP_H45, v1.p11.GROUP_H67)
RELIABILITY_AXIS = "lateral"
RELIABILITY_MIN_TAIL_ROWS = 10


def _reliability_coordinate(df: pd.DataFrame, innovation_scale: float) -> np.ndarray:
    scale = float(innovation_scale)
    if not np.isfinite(scale) or scale <= 0.0:
        raise RuntimeError("Phase 12 iteration-3 lateral innovation scale must be positive and finite")
    raw = df["p9_anchor_innovation_lateral_abs"].to_numpy(float)
    if not np.all(np.isfinite(raw)) or np.any(raw < 0.0):
        raise RuntimeError("Phase 12 iteration-3 anchor innovation must be finite and nonnegative")
    return np.log1p(raw / scale)


def _fit_reliability_models(
    scale_fit: pd.DataFrame,
    scale_models: dict[str, object],
    innovation_scale: float,
) -> dict[str, object]:
    d = scale_fit[v1.p11._available(scale_fit)].copy()
    d["phase12_group"] = v1.p11._groups(d).astype(str)
    models: dict[str, object] = {}

    for group in RELIABILITY_GROUPS:
        gd = d[d["phase12_group"] == group].copy()
        if gd.empty:
            raise RuntimeError(f"Phase 12 iteration-3 empty reliability group {group}")

        u = _reliability_coordinate(gd, innovation_scale)
        baseline = v2._scale_values(gd, scale_models, RELIABILITY_AXIS)
        error = gd["p14_lateral_abs_error_m"].to_numpy(float)
        residual = error / baseline

        if not np.all(np.isfinite(baseline)) or np.any(baseline <= 0.0):
            raise RuntimeError(f"Phase 12 iteration-3 invalid baseline scale in {group}")
        if not np.all(np.isfinite(error)) or np.any(error < 0.0):
            raise RuntimeError(f"Phase 12 iteration-3 invalid scale-fit error in {group}")
        if not np.all(np.isfinite(residual)) or np.any(residual < 0.0):
            raise RuntimeError(f"Phase 12 iteration-3 invalid residual in {group}")

        u10, u90 = np.quantile(u, [0.10, 0.90])
        u33, u67 = np.quantile(u, [1.0 / 3.0, 2.0 / 3.0])
        if not np.isfinite(u10) or not np.isfinite(u90) or u90 <= u10:
            raise RuntimeError(f"Phase 12 iteration-3 invalid innovation anchors for {group}: {u10}, {u90}")

        low_mask = u <= u33
        high_mask = u >= u67
        if int(np.sum(low_mask)) < RELIABILITY_MIN_TAIL_ROWS or int(np.sum(high_mask)) < RELIABILITY_MIN_TAIL_ROWS:
            raise RuntimeError(f"Phase 12 iteration-3 underpowered innovation tails for {group}")

        low = float(np.median(residual[low_mask]))
        high_raw = float(np.median(residual[high_mask]))
        if not np.isfinite(low) or low <= 0.0 or not np.isfinite(high_raw) or high_raw < 0.0:
            raise RuntimeError(f"Phase 12 iteration-3 invalid residual anchors for {group}")
        high = max(high_raw, low)
        center = float(np.sqrt(low * high))
        if not np.isfinite(center) or center <= 0.0:
            raise RuntimeError(f"Phase 12 iteration-3 invalid reliability center for {group}")

        models[group] = {
            "coordinate": "log1p(p9_anchor_innovation_lateral_abs / frozen_lateral_innovation_scale)",
            "u10": float(u10),
            "u90": float(u90),
            "residual_low": low,
            "residual_high": high,
            "residual_high_raw": high_raw,
            "geometric_center": center,
            "rows": int(len(gd)),
            "low_tail_rows": int(np.sum(low_mask)),
            "high_tail_rows": int(np.sum(high_mask)),
        }
    return models


def _scale_values(
    df: pd.DataFrame,
    scale_models: dict[str, object],
    reliability_models: dict[str, object],
    innovation_scale: float,
    axis: str,
) -> np.ndarray:
    baseline = v2._scale_values(df, scale_models, axis)
    if axis != RELIABILITY_AXIS:
        return baseline

    groups = v1.p11._groups(df).astype(str).to_numpy()
    u = _reliability_coordinate(df, innovation_scale)
    out = baseline.copy()

    for i, group in enumerate(groups):
        if group not in RELIABILITY_GROUPS:
            continue
        model = reliability_models[group]
        u10 = float(model["u10"])
        u90 = float(model["u90"])
        low = float(model["residual_low"])
        high = float(model["residual_high"])
        center = float(model["geometric_center"])
        t = float(np.clip((u[i] - u10) / (u90 - u10), 0.0, 1.0))
        raw_factor = low + t * (high - low)
        factor = raw_factor / center
        out[i] = baseline[i] * factor

    if not np.all(np.isfinite(out)) or np.any(out <= 0.0):
        raise RuntimeError("Phase 12 iteration-3 produced nonpositive or non-finite scale")
    return out


def _fit_normalized_radii(
    df: pd.DataFrame,
    scale_models: dict[str, object],
    reliability_models: dict[str, object],
    innovation_scale: float,
    label: str,
) -> tuple[dict[str, object], dict[str, int]]:
    counts = v1.p11._group_counts(df)
    v1.p11._assert_minimums(counts, v1.CAL_MINIMUMS, label)

    d = df[v1.p11._available(df)].copy()
    d["phase12_group"] = v1.p11._groups(d).astype(str)
    radii: dict[str, object] = {}

    for group in v1.GROUPS:
        gd = d[d["phase12_group"] == group]
        radii[group] = {}
        for axis in ("lateral", "altitude"):
            error = gd[f"p14_{axis}_abs_error_m"].to_numpy(float)
            scale = _scale_values(gd, scale_models, reliability_models, innovation_scale, axis)
            score = error / scale
            raw = [v1.p11.p9._finite_conformal(score, q) for q in v1.TARGETS]
            nested = np.maximum.accumulate(np.asarray(raw, dtype=float))
            if not np.all(np.isfinite(nested)) or np.any(nested < 0.0):
                raise RuntimeError(f"Phase 12 iteration-3 invalid conformal radii for {group}/{axis}")
            radii[group][axis] = {
                f"{q:.2f}": float(nested[i]) for i, q in enumerate(v1.TARGETS)
            }
    return radii, counts


def _build_candidate(predecessor_path: Path, git_sha: str | None) -> dict[str, object]:
    predecessor = v1._load_json(predecessor_path)
    for key in ("velocity_caps", "innovation_scales"):
        if key not in predecessor:
            raise RuntimeError(f"Phase 12 iteration-3 predecessor is missing required key {key}")

    base = {
        "velocity_caps": predecessor["velocity_caps"],
        "innovation_scales": predecessor["innovation_scales"],
    }
    scale_fit = v1._event(
        "phase12_v3_scale_fit",
        v1.SCALE_FIT_SEED,
        v1.SCALE_FIT_FAMILIES,
        v1.SCALE_FIT_DOMAINS,
        v1.SCALE_FIT_STRATA,
        base,
    )
    cal_a = v1._event(
        "phase12_v3_calibration_a",
        v1.CAL_A_SEED,
        v1.CAL_A_FAMILIES,
        v1.CAL_A_DOMAINS,
        v1.CAL_A_STRATA,
        base,
    )
    cal_b = v1._event(
        "phase12_v3_calibration_b",
        v1.CAL_B_SEED,
        v1.CAL_B_FAMILIES,
        v1.CAL_B_DOMAINS,
        v1.CAL_B_STRATA,
        base,
    )

    scale_models, scale_counts = v1._fit_scale_models(scale_fit)
    lateral_innovation_scale = float(predecessor["innovation_scales"]["lateral"])
    reliability_models = _fit_reliability_models(scale_fit, scale_models, lateral_innovation_scale)
    rad_a, cal_a_counts = _fit_normalized_radii(
        cal_a,
        scale_models,
        reliability_models,
        lateral_innovation_scale,
        "phase12 iteration-3 calibration A",
    )
    rad_b, cal_b_counts = _fit_normalized_radii(
        cal_b,
        scale_models,
        reliability_models,
        lateral_innovation_scale,
        "phase12 iteration-3 calibration B",
    )
    robust = v1._max_envelope(rad_a, rad_b)
    severity_thresholds = v1.p11._severity_thresholds(cal_a, cal_b)

    return {
        "schema": CANDIDATE_SCHEMA,
        "method": METHOD,
        "development_iteration": 3,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "scientific_git_sha": git_sha,
        "predecessor_candidate_sha256": v1._sha256_file(predecessor_path),
        "predecessor_phase": "phase11_p14r_closed",
        "point_estimator": "unchanged_phase11_p14r",
        "velocity_caps": predecessor["velocity_caps"],
        "innovation_scales": predecessor["innovation_scales"],
        "scale_models": scale_models,
        "continuity_scale_shrinkage_exponent": v2.CONTINUITY_SCALE_SHRINKAGE,
        "lateral_reliability_coordinate": "log1p_normalized_anchor_innovation",
        "lateral_reliability_models": reliability_models,
        "normalized_radii_calibration_a": rad_a,
        "normalized_radii_calibration_b": rad_b,
        "robust_normalized_radii": robust,
        "high_severity_thresholds": severity_thresholds,
        "group_counts": {
            "scale_fit": scale_counts,
            "calibration_a": cal_a_counts,
            "calibration_b": cal_b_counts,
        },
        "seeds": {
            "scale_fit": v1.SCALE_FIT_SEED,
            "calibration_a": v1.CAL_A_SEED,
            "calibration_b": v1.CAL_B_SEED,
            "development_smoke": v1.DEV_SEED,
            "seen_transfer": v1.TRANSFER_SEED,
            "protected_validation": v1.VALIDATION_SEED,
            "final_holdout": v1.FINAL_SEED,
        },
        "phase11_protected_seed_forbidden": 858858,
        "phase11_retired_p15_v2_seed_forbidden": 869869,
    }


def _halfwidths(df: pd.DataFrame, candidate: dict[str, object], axis: str, q: float) -> np.ndarray:
    groups = v1.p11._groups(df).astype(str).to_numpy()
    scale = _scale_values(
        df,
        candidate["scale_models"],
        candidate["lateral_reliability_models"],
        float(candidate["innovation_scales"]["lateral"]),
        axis,
    )
    key = f"{q:.2f}"
    table = candidate["robust_normalized_radii"]
    multipliers = np.asarray([float(table[g][axis][key]) for g in groups], dtype=float)
    out = scale * multipliers
    if not np.all(np.isfinite(out)) or np.any(out < 0.0):
        raise RuntimeError("Phase 12 iteration-3 produced invalid interval half-width")
    return out


def _summarize(
    df: pd.DataFrame,
    candidate: dict[str, object],
    role: str,
    seed: int,
    minimums: dict[str, int],
) -> dict[str, object]:
    original = v1.p11._halfwidths
    v1.p11._halfwidths = _halfwidths
    try:
        return v1.p11.summarize(df, candidate, role, seed, minimums)
    finally:
        v1.p11._halfwidths = original


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Phase 12 iteration 3: lateral innovation-residual normalized robust conformal"
    )
    p.add_argument("--stage", choices=("freeze", "dev", "transfer", "validation", "final"), required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--predecessor", type=Path)
    p.add_argument("--candidate", type=Path)
    p.add_argument("--git-sha")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    if args.stage == "freeze":
        if args.predecessor is None:
            raise SystemExit("--predecessor is required for --stage freeze")
        candidate = _build_candidate(args.predecessor, args.git_sha)
        path = args.out / "candidate_freeze.json"
        path.write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("PHASE12_V3_CANDIDATE_SHA256=" + v1._sha256_file(path))
        print("PHASE12_V3_SCALE_COUNTS=" + json.dumps(candidate["group_counts"], sort_keys=True))
        print("PHASE12_V3_RELIABILITY_MODELS=" + json.dumps(candidate["lateral_reliability_models"], sort_keys=True))
        return

    if args.candidate is None:
        raise SystemExit("--candidate is required for evaluation stages")
    candidate = v1._load_json(args.candidate)
    if candidate.get("schema") != CANDIDATE_SCHEMA:
        raise RuntimeError("unexpected Phase 12 iteration-3 candidate schema")
    if float(candidate.get("continuity_scale_shrinkage_exponent", -1.0)) != v2.CONTINUITY_SCALE_SHRINKAGE:
        raise RuntimeError("Phase 12 iteration-3 continuity shrinkage mismatch")
    if candidate.get("lateral_reliability_coordinate") != "log1p_normalized_anchor_innovation":
        raise RuntimeError("Phase 12 iteration-3 reliability-coordinate mismatch")

    seed, families, domains, strata, minimums, filename = v1._stage_config(args.stage)
    df = v1._event(f"phase12_v3_{args.stage}", seed, families, domains, strata, candidate)
    result = _summarize(df, candidate, f"phase12_v3_{args.stage}", seed, minimums)
    result["schema"] = f"aegisland.phase12.v3.{args.stage}-result.v1"
    result["candidate_sha256"] = v1._sha256_file(args.candidate)
    result["scientific_git_sha"] = args.git_sha
    result["simulation_only"] = True
    result["safety_acceptance"] = False
    result["controller_tuning_allowed"] = False
    result["continuity_scale_shrinkage_exponent"] = v2.CONTINUITY_SCALE_SHRINKAGE
    result["lateral_reliability_coordinate"] = "log1p_normalized_anchor_innovation"
    if args.stage == "dev":
        result["development_only"] = True
        result["eligible_for_progression"] = False

    (args.out / "candidate_freeze.json").write_text(
        args.candidate.read_text(encoding="utf-8"), encoding="utf-8"
    )
    result_path = args.out / filename
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PHASE12_V3_{args.stage.upper()}_RESULT_SHA256=" + v1._sha256_file(result_path))
    print(
        f"PHASE12_V3_{args.stage.upper()}_ALL_PRIMARY_GATES_PASS="
        + str(bool(result.get("all_primary_gates_pass", False))).lower()
    )
    print(json.dumps(result.get("gates", {}), sort_keys=True))


if __name__ == "__main__":
    main()
