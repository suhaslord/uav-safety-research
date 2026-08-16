from __future__ import annotations

import argparse
import json
import math
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scripts import run_phase11_p8_innovation_clipped_continuity as p8
except ModuleNotFoundError:
    import run_phase11_p8_innovation_clipped_continuity as p8

p1 = p8.p1

FIT_SEED = 407407
CALIBRATION_SEED = 418418
TRANSFER_SEED = 429429
VALIDATION_SEED = 440440
FRAMES_PER_SEQUENCE = 60
TARGETS = (0.50, 0.68, 0.80, 0.90, 0.95)
MAX_CONTINUITY_GAP = 7
DAMPING = 0.85
VELOCITY_CAP_QUANTILE = 0.99
INNOVATION_SCALE_QUANTILE = 0.95
SOFT_SCALE_MULTIPLIER = 3.0
BLEND_PREVIOUS_SLOPE = 0.5
BLEND_SOFT_UPDATED_SLOPE = 0.5

FIT_FAMILIES = tuple(range(150, 156))
CALIBRATION_FAMILIES = tuple(range(156, 168))
TRANSFER_FAMILIES = tuple(range(168, 178))
VALIDATION_FAMILIES = tuple(range(178, 188))

FIT_DOMAINS = p8.FIT_DOMAINS
CALIBRATION_DOMAINS = (
    "edge+temporal_dropout",
    "small_scale+temporal_dropout",
    "oblique+temporal_dropout",
    "dim+temporal_dropout",
    "blur_noise+temporal_dropout",
    "low_contrast+temporal_dropout",
    "edge+small_scale+temporal_dropout",
    "oblique+dim+temporal_dropout",
)
TRANSFER_DOMAINS = (
    "edge+blur_noise+temporal_dropout",
    "small_scale+dim+temporal_dropout",
    "oblique+low_contrast+temporal_dropout",
    "dim+blur_noise+temporal_dropout",
    "edge+oblique+temporal_dropout",
    "small_scale+blur_noise+low_contrast+temporal_dropout",
    "edge+dim+low_contrast+temporal_dropout",
    "small_scale+oblique+blur_noise+temporal_dropout",
)
VALIDATION_DOMAINS = (
    "edge+low_contrast+temporal_dropout",
    "small_scale+oblique+temporal_dropout",
    "dim+low_contrast+temporal_dropout",
    "blur_noise+low_contrast+temporal_dropout",
    "edge+small_scale+oblique+temporal_dropout",
    "edge+oblique+dim+blur_noise+temporal_dropout",
    "small_scale+dim+blur_noise+low_contrast+temporal_dropout",
    "edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout",
)

GROUP_BASE = "base_output"
GROUP_H3 = "continuity_h3"
GROUP_H45 = "continuity_h45"
GROUP_H67 = "continuity_h67"
GROUPS = (GROUP_BASE, GROUP_H3, GROUP_H45, GROUP_H67)

CALIBRATION_MINIMUMS = {
    GROUP_BASE: 1000,
    GROUP_H3: 120,
    GROUP_H45: 60,
    GROUP_H67: 30,
}
TRANSFER_MINIMUMS = {
    GROUP_BASE: 800,
    GROUP_H3: 100,
    GROUP_H45: 50,
    GROUP_H67: 20,
}


def _raw(name: str, seed: int, families: tuple[int, ...], domains: tuple[str, ...]) -> pd.DataFrame:
    return p1.generate_split(name, seed, families, domains, frames=FRAMES_PER_SEQUENCE)


