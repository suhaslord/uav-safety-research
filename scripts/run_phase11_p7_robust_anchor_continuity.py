from __future__ import annotations

import argparse
import json
import math
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scripts import run_phase11_p5_perception_continuity as p5
except ModuleNotFoundError:
    import run_phase11_p5_perception_continuity as p5

p1 = p5.p1

FIT_SEED = 297297
CALIBRATION_SEED = 308308
ADAPTATION_SEED = 319319
TRANSFER_SEED = 330330
VALIDATION_SEED = 341341
FRAMES_PER_SEQUENCE = 60
TARGETS = p5.TARGETS
RIDGE_LAMBDA = 4.0
MAX_CONTINUITY_GAP = 7
DAMPING = 0.85
VELOCITY_CAP_QUANTILE = 0.99
MIN_ADAPTATION_CONTINUITY_ROWS = 80
MIN_TRANSFER_CONTINUITY_ROWS = 50
MIN_TRANSFER_BASE_ROWS = 200

FIT_FAMILIES = tuple(range(102, 108))
CALIBRATION_FAMILIES = tuple(range(108, 111))
ADAPTATION_FAMILIES = tuple(range(111, 114))
TRANSFER_FAMILIES = tuple(range(114, 117))
VALIDATION_FAMILIES = tuple(range(117, 120))

FIT_DOMAINS = p5.FIT_DOMAINS
ADAPTATION_DOMAINS = (
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
    "small_scale+blur_noise+low_contrast",
    "edge+dim+low_contrast",
    "small_scale+oblique+blur_noise",
)
VALIDATION_DOMAINS = (
    "edge+low_contrast+temporal_dropout",
    "small_scale+oblique+temporal_dropout",
    "dim+low_contrast+temporal_dropout",
    "blur_noise+low_contrast+temporal_dropout",
    "edge+small_scale+oblique",
    "edge+oblique+dim+blur_noise",
    "small_scale+dim+blur_noise+temporal_dropout",
    "edge+small_scale+oblique+dim+blur_noise+temporal_dropout",
)

RISK_COLUMNS = p5.RISK_COLUMNS
BASE_SOURCE_NAMES = (
    "partial_edge",
    "phase9_center_regeometry",
    "known_aruco_refined",
    "temporal_bridge",
    "robust_continuity",
)
TRANSFER_GROUPS = ("base_output", "robust_continuity")


def _raw(name: str, seed: int, families: tuple[int, ...], domains: tuple[str, ...]) -> pd.DataFrame:
    return p1.generate_split(name, seed, families, domains, frames=FRAMES_PER_SEQUENCE)


def _fit_velocity_caps(raw_fit: pd.DataFrame) -> dict[str, float]:
    # Identical rule to P5/P6, but evaluated on fresh P7 fit evidence.
    slopes = {"lateral": [], "altitude": []}
    for _, group in raw_fit.groupby("sequence_id"):
        d = group[group["candidate_available"]].sort_values("frame_index")
        rows = list(d.itertuples(index=False))
        for left, right in zip(rows, rows[1:]):
            dt = int(right.frame_index) - int(left.frame_index)
            if dt <= 0:
                continue
            slopes["lateral"].append(
                abs((float(right.estimate_lateral_x_m) - float(left.estimate_lateral_x_m)) / dt)
            )
            slopes["altitude"].append(
                abs((float(right.estimate_altitude_m) - float(left.estimate_altitude_m)) / dt)
            )
    result: dict[str, float] = {}
    for axis in ("lateral", "altitude"):
        arr = np.asarray(slopes[axis], dtype=float)
        arr = arr[np.isfinite(arr)]
        if not arr.size:
            raise RuntimeError(f"no finite P7 {axis} anchor slopes")
        result[axis] = float(max(1e-6, np.quantile(arr, VELOCITY_CAP_QUANTILE)))
    return result


def _pairwise_median_slope(values: list[tuple[int, float]], cap: float) -> float:
    if len(values) < 2:
        return 0.0
    recent = values[-3:]
    slopes: list[float] = []
    for i in range(len(recent)):
        for j in range(i + 1, len(recent)):
            dt = recent[j][0] - recent[i][0]
            if dt > 0:
                slopes.append((recent[j][1] - recent[i][1]) / dt)
    if not slopes:
        return 0.0
    slope = float(np.median(np.asarray(slopes, dtype=float)))
    return float(np.clip(slope, -cap, cap))


def _robust_axis_state(values: list[tuple[int, float]], cap: float) -> tuple[float, float]:
    if len(values) < 2:
        latest = float(values[-1][1]) if values else float("nan")
        return 0.0, latest
    recent = values[-3:]
    slope = _pairwise_median_slope(recent, cap)
    intercepts = np.asarray([y - slope * t for t, y in recent], dtype=float)
    intercept = float(np.median(intercepts))
    latest_t = recent[-1][0]
    trend_latest = float(intercept + slope * latest_t)
    return slope, trend_latest


