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

FIT_SEED = 88088
CALIBRATION_SEED = 99099
TRANSFER_SEED = 101101
VALIDATION_SEED = 112112
FRAMES_PER_SEQUENCE = 60
TARGETS = (0.50, 0.68, 0.80, 0.90, 0.95)
FIT_FAMILIES = tuple(range(27, 33))
CALIBRATION_FAMILIES = tuple(range(33, 36))
TRANSFER_FAMILIES = tuple(range(36, 39))
VALIDATION_FAMILIES = tuple(range(39, 42))
FIT_DOMAINS = p1.FIT_DOMAINS
TRANSFER_DOMAINS = (
    "edge+dim",
    "small_scale+blur_noise",
    "oblique+low_contrast",
    "edge+temporal_dropout",
    "dim+blur_noise",
    "small_scale+oblique",
    "edge+low_contrast+temporal_dropout",
    "small_scale+dim+blur_noise",
)
VALIDATION_DOMAINS = (
    "edge+blur_noise",
    "small_scale+dim",
    "oblique+temporal_dropout",
    "blur_noise+low_contrast",
    "edge+small_scale+oblique",
    "dim+low_contrast+temporal_dropout",
    "edge+oblique+blur_noise+low_contrast",
    "small_scale+oblique+dim+temporal_dropout",
)
BUDGET_SCALE = 1.10
BUDGET_QUANTILE = 0.99


def _prepare(name: str, seed: int, families: tuple[int, ...], domains: tuple[str, ...]) -> pd.DataFrame:
    raw = p1.generate_split(name, seed, families, domains, frames=FRAMES_PER_SEQUENCE)
    return p1.add_reliability_state(p1.add_temporal_bridge(raw))


def _available(df: pd.DataFrame) -> pd.Series:
    return df["p1_available"].astype(bool) & df["truth_visible"].astype(bool)


def _finite_conformal(values: np.ndarray | pd.Series, q: float) -> float:
    arr = np.asarray(values, dtype=float)
    arr = np.sort(arr[np.isfinite(arr)])
    if arr.size == 0:
        return float("nan")
    k = int(math.ceil((arr.size + 1) * q))
    return float(arr[min(arr.size - 1, max(0, k - 1))])


def _single_factor_calibration(calibration: pd.DataFrame, models: dict[str, list[float]]) -> dict[str, dict[str, float]]:
    d = calibration[_available(calibration)].copy()
    mult = p1._multiplier(d)
    out: dict[str, dict[str, float]] = {}
    for axis in ("lateral", "altitude"):
        pred = p1._predicted_scale(d, models[axis])
        normalized = d[f"p1_{axis}_abs_error_m"].to_numpy(float) / np.maximum(pred * mult, 1e-9)
        out[axis] = {f"{q:.2f}": _finite_conformal(normalized, q) for q in TARGETS}
    return out


def _provisional_halfwidth(df: pd.DataFrame, models: dict[str, list[float]], q_single: dict[str, dict[str, float]], axis: str, q: float) -> np.ndarray:
    pred = p1._predicted_scale(df, models[axis])
    mult = p1._multiplier(df)
    return pred * mult * float(q_single[axis][f"{q:.2f}"])