def _fit_velocity_caps(raw_fit: pd.DataFrame) -> dict[str, float]:
    values: dict[str, list[float]] = {"lateral": [], "altitude": []}
    for _, group in raw_fit.groupby("sequence_id"):
        genuine = group[group["candidate_available"]].sort_values("frame_index")
        rows = list(genuine.itertuples(index=False))
        for a, b in zip(rows, rows[1:]):
            dt = int(b.frame_index) - int(a.frame_index)
            if dt <= 0:
                continue
            values["lateral"].append(abs((float(b.estimate_lateral_x_m) - float(a.estimate_lateral_x_m)) / dt))
            values["altitude"].append(abs((float(b.estimate_altitude_m) - float(a.estimate_altitude_m)) / dt))
    result: dict[str, float] = {}
    for axis in ("lateral", "altitude"):
        arr = np.asarray(values[axis], dtype=float)
        arr = arr[np.isfinite(arr)]
        if not arr.size:
            raise RuntimeError(f"no finite P9 {axis} genuine-anchor slopes")
        result[axis] = float(max(1e-6, np.quantile(arr, VELOCITY_CAP_QUANTILE)))
    return result


def _fit_innovation_scales(raw_fit: pd.DataFrame, velocity_caps: dict[str, float]) -> dict[str, float]:
    values: dict[str, list[float]] = {"lateral": [], "altitude": []}
    for _, group in raw_fit.groupby("sequence_id"):
        genuine = group[group["candidate_available"]].sort_values("frame_index")
        anchors: list[tuple[int, float, float]] = []
        for row in genuine.itertuples(index=False):
            current = (int(row.frame_index), float(row.estimate_lateral_x_m), float(row.estimate_altitude_m))
            if len(anchors) >= 2:
                a, b = anchors[-2:]
                dt = b[0] - a[0]
                forward = current[0] - b[0]
                if dt > 0 and forward > 0:
                    m_lat = float(np.clip((b[1] - a[1]) / dt, -velocity_caps["lateral"], velocity_caps["lateral"]))
                    m_alt = float(np.clip((b[2] - a[2]) / dt, -velocity_caps["altitude"], velocity_caps["altitude"]))
                    pred_lat = b[1] + m_lat * forward
                    pred_alt = b[2] + m_alt * forward
                    values["lateral"].append(abs(current[1] - pred_lat))
                    values["altitude"].append(abs(current[2] - pred_alt))
            anchors.append(current)
            anchors = anchors[-3:]
    result: dict[str, float] = {}
    for axis in ("lateral", "altitude"):
        arr = np.asarray(values[axis], dtype=float)
        arr = arr[np.isfinite(arr)]
        if not arr.size:
            raise RuntimeError(f"no finite P9 {axis} innovations")
        result[axis] = float(max(1e-6, np.quantile(arr, INNOVATION_SCALE_QUANTILE)))
    return result


def _axis_state(values: list[tuple[int, float]], velocity_cap: float, innovation_scale: float) -> dict[str, float | bool]:
    if not values:
        return {"state": float("nan"), "slope": 0.0, "innovation_abs": 0.0, "innovation_available": False, "gain": 1.0, "slope_utilization": 0.0}
    if len(values) == 1:
        return {"state": float(values[-1][1]), "slope": 0.0, "innovation_abs": 0.0, "innovation_available": False, "gain": 1.0, "slope_utilization": 0.0}
    recent = values[-3:]
    if len(recent) == 2:
        a, b = recent
        dt = b[0] - a[0]
        raw = (b[1] - a[1]) / dt if dt > 0 else 0.0
        slope = float(np.clip(raw, -velocity_cap, velocity_cap))
        return {
            "state": float(b[1]), "slope": slope, "innovation_abs": 0.0,
            "innovation_available": False, "gain": 1.0,
            "slope_utilization": min(1.0, abs(slope) / max(velocity_cap, 1e-9)),
        }
    a, b, c = recent
    dt_prev = b[0] - a[0]
    dt_new = c[0] - b[0]
    if dt_prev <= 0 or dt_new <= 0:
        return {"state": float(c[1]), "slope": 0.0, "innovation_abs": 0.0, "innovation_available": False, "gain": 1.0, "slope_utilization": 0.0}
    m_prev = float(np.clip((b[1] - a[1]) / dt_prev, -velocity_cap, velocity_cap))
    pred_c = b[1] + m_prev * dt_new
    innovation = float(c[1] - pred_c)
    scale = max(float(innovation_scale), 1e-9)
    denom = SOFT_SCALE_MULTIPLIER * scale
    e_soft = float(innovation / math.sqrt(1.0 + (innovation / denom) ** 2))
    gain = float(e_soft / innovation) if abs(innovation) > 1e-12 else 1.0
    state = float(pred_c + e_soft)
    m_latest = (state - b[1]) / dt_new
    blended = BLEND_PREVIOUS_SLOPE * m_prev + BLEND_SOFT_UPDATED_SLOPE * m_latest
    slope = float(np.clip(blended, -velocity_cap, velocity_cap))
    return {
        "state": state, "slope": slope, "innovation_abs": abs(innovation),
        "innovation_available": True, "gain": gain,
        "slope_utilization": min(1.0, abs(slope) / max(velocity_cap, 1e-9)),
    }


