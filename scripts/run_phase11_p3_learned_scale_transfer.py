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

FIT_SEED = 121121
CALIBRATION_SEED = 132132
TRANSFER_SEED = 143143
VALIDATION_SEED = 154154
FRAMES_PER_SEQUENCE = 60
TARGETS = (0.50, 0.68, 0.80, 0.90, 0.95)
RIDGE_LAMBDA = 2.0
FIT_FAMILIES = tuple(range(42, 48))
CALIBRATION_FAMILIES = tuple(range(48, 51))
TRANSFER_FAMILIES = tuple(range(51, 54))
VALIDATION_FAMILIES = tuple(range(54, 57))
FIT_DOMAINS = p1.FIT_DOMAINS
TRANSFER_DOMAINS = (
    "edge+blur_noise",
    "small_scale+dim",
    "oblique+temporal_dropout",
    "blur_noise+low_contrast",
    "edge+small_scale+dim",
    "small_scale+oblique+temporal_dropout",
    "edge+dim+low_contrast",
    "oblique+blur_noise+temporal_dropout",
)
VALIDATION_DOMAINS = (
    "edge+small_scale",
    "oblique+dim",
    "blur_noise+temporal_dropout",
    "edge+oblique+low_contrast",
    "small_scale+blur_noise+low_contrast",
    "edge+dim+temporal_dropout",
    "small_scale+oblique+dim+blur_noise",
    "edge+small_scale+oblique+temporal_dropout+low_contrast",
)
BUDGET_QUANTILE = 0.99
BUDGET_SCALE = 1.10
RISK_COLUMNS = tuple(f"risk_{name}" for name in ("edge", "scale", "oblique", "dim", "blur", "contrast", "temporal", "track"))


def _prepare(name: str, seed: int, families: tuple[int, ...], domains: tuple[str, ...]) -> pd.DataFrame:
    raw = p1.generate_split(name, seed, families, domains, frames=FRAMES_PER_SEQUENCE)
    return p1.add_reliability_state(p1.add_temporal_bridge(raw))


def _available(df: pd.DataFrame) -> pd.Series:
    return df["p1_available"].astype(bool) & df["truth_visible"].astype(bool)


def _scale_basis(df: pd.DataFrame) -> np.ndarray:
    risks = df[list(RISK_COLUMNS)].to_numpy(float)
    primary = risks[:, :7]
    sorted_primary = np.sort(primary, axis=1)
    top1 = sorted_primary[:, -1]
    top2 = sorted_primary[:, -2]
    risk = df["risk_score"].to_numpy(float)
    coactivation = df["coactivation_count"].to_numpy(float) / 7.0
    bridge = df["bridge_horizon"].to_numpy(float)
    source = df["p1_source"].fillna("").astype(str)
    return np.column_stack([
        np.ones(len(df)),
        risks,
        risk,
        risk * risk,
        coactivation,
        coactivation * coactivation,
        top1,
        top2,
        bridge,
        bridge * risk,
        (source == "partial_edge").to_numpy(float),
        (source == "phase9_center_regeometry").to_numpy(float),
        (source == "known_aruco_refined").to_numpy(float),
        (source == "temporal_bridge").to_numpy(float),
    ])


