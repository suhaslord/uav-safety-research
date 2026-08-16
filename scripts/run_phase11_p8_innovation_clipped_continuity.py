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

FIT_SEED = 352352
CALIBRATION_SEED = 363363
ADAPTATION_SEED = 374374
TRANSFER_SEED = 385385
VALIDATION_SEED = 396396
FRAMES_PER_SEQUENCE = 60
TARGETS = p5.TARGETS
RIDGE_LAMBDA = 4.0
MAX_CONTINUITY_GAP = 7
DAMPING = 0.85
VELOCITY_CAP_QUANTILE = 0.99
INNOVATION_CAP_QUANTILE = 0.95
INNOVATION_UTILIZATION_MAX = 3.0
BLEND_PREVIOUS_SLOPE = 0.5
BLEND_CORRECTED_SLOPE = 0.5
MIN_ADAPTATION_CONTINUITY_ROWS = 90
MIN_TRANSFER_CONTINUITY_ROWS = 60
MIN_TRANSFER_BASE_ROWS = 400

FIT_FAMILIES = tuple(range(120, 126))
CALIBRATION_FAMILIES = tuple(range(126, 129))
ADAPTATION_FAMILIES = tuple(range(129, 138))
TRANSFER_FAMILIES = tuple(range(138, 144))
VALIDATION_FAMILIES = tuple(range(144, 150))

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
    "small_scale+blur_noise+temporal_dropout",
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

RISK_COLUMNS = p5.RISK_COLUMNS
SOURCE_NAMES = (
    "partial_edge",
    "phase9_center_regeometry",
    "known_aruco_refined",
    "temporal_bridge",
    "innovation_clipped_continuity",
)
TRANSFER_GROUPS = ("base_output", "innovation_clipped_continuity")


def _raw(name: str, seed: int, families: tuple[int, ...], domains: tuple[str, ...]) -> pd.DataFrame:
    return p1.generate_split(name, seed, families, domains, frames=FRAMES_PER_SEQUENCE)


def _fit_velocity_caps(raw_fit: pd.DataFrame) -> dict[str, float]:
    slopes = {"lateral": [], "altitude": []}
    for _, group in raw_fit.groupby("sequence_id"):
        genuine = group[group["candidate_available"]].sort_values("frame_index")
        rows = list(genuine.itertuples(index=False))
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
            raise RuntimeError(f"no finite P8 {axis} genuine-anchor slopes")
        result[axis] = float(max(1e-6, np.quantile(arr, VELOCITY_CAP_QUANTILE)))
    return result


def _fit_innovation_caps(raw_fit: pd.DataFrame) -> dict[str, float]:
    innovations = {"lateral": [], "altitude": []}
    for _, group in raw_fit.groupby("sequence_id"):
        genuine = group[group["candidate_available"]].sort_values("frame_index")
        anchors: list[tuple[int, float, float]] = []
        for row in genuine.itertuples(index=False):
            current = (
                int(row.frame_index),
                float(row.estimate_lateral_x_m),
                float(row.estimate_altitude_m),
            )
            if len(anchors) >= 2:
                a, b = anchors[-2:]
                dt = b[0] - a[0]
                forward = current[0] - b[0]
                if dt > 0 and forward >= 0:
                    pred_lat = b[1] + ((b[1] - a[1]) / dt) * forward
                    pred_alt = b[2] + ((b[2] - a[2]) / dt) * forward
                    innovations["lateral"].append(abs(current[1] - pred_lat))
                    innovations["altitude"].append(abs(current[2] - pred_alt))
            anchors.append(current)
            anchors = anchors[-3:]
    result: dict[str, float] = {}
    for axis in ("lateral", "altitude"):
        arr = np.asarray(innovations[axis], dtype=float)
        arr = arr[np.isfinite(arr)]
        if not arr.size:
            raise RuntimeError(f"no finite P8 {axis} genuine-anchor innovations")
        result[axis] = float(max(1e-6, np.quantile(arr, INNOVATION_CAP_QUANTILE)))
    return result