def _damped_steps(horizon: int) -> float:
    return float(sum(DAMPING**k for k in range(horizon)))


def add_p9_continuity(raw: pd.DataFrame, velocity_caps: dict[str, float], innovation_scales: dict[str, float]) -> pd.DataFrame:
    out = p1.add_reliability_state(p1.add_temporal_bridge(raw, max_gap=2)).copy()
    out["p9_available"] = out["p1_available"].astype(bool)
    out["p9_estimate_lateral_x_m"] = out["p1_estimate_lateral_x_m"]
    out["p9_estimate_altitude_m"] = out["p1_estimate_altitude_m"]
    out["p9_source"] = out["p1_source"].fillna("")
    out["p9_continuity_horizon"] = out["bridge_horizon"].astype(int)
    out["p9_anchor_innovation_lateral_abs"] = 0.0
    out["p9_anchor_innovation_altitude_abs"] = 0.0
    out["p9_anchor_innovation_available"] = False
    out["p9_lateral_gain"] = 1.0
    out["p9_altitude_gain"] = 1.0
    out["p9_lateral_slope_cap_utilization"] = 0.0
    out["p9_altitude_slope_cap_utilization"] = 0.0
    out["p9_unavailable_reason"] = ""

    for _, indices in out.groupby("sequence_id").groups.items():
        ordered = sorted(indices, key=lambda idx: int(out.loc[idx, "frame_index"]))
        anchors: list[tuple[int, float, float]] = []
        for idx in ordered:
            frame = int(out.loc[idx, "frame_index"])
            genuine = bool(out.loc[idx, "candidate_available"])
            if genuine:
                anchors.append((frame, float(out.loc[idx, "estimate_lateral_x_m"]), float(out.loc[idx, "estimate_altitude_m"])))
                anchors = anchors[-3:]

            lat = _axis_state([(a[0], a[1]) for a in anchors], velocity_caps["lateral"], innovation_scales["lateral"])
            alt = _axis_state([(a[0], a[2]) for a in anchors], velocity_caps["altitude"], innovation_scales["altitude"])
            out.loc[idx, "p9_anchor_innovation_lateral_abs"] = lat["innovation_abs"]
            out.loc[idx, "p9_anchor_innovation_altitude_abs"] = alt["innovation_abs"]
            out.loc[idx, "p9_anchor_innovation_available"] = bool(lat["innovation_available"] and alt["innovation_available"])
            out.loc[idx, "p9_lateral_gain"] = lat["gain"]
            out.loc[idx, "p9_altitude_gain"] = alt["gain"]
            out.loc[idx, "p9_lateral_slope_cap_utilization"] = lat["slope_utilization"]
            out.loc[idx, "p9_altitude_slope_cap_utilization"] = alt["slope_utilization"]

            if genuine or bool(out.loc[idx, "p1_available"]):
                continue
            if len(anchors) < 2:
                out.loc[idx, "p9_unavailable_reason"] = "insufficient_anchors"
                continue
            horizon = frame - anchors[-1][0]
            if horizon <= 2:
                continue
            if horizon > MAX_CONTINUITY_GAP:
                out.loc[idx, "p9_unavailable_reason"] = "gap_beyond_horizon"
                continue
            step_sum = _damped_steps(horizon)
            out.loc[idx, "p9_available"] = True
            out.loc[idx, "p9_estimate_lateral_x_m"] = float(lat["state"]) + float(lat["slope"]) * step_sum
            out.loc[idx, "p9_estimate_altitude_m"] = float(alt["state"]) + float(alt["slope"]) * step_sum
            out.loc[idx, "p9_source"] = "soft_innovation_continuity"
            out.loc[idx, "p9_continuity_horizon"] = horizon

    out["p9_lateral_abs_error_m"] = np.abs(out["p9_estimate_lateral_x_m"] - out["truth_lateral_x_m"])
    out["p9_altitude_abs_error_m"] = np.abs(out["p9_estimate_altitude_m"] - out["truth_altitude_m"])
    return out