def _ridge_fit(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    penalty = np.eye(x.shape[1], dtype=float)
    penalty[0, 0] = 0.0
    return np.linalg.solve(x.T @ x + RIDGE_LAMBDA * penalty, x.T @ y)


def _fit_models(fit: pd.DataFrame) -> dict[str, list[float]]:
    d = fit[_available(fit)].copy()
    x = _scale_basis(d)
    models = {}
    for axis in ("lateral", "altitude"):
        y = np.log(d[f"p1_{axis}_abs_error_m"].to_numpy(float) + 1e-4)
        models[axis] = _ridge_fit(x, y).tolist()
    return models


def _predicted_scale(df: pd.DataFrame, coefficients: list[float]) -> np.ndarray:
    return np.exp(_scale_basis(df) @ np.asarray(coefficients, dtype=float))


def _finite_conformal(values: np.ndarray | pd.Series, q: float) -> float:
    arr = np.asarray(values, dtype=float)
    arr = np.sort(arr[np.isfinite(arr)])
    if arr.size == 0:
        return float("nan")
    k = int(math.ceil((arr.size + 1) * q))
    return float(arr[min(arr.size - 1, max(0, k - 1))])


def _single_factor_calibration(calibration: pd.DataFrame, models: dict[str, list[float]]) -> dict[str, dict[str, float]]:
    d = calibration[_available(calibration)].copy()
    output = {}
    for axis in ("lateral", "altitude"):
        predicted = _predicted_scale(d, models[axis])
        normalized = d[f"p1_{axis}_abs_error_m"].to_numpy(float) / np.maximum(predicted, 1e-9)
        output[axis] = {f"{q:.2f}": _finite_conformal(normalized, q) for q in TARGETS}
    return output


def _provisional(df: pd.DataFrame, candidate: dict[str, object], axis: str, q: float) -> np.ndarray:
    return (
        _predicted_scale(df, candidate["scale_models"][axis])
        * float(candidate["single_factor_conformal"][axis][f"{q:.2f}"])
    )


def _transfer_calibration(transfer_df: pd.DataFrame, models: dict[str, list[float]], single: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    d = transfer_df[_available(transfer_df)].copy()
    candidate = {"scale_models": models, "single_factor_conformal": single}
    output = {}
    for axis in ("lateral", "altitude"):
        error = d[f"p1_{axis}_abs_error_m"].to_numpy(float)
        output[axis] = {}
        for q in TARGETS:
            provisional = _provisional(d, candidate, axis, q)
            ratio = error / np.maximum(provisional, 1e-9)
            output[axis][f"{q:.2f}"] = _finite_conformal(ratio, q)
    return output


def final_halfwidths(df: pd.DataFrame, candidate: dict[str, object], axis: str) -> dict[str, np.ndarray]:
    columns = []
    for q in TARGETS:
        columns.append(
            _provisional(df, candidate, axis, q)
            * float(candidate["transfer_multipliers"][axis][f"{q:.2f}"])
        )
    nested = np.maximum.accumulate(np.column_stack(columns), axis=1)
    return {f"{q:.2f}": nested[:, i] for i, q in enumerate(TARGETS)}


def _build_candidate(fit: pd.DataFrame, calibration: pd.DataFrame, transfer_df: pd.DataFrame, git_sha: str) -> dict[str, object]:
    models = _fit_models(fit)
    single = _single_factor_calibration(calibration, models)
    transfer = _transfer_calibration(transfer_df, models, single)
    candidate: dict[str, object] = {
        "schema": "aegisland.phase11.p3.candidate-freeze.v1",
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
        "scale_basis": [
            "intercept", *RISK_COLUMNS, "risk_score", "risk_score_sq",
            "coactivation_norm", "coactivation_norm_sq", "top1_primary_risk",
            "top2_primary_risk", "bridge_horizon", "bridge_x_risk",
            "source_partial_edge", "source_regeometry", "source_known_aruco_refined",
            "source_temporal_bridge",
        ],
        "scale_models": models,
        "single_factor_conformal": single,
        "transfer_multipliers": transfer,
        "budget_rule": {"quantile": BUDGET_QUANTILE, "scale": BUDGET_SCALE},
    }
    d = transfer_df[_available(transfer_df)].copy()
    budgets = {}
    for axis in ("lateral", "altitude"):
        hw = final_halfwidths(d, candidate, axis)["0.95"]
        budgets[axis] = BUDGET_SCALE * float(np.quantile(hw, BUDGET_QUANTILE))
    candidate["uncertainty_budget_halfwidth_95"] = budgets
    return candidate


def _budget_accept(df: pd.DataFrame, candidate: dict[str, object]) -> pd.Series:
    available = _available(df).to_numpy(bool)
    lateral = final_halfwidths(df, candidate, "lateral")["0.95"]
    altitude = final_halfwidths(df, candidate, "altitude")["0.95"]
    budget = candidate["uncertainty_budget_halfwidth_95"]
    return pd.Series(
        available
        & (lateral <= float(budget["lateral"]))
        & (altitude <= float(budget["altitude"])),
        index=df.index,
    )


def _coverage(df: pd.DataFrame, candidate: dict[str, object], accepted: pd.Series) -> dict[str, dict[str, float]]:
    d = df[accepted & _available(df)].copy()
    output = {}
    for axis in ("lateral", "altitude"):
        widths = final_halfwidths(d, candidate, axis)
        error = d[f"p1_{axis}_abs_error_m"].to_numpy(float)
        output[axis] = {f"{q:.2f}": float(np.mean(error <= widths[f"{q:.2f}"])) if error.size else float("nan") for q in TARGETS}
    return output


def _error_stats(df: pd.DataFrame, accepted: pd.Series) -> dict[str, float]:
    available = _available(df)
    mask = accepted & available
    d = df[mask]
    output = {
        "preselection_available_fraction": float(available.mean()),
        "usable_availability": float(mask.mean()),
        "retention_conditional_on_available": float(mask.sum() / max(1, available.sum())),
    }
    for axis in ("lateral", "altitude"):
        values = d[f"p1_{axis}_abs_error_m"].dropna().to_numpy(float)
        output[f"{axis}_mae"] = float(np.mean(values)) if values.size else float("nan")
        output[f"{axis}_p95"] = float(np.percentile(values, 95)) if values.size else float("nan")
    return output


def _interval_stats(df: pd.DataFrame, candidate: dict[str, object]) -> dict[str, dict[str, float]]:
    d = df[_available(df)].copy()
    output = {}
    for axis in ("lateral", "altitude"):
        hw = final_halfwidths(d, candidate, axis)["0.95"]
        output[axis] = {
            "median_halfwidth_95": float(np.median(hw)),
            "p95_halfwidth_95": float(np.percentile(hw, 95)),
        }
    return output


def _auc(labels: np.ndarray, scores: np.ndarray) -> float:
    positive, negative = scores[labels == 1], scores[labels == 0]
    if not len(positive) or not len(negative):
        return float("nan")
    wins = sum(float(np.sum(score > negative)) + 0.5 * float(np.sum(score == negative)) for score in positive)
    return float(wins / (len(positive) * len(negative)))


def _shift_auc(calibration: pd.DataFrame, evaluated: pd.DataFrame) -> float:
    a = calibration.groupby("sequence_id", as_index=False)["severity"].mean(); a["label"] = 0
    b = evaluated.groupby("sequence_id", as_index=False)["severity"].mean(); b["label"] = 1
    joined = pd.concat([a, b], ignore_index=True)
    return _auc(joined["label"].to_numpy(int), joined["severity"].to_numpy(float))


def summarize(evaluated: pd.DataFrame, calibration_df: pd.DataFrame, candidate: dict[str, object], role: str, seed: int) -> dict[str, object]:
    accept_all = pd.Series(True, index=evaluated.index)
    accept_budget = _budget_accept(evaluated, candidate)
    coverage = _coverage(evaluated, candidate, accept_all)
    selected_coverage = _coverage(evaluated, candidate, accept_budget)
    all_errors = _error_stats(evaluated, accept_all)
    selected_errors = _error_stats(evaluated, accept_budget)
    intervals = _interval_stats(evaluated, candidate)

    h1 = {"lateral_95_coverage": coverage["lateral"]["0.95"], "altitude_95_coverage": coverage["altitude"]["0.95"]}
    h1["pass"] = bool(0.90 <= h1["lateral_95_coverage"] <= 0.98 and 0.90 <= h1["altitude_95_coverage"] <= 0.98)

    mace = float(np.mean([abs(coverage[axis][f"{q:.2f}"] - q) for axis in ("lateral", "altitude") for q in TARGETS]))
    h2 = {"mean_absolute_coverage_error": mace, "pass": bool(mace <= 0.06)}

    h3 = {}
    for axis in ("lateral", "altitude"):
        p95 = all_errors[f"{axis}_p95"]
        h3[f"{axis}_median_halfwidth_over_p95_error"] = intervals[axis]["median_halfwidth_95"] / p95
        h3[f"{axis}_p95_halfwidth_over_p95_error"] = intervals[axis]["p95_halfwidth_95"] / p95
    h3["pass"] = bool(
        h3["lateral_median_halfwidth_over_p95_error"] <= 1.25
        and h3["altitude_median_halfwidth_over_p95_error"] <= 1.25
        and h3["lateral_p95_halfwidth_over_p95_error"] <= 2.25
        and h3["altitude_p95_halfwidth_over_p95_error"] <= 2.25
    )

    h4 = {
        "retention_conditional_on_available": selected_errors["retention_conditional_on_available"],
        "truth_visible_usable_availability": selected_errors["usable_availability"],
        "lateral_p95_nonworsening": selected_errors["lateral_p95"] <= all_errors["lateral_p95"],
        "altitude_p95_nonworsening": selected_errors["altitude_p95"] <= all_errors["altitude_p95"],
    }
    h4["pass"] = bool(h4["retention_conditional_on_available"] >= 0.90 and h4["truth_visible_usable_availability"] >= 0.80 and h4["lateral_p95_nonworsening"] and h4["altitude_p95_nonworsening"])

    h5 = {"trajectory_level_auroc": _shift_auc(calibration_df, evaluated)}
    h5["pass"] = bool(h5["trajectory_level_auroc"] >= 0.85)
    gates = {
        "h1_full_availability_coverage": h1,
        "h2_calibration_curve": h2,
        "h3_interval_tail_efficiency": h3,
        "h4_uncertainty_budget_usefulness": h4,
        "h5_shift_discrimination": h5,
    }
    return {
        "schema": "aegisland.phase11.p3.result.v1",
        "evidence_role": role,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "evaluated_seed_seen_after_run": seed,
        "all_primary_gates_pass": bool(all(g["pass"] for g in gates.values())),
        "gates": gates,
        "coverage_all_available": coverage,
        "coverage_after_budget": selected_coverage,
        "interval_stats_all_available": intervals,
        "error_stats_all_available": all_errors,
        "error_stats_after_budget": selected_errors,
    }


def freeze(out: Path, git_sha: str) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    fit = _prepare("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS)
    calibration = _prepare("calibration", CALIBRATION_SEED, CALIBRATION_FAMILIES, FIT_DOMAINS)
    transfer_df = _prepare("transfer", TRANSFER_SEED, TRANSFER_FAMILIES, TRANSFER_DOMAINS)
    candidate = _build_candidate(fit, calibration, transfer_df, git_sha)
    transfer_result = summarize(transfer_df, calibration, candidate, "phase11_p3_seen_transfer_calibration", TRANSFER_SEED)
    fit.to_csv(out / "fit_frames.csv", index=False)
    calibration.to_csv(out / "calibration_frames.csv", index=False)
    transfer_df.to_csv(out / "transfer_frames.csv", index=False)
    (out / "candidate_freeze.json").write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "transfer_result.json").write_text(json.dumps(transfer_result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("P3_CANDIDATE_FREEZE_JSON=" + json.dumps(candidate, sort_keys=True))
    print("P3_TRANSFER_GATES=" + json.dumps(transfer_result["gates"], sort_keys=True))
    return candidate


def validate(out: Path, candidate_path: Path, git_sha: str) -> dict[str, object]:
    if not candidate_path.exists():
        raise SystemExit("validation requires committed P3 candidate freeze JSON")
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    if int(candidate.get("validation_seed_unseen_at_freeze", -1)) != VALIDATION_SEED:
        raise SystemExit("candidate freeze does not match P3 validation seed")
    out.mkdir(parents=True, exist_ok=True)
    calibration = _prepare("calibration", CALIBRATION_SEED, CALIBRATION_FAMILIES, FIT_DOMAINS)
    validation = _prepare("validation", VALIDATION_SEED, VALIDATION_FAMILIES, VALIDATION_DOMAINS)
    result = summarize(validation, calibration, candidate, "phase11_p3_frozen_candidate_validation", VALIDATION_SEED)
    result["git_sha"] = git_sha
    validation.to_csv(out / "validation_frames.csv", index=False)
    (out / "validation_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("P3_VALIDATION_GATES=" + json.dumps(result["gates"], sort_keys=True))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 11 P3 learned-scale composition transfer benchmark")
    parser.add_argument("--stage", choices=("freeze", "validation"), required=True)
    parser.add_argument("--out", type=Path, default=Path("results/phase11_p3"))
    parser.add_argument("--candidate", type=Path, default=Path("results/phase11_p3/candidate_freeze.json"))
    parser.add_argument("--git-sha", default="unknown")
    args = parser.parse_args()
    if args.stage == "freeze":
        freeze(args.out, args.git_sha)
    else:
        validate(args.out, args.candidate, args.git_sha)


if __name__ == "__main__":
    main()
