from __future__ import annotations

import argparse
import json
import math
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scripts import run_phase11_p1_adaptive_reliability as p1
except ModuleNotFoundError:
    import run_phase11_p1_adaptive_reliability as p1

FIT_SEED = 209209
CALIBRATION_SEED = 220220
TRANSFER_SEED = 231231
VALIDATION_SEED = 242242
FRAMES_PER_SEQUENCE = 60
TARGETS = (0.50, 0.68, 0.80, 0.90, 0.95)
RIDGE_LAMBDA = 4.0
MAX_CONTINUITY_GAP = 5
DAMPING = 0.85
VELOCITY_CAP_QUANTILE = 0.99

FIT_FAMILIES = tuple(range(72, 78))
CALIBRATION_FAMILIES = tuple(range(78, 81))
TRANSFER_FAMILIES = tuple(range(81, 84))
VALIDATION_FAMILIES = tuple(range(84, 87))

FIT_DOMAINS = p1.FIT_DOMAINS
TRANSFER_DOMAINS = (
    "edge+temporal_dropout",
    "small_scale+dim",
    "oblique+blur_noise",
    "dim+low_contrast",
    "edge+small_scale+temporal_dropout",
    "oblique+blur_noise+low_contrast",
    "edge+dim+blur_noise",
    "small_scale+oblique+low_contrast",
)
VALIDATION_DOMAINS = (
    "edge+blur_noise",
    "small_scale+temporal_dropout",
    "oblique+dim",
    "blur_noise+low_contrast+temporal_dropout",
    "edge+small_scale+oblique",
    "small_scale+dim+blur_noise",
    "edge+oblique+low_contrast+temporal_dropout",
    "edge+small_scale+oblique+dim+blur_noise",
)

RISK_COLUMNS = tuple(
    f"risk_{name}"
    for name in ("edge", "scale", "oblique", "dim", "blur", "contrast", "temporal", "track")
)


def _generate_raw(name: str, seed: int, families: tuple[int, ...], domains: tuple[str, ...]) -> pd.DataFrame:
    return p1.generate_split(name, seed, families, domains, frames=FRAMES_PER_SEQUENCE)


def _fit_velocity_caps(raw_fit: pd.DataFrame) -> dict[str, float]:
    slopes = {"lateral": [], "altitude": []}
    for _, g in raw_fit.groupby("sequence_id"):
        d = g[g["candidate_available"]].sort_values("frame_index")
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
    result = {}
    for axis in ("lateral", "altitude"):
        arr = np.asarray(slopes[axis], dtype=float)
        arr = arr[np.isfinite(arr)]
        if not arr.size:
            raise RuntimeError(f"no finite {axis} anchor slopes in P5 fit split")
        result[axis] = float(max(1e-6, np.quantile(arr, VELOCITY_CAP_QUANTILE)))
    return result


def _local_slope(anchors: list[tuple[int, float, float]], caps: dict[str, float]) -> tuple[float, float]:
    if len(anchors) < 2:
        return 0.0, 0.0
    recent = anchors[-3:]
    lat_slopes: list[float] = []
    alt_slopes: list[float] = []
    for left, right in zip(recent, recent[1:]):
        dt = right[0] - left[0]
        if dt <= 0:
            continue
        lat_slopes.append((right[1] - left[1]) / dt)
        alt_slopes.append((right[2] - left[2]) / dt)
    if not lat_slopes:
        return 0.0, 0.0
    lat = float(np.median(np.asarray(lat_slopes, dtype=float)))
    alt = float(np.median(np.asarray(alt_slopes, dtype=float)))
    lat = float(np.clip(lat, -caps["lateral"], caps["lateral"]))
    alt = float(np.clip(alt, -caps["altitude"], caps["altitude"]))
    return lat, alt


def _damped_steps(horizon: int) -> float:
    return float(sum(DAMPING**k for k in range(horizon)))