def _available(df: pd.DataFrame) -> pd.Series:
    return df["p9_available"].astype(bool) & df["truth_visible"].astype(bool)


def _group_series(df: pd.DataFrame) -> pd.Series:
    source = df["p9_source"].fillna("").astype(str)
    h = df["p9_continuity_horizon"].astype(int)
    values = np.full(len(df), GROUP_BASE, dtype=object)
    continuity = source.to_numpy() == "soft_innovation_continuity"
    values[continuity & (h.to_numpy() == 3)] = GROUP_H3
    values[continuity & np.isin(h.to_numpy(), [4, 5])] = GROUP_H45
    values[continuity & np.isin(h.to_numpy(), [6, 7])] = GROUP_H67
    return pd.Series(values, index=df.index, dtype="object")


def _finite_conformal(values: np.ndarray | pd.Series, q: float) -> float:
    arr = np.asarray(values, dtype=float)
    arr = np.sort(arr[np.isfinite(arr)])
    if not arr.size:
        return float("nan")
    k = int(math.ceil((arr.size + 1) * q))
    return float(arr[min(arr.size - 1, max(0, k - 1))])


def _fit_direct_radii(calibration: pd.DataFrame) -> tuple[dict[str, dict[str, dict[str, float]]], dict[str, int]]:
    d = calibration[_available(calibration)].copy()
    d["p9_group"] = _group_series(d)
    counts = {group: int((d["p9_group"] == group).sum()) for group in GROUPS}
    for group, minimum in CALIBRATION_MINIMUMS.items():
        if counts[group] < minimum:
            raise RuntimeError(f"P9 calibration group {group} rows {counts[group]} < {minimum}")
    radii: dict[str, dict[str, dict[str, float]]] = {}
    for group in GROUPS:
        gd = d[d["p9_group"] == group]
        radii[group] = {}
        for axis in ("lateral", "altitude"):
            errors = gd[f"p9_{axis}_abs_error_m"].to_numpy(float)
            raw = [_finite_conformal(errors, q) for q in TARGETS]
            nested = np.maximum.accumulate(np.asarray(raw, dtype=float))
            radii[group][axis] = {f"{q:.2f}": float(nested[i]) for i, q in enumerate(TARGETS)}
    return radii, counts


def _build_candidate(fit_raw: pd.DataFrame, calibration_raw: pd.DataFrame, git_sha: str) -> tuple[dict[str, object], pd.DataFrame]:
    velocity_caps = _fit_velocity_caps(fit_raw)
    innovation_scales = _fit_innovation_scales(fit_raw, velocity_caps)
    calibration = add_p9_continuity(calibration_raw, velocity_caps, innovation_scales)
    radii, counts = _fit_direct_radii(calibration)
    candidate = {
        "schema": "aegisland.phase11.p9.candidate-freeze.v1",
        "git_sha": git_sha,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "fit_seed": FIT_SEED,
        "calibration_seed": CALIBRATION_SEED,
        "transfer_seed_unseen_at_freeze": TRANSFER_SEED,
        "validation_seed_unseen_at_freeze": VALIDATION_SEED,
        "fit_families": list(FIT_FAMILIES),
        "calibration_families": list(CALIBRATION_FAMILIES),
        "transfer_families": list(TRANSFER_FAMILIES),
        "validation_families": list(VALIDATION_FAMILIES),
        "continuity_constants": {
            "max_continuity_gap": MAX_CONTINUITY_GAP,
            "damping": DAMPING,
            "velocity_cap_quantile": VELOCITY_CAP_QUANTILE,
            "innovation_scale_quantile": INNOVATION_SCALE_QUANTILE,
            "soft_scale_multiplier": SOFT_SCALE_MULTIPLIER,
            "blend_previous_slope": BLEND_PREVIOUS_SLOPE,
            "blend_soft_updated_slope": BLEND_SOFT_UPDATED_SLOPE,
        },
        "velocity_caps": velocity_caps,
        "innovation_scales": innovation_scales,
        "groups": list(GROUPS),
        "calibration_minimums": CALIBRATION_MINIMUMS,
        "transfer_minimums": TRANSFER_MINIMUMS,
        "calibration_group_rows": counts,
        "direct_conformal_radii": radii,
    }
    return candidate, calibration