def _anchor_innovation(anchors: list[tuple[int, float, float]]) -> tuple[float, float, bool]:
    if len(anchors) < 3:
        return 0.0, 0.0, False
    a, b, c = anchors[-3:]
    dt = b[0] - a[0]
    forward = c[0] - b[0]
    if dt <= 0 or forward < 0:
        return 0.0, 0.0, False
    pred_lat = b[1] + ((b[1] - a[1]) / dt) * forward
    pred_alt = b[2] + ((b[2] - a[2]) / dt) * forward
    return abs(c[1] - pred_lat), abs(c[2] - pred_alt), True


def _damped_steps(horizon: int) -> float:
    return float(sum(DAMPING**k for k in range(horizon)))


def add_p7_continuity(raw: pd.DataFrame, velocity_caps: dict[str, float]) -> pd.DataFrame:
    out = p1.add_reliability_state(p1.add_temporal_bridge(raw, max_gap=2)).copy()
    out["p7_available"] = out["p1_available"].astype(bool)
    out["p7_estimate_lateral_x_m"] = out["p1_estimate_lateral_x_m"]
    out["p7_estimate_altitude_m"] = out["p1_estimate_altitude_m"]
    out["p7_source"] = out["p1_source"].fillna("")
    out["p7_continuity_horizon"] = out["bridge_horizon"].astype(int)
    out["p7_lateral_slope_cap_utilization"] = 0.0
    out["p7_altitude_slope_cap_utilization"] = 0.0
    out["p7_anchor_innovation_lateral_abs"] = 0.0
    out["p7_anchor_innovation_altitude_abs"] = 0.0
    out["p7_anchor_innovation_available"] = False
    out["p7_unavailable_reason"] = ""

    for _, indices in out.groupby("sequence_id").groups.items():
        ordered = sorted(indices, key=lambda idx: int(out.loc[idx, "frame_index"]))
        anchors: list[tuple[int, float, float]] = []
        for idx in ordered:
            frame = int(out.loc[idx, "frame_index"])
            genuine = bool(out.loc[idx, "candidate_available"])

            if genuine:
                if len(anchors) >= 2:
                    temp = [*anchors[-2:], (
                        frame,
                        float(out.loc[idx, "estimate_lateral_x_m"]),
                        float(out.loc[idx, "estimate_altitude_m"]),
                    )]
                    lat_innov, alt_innov, available = _anchor_innovation(temp)
                    out.loc[idx, "p7_anchor_innovation_lateral_abs"] = lat_innov
                    out.loc[idx, "p7_anchor_innovation_altitude_abs"] = alt_innov
                    out.loc[idx, "p7_anchor_innovation_available"] = available

                anchors.append(
                    (
                        frame,
                        float(out.loc[idx, "estimate_lateral_x_m"]),
                        float(out.loc[idx, "estimate_altitude_m"]),
                    )
                )
                anchors = anchors[-3:]
                lat_values = [(a[0], a[1]) for a in anchors]
                alt_values = [(a[0], a[2]) for a in anchors]
                lat_slope, _ = _robust_axis_state(lat_values, velocity_caps["lateral"])
                alt_slope, _ = _robust_axis_state(alt_values, velocity_caps["altitude"])
                out.loc[idx, "p7_lateral_slope_cap_utilization"] = min(
                    1.0, abs(lat_slope) / max(velocity_caps["lateral"], 1e-9)
                )
                out.loc[idx, "p7_altitude_slope_cap_utilization"] = min(
                    1.0, abs(alt_slope) / max(velocity_caps["altitude"], 1e-9)
                )
                continue

            lat_innov, alt_innov, innovation_available = _anchor_innovation(anchors)
            out.loc[idx, "p7_anchor_innovation_lateral_abs"] = lat_innov
            out.loc[idx, "p7_anchor_innovation_altitude_abs"] = alt_innov
            out.loc[idx, "p7_anchor_innovation_available"] = innovation_available

            lat_values = [(a[0], a[1]) for a in anchors]
            alt_values = [(a[0], a[2]) for a in anchors]
            lat_slope, lat_trend_latest = _robust_axis_state(lat_values, velocity_caps["lateral"])
            alt_slope, alt_trend_latest = _robust_axis_state(alt_values, velocity_caps["altitude"])
            out.loc[idx, "p7_lateral_slope_cap_utilization"] = min(
                1.0, abs(lat_slope) / max(velocity_caps["lateral"], 1e-9)
            )
            out.loc[idx, "p7_altitude_slope_cap_utilization"] = min(
                1.0, abs(alt_slope) / max(velocity_caps["altitude"], 1e-9)
            )

            if bool(out.loc[idx, "p1_available"]):
                continue
            if len(anchors) < 2:
                out.loc[idx, "p7_unavailable_reason"] = "insufficient_anchors"
                continue

            horizon = frame - anchors[-1][0]
            if horizon <= 2:
                continue
            if horizon > MAX_CONTINUITY_GAP:
                out.loc[idx, "p7_unavailable_reason"] = "gap_beyond_horizon"
                continue

            step_sum = _damped_steps(horizon)
            pred_lat = lat_trend_latest + lat_slope * step_sum
            pred_alt = alt_trend_latest + alt_slope * step_sum
            out.loc[idx, "p7_available"] = True
            out.loc[idx, "p7_estimate_lateral_x_m"] = pred_lat
            out.loc[idx, "p7_estimate_altitude_m"] = pred_alt
            out.loc[idx, "p7_source"] = "robust_continuity"
            out.loc[idx, "p7_continuity_horizon"] = horizon

    out["p7_lateral_abs_error_m"] = np.abs(
        out["p7_estimate_lateral_x_m"] - out["truth_lateral_x_m"]
    )
    out["p7_altitude_abs_error_m"] = np.abs(
        out["p7_estimate_altitude_m"] - out["truth_altitude_m"]
    )
    return out