def add_p5_continuity(raw: pd.DataFrame, velocity_caps: dict[str, float]) -> pd.DataFrame:
    base = p1.add_reliability_state(p1.add_temporal_bridge(raw, max_gap=2)).copy()
    base["p5_available"] = base["p1_available"].astype(bool)
    base["p5_estimate_lateral_x_m"] = base["p1_estimate_lateral_x_m"]
    base["p5_estimate_altitude_m"] = base["p1_estimate_altitude_m"]
    base["p5_source"] = base["p1_source"].fillna("")
    base["p5_continuity_horizon"] = base["bridge_horizon"].astype(int)
    base["p5_local_lateral_slope_abs"] = 0.0
    base["p5_local_altitude_slope_abs"] = 0.0

    for _, indices in base.groupby("sequence_id").groups.items():
        ordered = sorted(indices, key=lambda i: int(base.loc[i, "frame_index"]))
        anchors: list[tuple[int, float, float]] = []
        for i in ordered:
            frame = int(base.loc[i, "frame_index"])
            genuine = bool(base.loc[i, "candidate_available"])
            if genuine:
                anchors.append(
                    (
                        frame,
                        float(base.loc[i, "estimate_lateral_x_m"]),
                        float(base.loc[i, "estimate_altitude_m"]),
                    )
                )
                anchors = anchors[-3:]
                continue

            lat_v, alt_v = _local_slope(anchors, velocity_caps)
            if bool(base.loc[i, "p1_available"]):
                base.loc[i, "p5_local_lateral_slope_abs"] = abs(lat_v)
                base.loc[i, "p5_local_altitude_slope_abs"] = abs(alt_v)
                continue

            if len(anchors) < 2:
                continue
            horizon = frame - anchors[-1][0]
            if horizon <= 2 or horizon > MAX_CONTINUITY_GAP:
                continue

            step_sum = _damped_steps(horizon)
            pred_lat = anchors[-1][1] + lat_v * step_sum
            pred_alt = anchors[-1][2] + alt_v * step_sum

            base.loc[i, "p5_available"] = True
            base.loc[i, "p5_estimate_lateral_x_m"] = pred_lat
            base.loc[i, "p5_estimate_altitude_m"] = pred_alt
            base.loc[i, "p5_source"] = "continuity_extension"
            base.loc[i, "p5_continuity_horizon"] = horizon
            base.loc[i, "p5_local_lateral_slope_abs"] = abs(lat_v)
            base.loc[i, "p5_local_altitude_slope_abs"] = abs(alt_v)

    base["p5_lateral_abs_error_m"] = np.abs(
        base["p5_estimate_lateral_x_m"] - base["truth_lateral_x_m"]
    )
    base["p5_altitude_abs_error_m"] = np.abs(
        base["p5_estimate_altitude_m"] - base["truth_altitude_m"]
    )
    return base


def _available(df: pd.DataFrame) -> pd.Series:
    return df["p5_available"].astype(bool) & df["truth_visible"].astype(bool)


def _continuous_basis(df: pd.DataFrame) -> np.ndarray:
    risks = df[list(RISK_COLUMNS)].to_numpy(float)
    primary = risks[:, :7]
    ordered = np.sort(primary, axis=1)
    top1 = ordered[:, -1]
    top2 = ordered[:, -2]
    risk = df["risk_score"].to_numpy(float)
    coactivation = df["coactivation_count"].to_numpy(float) / 7.0
    horizon = df["p5_continuity_horizon"].to_numpy(float)
    lat_slope = df["p5_local_lateral_slope_abs"].to_numpy(float)
    alt_slope = df["p5_local_altitude_slope_abs"].to_numpy(float)
    return np.column_stack(
        [risks, risk, coactivation, top1, top2, horizon, lat_slope, alt_slope]
    )


def _source_basis(df: pd.DataFrame) -> np.ndarray:
    source = df["p5_source"].fillna("").astype(str)
    return np.column_stack(
        [
            (source == "partial_edge").to_numpy(float),
            (source == "phase9_center_regeometry").to_numpy(float),
            (source == "known_aruco_refined").to_numpy(float),
            (source == "temporal_bridge").to_numpy(float),
            (source == "continuity_extension").to_numpy(float),
        ]
    )


def _fit_standardizer(df: pd.DataFrame) -> dict[str, list[float]]:
    x = _continuous_basis(df)
    mean = x.mean(axis=0)
    std = x.std(axis=0)
    std = np.where(std < 1e-6, 1.0, std)
    return {"mean": mean.tolist(), "std": std.tolist()}