def _halfwidths(df: pd.DataFrame, candidate: dict[str, object], axis: str, q: float) -> np.ndarray:
    groups = _group_series(df).to_numpy(str)
    table = candidate["direct_conformal_radii"]
    return np.asarray([float(table[group][axis][f"{q:.2f}"]) for group in groups], dtype=float)


def _coverage(df: pd.DataFrame, candidate: dict[str, object]) -> dict[str, dict[str, float]]:
    d = df[_available(df)].copy()
    result: dict[str, dict[str, float]] = {}
    for axis in ("lateral", "altitude"):
        err = d[f"p9_{axis}_abs_error_m"].to_numpy(float)
        result[axis] = {}
        for q in TARGETS:
            hw = _halfwidths(d, candidate, axis, q)
            result[axis][f"{q:.2f}"] = float(np.mean(err <= hw)) if err.size else float("nan")
    return result


def _subset_stats(df: pd.DataFrame, candidate: dict[str, object], groups: set[str]) -> dict[str, object]:
    group_series = _group_series(df)
    d = df[_available(df) & group_series.isin(groups)].copy()
    result: dict[str, object] = {"rows": int(len(d)), "coverage_95": {}, "p95_error": {}, "p95_halfwidth": {}, "p95_halfwidth_over_p95_error": {}}
    for axis in ("lateral", "altitude"):
        err = d[f"p9_{axis}_abs_error_m"].dropna().to_numpy(float)
        if not err.size:
            for key in ("coverage_95", "p95_error", "p95_halfwidth", "p95_halfwidth_over_p95_error"):
                result[key][axis] = float("nan")
            continue
        hw = _halfwidths(d, candidate, axis, 0.95)
        p95e = float(np.percentile(err, 95)); p95w = float(np.percentile(hw, 95))
        result["coverage_95"][axis] = float(np.mean(err <= hw))
        result["p95_error"][axis] = p95e; result["p95_halfwidth"][axis] = p95w
        result["p95_halfwidth_over_p95_error"][axis] = p95w / p95e if p95e > 0 else float("nan")
    return result


def _error_interval_stats(df: pd.DataFrame, candidate: dict[str, object]) -> tuple[dict[str, float], dict[str, dict[str, float]]]:
    mask = _available(df); d = df[mask].copy()
    errors: dict[str, float] = {"available_fraction": float(mask.mean()), "available_rows": int(mask.sum()), "total_rows": int(len(df))}
    intervals: dict[str, dict[str, float]] = {}
    for axis in ("lateral", "altitude"):
        err = d[f"p9_{axis}_abs_error_m"].dropna().to_numpy(float)
        hw = _halfwidths(d, candidate, axis, 0.95)
        errors[f"{axis}_mae"] = float(np.mean(err)) if err.size else float("nan")
        errors[f"{axis}_p95"] = float(np.percentile(err, 95)) if err.size else float("nan")
        intervals[axis] = {"median_halfwidth_95": float(np.median(hw)) if hw.size else float("nan"), "p95_halfwidth_95": float(np.percentile(hw, 95)) if hw.size else float("nan")}
    return errors, intervals


def _auc(labels: np.ndarray, scores: np.ndarray) -> float:
    pos = scores[labels == 1]; neg = scores[labels == 0]
    if not len(pos) or not len(neg): return float("nan")
    wins = sum(float(np.sum(v > neg)) + 0.5 * float(np.sum(v == neg)) for v in pos)
    return float(wins / (len(pos) * len(neg)))