def _available(df: pd.DataFrame) -> pd.Series:
    return df["p7_available"].astype(bool) & df["truth_visible"].astype(bool)


def _base_continuous_basis(df: pd.DataFrame) -> np.ndarray:
    risks = df[list(RISK_COLUMNS)].to_numpy(float)
    primary = risks[:, :7]
    ordered = np.sort(primary, axis=1)
    top1 = ordered[:, -1]
    top2 = ordered[:, -2]
    risk = df["risk_score"].to_numpy(float)
    coactivation = df["coactivation_count"].to_numpy(float) / 7.0
    horizon = df["p7_continuity_horizon"].to_numpy(float)
    lat_util = df["p7_lateral_slope_cap_utilization"].to_numpy(float)
    alt_util = df["p7_altitude_slope_cap_utilization"].to_numpy(float)
    lat_innov = df["p7_anchor_innovation_lateral_abs"].to_numpy(float)
    alt_innov = df["p7_anchor_innovation_altitude_abs"].to_numpy(float)
    innov_available = df["p7_anchor_innovation_available"].to_numpy(bool).astype(float)
    return np.column_stack(
        [
            risks,
            risk,
            coactivation,
            top1,
            top2,
            horizon,
            lat_util,
            alt_util,
            lat_innov,
            alt_innov,
            innov_available,
        ]
    )


def _source_basis(df: pd.DataFrame) -> np.ndarray:
    source = df["p7_source"].fillna("").astype(str)
    return np.column_stack(
        [(source == name).to_numpy(float) for name in BASE_SOURCE_NAMES]
    )


def _fit_standardizer(values: np.ndarray) -> dict[str, list[float]]:
    mean = values.mean(axis=0)
    std = values.std(axis=0)
    std = np.where(std < 1e-6, 1.0, std)
    return {"mean": mean.tolist(), "std": std.tolist()}


def _standardize(values: np.ndarray, standardizer: dict[str, list[float]]) -> np.ndarray:
    mean = np.asarray(standardizer["mean"], dtype=float)
    std = np.asarray(standardizer["std"], dtype=float)
    return (values - mean) / std


def _base_design(df: pd.DataFrame, standardizer: dict[str, list[float]]) -> np.ndarray:
    z = _standardize(_base_continuous_basis(df), standardizer)
    return np.column_stack([np.ones(len(df)), z, _source_basis(df)])