def _axis_state(
    values: list[tuple[int, float]], velocity_cap: float, innovation_cap: float
) -> dict[str, float | bool]:
    if not values:
        return {
            "slope": 0.0,
            "state": float("nan"),
            "raw_innovation_abs": 0.0,
            "innovation_available": False,
            "innovation_utilization": 0.0,
            "slope_utilization": 0.0,
            "innovation_clipped": False,
        }
    if len(values) == 1:
        return {
            "slope": 0.0,
            "state": float(values[-1][1]),
            "raw_innovation_abs": 0.0,
            "innovation_available": False,
            "innovation_utilization": 0.0,
            "slope_utilization": 0.0,
            "innovation_clipped": False,
        }

    recent = values[-3:]
    if len(recent) == 2:
        a, b = recent
        dt = b[0] - a[0]
        raw_slope = (b[1] - a[1]) / dt if dt > 0 else 0.0
        slope = float(np.clip(raw_slope, -velocity_cap, velocity_cap))
        return {
            "slope": slope,
            "state": float(b[1]),
            "raw_innovation_abs": 0.0,
            "innovation_available": False,
            "innovation_utilization": 0.0,
            "slope_utilization": min(1.0, abs(slope) / max(velocity_cap, 1e-9)),
            "innovation_clipped": False,
        }

    a, b, c = recent
    dt_prev = b[0] - a[0]
    dt_new = c[0] - b[0]
    if dt_prev <= 0 or dt_new <= 0:
        return {
            "slope": 0.0,
            "state": float(c[1]),
            "raw_innovation_abs": 0.0,
            "innovation_available": False,
            "innovation_utilization": 0.0,
            "slope_utilization": 0.0,
            "innovation_clipped": False,
        }

    m_prev = (b[1] - a[1]) / dt_prev
    pred_c = b[1] + m_prev * dt_new
    innovation = c[1] - pred_c
    clipped_innovation = float(np.clip(innovation, -innovation_cap, innovation_cap))
    corrected_c = pred_c + clipped_innovation
    m_new = (corrected_c - b[1]) / dt_new
    blended = BLEND_PREVIOUS_SLOPE * m_prev + BLEND_CORRECTED_SLOPE * m_new
    slope = float(np.clip(blended, -velocity_cap, velocity_cap))
    raw_abs = abs(float(innovation))
    utilization = min(
        INNOVATION_UTILIZATION_MAX, raw_abs / max(innovation_cap, 1e-9)
    )
    return {
        "slope": slope,
        "state": float(corrected_c),
        "raw_innovation_abs": raw_abs,
        "innovation_available": True,
        "innovation_utilization": float(utilization),
        "slope_utilization": min(1.0, abs(slope) / max(velocity_cap, 1e-9)),
        "innovation_clipped": bool(raw_abs > innovation_cap),
    }


def _damped_steps(horizon: int) -> float:
    return float(sum(DAMPING**k for k in range(horizon)))