def _shift_auc(reference: pd.DataFrame, evaluated: pd.DataFrame) -> float:
    a = reference.groupby("sequence_id", as_index=False)["severity"].mean(); a["label"] = 0
    b = evaluated.groupby("sequence_id", as_index=False)["severity"].mean(); b["label"] = 1
    d = pd.concat([a, b], ignore_index=True)
    return _auc(d["label"].to_numpy(int), d["severity"].to_numpy(float))


def _secondary(df: pd.DataFrame, candidate: dict[str, object]) -> dict[str, object]:
    d = df[_available(df)].copy(); d["p9_group"] = _group_series(d)
    per_group: dict[str, object] = {}
    for group in GROUPS:
        gd = d[d["p9_group"] == group]
        per_group[group] = _subset_stats(df, candidate, {group})
    continuity = d[d["p9_source"].astype(str) == "soft_innovation_continuity"]
    gains: dict[str, object] = {}
    for axis in ("lateral", "altitude"):
        arr = continuity[f"p9_{axis}_gain"].dropna().to_numpy(float)
        gains[axis] = {
            "median": float(np.median(arr)) if arr.size else float("nan"),
            "fraction_lt_0_90": float(np.mean(arr < 0.90)) if arr.size else float("nan"),
            "fraction_lt_0_75": float(np.mean(arr < 0.75)) if arr.size else float("nan"),
            "fraction_lt_0_50": float(np.mean(arr < 0.50)) if arr.size else float("nan"),
        }
    unavailable = df[~df["p9_available"].astype(bool)]["p9_unavailable_reason"].value_counts().to_dict()
    horizon_rows = []
    for h in range(3, 8):
        hd = continuity[continuity["p9_continuity_horizon"].astype(int) == h]
        item: dict[str, object] = {"horizon": h, "rows": int(len(hd))}
        for axis in ("lateral", "altitude"):
            err = hd[f"p9_{axis}_abs_error_m"].dropna().to_numpy(float)
            item[f"{axis}_mae"] = float(np.mean(err)) if err.size else float("nan")
            item[f"{axis}_p95"] = float(np.percentile(err, 95)) if err.size else float("nan")
        horizon_rows.append(item)
    return {"groups": per_group, "gain": gains, "unavailable_reason_counts": {str(k): int(v) for k, v in unavailable.items()}, "continuity_by_horizon": horizon_rows}