def _design(df: pd.DataFrame, standardizer: dict[str, list[float]]) -> np.ndarray:
    cont = _continuous_basis(df)
    mean = np.asarray(standardizer["mean"], dtype=float)
    std = np.asarray(standardizer["std"], dtype=float)
    z = (cont - mean) / std
    return np.column_stack([np.ones(len(df)), z, _source_basis(df)])


def _ridge_fit(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    penalty = np.eye(x.shape[1], dtype=float)
    penalty[0, 0] = 0.0
    return np.linalg.solve(x.T @ x + RIDGE_LAMBDA * penalty, x.T @ y)


def _fit_models(fit: pd.DataFrame) -> dict[str, object]:
    d = fit[_available(fit)].copy()
    standardizer = _fit_standardizer(d)
    x = _design(d, standardizer)
    axes: dict[str, object] = {}
    for axis in ("lateral", "altitude"):
        raw_y = np.log(d[f"p5_{axis}_abs_error_m"].to_numpy(float) + 1e-4)
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


def _predicted_scale(df: pd.DataFrame, model: dict[str, object]) -> dict[str, np.ndarray]:
    x = _design(df, model["standardizer"])
    result: dict[str, np.ndarray] = {}
    for axis in ("lateral", "altitude"):
        axis_model = model["axes"][axis]
        log_scale = x @ np.asarray(axis_model["coefficients"], dtype=float)
        lo, hi = axis_model["prediction_guard_log_bounds"]
        result[axis] = np.exp(np.clip(log_scale, float(lo), float(hi)))
    return result


def _finite_conformal(values: np.ndarray | pd.Series, q: float) -> float:
    arr = np.asarray(values, dtype=float)
    arr = np.sort(arr[np.isfinite(arr)])
    if arr.size == 0:
        return float("nan")
    k = int(math.ceil((arr.size + 1) * q))
    return float(arr[min(arr.size - 1, max(0, k - 1))])


def _single_factor_calibration(
    calibration: pd.DataFrame, model: dict[str, object]
) -> dict[str, dict[str, float]]:
    d = calibration[_available(calibration)].copy()
    predicted = _predicted_scale(d, model)
    result: dict[str, dict[str, float]] = {}
    for axis in ("lateral", "altitude"):
        normalized = d[f"p5_{axis}_abs_error_m"].to_numpy(float) / np.maximum(
            predicted[axis], 1e-9
        )
        result[axis] = {
            f"{q:.2f}": _finite_conformal(normalized, q) for q in TARGETS
        }
    return result


def _provisional(
    df: pd.DataFrame, candidate: dict[str, object], axis: str, q: float
) -> np.ndarray:
    predicted = _predicted_scale(df, candidate["scale_model"])[axis]
    return predicted * float(candidate["single_factor_conformal"][axis][f"{q:.2f}"])


def _transfer_calibration(
    transfer_df: pd.DataFrame,
    model: dict[str, object],
    single: dict[str, dict[str, float]],
) -> dict[str, dict[str, float]]:
    d = transfer_df[_available(transfer_df)].copy()
    provisional_candidate = {
        "scale_model": model,
        "single_factor_conformal": single,
    }
    result: dict[str, dict[str, float]] = {}
    for axis in ("lateral", "altitude"):
        error = d[f"p5_{axis}_abs_error_m"].to_numpy(float)
        result[axis] = {}
        for q in TARGETS:
            radius = _provisional(d, provisional_candidate, axis, q)
            result[axis][f"{q:.2f}"] = _finite_conformal(
                error / np.maximum(radius, 1e-9), q
            )
    return result


def final_halfwidths(
    df: pd.DataFrame, candidate: dict[str, object], axis: str
) -> dict[str, np.ndarray]:
    cols = []
    for q in TARGETS:
        cols.append(
            _provisional(df, candidate, axis, q)
            * float(candidate["transfer_multipliers"][axis][f"{q:.2f}"])
        )
    nested = np.maximum.accumulate(np.column_stack(cols), axis=1)
    return {f"{q:.2f}": nested[:, i] for i, q in enumerate(TARGETS)}


def _build_candidate(
    fit: pd.DataFrame,
    calibration: pd.DataFrame,
    transfer_df: pd.DataFrame,
    velocity_caps: dict[str, float],
    git_sha: str,
) -> dict[str, object]:
    model = _fit_models(fit)
    single = _single_factor_calibration(calibration, model)
    transfer = _transfer_calibration(transfer_df, model, single)
    return {
        "schema": "aegisland.phase11.p5.candidate-freeze.v1",
        "git_sha": git_sha,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "validation_seed_unseen_at_freeze": VALIDATION_SEED,
        "fit_seed": FIT_SEED,
        "calibration_seed": CALIBRATION_SEED,
        "transfer_seed": TRANSFER_SEED,
        "fit_families": list(FIT_FAMILIES),
        "calibration_families": list(CALIBRATION_FAMILIES),
        "transfer_families": list(TRANSFER_FAMILIES),
        "validation_families": list(VALIDATION_FAMILIES),
        "max_continuity_gap": MAX_CONTINUITY_GAP,
        "damping": DAMPING,
        "velocity_cap_quantile": VELOCITY_CAP_QUANTILE,
        "velocity_caps": velocity_caps,
        "ridge_lambda": RIDGE_LAMBDA,
        "continuous_basis": [
            *RISK_COLUMNS,
            "risk_score",
            "coactivation_norm",
            "top1_primary_risk",
            "top2_primary_risk",
            "continuity_horizon",
            "local_lateral_slope_abs",
            "local_altitude_slope_abs",
        ],
        "source_basis": [
            "partial_edge",
            "phase9_center_regeometry",
            "known_aruco_refined",
            "temporal_bridge",
            "continuity_extension",
        ],
        "scale_model": model,
        "single_factor_conformal": single,
        "transfer_multipliers": transfer,
    }


def _coverage(
    df: pd.DataFrame, candidate: dict[str, object]
) -> dict[str, dict[str, float]]:
    d = df[_available(df)].copy()
    result: dict[str, dict[str, float]] = {}
    for axis in ("lateral", "altitude"):
        widths = final_halfwidths(d, candidate, axis)
        error = d[f"p5_{axis}_abs_error_m"].to_numpy(float)
        result[axis] = {
            f"{q:.2f}": float(np.mean(error <= widths[f"{q:.2f}"]))
            if error.size
            else float("nan")
            for q in TARGETS
        }
    return result


def _error_stats(df: pd.DataFrame) -> dict[str, float]:
    available = _available(df)
    d = df[available]
    result = {
        "available_fraction": float(available.mean()),
        "available_rows": int(available.sum()),
        "total_rows": int(len(df)),
    }
    for axis in ("lateral", "altitude"):
        values = d[f"p5_{axis}_abs_error_m"].dropna().to_numpy(float)
        result[f"{axis}_mae"] = (
            float(np.mean(values)) if values.size else float("nan")
        )
        result[f"{axis}_p95"] = (
            float(np.percentile(values, 95)) if values.size else float("nan")
        )
    return result


def _interval_stats(
    df: pd.DataFrame, candidate: dict[str, object]
) -> dict[str, dict[str, float]]:
    d = df[_available(df)].copy()
    result: dict[str, dict[str, float]] = {}
    for axis in ("lateral", "altitude"):
        hw = final_halfwidths(d, candidate, axis)["0.95"]
        result[axis] = {
            "median_halfwidth_95": float(np.median(hw))
            if hw.size
            else float("nan"),
            "p95_halfwidth_95": float(np.percentile(hw, 95))
            if hw.size
            else float("nan"),
        }
    return result


def _continuity_stats(
    df: pd.DataFrame, candidate: dict[str, object]
) -> dict[str, object]:
    d = df[
        _available(df) & (df["p5_source"].astype(str) == "continuity_extension")
    ].copy()
    result: dict[str, object] = {
        "rows": int(len(d)),
        "fraction_of_truth_visible": float(len(d) / len(df)) if len(df) else float("nan"),
        "coverage_95": {},
        "p95_error": {},
        "p95_halfwidth": {},
        "p95_halfwidth_over_p95_error": {},
    }
    for axis in ("lateral", "altitude"):
        err = d[f"p5_{axis}_abs_error_m"].dropna().to_numpy(float)
        if not err.size:
            result["coverage_95"][axis] = float("nan")
            result["p95_error"][axis] = float("nan")
            result["p95_halfwidth"][axis] = float("nan")
            result["p95_halfwidth_over_p95_error"][axis] = float("nan")
            continue
        hw = final_halfwidths(d, candidate, axis)["0.95"]
        p95_err = float(np.percentile(err, 95))
        p95_hw = float(np.percentile(hw, 95))
        result["coverage_95"][axis] = float(np.mean(err <= hw))
        result["p95_error"][axis] = p95_err
        result["p95_halfwidth"][axis] = p95_hw
        result["p95_halfwidth_over_p95_error"][axis] = (
            p95_hw / p95_err if p95_err > 0 else float("nan")
        )
    return result


def _auc(labels: np.ndarray, scores: np.ndarray) -> float:
    positive, negative = scores[labels == 1], scores[labels == 0]
    if not len(positive) or not len(negative):
        return float("nan")
    wins = sum(
        float(np.sum(score > negative)) + 0.5 * float(np.sum(score == negative))
        for score in positive
    )
    return float(wins / (len(positive) * len(negative)))


def _shift_auc(calibration: pd.DataFrame, evaluated: pd.DataFrame) -> float:
    a = calibration.groupby("sequence_id", as_index=False)["severity"].mean()
    a["label"] = 0
    b = evaluated.groupby("sequence_id", as_index=False)["severity"].mean()
    b["label"] = 1
    combined = pd.concat([a, b], ignore_index=True)
    return _auc(
        combined["label"].to_numpy(int), combined["severity"].to_numpy(float)
    )


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
    continuity = _continuity_stats(evaluated, candidate)

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
        p95 = errors[f"{axis}_p95"]
        h4[f"{axis}_median_halfwidth_over_p95_error"] = (
            intervals[axis]["median_halfwidth_95"] / p95
        )
        h4[f"{axis}_p95_halfwidth_over_p95_error"] = (
            intervals[axis]["p95_halfwidth_95"] / p95
        )
    h4["pass"] = bool(
        h4["lateral_median_halfwidth_over_p95_error"] <= 1.25
        and h4["altitude_median_halfwidth_over_p95_error"] <= 1.25
        and h4["lateral_p95_halfwidth_over_p95_error"] <= 2.25
        and h4["altitude_p95_halfwidth_over_p95_error"] <= 2.25
    )

    h5 = {
        "continuity_rows": continuity["rows"],
        "lateral_95_coverage": continuity["coverage_95"]["lateral"],
        "altitude_95_coverage": continuity["coverage_95"]["altitude"],
        "lateral_p95_halfwidth_over_p95_error": continuity[
            "p95_halfwidth_over_p95_error"
        ]["lateral"],
        "altitude_p95_halfwidth_over_p95_error": continuity[
            "p95_halfwidth_over_p95_error"
        ]["altitude"],
    }
    h5["pass"] = bool(
        h5["continuity_rows"] > 0
        and 0.88 <= h5["lateral_95_coverage"] <= 0.99
        and 0.88 <= h5["altitude_95_coverage"] <= 0.99
        and h5["lateral_p95_halfwidth_over_p95_error"] <= 2.75
        and h5["altitude_p95_halfwidth_over_p95_error"] <= 2.75
    )

    h6 = {"trajectory_level_auroc": _shift_auc(calibration_df, evaluated)}
    h6["pass"] = bool(h6["trajectory_level_auroc"] >= 0.85)

    gates = {
        "h1_useful_availability": h1,
        "h2_coverage_transfer": h2,
        "h3_calibration_curve": h3,
        "h4_interval_efficiency": h4,
        "h5_continuity_specific_honesty": h5,
        "h6_shift_discrimination": h6,
    }
    primary_names = (
        "h1_useful_availability",
        "h2_coverage_transfer",
        "h3_calibration_curve",
        "h4_interval_efficiency",
        "h5_continuity_specific_honesty",
    )
    return {
        "schema": "aegisland.phase11.p5.result.v1",
        "evidence_role": role,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "evaluated_seed_seen_after_run": seed,
        "all_primary_gates_pass": bool(all(gates[name]["pass"] for name in primary_names)),
        "gates": gates,
        "coverage": coverage,
        "interval_stats": intervals,
        "error_stats": errors,
        "continuity_stats": continuity,
    }


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_manifest(out: Path, names: list[str], git_sha: str, stage: str) -> None:
    manifest = {
        "schema": "aegisland.phase11.p5.manifest.v1",
        "stage": stage,
        "git_sha": git_sha,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "files": {
            name: {
                "sha256": _hash_file(out / name),
                "bytes": (out / name).stat().st_size,
            }
            for name in names
        },
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def freeze(out: Path, git_sha: str) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    fit_raw = _generate_raw("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS)
    caps = _fit_velocity_caps(fit_raw)
    fit = add_p5_continuity(fit_raw, caps)

    cal_raw = _generate_raw(
        "calibration", CALIBRATION_SEED, CALIBRATION_FAMILIES, FIT_DOMAINS
    )
    transfer_raw = _generate_raw(
        "transfer", TRANSFER_SEED, TRANSFER_FAMILIES, TRANSFER_DOMAINS
    )
    calibration = add_p5_continuity(cal_raw, caps)
    transfer_df = add_p5_continuity(transfer_raw, caps)

    candidate = _build_candidate(
        fit, calibration, transfer_df, caps, git_sha
    )
    transfer_result = summarize(
        transfer_df,
        calibration,
        candidate,
        "phase11_p5_seen_transfer_calibration",
        TRANSFER_SEED,
    )

    fit.to_csv(out / "fit_frames.csv", index=False)
    calibration.to_csv(out / "calibration_frames.csv", index=False)
    transfer_df.to_csv(out / "transfer_frames.csv", index=False)
    (out / "candidate_freeze.json").write_text(
        json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "transfer_result.json").write_text(
        json.dumps(transfer_result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_manifest(
        out,
        [
            "fit_frames.csv",
            "calibration_frames.csv",
            "transfer_frames.csv",
            "candidate_freeze.json",
            "transfer_result.json",
        ],
        git_sha,
        "freeze",
    )
    return transfer_result


def validate(out: Path, candidate_path: Path, git_sha: str) -> dict[str, object]:
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    if candidate.get("schema") != "aegisland.phase11.p5.candidate-freeze.v1":
        raise SystemExit("invalid P5 candidate schema")
    if candidate.get("validation_seed_unseen_at_freeze") != VALIDATION_SEED:
        raise SystemExit("candidate validation seed mismatch")
    if candidate.get("max_continuity_gap") != MAX_CONTINUITY_GAP:
        raise SystemExit("candidate continuity horizon mismatch")
    if float(candidate.get("damping")) != DAMPING:
        raise SystemExit("candidate damping mismatch")

    out.mkdir(parents=True, exist_ok=True)
    validation_raw = _generate_raw(
        "validation", VALIDATION_SEED, VALIDATION_FAMILIES, VALIDATION_DOMAINS
    )
    validation = add_p5_continuity(validation_raw, candidate["velocity_caps"])

    calibration_raw = _generate_raw(
        "calibration", CALIBRATION_SEED, CALIBRATION_FAMILIES, FIT_DOMAINS
    )
    calibration = add_p5_continuity(
        calibration_raw, candidate["velocity_caps"]
    )

    result = summarize(
        validation,
        calibration,
        candidate,
        "phase11_p5_frozen_candidate_validation",
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
        description="Run the preregistered Phase 11 P5 perception-continuity benchmark."
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
        print("P5_TRANSFER_GATES=" + json.dumps(result["gates"], sort_keys=True))
        print(
            "P5_CANDIDATE_FREEZE_JSON="
            + (args.out / "candidate_freeze.json").read_text(encoding="utf-8").strip()
        )
        return
    if args.candidate is None:
        raise SystemExit("--candidate is required for validation stage")
    result = validate(args.out, args.candidate, args.git_sha)
    print("P5_VALIDATION_GATES=" + json.dumps(result["gates"], sort_keys=True))


if __name__ == "__main__":
    main()