def add_p8_continuity(
    raw: pd.DataFrame,
    velocity_caps: dict[str, float],
    innovation_caps: dict[str, float],
) -> pd.DataFrame:
    out = p1.add_reliability_state(p1.add_temporal_bridge(raw, max_gap=2)).copy()
    out["p8_available"] = out["p1_available"].astype(bool)
    out["p8_estimate_lateral_x_m"] = out["p1_estimate_lateral_x_m"]
    out["p8_estimate_altitude_m"] = out["p1_estimate_altitude_m"]
    out["p8_source"] = out["p1_source"].fillna("")
    out["p8_continuity_horizon"] = out["bridge_horizon"].astype(int)
    out["p8_lateral_slope_cap_utilization"] = 0.0
    out["p8_altitude_slope_cap_utilization"] = 0.0
    out["p8_anchor_innovation_lateral_abs"] = 0.0
    out["p8_anchor_innovation_altitude_abs"] = 0.0
    out["p8_lateral_innovation_cap_utilization"] = 0.0
    out["p8_altitude_innovation_cap_utilization"] = 0.0
    out["p8_anchor_innovation_available"] = False
    out["p8_lateral_innovation_clipped"] = False
    out["p8_altitude_innovation_clipped"] = False
    out["p8_unavailable_reason"] = ""

    for _, indices in out.groupby("sequence_id").groups.items():
        ordered = sorted(indices, key=lambda idx: int(out.loc[idx, "frame_index"]))
        anchors: list[tuple[int, float, float]] = []
        for idx in ordered:
            frame = int(out.loc[idx, "frame_index"])
            genuine = bool(out.loc[idx, "candidate_available"])
            if genuine:
                anchors.append(
                    (
                        frame,
                        float(out.loc[idx, "estimate_lateral_x_m"]),
                        float(out.loc[idx, "estimate_altitude_m"]),
                    )
                )
                anchors = anchors[-3:]

            lat_state = _axis_state(
                [(a[0], a[1]) for a in anchors],
                velocity_caps["lateral"],
                innovation_caps["lateral"],
            )
            alt_state = _axis_state(
                [(a[0], a[2]) for a in anchors],
                velocity_caps["altitude"],
                innovation_caps["altitude"],
            )
            out.loc[idx, "p8_lateral_slope_cap_utilization"] = lat_state["slope_utilization"]
            out.loc[idx, "p8_altitude_slope_cap_utilization"] = alt_state["slope_utilization"]
            out.loc[idx, "p8_anchor_innovation_lateral_abs"] = lat_state["raw_innovation_abs"]
            out.loc[idx, "p8_anchor_innovation_altitude_abs"] = alt_state["raw_innovation_abs"]
            out.loc[idx, "p8_lateral_innovation_cap_utilization"] = lat_state["innovation_utilization"]
            out.loc[idx, "p8_altitude_innovation_cap_utilization"] = alt_state["innovation_utilization"]
            out.loc[idx, "p8_anchor_innovation_available"] = bool(
                lat_state["innovation_available"] and alt_state["innovation_available"]
            )
            out.loc[idx, "p8_lateral_innovation_clipped"] = lat_state["innovation_clipped"]
            out.loc[idx, "p8_altitude_innovation_clipped"] = alt_state["innovation_clipped"]

            if genuine or bool(out.loc[idx, "p1_available"]):
                continue
            if len(anchors) < 2:
                out.loc[idx, "p8_unavailable_reason"] = "insufficient_anchors"
                continue
            horizon = frame - anchors[-1][0]
            if horizon <= 2:
                continue
            if horizon > MAX_CONTINUITY_GAP:
                out.loc[idx, "p8_unavailable_reason"] = "gap_beyond_horizon"
                continue

            step_sum = _damped_steps(horizon)
            pred_lat = float(lat_state["state"]) + float(lat_state["slope"]) * step_sum
            pred_alt = float(alt_state["state"]) + float(alt_state["slope"]) * step_sum
            out.loc[idx, "p8_available"] = True
            out.loc[idx, "p8_estimate_lateral_x_m"] = pred_lat
            out.loc[idx, "p8_estimate_altitude_m"] = pred_alt
            out.loc[idx, "p8_source"] = "innovation_clipped_continuity"
            out.loc[idx, "p8_continuity_horizon"] = horizon

    out["p8_lateral_abs_error_m"] = np.abs(
        out["p8_estimate_lateral_x_m"] - out["truth_lateral_x_m"]
    )
    out["p8_altitude_abs_error_m"] = np.abs(
        out["p8_estimate_altitude_m"] - out["truth_altitude_m"]
    )
    return out