def summarize(evaluated: pd.DataFrame, reference: pd.DataFrame, candidate: dict[str, object], role: str, seed: int, require_transfer_minimums: bool) -> dict[str, object]:
    available_eval = evaluated[_available(evaluated)].copy(); groups = _group_series(available_eval)
    group_counts = {group: int((groups == group).sum()) for group in GROUPS}
    minima_pass = True
    if require_transfer_minimums:
        minima_pass = all(group_counts[g] >= TRANSFER_MINIMUMS[g] for g in GROUPS)
    coverage = _coverage(evaluated, candidate)
    errors, intervals = _error_interval_stats(evaluated, candidate)
    continuity = _subset_stats(evaluated, candidate, {GROUP_H3, GROUP_H45, GROUP_H67})
    base = _subset_stats(evaluated, candidate, {GROUP_BASE})
    h1 = {"available_fraction": errors["available_fraction"], "pass": bool(errors["available_fraction"] >= 0.92)}
    h2 = {"lateral_95_coverage": coverage["lateral"]["0.95"], "altitude_95_coverage": coverage["altitude"]["0.95"]}
    h2["pass"] = bool(0.90 <= h2["lateral_95_coverage"] <= 0.98 and 0.90 <= h2["altitude_95_coverage"] <= 0.98)
    mace = float(np.mean([abs(coverage[a][f"{q:.2f}"] - q) for a in ("lateral", "altitude") for q in TARGETS]))
    h3 = {"mean_absolute_coverage_error": mace, "pass": bool(mace <= 0.06)}
    h4: dict[str, object] = {}
    for axis in ("lateral", "altitude"):
        p95 = errors[f"{axis}_p95"]
        h4[f"{axis}_median_halfwidth_over_p95_error"] = intervals[axis]["median_halfwidth_95"] / p95
        h4[f"{axis}_p95_halfwidth_over_p95_error"] = intervals[axis]["p95_halfwidth_95"] / p95
    h4["pass"] = bool(h4["lateral_median_halfwidth_over_p95_error"] <= 1.25 and h4["altitude_median_halfwidth_over_p95_error"] <= 1.25 and h4["lateral_p95_halfwidth_over_p95_error"] <= 2.25 and h4["altitude_p95_halfwidth_over_p95_error"] <= 2.25)
    h5 = {"rows": continuity["rows"], "lateral_95_coverage": continuity["coverage_95"]["lateral"], "altitude_95_coverage": continuity["coverage_95"]["altitude"], "lateral_p95_halfwidth_over_p95_error": continuity["p95_halfwidth_over_p95_error"]["lateral"], "altitude_p95_halfwidth_over_p95_error": continuity["p95_halfwidth_over_p95_error"]["altitude"]}
    h5["pass"] = bool(h5["rows"] > 0 and 0.88 <= h5["lateral_95_coverage"] <= 0.99 and 0.88 <= h5["altitude_95_coverage"] <= 0.99 and h5["lateral_p95_halfwidth_over_p95_error"] <= 2.75 and h5["altitude_p95_halfwidth_over_p95_error"] <= 2.75)
    h6 = {"rows": base["rows"], "lateral_95_coverage": base["coverage_95"]["lateral"], "altitude_95_coverage": base["coverage_95"]["altitude"], "lateral_p95_halfwidth_over_p95_error": base["p95_halfwidth_over_p95_error"]["lateral"], "altitude_p95_halfwidth_over_p95_error": base["p95_halfwidth_over_p95_error"]["altitude"]}
    h6["pass"] = bool(h6["rows"] > 0 and 0.90 <= h6["lateral_95_coverage"] <= 0.98 and 0.90 <= h6["altitude_95_coverage"] <= 0.98 and h6["lateral_p95_halfwidth_over_p95_error"] <= 2.25 and h6["altitude_p95_halfwidth_over_p95_error"] <= 2.25)
    h7 = {"trajectory_level_auroc": _shift_auc(reference, evaluated)}; h7["pass"] = bool(h7["trajectory_level_auroc"] >= 0.85)
    gates = {"transfer_group_minimums": {"counts": group_counts, "required": TRANSFER_MINIMUMS, "pass": bool(minima_pass)}, "h1_useful_availability": h1, "h2_overall_coverage": h2, "h3_calibration_curve": h3, "h4_overall_interval_efficiency": h4, "h5_continuity_specific_honesty": h5, "h6_base_output_honesty": h6, "h7_shift_discrimination": h7}
    primary = ("h1_useful_availability", "h2_overall_coverage", "h3_calibration_curve", "h4_overall_interval_efficiency", "h5_continuity_specific_honesty", "h6_base_output_honesty")
    return {"schema": "aegisland.phase11.p9.result.v1", "evidence_role": role, "simulation_only": True, "safety_acceptance": False, "controller_tuning_allowed": False, "evaluated_seed_seen_after_run": seed, "all_primary_gates_pass": bool(minima_pass and all(gates[g]["pass"] for g in primary)), "gates": gates, "coverage": coverage, "error_stats": errors, "interval_stats": intervals, "continuity_stats": continuity, "base_output_stats": base, "secondary_diagnostics": _secondary(evaluated, candidate)}


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _manifest(out: Path, files: list[str], stage: str, git_sha: str) -> None:
    payload = {"schema": "aegisland.phase11.p9.manifest.v1", "stage": stage, "git_sha": git_sha, "simulation_only": True, "safety_acceptance": False, "controller_tuning_allowed": False, "files": {name: {"sha256": _hash_file(out / name), "bytes": (out / name).stat().st_size} for name in files}}
    (out / "manifest.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def freeze(out: Path, git_sha: str) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    fit_raw = _raw("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS)
    calibration_raw = _raw("calibration", CALIBRATION_SEED, CALIBRATION_FAMILIES, CALIBRATION_DOMAINS)
    candidate, calibration = _build_candidate(fit_raw, calibration_raw, git_sha)
    fit_raw.to_csv(out / "fit_frames.csv", index=False)
    calibration.to_csv(out / "calibration_frames.csv", index=False)
    (out / "candidate_freeze.json").write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(out, ["fit_frames.csv", "calibration_frames.csv", "candidate_freeze.json"], "freeze", git_sha)
    return candidate