def _ridge_fit(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    penalty = np.eye(x.shape[1], dtype=float)
    penalty[0, 0] = 0.0
    return np.linalg.solve(x.T @ x + RIDGE_LAMBDA * penalty, x.T @ y)


def _fit_base_models(fit: pd.DataFrame) -> dict[str, object]:
    d = fit[_available(fit)].copy()
    continuous = _base_continuous_basis(d)
    standardizer = _fit_standardizer(continuous)
    x = _base_design(d, standardizer)
    axes: dict[str, object] = {}
    for axis in ("lateral", "altitude"):
        raw_y = np.log(d[f"p7_{axis}_abs_error_m"].to_numpy(float) + 1e-4)
        lo, hi = np.quantile(raw_y, [0.02, 0.98])
        y = np.clip(raw_y, lo, hi)
        coef = _ridge_fit(x, y)
        fitted = x @ coef
        pred_lo, pred_hi = np.quantile(fitted, [0.01, 0.99])
        axes[axis] = {
            "coefficients": coef.tolist(),
            "target_winsor_log_bounds": [float(lo), float(hi)],
            "prediction_guard_log_bounds": [float(pred_lo - 0.35), float(pred_hi + 0.35)],
        }
    return {"standardizer": standardizer, "axes": axes}


def _base_predicted_scale(df: pd.DataFrame, model: dict[str, object]) -> dict[str, np.ndarray]:
    x = _base_design(df, model["standardizer"])
    result: dict[str, np.ndarray] = {}
    for axis in ("lateral", "altitude"):
        axis_model = model["axes"][axis]
        log_scale = x @ np.asarray(axis_model["coefficients"], dtype=float)
        lo, hi = axis_model["prediction_guard_log_bounds"]
        result[axis] = np.exp(np.clip(log_scale, float(lo), float(hi)))
    return result


def _correction_basis(df: pd.DataFrame) -> np.ndarray:
    return np.column_stack(
        [
            df["p7_continuity_horizon"].to_numpy(float),
            df["p7_lateral_slope_cap_utilization"].to_numpy(float),
            df["p7_altitude_slope_cap_utilization"].to_numpy(float),
            df["p7_anchor_innovation_lateral_abs"].to_numpy(float),
            df["p7_anchor_innovation_altitude_abs"].to_numpy(float),
            df["p7_anchor_innovation_available"].to_numpy(bool).astype(float),
            df["risk_score"].to_numpy(float),
            df["coactivation_count"].to_numpy(float) / 7.0,
        ]
    )


def _correction_design(df: pd.DataFrame, standardizer: dict[str, list[float]]) -> np.ndarray:
    z = _standardize(_correction_basis(df), standardizer)
    return np.column_stack([np.ones(len(df)), z])


def _fit_continuity_correction(
    adaptation: pd.DataFrame, base_model: dict[str, object]
) -> dict[str, object]:
    d = adaptation[
        _available(adaptation) & (adaptation["p7_source"].astype(str) == "robust_continuity")
    ].copy()
    if len(d) < MIN_ADAPTATION_CONTINUITY_ROWS:
        raise RuntimeError(
            f"P7 adaptation continuity rows {len(d)} < {MIN_ADAPTATION_CONTINUITY_ROWS}"
        )
    basis = _correction_basis(d)
    standardizer = _fit_standardizer(basis)
    x = _correction_design(d, standardizer)
    base_scale = _base_predicted_scale(d, base_model)
    axes: dict[str, object] = {}
    for axis in ("lateral", "altitude"):
        ratio = d[f"p7_{axis}_abs_error_m"].to_numpy(float) / np.maximum(
            base_scale[axis], 1e-9
        )
        raw_y = np.log(ratio + 1e-4)
        lo, hi = np.quantile(raw_y, [0.02, 0.98])
        y = np.clip(raw_y, lo, hi)
        coef = _ridge_fit(x, y)
        fitted = x @ coef
        pred_lo, pred_hi = np.quantile(fitted, [0.01, 0.99])
        axes[axis] = {
            "coefficients": coef.tolist(),
            "target_winsor_log_bounds": [float(lo), float(hi)],
            "prediction_guard_log_bounds": [float(pred_lo - 0.35), float(pred_hi + 0.35)],
        }
    return {
        "rows": int(len(d)),
        "standardizer": standardizer,
        "axes": axes,
    }


def _corrected_scale(
    df: pd.DataFrame,
    base_model: dict[str, object],
    correction_model: dict[str, object],
) -> dict[str, np.ndarray]:
    base = _base_predicted_scale(df, base_model)
    continuity = (df["p7_source"].astype(str).to_numpy() == "robust_continuity")
    result = {axis: values.copy() for axis, values in base.items()}
    if not np.any(continuity):
        return result
    d = df.loc[continuity]
    x = _correction_design(d, correction_model["standardizer"])
    for axis in ("lateral", "altitude"):
        axis_model = correction_model["axes"][axis]
        log_corr = x @ np.asarray(axis_model["coefficients"], dtype=float)
        lo, hi = axis_model["prediction_guard_log_bounds"]
        correction = np.exp(np.clip(log_corr, float(lo), float(hi)))
        result[axis][continuity] *= correction
    return result


def _finite_conformal(values: np.ndarray | pd.Series, q: float) -> float:
    arr = np.asarray(values, dtype=float)
    arr = np.sort(arr[np.isfinite(arr)])
    if arr.size == 0:
        return float("nan")
    k = int(math.ceil((arr.size + 1) * q))
    return float(arr[min(arr.size - 1, max(0, k - 1))])


def _single_factor_calibration(
    calibration: pd.DataFrame,
    base_model: dict[str, object],
    correction_model: dict[str, object],
) -> dict[str, dict[str, float]]:
    d = calibration[_available(calibration)].copy()
    scale = _corrected_scale(d, base_model, correction_model)
    result: dict[str, dict[str, float]] = {}
    for axis in ("lateral", "altitude"):
        normalized = d[f"p7_{axis}_abs_error_m"].to_numpy(float) / np.maximum(
            scale[axis], 1e-9
        )
        result[axis] = {
            f"{q:.2f}": _finite_conformal(normalized, q) for q in TARGETS
        }
    return result


def _transfer_group_series(df: pd.DataFrame) -> pd.Series:
    return pd.Series(
        np.where(
            df["p7_source"].astype(str).to_numpy() == "robust_continuity",
            "robust_continuity",
            "base_output",
        ),
        index=df.index,
        dtype="object",
    )


def _provisional_radius(
    df: pd.DataFrame, candidate: dict[str, object], axis: str, q: float
) -> np.ndarray:
    scale = _corrected_scale(
        df, candidate["base_scale_model"], candidate["continuity_correction_model"]
    )[axis]
    return scale * float(candidate["single_factor_conformal"][axis][f"{q:.2f}"])


def _fit_transfer_multipliers(
    transfer: pd.DataFrame,
    base_model: dict[str, object],
    correction_model: dict[str, object],
    single: dict[str, dict[str, float]],
) -> tuple[dict[str, dict[str, dict[str, float]]], dict[str, int]]:
    d = transfer[_available(transfer)].copy()
    d["p7_transfer_group"] = _transfer_group_series(d)
    counts = {
        group: int((d["p7_transfer_group"] == group).sum()) for group in TRANSFER_GROUPS
    }
    if counts["robust_continuity"] < MIN_TRANSFER_CONTINUITY_ROWS:
        raise RuntimeError(
            f"P7 transfer continuity rows {counts['robust_continuity']} < {MIN_TRANSFER_CONTINUITY_ROWS}"
        )
    if counts["base_output"] < MIN_TRANSFER_BASE_ROWS:
        raise RuntimeError(
            f"P7 transfer base rows {counts['base_output']} < {MIN_TRANSFER_BASE_ROWS}"
        )
    provisional_candidate = {
        "base_scale_model": base_model,
        "continuity_correction_model": correction_model,
        "single_factor_conformal": single,
    }
    result: dict[str, dict[str, dict[str, float]]] = {}
    for group in TRANSFER_GROUPS:
        g = d[d["p7_transfer_group"] == group].copy()
        result[group] = {}
        for axis in ("lateral", "altitude"):
            error = g[f"p7_{axis}_abs_error_m"].to_numpy(float)
            result[group][axis] = {}
            for q in TARGETS:
                radius = _provisional_radius(g, provisional_candidate, axis, q)
                result[group][axis][f"{q:.2f}"] = _finite_conformal(
                    error / np.maximum(radius, 1e-9), q
                )
    return result, counts


def final_halfwidths(
    df: pd.DataFrame, candidate: dict[str, object], axis: str
) -> dict[str, np.ndarray]:
    groups = _transfer_group_series(df).to_numpy(str)
    cols: list[np.ndarray] = []
    for q in TARGETS:
        provisional = _provisional_radius(df, candidate, axis, q)
        multipliers = np.asarray(
            [
                float(candidate["transfer_multipliers"][group][axis][f"{q:.2f}"])
                for group in groups
            ],
            dtype=float,
        )
        cols.append(provisional * multipliers)
    nested = np.maximum.accumulate(np.column_stack(cols), axis=1)
    return {f"{q:.2f}": nested[:, i] for i, q in enumerate(TARGETS)}


def _build_candidate(
    fit: pd.DataFrame,
    calibration: pd.DataFrame,
    adaptation: pd.DataFrame,
    transfer: pd.DataFrame,
    velocity_caps: dict[str, float],
    git_sha: str,
) -> dict[str, object]:
    base_model = _fit_base_models(fit)
    correction_model = _fit_continuity_correction(adaptation, base_model)
    single = _single_factor_calibration(calibration, base_model, correction_model)
    transfer_multipliers, transfer_counts = _fit_transfer_multipliers(
        transfer, base_model, correction_model, single
    )
    return {
        "schema": "aegisland.phase11.p7.candidate-freeze.v1",
        "git_sha": git_sha,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "fit_seed": FIT_SEED,
        "calibration_seed": CALIBRATION_SEED,
        "adaptation_seed": ADAPTATION_SEED,
        "transfer_seed": TRANSFER_SEED,
        "validation_seed_unseen_at_freeze": VALIDATION_SEED,
        "fit_families": list(FIT_FAMILIES),
        "calibration_families": list(CALIBRATION_FAMILIES),
        "adaptation_families": list(ADAPTATION_FAMILIES),
        "transfer_families": list(TRANSFER_FAMILIES),
        "validation_families": list(VALIDATION_FAMILIES),
        "continuity_constants": {
            "max_continuity_gap": MAX_CONTINUITY_GAP,
            "damping": DAMPING,
            "velocity_cap_quantile": VELOCITY_CAP_QUANTILE,
            "anchor_window": 3,
            "robust_slope": "median_all_pairwise",
            "robust_intercept": "median_anchor_intercepts",
        },
        "velocity_caps": velocity_caps,
        "ridge_lambda": RIDGE_LAMBDA,
        "minimum_rows": {
            "adaptation_robust_continuity": MIN_ADAPTATION_CONTINUITY_ROWS,
            "transfer_robust_continuity": MIN_TRANSFER_CONTINUITY_ROWS,
            "transfer_base_output": MIN_TRANSFER_BASE_ROWS,
        },
        "base_scale_model": base_model,
        "continuity_correction_model": correction_model,
        "single_factor_conformal": single,
        "transfer_groups": list(TRANSFER_GROUPS),
        "transfer_group_rows": transfer_counts,
        "transfer_multipliers": transfer_multipliers,
    }


def _coverage(df: pd.DataFrame, candidate: dict[str, object]) -> dict[str, dict[str, float]]:
    d = df[_available(df)].copy()
    result: dict[str, dict[str, float]] = {}
    for axis in ("lateral", "altitude"):
        error = d[f"p7_{axis}_abs_error_m"].to_numpy(float)
        widths = final_halfwidths(d, candidate, axis)
        result[axis] = {
            f"{q:.2f}": float(np.mean(error <= widths[f"{q:.2f}"]))
            if error.size
            else float("nan")
            for q in TARGETS
        }
    return result


def _error_stats(df: pd.DataFrame) -> dict[str, float]:
    mask = _available(df)
    d = df[mask]
    result: dict[str, float] = {
        "available_fraction": float(mask.mean()),
        "available_rows": int(mask.sum()),
        "total_rows": int(len(df)),
    }
    for axis in ("lateral", "altitude"):
        values = d[f"p7_{axis}_abs_error_m"].dropna().to_numpy(float)
        result[f"{axis}_mae"] = float(np.mean(values)) if values.size else float("nan")
        result[f"{axis}_p95"] = float(np.percentile(values, 95)) if values.size else float("nan")
    return result


def _interval_stats(
    df: pd.DataFrame, candidate: dict[str, object]
) -> dict[str, dict[str, float]]:
    d = df[_available(df)].copy()
    result: dict[str, dict[str, float]] = {}
    for axis in ("lateral", "altitude"):
        widths = final_halfwidths(d, candidate, axis)["0.95"]
        result[axis] = {
            "median_halfwidth_95": float(np.median(widths)) if widths.size else float("nan"),
            "p95_halfwidth_95": float(np.percentile(widths, 95)) if widths.size else float("nan"),
        }
    return result


def _subset_stats(
    df: pd.DataFrame, candidate: dict[str, object], group: str
) -> dict[str, object]:
    mask = _available(df) & (_transfer_group_series(df) == group)
    d = df[mask].copy()
    result: dict[str, object] = {
        "rows": int(len(d)),
        "fraction_of_truth_visible": float(len(d) / len(df)) if len(df) else float("nan"),
        "coverage_95": {},
        "p95_error": {},
        "p95_halfwidth": {},
        "p95_halfwidth_over_p95_error": {},
    }
    for axis in ("lateral", "altitude"):
        error = d[f"p7_{axis}_abs_error_m"].dropna().to_numpy(float)
        if not error.size:
            for key in (
                "coverage_95",
                "p95_error",
                "p95_halfwidth",
                "p95_halfwidth_over_p95_error",
            ):
                result[key][axis] = float("nan")
            continue
        widths = final_halfwidths(d, candidate, axis)["0.95"]
        p95_error = float(np.percentile(error, 95))
        p95_width = float(np.percentile(widths, 95))
        result["coverage_95"][axis] = float(np.mean(error <= widths))
        result["p95_error"][axis] = p95_error
        result["p95_halfwidth"][axis] = p95_width
        result["p95_halfwidth_over_p95_error"][axis] = (
            p95_width / p95_error if p95_error > 0 else float("nan")
        )
    return result


def _auc(labels: np.ndarray, scores: np.ndarray) -> float:
    pos = scores[labels == 1]
    neg = scores[labels == 0]
    if not len(pos) or not len(neg):
        return float("nan")
    wins = sum(float(np.sum(score > neg)) + 0.5 * float(np.sum(score == neg)) for score in pos)
    return float(wins / (len(pos) * len(neg)))


def _shift_auc(calibration: pd.DataFrame, evaluated: pd.DataFrame) -> float:
    left = calibration.groupby("sequence_id", as_index=False)["severity"].mean()
    left["label"] = 0
    right = evaluated.groupby("sequence_id", as_index=False)["severity"].mean()
    right["label"] = 1
    combined = pd.concat([left, right], ignore_index=True)
    return _auc(combined["label"].to_numpy(int), combined["severity"].to_numpy(float))


def _secondary_diagnostics(
    evaluated: pd.DataFrame,
    velocity_caps: dict[str, float],
) -> dict[str, object]:
    continuity = evaluated[
        _available(evaluated) & (evaluated["p7_source"].astype(str) == "robust_continuity")
    ].copy()
    horizons = {
        str(int(k)): int(v)
        for k, v in continuity["p7_continuity_horizon"].value_counts().sort_index().items()
    }
    unavailable = evaluated[~_available(evaluated)]
    unavailable_reasons = {
        str(k): int(v)
        for k, v in unavailable["p7_unavailable_reason"].replace("", "other").value_counts().items()
    }
    diagnostics: dict[str, object] = {
        "continuity_horizon_counts": horizons,
        "unavailable_reason_counts": unavailable_reasons,
        "continuity_anchor_innovation": {},
        "continuity_slope_cap_utilization": {},
        "continuity_error_by_horizon": [],
    }
    for axis in ("lateral", "altitude"):
        innov = continuity[f"p7_anchor_innovation_{axis}_abs"].to_numpy(float)
        util = continuity[f"p7_{axis}_slope_cap_utilization"].to_numpy(float)
        diagnostics["continuity_anchor_innovation"][axis] = {
            "median": float(np.median(innov)) if innov.size else float("nan"),
            "p95": float(np.percentile(innov, 95)) if innov.size else float("nan"),
        }
        diagnostics["continuity_slope_cap_utilization"][axis] = {
            "median": float(np.median(util)) if util.size else float("nan"),
            "p95": float(np.percentile(util, 95)) if util.size else float("nan"),
            "fraction_ge_0_99": float(np.mean(util >= 0.99)) if util.size else float("nan"),
            "cap": float(velocity_caps[axis]),
        }
    for horizon, group in continuity.groupby("p7_continuity_horizon"):
        row: dict[str, object] = {"horizon": int(horizon), "rows": int(len(group))}
        for axis in ("lateral", "altitude"):
            values = group[f"p7_{axis}_abs_error_m"].to_numpy(float)
            row[f"{axis}_mae"] = float(np.mean(values))
            row[f"{axis}_p95"] = float(np.percentile(values, 95))
        diagnostics["continuity_error_by_horizon"].append(row)
    return diagnostics


def summarize(
    evaluated: pd.DataFrame,
    calibration_df: pd.DataFrame,
    candidate: dict[str, object],
    role: str,
    seed: int,
) -> dict[str, object]:
    coverage = _coverage(evaluated, candidate)
    errors = _error_stats(evaluated)
    intervals = _interval_stats(evaluated, candidate)
    continuity = _subset_stats(evaluated, candidate, "robust_continuity")
    base = _subset_stats(evaluated, candidate, "base_output")

    h1 = {
        "available_fraction": errors["available_fraction"],
        "pass": bool(errors["available_fraction"] >= 0.92),
    }
    h2 = {
        "lateral_95_coverage": coverage["lateral"]["0.95"],
        "altitude_95_coverage": coverage["altitude"]["0.95"],
    }
    h2["pass"] = bool(
        0.90 <= h2["lateral_95_coverage"] <= 0.98
        and 0.90 <= h2["altitude_95_coverage"] <= 0.98
    )
    mace = float(
        np.mean(
            [
                abs(coverage[axis][f"{q:.2f}"] - q)
                for axis in ("lateral", "altitude")
                for q in TARGETS
            ]
        )
    )
    h3 = {"mean_absolute_coverage_error": mace, "pass": bool(mace <= 0.06)}
    h4: dict[str, object] = {}
    for axis in ("lateral", "altitude"):
        p95_error = errors[f"{axis}_p95"]
        h4[f"{axis}_median_halfwidth_over_p95_error"] = (
            intervals[axis]["median_halfwidth_95"] / p95_error
        )
        h4[f"{axis}_p95_halfwidth_over_p95_error"] = (
            intervals[axis]["p95_halfwidth_95"] / p95_error
        )
    h4["pass"] = bool(
        h4["lateral_median_halfwidth_over_p95_error"] <= 1.25
        and h4["altitude_median_halfwidth_over_p95_error"] <= 1.25
        and h4["lateral_p95_halfwidth_over_p95_error"] <= 2.25
        and h4["altitude_p95_halfwidth_over_p95_error"] <= 2.25
    )
    h5 = {
        "rows": continuity["rows"],
        "lateral_95_coverage": continuity["coverage_95"]["lateral"],
        "altitude_95_coverage": continuity["coverage_95"]["altitude"],
        "lateral_p95_halfwidth_over_p95_error": continuity["p95_halfwidth_over_p95_error"]["lateral"],
        "altitude_p95_halfwidth_over_p95_error": continuity["p95_halfwidth_over_p95_error"]["altitude"],
    }
    h5["pass"] = bool(
        h5["rows"] > 0
        and 0.88 <= h5["lateral_95_coverage"] <= 0.99
        and 0.88 <= h5["altitude_95_coverage"] <= 0.99
        and h5["lateral_p95_halfwidth_over_p95_error"] <= 2.75
        and h5["altitude_p95_halfwidth_over_p95_error"] <= 2.75
    )
    h6 = {
        "rows": base["rows"],
        "lateral_95_coverage": base["coverage_95"]["lateral"],
        "altitude_95_coverage": base["coverage_95"]["altitude"],
        "lateral_p95_halfwidth_over_p95_error": base["p95_halfwidth_over_p95_error"]["lateral"],
        "altitude_p95_halfwidth_over_p95_error": base["p95_halfwidth_over_p95_error"]["altitude"],
    }
    h6["pass"] = bool(
        h6["rows"] > 0
        and 0.90 <= h6["lateral_95_coverage"] <= 0.98
        and 0.90 <= h6["altitude_95_coverage"] <= 0.98
        and h6["lateral_p95_halfwidth_over_p95_error"] <= 2.25
        and h6["altitude_p95_halfwidth_over_p95_error"] <= 2.25
    )
    h7 = {"trajectory_level_auroc": _shift_auc(calibration_df, evaluated)}
    h7["pass"] = bool(h7["trajectory_level_auroc"] >= 0.85)
    gates = {
        "h1_useful_availability": h1,
        "h2_overall_coverage_transfer": h2,
        "h3_overall_calibration_curve": h3,
        "h4_overall_interval_efficiency": h4,
        "h5_robust_continuity_honesty": h5,
        "h6_base_output_honesty": h6,
        "h7_shift_discrimination": h7,
    }
    primary = (
        "h1_useful_availability",
        "h2_overall_coverage_transfer",
        "h3_overall_calibration_curve",
        "h4_overall_interval_efficiency",
        "h5_robust_continuity_honesty",
        "h6_base_output_honesty",
    )
    return {
        "schema": "aegisland.phase11.p7.result.v1",
        "evidence_role": role,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "evaluated_seed_seen_after_run": seed,
        "all_primary_gates_pass": bool(all(gates[name]["pass"] for name in primary)),
        "gates": gates,
        "coverage": coverage,
        "error_stats": errors,
        "interval_stats": intervals,
        "robust_continuity_stats": continuity,
        "base_output_stats": base,
        "secondary_diagnostics": _secondary_diagnostics(evaluated, candidate["velocity_caps"]),
    }


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_manifest(out: Path, names: list[str], git_sha: str, stage: str) -> None:
    manifest = {
        "schema": "aegisland.phase11.p7.manifest.v1",
        "stage": stage,
        "git_sha": git_sha,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "files": {
            name: {"sha256": _hash_file(out / name), "bytes": (out / name).stat().st_size}
            for name in names
        },
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def freeze(out: Path, git_sha: str) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    fit_raw = _raw("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS)
    caps = _fit_velocity_caps(fit_raw)
    fit = add_p7_continuity(fit_raw, caps)
    calibration = add_p7_continuity(
        _raw("calibration", CALIBRATION_SEED, CALIBRATION_FAMILIES, FIT_DOMAINS), caps
    )
    adaptation = add_p7_continuity(
        _raw("adaptation", ADAPTATION_SEED, ADAPTATION_FAMILIES, ADAPTATION_DOMAINS), caps
    )
    transfer = add_p7_continuity(
        _raw("transfer", TRANSFER_SEED, TRANSFER_FAMILIES, TRANSFER_DOMAINS), caps
    )
    candidate = _build_candidate(fit, calibration, adaptation, transfer, caps, git_sha)
    result = summarize(
        transfer,
        calibration,
        candidate,
        "phase11_p7_seen_transfer_calibration",
        TRANSFER_SEED,
    )

    fit.to_csv(out / "fit_frames.csv", index=False)
    calibration.to_csv(out / "calibration_frames.csv", index=False)
    adaptation.to_csv(out / "adaptation_frames.csv", index=False)
    transfer.to_csv(out / "transfer_frames.csv", index=False)
    (out / "candidate_freeze.json").write_text(
        json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "transfer_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    names = [
        "fit_frames.csv",
        "calibration_frames.csv",
        "adaptation_frames.csv",
        "transfer_frames.csv",
        "candidate_freeze.json",
        "transfer_result.json",
    ]
    _write_manifest(out, names, git_sha, "freeze")
    return result


def validate(out: Path, candidate_path: Path, git_sha: str) -> dict[str, object]:
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    if candidate.get("schema") != "aegisland.phase11.p7.candidate-freeze.v1":
        raise SystemExit("invalid P7 candidate schema")
    if candidate.get("validation_seed_unseen_at_freeze") != VALIDATION_SEED:
        raise SystemExit("P7 validation seed mismatch")
    constants = candidate.get("continuity_constants", {})
    if int(constants.get("max_continuity_gap", -1)) != MAX_CONTINUITY_GAP:
        raise SystemExit("P7 continuity horizon changed")
    if float(constants.get("damping", -1.0)) != DAMPING:
        raise SystemExit("P7 damping changed")
    if float(constants.get("velocity_cap_quantile", -1.0)) != VELOCITY_CAP_QUANTILE:
        raise SystemExit("P7 velocity cap rule changed")

    out.mkdir(parents=True, exist_ok=True)
    validation = add_p7_continuity(
        _raw("validation", VALIDATION_SEED, VALIDATION_FAMILIES, VALIDATION_DOMAINS),
        candidate["velocity_caps"],
    )
    calibration = add_p7_continuity(
        _raw("calibration", CALIBRATION_SEED, CALIBRATION_FAMILIES, FIT_DOMAINS),
        candidate["velocity_caps"],
    )
    result = summarize(
        validation,
        calibration,
        candidate,
        "phase11_p7_frozen_candidate_validation",
        VALIDATION_SEED,
    )
    validation.to_csv(out / "validation_frames.csv", index=False)
    (out / "validation_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "candidate_freeze.json").write_text(
        json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _write_manifest(
        out,
        ["validation_frames.csv", "validation_result.json", "candidate_freeze.json"],
        git_sha,
        "validation",
    )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run preregistered Phase 11 P7 robust-anchor continuity benchmark."
    )
    parser.add_argument("--stage", choices=("freeze", "validation"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--git-sha", default="unknown")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.stage == "freeze":
        result = freeze(args.out, args.git_sha)
        print("P7_TRANSFER_GATES=" + json.dumps(result["gates"], sort_keys=True))
        return
    if args.candidate is None:
        raise SystemExit("--candidate is required for validation stage")
    result = validate(args.out, args.candidate, args.git_sha)
    print("P7_VALIDATION_GATES=" + json.dumps(result["gates"], sort_keys=True))


if __name__ == "__main__":
    main()