def _available(df: pd.DataFrame) -> pd.Series:
    return df["p8_available"].astype(bool) & df["truth_visible"].astype(bool)


def _base_continuous_basis(df: pd.DataFrame) -> np.ndarray:
    risks = df[list(RISK_COLUMNS)].to_numpy(float)
    primary = risks[:, :7]
    ordered = np.sort(primary, axis=1)
    top1 = ordered[:, -1]
    top2 = ordered[:, -2]
    return np.column_stack(
        [
            risks,
            df["risk_score"].to_numpy(float),
            df["coactivation_count"].to_numpy(float) / 7.0,
            top1,
            top2,
            df["p8_continuity_horizon"].to_numpy(float),
            df["p8_lateral_slope_cap_utilization"].to_numpy(float),
            df["p8_altitude_slope_cap_utilization"].to_numpy(float),
            df["p8_anchor_innovation_lateral_abs"].to_numpy(float),
            df["p8_anchor_innovation_altitude_abs"].to_numpy(float),
            df["p8_lateral_innovation_cap_utilization"].to_numpy(float),
            df["p8_altitude_innovation_cap_utilization"].to_numpy(float),
            df["p8_anchor_innovation_available"].to_numpy(bool).astype(float),
        ]
    )


def _source_basis(df: pd.DataFrame) -> np.ndarray:
    source = df["p8_source"].fillna("").astype(str)
    return np.column_stack([(source == name).to_numpy(float) for name in SOURCE_NAMES])


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
    standardizer = _fit_standardizer(_base_continuous_basis(d))
    x = _base_design(d, standardizer)
    axes: dict[str, object] = {}
    for axis in ("lateral", "altitude"):
        raw_y = np.log(d[f"p8_{axis}_abs_error_m"].to_numpy(float) + 1e-4)
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
            df["p8_continuity_horizon"].to_numpy(float),
            df["p8_lateral_slope_cap_utilization"].to_numpy(float),
            df["p8_altitude_slope_cap_utilization"].to_numpy(float),
            df["p8_anchor_innovation_lateral_abs"].to_numpy(float),
            df["p8_anchor_innovation_altitude_abs"].to_numpy(float),
            df["p8_lateral_innovation_cap_utilization"].to_numpy(float),
            df["p8_altitude_innovation_cap_utilization"].to_numpy(float),
            df["p8_anchor_innovation_available"].to_numpy(bool).astype(float),
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
        _available(adaptation)
        & (adaptation["p8_source"].astype(str) == "innovation_clipped_continuity")
    ].copy()
    if len(d) < MIN_ADAPTATION_CONTINUITY_ROWS:
        raise RuntimeError(
            f"P8 adaptation continuity rows {len(d)} < {MIN_ADAPTATION_CONTINUITY_ROWS}"
        )
    standardizer = _fit_standardizer(_correction_basis(d))
    x = _correction_design(d, standardizer)
    base_scale = _base_predicted_scale(d, base_model)
    axes: dict[str, object] = {}
    for axis in ("lateral", "altitude"):
        ratio = d[f"p8_{axis}_abs_error_m"].to_numpy(float) / np.maximum(
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
    return {"rows": int(len(d)), "standardizer": standardizer, "axes": axes}


def _corrected_scale(
    df: pd.DataFrame,
    base_model: dict[str, object],
    correction_model: dict[str, object],
) -> dict[str, np.ndarray]:
    result = {axis: values.copy() for axis, values in _base_predicted_scale(df, base_model).items()}
    mask = df["p8_source"].astype(str).to_numpy() == "innovation_clipped_continuity"
    if not np.any(mask):
        return result
    d = df.loc[mask]
    x = _correction_design(d, correction_model["standardizer"])
    for axis in ("lateral", "altitude"):
        axis_model = correction_model["axes"][axis]
        log_corr = x @ np.asarray(axis_model["coefficients"], dtype=float)
        lo, hi = axis_model["prediction_guard_log_bounds"]
        result[axis][mask] *= np.exp(np.clip(log_corr, float(lo), float(hi)))
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
        normalized = d[f"p8_{axis}_abs_error_m"].to_numpy(float) / np.maximum(
            scale[axis], 1e-9
        )
        result[axis] = {
            f"{q:.2f}": _finite_conformal(normalized, q) for q in TARGETS
        }
    return result


def _transfer_group_series(df: pd.DataFrame) -> pd.Series:
    return pd.Series(
        np.where(
            df["p8_source"].astype(str).to_numpy() == "innovation_clipped_continuity",
            "innovation_clipped_continuity",
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
    d["p8_group"] = _transfer_group_series(d)
    counts = {group: int((d["p8_group"] == group).sum()) for group in TRANSFER_GROUPS}
    if counts["innovation_clipped_continuity"] < MIN_TRANSFER_CONTINUITY_ROWS:
        raise RuntimeError(
            f"P8 transfer continuity rows {counts['innovation_clipped_continuity']} < {MIN_TRANSFER_CONTINUITY_ROWS}"
        )
    if counts["base_output"] < MIN_TRANSFER_BASE_ROWS:
        raise RuntimeError(
            f"P8 transfer base rows {counts['base_output']} < {MIN_TRANSFER_BASE_ROWS}"
        )
    provisional_candidate = {
        "base_scale_model": base_model,
        "continuity_correction_model": correction_model,
        "single_factor_conformal": single,
    }
    result: dict[str, dict[str, dict[str, float]]] = {}
    for group in TRANSFER_GROUPS:
        g = d[d["p8_group"] == group].copy()
        result[group] = {}
        for axis in ("lateral", "altitude"):
            error = g[f"p8_{axis}_abs_error_m"].to_numpy(float)
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
    columns: list[np.ndarray] = []
    for q in TARGETS:
        provisional = _provisional_radius(df, candidate, axis, q)
        multipliers = np.asarray(
            [
                float(candidate["transfer_multipliers"][group][axis][f"{q:.2f}"])
                for group in groups
            ],
            dtype=float,
        )
        columns.append(provisional * multipliers)
    nested = np.maximum.accumulate(np.column_stack(columns), axis=1)
    return {f"{q:.2f}": nested[:, i] for i, q in enumerate(TARGETS)}


def _build_candidate(
    fit: pd.DataFrame,
    calibration: pd.DataFrame,
    adaptation: pd.DataFrame,
    transfer: pd.DataFrame,
    velocity_caps: dict[str, float],
    innovation_caps: dict[str, float],
    git_sha: str,
) -> dict[str, object]:
    base_model = _fit_base_models(fit)
    correction_model = _fit_continuity_correction(adaptation, base_model)
    single = _single_factor_calibration(calibration, base_model, correction_model)
    transfer_multipliers, transfer_counts = _fit_transfer_multipliers(
        transfer, base_model, correction_model, single
    )
    return {
        "schema": "aegisland.phase11.p8.candidate-freeze.v1",
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
            "innovation_cap_quantile": INNOVATION_CAP_QUANTILE,
            "innovation_utilization_max": INNOVATION_UTILIZATION_MAX,
            "blend_previous_slope": BLEND_PREVIOUS_SLOPE,
            "blend_corrected_slope": BLEND_CORRECTED_SLOPE,
        },
        "velocity_caps": velocity_caps,
        "innovation_caps": innovation_caps,
        "ridge_lambda": RIDGE_LAMBDA,
        "minimum_rows": {
            "adaptation_innovation_clipped_continuity": MIN_ADAPTATION_CONTINUITY_ROWS,
            "transfer_innovation_clipped_continuity": MIN_TRANSFER_CONTINUITY_ROWS,
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
        error = d[f"p8_{axis}_abs_error_m"].to_numpy(float)
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
        values = d[f"p8_{axis}_abs_error_m"].dropna().to_numpy(float)
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
        error = d[f"p8_{axis}_abs_error_m"].dropna().to_numpy(float)
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


def _secondary_diagnostics(evaluated: pd.DataFrame, candidate: dict[str, object]) -> dict[str, object]:
    continuity = evaluated[
        _available(evaluated)
        & (evaluated["p8_source"].astype(str) == "innovation_clipped_continuity")
    ].copy()
    unavailable = evaluated[~_available(evaluated)].copy()
    result: dict[str, object] = {
        "continuity_horizon_counts": {
            str(int(k)): int(v)
            for k, v in continuity["p8_continuity_horizon"].value_counts().sort_index().items()
        },
        "unavailable_reason_counts": {
            str(k): int(v)
            for k, v in unavailable["p8_unavailable_reason"].replace("", "other").value_counts().items()
        },
        "continuity_by_horizon": [],
        "innovation": {},
        "slope_cap_utilization": {},
        "fraction_any_innovation_clipped": float(
            np.mean(
                continuity["p8_lateral_innovation_clipped"].to_numpy(bool)
                | continuity["p8_altitude_innovation_clipped"].to_numpy(bool)
            )
        ) if len(continuity) else float("nan"),
    }
    for axis in ("lateral", "altitude"):
        innov = continuity[f"p8_anchor_innovation_{axis}_abs"].to_numpy(float)
        innov_util = continuity[f"p8_{axis}_innovation_cap_utilization"].to_numpy(float)
        slope_util = continuity[f"p8_{axis}_slope_cap_utilization"].to_numpy(float)
        result["innovation"][axis] = {
            "median_abs": float(np.median(innov)) if innov.size else float("nan"),
            "p95_abs": float(np.percentile(innov, 95)) if innov.size else float("nan"),
            "median_cap_utilization": float(np.median(innov_util)) if innov_util.size else float("nan"),
            "p95_cap_utilization": float(np.percentile(innov_util, 95)) if innov_util.size else float("nan"),
            "cap": float(candidate["innovation_caps"][axis]),
        }
        result["slope_cap_utilization"][axis] = {
            "median": float(np.median(slope_util)) if slope_util.size else float("nan"),
            "p95": float(np.percentile(slope_util, 95)) if slope_util.size else float("nan"),
            "fraction_ge_0_99": float(np.mean(slope_util >= 0.99)) if slope_util.size else float("nan"),
            "cap": float(candidate["velocity_caps"][axis]),
        }
    for horizon, group in continuity.groupby("p8_continuity_horizon"):
        row: dict[str, object] = {"horizon": int(horizon), "rows": int(len(group))}
        for axis in ("lateral", "altitude"):
            values = group[f"p8_{axis}_abs_error_m"].to_numpy(float)
            row[f"{axis}_mae"] = float(np.mean(values))
            row[f"{axis}_p95"] = float(np.percentile(values, 95))
        result["continuity_by_horizon"].append(row)
    return result


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
    continuity = _subset_stats(evaluated, candidate, "innovation_clipped_continuity")
    base = _subset_stats(evaluated, candidate, "base_output")

    h1 = {"available_fraction": errors["available_fraction"]}
    h1["pass"] = bool(h1["available_fraction"] >= 0.92)

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
        h4[f"{axis}_median_halfwidth_over_p95_error"] = intervals[axis]["median_halfwidth_95"] / p95_error
        h4[f"{axis}_p95_halfwidth_over_p95_error"] = intervals[axis]["p95_halfwidth_95"] / p95_error
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
        "h2_overall_coverage": h2,
        "h3_calibration_curve": h3,
        "h4_overall_interval_efficiency": h4,
        "h5_continuity_specific_honesty": h5,
        "h6_base_output_honesty": h6,
        "h7_shift_discrimination": h7,
    }
    primary = (
        "h1_useful_availability",
        "h2_overall_coverage",
        "h3_calibration_curve",
        "h4_overall_interval_efficiency",
        "h5_continuity_specific_honesty",
        "h6_base_output_honesty",
    )
    return {
        "schema": "aegisland.phase11.p8.result.v1",
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
        "continuity_stats": continuity,
        "base_output_stats": base,
        "secondary_diagnostics": _secondary_diagnostics(evaluated, candidate),
    }


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_manifest(out: Path, names: list[str], git_sha: str, stage: str) -> None:
    manifest = {
        "schema": "aegisland.phase11.p8.manifest.v1",
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
    velocity_caps = _fit_velocity_caps(fit_raw)
    innovation_caps = _fit_innovation_caps(fit_raw)
    fit = add_p8_continuity(fit_raw, velocity_caps, innovation_caps)
    calibration = add_p8_continuity(
        _raw("calibration", CALIBRATION_SEED, CALIBRATION_FAMILIES, FIT_DOMAINS),
        velocity_caps,
        innovation_caps,
    )
    adaptation = add_p8_continuity(
        _raw("adaptation", ADAPTATION_SEED, ADAPTATION_FAMILIES, ADAPTATION_DOMAINS),
        velocity_caps,
        innovation_caps,
    )
    transfer = add_p8_continuity(
        _raw("transfer", TRANSFER_SEED, TRANSFER_FAMILIES, TRANSFER_DOMAINS),
        velocity_caps,
        innovation_caps,
    )
    candidate = _build_candidate(
        fit,
        calibration,
        adaptation,
        transfer,
        velocity_caps,
        innovation_caps,
        git_sha,
    )
    result = summarize(
        transfer,
        calibration,
        candidate,
        "phase11_p8_seen_transfer_calibration",
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
    if candidate.get("schema") != "aegisland.phase11.p8.candidate-freeze.v1":
        raise SystemExit("invalid P8 candidate schema")
    if candidate.get("validation_seed_unseen_at_freeze") != VALIDATION_SEED:
        raise SystemExit("P8 validation seed mismatch")
    constants = candidate.get("continuity_constants", {})
    expected = {
        "max_continuity_gap": MAX_CONTINUITY_GAP,
        "damping": DAMPING,
        "velocity_cap_quantile": VELOCITY_CAP_QUANTILE,
        "innovation_cap_quantile": INNOVATION_CAP_QUANTILE,
        "innovation_utilization_max": INNOVATION_UTILIZATION_MAX,
        "blend_previous_slope": BLEND_PREVIOUS_SLOPE,
        "blend_corrected_slope": BLEND_CORRECTED_SLOPE,
    }
    for key, value in expected.items():
        if float(constants.get(key, float("nan"))) != float(value):
            raise SystemExit(f"P8 candidate constant changed: {key}")

    out.mkdir(parents=True, exist_ok=True)
    validation = add_p8_continuity(
        _raw("validation", VALIDATION_SEED, VALIDATION_FAMILIES, VALIDATION_DOMAINS),
        candidate["velocity_caps"],
        candidate["innovation_caps"],
    )
    calibration = add_p8_continuity(
        _raw("calibration", CALIBRATION_SEED, CALIBRATION_FAMILIES, FIT_DOMAINS),
        candidate["velocity_caps"],
        candidate["innovation_caps"],
    )
    result = summarize(
        validation,
        calibration,
        candidate,
        "phase11_p8_frozen_candidate_validation",
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
        description="Run preregistered Phase 11 P8 innovation-clipped continuity benchmark."
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
        print("P8_TRANSFER_GATES=" + json.dumps(result["gates"], sort_keys=True))
        return
    if args.candidate is None:
        raise SystemExit("--candidate is required for validation stage")
    result = validate(args.out, args.candidate, args.git_sha)
    print("P8_VALIDATION_GATES=" + json.dumps(result["gates"], sort_keys=True))


if __name__ == "__main__":
    main()