def _load_candidate(path: Path) -> dict[str, object]:
    c = json.loads(path.read_text(encoding="utf-8"))
    if c.get("schema") != "aegisland.phase11.p9.candidate-freeze.v1": raise SystemExit("invalid P9 candidate schema")
    if c.get("transfer_seed_unseen_at_freeze") != TRANSFER_SEED or c.get("validation_seed_unseen_at_freeze") != VALIDATION_SEED: raise SystemExit("P9 candidate seed boundary mismatch")
    return c


def transfer(out: Path, candidate_path: Path, git_sha: str) -> dict[str, object]:
    candidate = _load_candidate(candidate_path); out.mkdir(parents=True, exist_ok=True)
    transfer_raw = _raw("transfer", TRANSFER_SEED, TRANSFER_FAMILIES, TRANSFER_DOMAINS)
    transfer_df = add_p9_continuity(transfer_raw, candidate["velocity_caps"], candidate["innovation_scales"])
    reference_raw = _raw("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS)
    reference = add_p9_continuity(reference_raw, candidate["velocity_caps"], candidate["innovation_scales"])
    result = summarize(transfer_df, reference, candidate, "phase11_p9_seen_transfer", TRANSFER_SEED, True)
    transfer_df.to_csv(out / "transfer_frames.csv", index=False)
    (out / "transfer_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "candidate_freeze.json").write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(out, ["transfer_frames.csv", "transfer_result.json", "candidate_freeze.json"], "transfer", git_sha)
    return result


def validate(out: Path, candidate_path: Path, git_sha: str) -> dict[str, object]:
    candidate = _load_candidate(candidate_path); out.mkdir(parents=True, exist_ok=True)
    validation_raw = _raw("validation", VALIDATION_SEED, VALIDATION_FAMILIES, VALIDATION_DOMAINS)
    validation = add_p9_continuity(validation_raw, candidate["velocity_caps"], candidate["innovation_scales"])
    reference_raw = _raw("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS)
    reference = add_p9_continuity(reference_raw, candidate["velocity_caps"], candidate["innovation_scales"])
    result = summarize(validation, reference, candidate, "phase11_p9_frozen_candidate_validation", VALIDATION_SEED, False)
    validation.to_csv(out / "validation_frames.csv", index=False)
    (out / "validation_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "candidate_freeze.json").write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(out, ["validation_frames.csv", "validation_result.json", "candidate_freeze.json"], "validation", git_sha)
    return result


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run preregistered Phase 11 P9 soft-update direct-conformal benchmark")
    p.add_argument("--stage", choices=("freeze", "transfer", "validation"), required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--candidate", type=Path)
    p.add_argument("--git-sha", default="unknown")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.stage == "freeze":
        c = freeze(args.out, args.git_sha)
        print("P9_CANDIDATE_FREEZE=" + json.dumps({"calibration_group_rows": c["calibration_group_rows"], "velocity_caps": c["velocity_caps"], "innovation_scales": c["innovation_scales"]}, sort_keys=True))
        return
    if args.candidate is None: raise SystemExit("--candidate required")
    if args.stage == "transfer":
        r = transfer(args.out, args.candidate, args.git_sha)
        print("P9_TRANSFER_GATES=" + json.dumps(r["gates"], sort_keys=True)); return
    r = validate(args.out, args.candidate, args.git_sha)
    print("P9_VALIDATION_GATES=" + json.dumps(r["gates"], sort_keys=True))


if __name__ == "__main__":
    main()
