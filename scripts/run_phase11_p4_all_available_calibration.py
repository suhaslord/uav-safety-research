from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scripts import run_phase11_p1_adaptive_reliability as p1
except ModuleNotFoundError:
    import run_phase11_p1_adaptive_reliability as p1

FIT_SEED = 165165
CALIBRATION_SEED = 176176
TRANSFER_SEED = 187187
VALIDATION_SEED = 198198
FRAMES_PER_SEQUENCE = 60
TARGETS = (0.50, 0.68, 0.80, 0.90, 0.95)
RIDGE_LAMBDA = 4.0
FIT_FAMILIES = tuple(range(57, 63))
CALIBRATION_FAMILIES = tuple(range(63, 66))
TRANSFER_FAMILIES = tuple(range(66, 69))
VALIDATION_FAMILIES = tuple(range(69, 72))
FIT_DOMAINS = p1.FIT_DOMAINS
TRANSFER_DOMAINS = (
    "edge+small_scale",
    "oblique+dim",
    "blur_noise+temporal_dropout",
    "small_scale+low_contrast",
    "edge+oblique+blur_noise",
    "small_scale+dim+temporal_dropout",
    "edge+blur_noise+low_contrast",
    "oblique+dim+low_contrast",
)
VALIDATION_DOMAINS = (
    "edge+oblique",
    "small_scale+temporal_dropout",
    "dim+low_contrast",
    "edge+small_scale+blur_noise",
    "oblique+dim+temporal_dropout",
    "small_scale+blur_noise+low_contrast",
    "edge+oblique+dim+low_contrast",
    "edge+small_scale+oblique+blur_noise+temporal_dropout",
)
RISK_COLUMNS = tuple(f"risk_{name}" for name in ("edge", "scale", "oblique", "dim", "blur", "contrast", "temporal", "track"))


def _prepare(name: str, seed: int, families: tuple[int, ...], domains: tuple[str, ...]) -> pd.DataFrame:
    raw = p1.generate_split(name, seed, families, domains, frames=FRAMES_PER_SEQUENCE)
    return p1.add_reliability_state(p1.add_temporal_bridge(raw))


def _available(df: pd.DataFrame) -> pd.Series:
    return df["p1_available"].astype(bool) & df["truth_visible"].astype(bool)


def _continuous_basis(df: pd.DataFrame) -> np.ndarray:
    risks = df[list(RISK_COLUMNS)].to_numpy(float)
    primary = risks[:, :7]
    ordered = np.sort(primary, axis=1)
    top1 = ordered[:, -1]
    top2 = ordered[:, -2]
    risk = df["risk_score"].to_numpy(float)
    coactivation = df["coactivation_count"].to_numpy(float) / 7.0
    bridge = df["bridge_horizon"].to_numpy(float)
    return np.column_stack([risks, risk, coactivation, top1, top2, bridge])


def _source_basis(df: pd.DataFrame) -> np.ndarray:
    source = df["p1_source"].fillna("").astype(str)
    return np.column_stack([
        (source == "partial_edge").to_numpy(float),
        (source == "phase9_center_regeometry").to_numpy(float),
        (source == "known_aruco_refined").to_numpy(float),
        (source == "temporal_bridge").to_numpy(float),
    ])


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
    axes = {}
    for axis in ("lateral", "altitude"):
        raw_y = np.log(d[f"p1_{axis}_abs_error_m"].to_numpy(float) + 1e-4)
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


def _predicted_scale(df: pd.DataFrame, model: dict[str, object]) -> np.ndarray:
    x = _design(df, model["standardizer"])
    out = {}
    for axis in ("lateral", "altitude"):
        axis_model = model["axes"][axis]
        log_scale = x @ np.asarray(axis_model["coefficients"], dtype=float)
        lo, hi = axis_model["prediction_guard_log_bounds"]
        out[axis] = np.exp(np.clip(log_scale, float(lo), float(hi)))
    return out


def _finite_conformal(values: np.ndarray | pd.Series, q: float) -> float:
    arr = np.asarray(values, dtype=float)
    arr = np.sort(arr[np.isfinite(arr)])
    if arr.size == 0:
        return float("nan")
    k = int(math.ceil((arr.size + 1) * q))
    return float(arr[min(arr.size - 1, max(0, k - 1))])


def _single_factor_calibration(calibration: pd.DataFrame, model: dict[str, object]) -> dict[str, dict[str, float]]:
    d = calibration[_available(calibration)].copy()
    predicted = _predicted_scale(d, model)
    result = {}
    for axis in ("lateral", "altitude"):
        normalized = d[f"p1_{axis}_abs_error_m"].to_numpy(float) / np.maximum(predicted[axis], 1e-9)
        result[axis] = {f"{q:.2f}": _finite_conformal(normalized, q) for q in TARGETS}
    return result