def _transfer_calibration(transfer: pd.DataFrame, models: dict[str, list[float]], q_single: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    d = transfer[_available(transfer)].copy()
    out: dict[str, dict[str, float]] = {}
    for axis in ("lateral", "altitude"):
        out[axis] = {}
        error = d[f"p1_{axis}_abs_error_m"].to_numpy(float)
        for q in TARGETS:
            provisional = _provisional_halfwidth(d, models, q_single, axis, q)
            ratio = error / np.maximum(provisional, 1e-9)
            out[axis][f"{q:.2f}"] = _finite_conformal(ratio, q)
    return out


def _raw_final_halfwidth(df: pd.DataFrame, candidate: dict[str, object], axis: str, q: float) -> np.ndarray:
    models = candidate["scale_models"]
    q_single = candidate["single_factor_conformal"]
    transfer = candidate["transfer_multipliers"]
    return (
        _provisional_halfwidth(df, models, q_single, axis, q)
        * float(transfer[axis][f"{q:.2f}"])
    )


def final_halfwidths(df: pd.DataFrame, candidate: dict[str, object], axis: str) -> dict[str, np.ndarray]:
    raw = np.column_stack([_raw_final_halfwidth(df, candidate, axis, q) for q in TARGETS])
    nested = np.maximum.accumulate(raw, axis=1)
    return {f"{q:.2f}": nested[:, i] for i, q in enumerate(TARGETS)}


def _build_candidate(fit: pd.DataFrame, calibration: pd.DataFrame, transfer_df: pd.DataFrame, git_sha: str) -> dict[str, object]:
    models = p1.fit_scale_models(fit)
    q_single = _single_factor_calibration(calibration, models)
    transfer = _transfer_calibration(transfer_df, models, q_single)
    candidate: dict[str, object] = {
        "schema": "aegisland.phase11.p2.candidate-freeze.v1",
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
        "scale_models": models,
        "single_factor_conformal": q_single,
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


def _coverage(df: pd.DataFrame, candidate: dict[str, object], accepted: pd.Series) -> dict[str, dict[str, float]]:
    subset = df[accepted & _available(df)].copy()
    out: dict[str, dict[str, float]] = {}
    for axis in ("lateral", "altitude"):
        widths = final_halfwidths(subset, candidate, axis)
        error = subset[f"p1_{axis}_abs_error_m"].to_numpy(float)
        out[axis] = {
            f"{q:.2f}": float(np.mean(error <= widths[f"{q:.2f}"])) if len(error) else float("nan")
            for q in TARGETS
        }
    return out


def _interval_stats(df: pd.DataFrame, candidate: dict[str, object], accepted: pd.Series) -> dict[str, dict[str, float]]:
    subset = df[accepted & _available(df)].copy()
    out = {}
    for axis in ("lateral", "altitude"):
        hw = final_halfwidths(subset, candidate, axis)["0.95"]
        out[axis] = {
            "median_halfwidth_95": float(np.median(hw)) if len(hw) else float("nan"),
            "p95_halfwidth_95": float(np.percentile(hw, 95)) if len(hw) else float("nan"),
        }
    return out


def _error_stats(df: pd.DataFrame, accepted: pd.Series) -> dict[str, float]:
    available = _available(df)
    mask = accepted & available
    d = df[mask]
    result = {
        "preselection_available_fraction": float(available.mean()),
        "usable_availability": float(mask.mean()),
        "retention_conditional_on_available": float(mask.sum() / max(1, available.sum())),
    }
    for axis in ("lateral", "altitude"):
        values = d[f"p1_{axis}_abs_error_m"].dropna().to_numpy(float)
        result[f"{axis}_mae"] = float(np.mean(values)) if values.size else float("nan")
        result[f"{axis}_p95"] = float(np.percentile(values, 95)) if values.size else float("nan")
    return result


def _budget_accept(df: pd.DataFrame, candidate: dict[str, object]) -> pd.Series:
    available = _available(df)
    lateral = final_halfwidths(df, candidate, "lateral")["0.95"]
    altitude = final_halfwidths(df, candidate, "altitude")["0.95"]
    budgets = candidate["uncertainty_budget_halfwidth_95"]
    return pd.Series(
        available.to_numpy(bool)
        & (lateral <= float(budgets["lateral"]))
        & (altitude <= float(budgets["altitude"])),
        index=df.index,
    )


def _auc(labels: np.ndarray, scores: np.ndarray) -> float:
    pos = scores[labels == 1]
    neg = scores[labels == 0]
    if not len(pos) or not len(neg):
        return float("nan")
    wins = sum(float(np.sum(p > neg)) + 0.5 * float(np.sum(p == neg)) for p in pos)
    return float(wins / (len(pos) * len(neg)))


def _shift_auc(calibration: pd.DataFrame, evaluated: pd.DataFrame) -> float:
    known = calibration.groupby("sequence_id", as_index=False)["severity"].mean(); known["label"] = 0
    shifted = evaluated.groupby("sequence_id", as_index=False)["severity"].mean(); shifted["label"] = 1
    combined = pd.concat([known, shifted], ignore_index=True)
    return _auc(combined["label"].to_numpy(int), combined["severity"].to_numpy(float))


def summarize(evaluated: pd.DataFrame, calibration_df: pd.DataFrame, candidate: dict[str, object], role: str, seed: int) -> dict[str, object]:
    all_available = pd.Series(True, index=evaluated.index)
    budget_accept = _budget_accept(evaluated, candidate)
    coverage_all = _coverage(evaluated, candidate, all_available)
    coverage_selected = _coverage(evaluated, candidate, budget_accept)
    intervals = _interval_stats(evaluated, candidate, all_available)
    all_errors = _error_stats(evaluated, all_available)
    selected_errors = _error_stats(evaluated, budget_accept)

    h1 = {
        "lateral_95_coverage": coverage_all["lateral"]["0.95"],
        "altitude_95_coverage": coverage_all["altitude"]["0.95"],
    }
    h1["pass"] = bool(0.90 <= h1["lateral_95_coverage"] <= 0.98 and 0.90 <= h1["altitude_95_coverage"] <= 0.98)

    mace = float(np.mean([
        abs(coverage_all[axis][f"{q:.2f}"] - q)
        for axis in ("lateral", "altitude") for q in TARGETS
    ]))
    h2 = {"mean_absolute_coverage_error": mace, "pass": bool(mace <= 0.06)}

    h3 = {}
    for axis in ("lateral", "altitude"):
        p95_error = all_errors[f"{axis}_p95"]
        h3[f"{axis}_median_halfwidth_over_p95_error"] = intervals[axis]["median_halfwidth_95"] / p95_error
        h3[f"{axis}_p95_halfwidth_over_p95_error"] = intervals[axis]["p95_halfwidth_95"] / p95_error
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
    h4["pass"] = bool(
        h4["retention_conditional_on_available"] >= 0.90
        and h4["truth_visible_usable_availability"] >= 0.80
        and h4["lateral_p95_nonworsening"]
        and h4["altitude_p95_nonworsening"]
    )

    auc = _shift_auc(calibration_df, evaluated)
    h5 = {"trajectory_level_auroc": auc, "pass": bool(auc >= 0.85)}
    gates = {
        "h1_full_availability_coverage_transfer": h1,
        "h2_calibration_curve": h2,
        "h3_interval_efficiency": h3,
        "h4_uncertainty_budget_availability": h4,
        "h5_shift_discrimination": h5,
    }
    return {
        "schema": "aegisland.phase11.p2.result.v1",
        "evidence_role": role,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "evaluated_seed_seen_after_run": seed,
        "all_primary_gates_pass": bool(all(g["pass"] for g in gates.values())),
        "gates": gates,
        "coverage_all_available": coverage_all,
        "coverage_after_budget": coverage_selected,
        "interval_stats_all_available": intervals,
        "error_stats_all_available": all_errors,
        "error_stats_after_budget": selected_errors,
    }


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def freeze(out: Path, git_sha: str) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    fit = _prepare("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS)
    calibration = _prepare("calibration", CALIBRATION_SEED, CALIBRATION_FAMILIES, FIT_DOMAINS)
    transfer_df = _prepare("transfer", TRANSFER_SEED, TRANSFER_FAMILIES, TRANSFER_DOMAINS)
    candidate = _build_candidate(fit, calibration, transfer_df, git_sha)
    transfer_result = summarize(transfer_df, calibration, candidate, "phase11_p2_seen_transfer_calibration", TRANSFER_SEED)

    fit.to_csv(out / "fit_frames.csv", index=False)
    calibration.to_csv(out / "calibration_frames.csv", index=False)
    transfer_df.to_csv(out / "transfer_frames.csv", index=False)
    (out / "candidate_freeze.json").write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "transfer_result.json").write_text(json.dumps(transfer_result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("P2_CANDIDATE_FREEZE_JSON=" + json.dumps(candidate, sort_keys=True))
    print("P2_TRANSFER_GATES=" + json.dumps(transfer_result["gates"], sort_keys=True))
    return candidate


def validate(out: Path, candidate_path: Path, git_sha: str) -> dict[str, object]:
    if not candidate_path.exists():
        raise SystemExit("validation requires a committed candidate-freeze JSON")
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    if int(candidate.get("validation_seed_unseen_at_freeze", -1)) != VALIDATION_SEED:
        raise SystemExit("candidate freeze does not match P2 validation seed")

    out.mkdir(parents=True, exist_ok=True)
    calibration = _prepare("calibration", CALIBRATION_SEED, CALIBRATION_FAMILIES, FIT_DOMAINS)
    validation = _prepare("validation", VALIDATION_SEED, VALIDATION_FAMILIES, VALIDATION_DOMAINS)
    result = summarize(validation, calibration, candidate, "phase11_p2_frozen_candidate_validation", VALIDATION_SEED)
    result["git_sha"] = git_sha
    validation.to_csv(out / "validation_frames.csv", index=False)
    (out / "validation_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("P2_VALIDATION_GATES=" + json.dumps(result["gates"], sort_keys=True))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 11 P2 composition-calibrated uncertainty benchmark")
    parser.add_argument("--stage", choices=("freeze", "validation"), required=True)
    parser.add_argument("--out", type=Path, default=Path("results/phase11_p2"))
    parser.add_argument("--candidate", type=Path, default=Path("results/phase11_p2/candidate_freeze.json"))
    parser.add_argument("--git-sha", default="unknown")
    args = parser.parse_args()
    if args.stage == "freeze":
        freeze(args.out, args.git_sha)
    else:
        validate(args.out, args.candidate, args.git_sha)


if __name__ == "__main__":
    main()