def _provisional(df: pd.DataFrame, candidate: dict[str, object], axis: str, q: float) -> np.ndarray:
    predicted = _predicted_scale(df, candidate["scale_model"])[axis]
    return predicted * float(candidate["single_factor_conformal"][axis][f"{q:.2f}"])


def _transfer_calibration(transfer_df: pd.DataFrame, model: dict[str, object], single: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    d = transfer_df[_available(transfer_df)].copy()
    provisional_candidate = {"scale_model": model, "single_factor_conformal": single}
    result = {}
    for axis in ("lateral", "altitude"):
        error = d[f"p1_{axis}_abs_error_m"].to_numpy(float)
        result[axis] = {}
        for q in TARGETS:
            radius = _provisional(d, provisional_candidate, axis, q)
            result[axis][f"{q:.2f}"] = _finite_conformal(error / np.maximum(radius, 1e-9), q)
    return result


def final_halfwidths(df: pd.DataFrame, candidate: dict[str, object], axis: str) -> dict[str, np.ndarray]:
    cols = []
    for q in TARGETS:
        cols.append(_provisional(df, candidate, axis, q) * float(candidate["transfer_multipliers"][axis][f"{q:.2f}"]))
    nested = np.maximum.accumulate(np.column_stack(cols), axis=1)
    return {f"{q:.2f}": nested[:, i] for i, q in enumerate(TARGETS)}


def _build_candidate(fit: pd.DataFrame, calibration: pd.DataFrame, transfer_df: pd.DataFrame, git_sha: str) -> dict[str, object]:
    model = _fit_models(fit)
    single = _single_factor_calibration(calibration, model)
    transfer = _transfer_calibration(transfer_df, model, single)
    return {
        "schema": "aegisland.phase11.p4.candidate-freeze.v1",
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
        "ridge_lambda": RIDGE_LAMBDA,
        "continuous_basis": [*RISK_COLUMNS, "risk_score", "coactivation_norm", "top1_primary_risk", "top2_primary_risk", "bridge_horizon"],
        "source_basis": ["partial_edge", "phase9_center_regeometry", "known_aruco_refined", "temporal_bridge"],
        "scale_model": model,
        "single_factor_conformal": single,
        "transfer_multipliers": transfer,
    }


def _coverage(df: pd.DataFrame, candidate: dict[str, object]) -> dict[str, dict[str, float]]:
    d = df[_available(df)].copy()
    out = {}
    for axis in ("lateral", "altitude"):
        widths = final_halfwidths(d, candidate, axis)
        error = d[f"p1_{axis}_abs_error_m"].to_numpy(float)
        out[axis] = {f"{q:.2f}": float(np.mean(error <= widths[f"{q:.2f}"])) if error.size else float("nan") for q in TARGETS}
    return out


def _error_stats(df: pd.DataFrame) -> dict[str, float]:
    available = _available(df)
    d = df[available]
    result = {"preselection_available_fraction": float(available.mean())}
    for axis in ("lateral", "altitude"):
        values = d[f"p1_{axis}_abs_error_m"].dropna().to_numpy(float)
        result[f"{axis}_mae"] = float(np.mean(values)) if values.size else float("nan")
        result[f"{axis}_p95"] = float(np.percentile(values, 95)) if values.size else float("nan")
    return result


def _interval_stats(df: pd.DataFrame, candidate: dict[str, object]) -> dict[str, dict[str, float]]:
    d = df[_available(df)].copy()
    result = {}
    for axis in ("lateral", "altitude"):
        hw = final_halfwidths(d, candidate, axis)["0.95"]
        result[axis] = {"median_halfwidth_95": float(np.median(hw)), "p95_halfwidth_95": float(np.percentile(hw, 95))}
    return result


def _auc(labels: np.ndarray, scores: np.ndarray) -> float:
    positive, negative = scores[labels == 1], scores[labels == 0]
    if not len(positive) or not len(negative):
        return float("nan")
    wins = sum(float(np.sum(score > negative)) + 0.5 * float(np.sum(score == negative)) for score in positive)
    return float(wins / (len(positive) * len(negative)))


def _shift_auc(calibration: pd.DataFrame, evaluated: pd.DataFrame) -> float:
    a = calibration.groupby("sequence_id", as_index=False)["severity"].mean(); a["label"] = 0
    b = evaluated.groupby("sequence_id", as_index=False)["severity"].mean(); b["label"] = 1
    combined = pd.concat([a, b], ignore_index=True)
    return _auc(combined["label"].to_numpy(int), combined["severity"].to_numpy(float))


def summarize(evaluated: pd.DataFrame, calibration_df: pd.DataFrame, candidate: dict[str, object], role: str, seed: int) -> dict[str, object]:
    coverage = _coverage(evaluated, candidate)
    errors = _error_stats(evaluated)
    intervals = _interval_stats(evaluated, candidate)
    h1 = {"lateral_95_coverage": coverage["lateral"]["0.95"], "altitude_95_coverage": coverage["altitude"]["0.95"]}
    h1["pass"] = bool(0.90 <= h1["lateral_95_coverage"] <= 0.98 and 0.90 <= h1["altitude_95_coverage"] <= 0.98)
    mace = float(np.mean([abs(coverage[axis][f"{q:.2f}"] - q) for axis in ("lateral", "altitude") for q in TARGETS]))
    h2 = {"mean_absolute_coverage_error": mace, "pass": bool(mace <= 0.06)}
    h3 = {}
    for axis in ("lateral", "altitude"):
        p95 = errors[f"{axis}_p95"]
        h3[f"{axis}_median_halfwidth_over_p95_error"] = intervals[axis]["median_halfwidth_95"] / p95
        h3[f"{axis}_p95_halfwidth_over_p95_error"] = intervals[axis]["p95_halfwidth_95"] / p95
    h3["pass"] = bool(
        h3["lateral_median_halfwidth_over_p95_error"] <= 1.25
        and h3["altitude_median_halfwidth_over_p95_error"] <= 1.25
        and h3["lateral_p95_halfwidth_over_p95_error"] <= 2.25
        and h3["altitude_p95_halfwidth_over_p95_error"] <= 2.25
    )
    h4 = {"preselection_available_fraction": errors["preselection_available_fraction"], "pass": bool(errors["preselection_available_fraction"] >= 0.90)}
    h5 = {"trajectory_level_auroc": _shift_auc(calibration_df, evaluated)}
    h5["pass"] = bool(h5["trajectory_level_auroc"] >= 0.85)
    gates = {"h1_coverage_transfer": h1, "h2_calibration_curve": h2, "h3_interval_efficiency": h3, "h4_availability": h4, "h5_shift_discrimination": h5}
    return {
        "schema": "aegisland.phase11.p4.result.v1",
        "evidence_role": role,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "evaluated_seed_seen_after_run": seed,
        "all_primary_gates_pass": bool(all(g["pass"] for g in gates.values())),
        "gates": gates,
        "coverage": coverage,
        "interval_stats": intervals,
        "error_stats": errors,
    }


def freeze(out: Path, git_sha: str) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    fit = _prepare("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS)
    calibration = _prepare("calibration", CALIBRATION_SEED, CALIBRATION_FAMILIES, FIT_DOMAINS)
    transfer_df = _prepare("transfer", TRANSFER_SEED, TRANSFER_FAMILIES, TRANSFER_DOMAINS)
    candidate = _build_candidate(fit, calibration, transfer_df, git_sha)
    transfer_result = summarize(transfer_df, calibration, candidate, "phase11_p4_seen_transfer_calibration", TRANSFER_SEED)
    fit.to_csv(out / "fit_frames.csv", index=False)
    calibration.to_csv(out / "calibration_frames.csv", index=False)
    transfer_df.to_csv(out / "transfer_frames.csv", index=False)
    (out / "candidate_freeze.json").write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "transfer_result.json").write_text(json.dumps(transfer_result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("P4_CANDIDATE_FREEZE_JSON=" + json.dumps(candidate, sort_keys=True))
    print("P4_TRANSFER_GATES=" + json.dumps(transfer_result["gates"], sort_keys=True))
    return candidate


def validate(out: Path, candidate_path: Path, git_sha: str) -> dict[str, object]:
    if not candidate_path.exists():
        raise SystemExit("validation requires committed P4 candidate-freeze JSON")
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    if int(candidate.get("validation_seed_unseen_at_freeze", -1)) != VALIDATION_SEED:
        raise SystemExit("candidate freeze does not match P4 validation seed")
    out.mkdir(parents=True, exist_ok=True)
    calibration = _prepare("calibration", CALIBRATION_SEED, CALIBRATION_FAMILIES, FIT_DOMAINS)
    validation = _prepare("validation", VALIDATION_SEED, VALIDATION_FAMILIES, VALIDATION_DOMAINS)
    result = summarize(validation, calibration, candidate, "phase11_p4_frozen_candidate_validation", VALIDATION_SEED)
    result["git_sha"] = git_sha
    validation.to_csv(out / "validation_frames.csv", index=False)
    (out / "validation_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("P4_VALIDATION_GATES=" + json.dumps(result["gates"], sort_keys=True))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 11 P4 all-available calibrated uncertainty benchmark")
    parser.add_argument("--stage", choices=("freeze", "validation"), required=True)
    parser.add_argument("--out", type=Path, default=Path("results/phase11_p4"))
    parser.add_argument("--candidate", type=Path, default=Path("results/phase11_p4/candidate_freeze.json"))
    parser.add_argument("--git-sha", default="unknown")
    args = parser.parse_args()
    if args.stage == "freeze":
        freeze(args.out, args.git_sha)
    else:
        validate(args.out, args.candidate, args.git_sha)


if __name__ == "__main__":
    main()
