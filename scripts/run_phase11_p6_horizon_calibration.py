from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scripts import run_phase11_p1_adaptive_reliability as p1
    from scripts import run_phase11_p5_calibrated_continuity as p5
except ModuleNotFoundError:
    import run_phase11_p1_adaptive_reliability as p1
    import run_phase11_p5_calibrated_continuity as p5

FIT_SEED = 253253
CALIBRATION_SEED = 264264
TRANSFER_SEED = 275275
DEVELOPMENT_SEED = 286286
VALIDATION_SEED = 297297
FRAMES_PER_SEQUENCE = 60
TARGETS = (0.50, 0.68, 0.80, 0.90, 0.95)
FIT_FAMILIES = tuple(range(87, 93))
CALIBRATION_FAMILIES = tuple(range(93, 96))
TRANSFER_FAMILIES = tuple(range(96, 99))
DEVELOPMENT_FAMILIES = tuple(range(99, 102))
VALIDATION_FAMILIES = tuple(range(102, 105))
FIT_DOMAINS = p1.FIT_DOMAINS
TRANSFER_DOMAINS = (
    "edge+temporal_dropout",
    "dim+temporal_dropout",
    "blur_noise+temporal_dropout",
    "small_scale+temporal_dropout",
    "edge+blur_noise",
    "oblique+dim",
    "edge+small_scale+temporal_dropout",
    "oblique+blur_noise+temporal_dropout",
)
DEVELOPMENT_DOMAINS = (
    "edge+dim",
    "small_scale+blur_noise",
    "oblique+low_contrast",
    "edge+low_contrast+temporal_dropout",
    "small_scale+dim+temporal_dropout",
    "edge+oblique+blur_noise",
    "dim+blur_noise+temporal_dropout",
    "edge+small_scale+oblique+low_contrast+temporal_dropout",
)
VALIDATION_DOMAINS = (
    "edge+small_scale",
    "oblique+temporal_dropout",
    "dim+low_contrast",
    "edge+blur_noise+temporal_dropout",
    "small_scale+oblique+dim",
    "blur_noise+low_contrast+temporal_dropout",
    "edge+oblique+dim+low_contrast",
    "edge+small_scale+oblique+blur_noise+temporal_dropout",
)
MIN_GROUP_COUNT = 40


def _raw(name: str, seed: int, families: tuple[int, ...], domains: tuple[str, ...]) -> pd.DataFrame:
    return p1.generate_split(name, seed, families, domains, frames=FRAMES_PER_SEQUENCE)


def _prepare(raw: pd.DataFrame, velocity_caps: dict[str, float]) -> pd.DataFrame:
    return p1.add_reliability_state(p5.add_continuity_bridge(raw, velocity_caps))


def _available(df: pd.DataFrame) -> pd.Series:
    return df["p1_available"].astype(bool) & df["truth_visible"].astype(bool)


def _group(df: pd.DataFrame) -> pd.Series:
    return pd.Series(np.where(df["bridge_horizon"].to_numpy(int) >= 3, "long", "direct_short"), index=df.index)


def _finite_conformal(values: np.ndarray | pd.Series, q: float) -> float:
    arr = np.asarray(values, dtype=float)
    arr = np.sort(arr[np.isfinite(arr)])
    if arr.size == 0:
        return float("nan")
    k = int(math.ceil((arr.size + 1) * q))
    return float(arr[min(arr.size - 1, max(0, k - 1))])


def _provisional(df: pd.DataFrame, scale_model: dict[str, object], single: dict[str, dict[str, float]], axis: str, q: float) -> np.ndarray:
    return p5.predicted_scale(df, scale_model, axis) * float(single[axis][f"{q:.2f}"])


def _horizon_transfer(transfer: pd.DataFrame, scale_model: dict[str, object], single: dict[str, dict[str, float]]) -> tuple[dict[str, dict[str, dict[str, float]]], dict[str, int]]:
    d = transfer[_available(transfer)].copy()
    groups = _group(d)
    counts = {name: int((groups == name).sum()) for name in ("direct_short", "long")}
    if counts["long"] < MIN_GROUP_COUNT or counts["direct_short"] < MIN_GROUP_COUNT:
        raise ValueError(f"insufficient horizon-group calibration rows: {counts}")
    output: dict[str, dict[str, dict[str, float]]] = {}
    for axis in ("lateral", "altitude"):
        output[axis] = {}
        error = d[f"p1_{axis}_abs_error_m"].to_numpy(float)
        for group_name in ("direct_short", "long"):
            mask = (groups == group_name).to_numpy(bool)
            output[axis][group_name] = {}
            for q in TARGETS:
                provisional = _provisional(d, scale_model, single, axis, q)
                ratio = error[mask] / np.maximum(provisional[mask], 1e-9)
                output[axis][group_name][f"{q:.2f}"] = _finite_conformal(ratio, q)
    return output, counts


def build_candidate(fit: pd.DataFrame, calibration: pd.DataFrame, transfer: pd.DataFrame, velocity_caps: dict[str, float], git_sha: str) -> dict[str, object]:
    scale_model = p5.fit_scale_model(fit)
    single = p5.single_factor_calibration(calibration, scale_model)
    transfer_multipliers, counts = _horizon_transfer(transfer, scale_model, single)
    return {
        "schema": "aegisland.phase11.p6.candidate-freeze.v1",
        "git_sha": git_sha,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "development_seed_unseen_at_freeze": DEVELOPMENT_SEED,
        "validation_seed_unseen_at_freeze": VALIDATION_SEED,
        "max_bridge_horizon": p5.MAX_BRIDGE_HORIZON,
        "velocity_caps": velocity_caps,
        "ridge_lambda": p5.RIDGE_LAMBDA,
        "scale_model": scale_model,
        "single_factor_conformal": single,
        "horizon_transfer_multipliers": transfer_multipliers,
        "horizon_group_counts": counts,
        "horizon_groups": {"direct_short": "bridge_horizon<=2", "long": "3<=bridge_horizon<=5"},
    }


def halfwidths(df: pd.DataFrame, candidate: dict[str, object], axis: str) -> dict[str, np.ndarray]:
    groups = _group(df).to_numpy(str)
    columns = []
    for q in TARGETS:
        provisional = _provisional(df, candidate["scale_model"], candidate["single_factor_conformal"], axis, q)
        multipliers = np.asarray([
            float(candidate["horizon_transfer_multipliers"][axis][group][f"{q:.2f}"])
            for group in groups
        ], dtype=float)
        columns.append(provisional * multipliers)
    nested = np.maximum.accumulate(np.column_stack(columns), axis=1)
    return {f"{q:.2f}": nested[:, i] for i, q in enumerate(TARGETS)}


def _subset_coverage(df: pd.DataFrame, candidate: dict[str, object], subset_mask: pd.Series) -> dict[str, dict[str, float]]:
    d = df[_available(df) & subset_mask].copy()
    output = {}
    for axis in ("lateral", "altitude"):
        widths = halfwidths(d, candidate, axis)
        error = d[f"p1_{axis}_abs_error_m"].to_numpy(float)
        output[axis] = {
            f"{q:.2f}": float(np.mean(error <= widths[f"{q:.2f}"])) if error.size else float("nan")
            for q in TARGETS
        }
    return output


def _error_stats(df: pd.DataFrame, subset_mask: pd.Series | None = None) -> dict[str, float]:
    mask = _available(df)
    if subset_mask is not None:
        mask = mask & subset_mask
    d = df[mask]
    result = {"count": int(mask.sum()), "availability": float(_available(df).mean())}
    for axis in ("lateral", "altitude"):
        arr = d[f"p1_{axis}_abs_error_m"].dropna().to_numpy(float)
        result[f"{axis}_mae"] = float(np.mean(arr)) if arr.size else float("nan")
        result[f"{axis}_p95"] = float(np.percentile(arr, 95)) if arr.size else float("nan")
    return result


def _interval_stats(df: pd.DataFrame, candidate: dict[str, object], subset_mask: pd.Series | None = None) -> dict[str, dict[str, float]]:
    mask = _available(df)
    if subset_mask is not None:
        mask = mask & subset_mask
    d = df[mask].copy()
    output = {}
    for axis in ("lateral", "altitude"):
        hw = halfwidths(d, candidate, axis)["0.95"]
        output[axis] = {
            "median_halfwidth_95": float(np.median(hw)) if hw.size else float("nan"),
            "p95_halfwidth_95": float(np.percentile(hw, 95)) if hw.size else float("nan"),
        }
    return output


def _auc(labels: np.ndarray, scores: np.ndarray) -> float:
    pos, neg = scores[labels == 1], scores[labels == 0]
    if not len(pos) or not len(neg):
        return float("nan")
    wins = sum(float(np.sum(score > neg)) + 0.5 * float(np.sum(score == neg)) for score in pos)
    return float(wins / (len(pos) * len(neg)))


def _shift_auc(calibration: pd.DataFrame, evaluated: pd.DataFrame) -> float:
    a = calibration.groupby("sequence_id", as_index=False)["severity"].mean(); a["label"] = 0
    b = evaluated.groupby("sequence_id", as_index=False)["severity"].mean(); b["label"] = 1
    z = pd.concat([a, b], ignore_index=True)
    return _auc(z["label"].to_numpy(int), z["severity"].to_numpy(float))


def summarize(evaluated: pd.DataFrame, calibration: pd.DataFrame, candidate: dict[str, object], role: str, seed: int) -> dict[str, object]:
    all_mask = pd.Series(True, index=evaluated.index)
    long_mask = evaluated["bridge_horizon"].between(3, 5)
    short_mask = evaluated["bridge_horizon"] <= 2
    coverage_all = _subset_coverage(evaluated, candidate, all_mask)
    coverage_long = _subset_coverage(evaluated, candidate, long_mask)
    coverage_short = _subset_coverage(evaluated, candidate, short_mask)
    errors_all = _error_stats(evaluated)
    errors_long = _error_stats(evaluated, long_mask)
    intervals_all = _interval_stats(evaluated, candidate)
    intervals_long = _interval_stats(evaluated, candidate, long_mask)

    d1 = {"availability": errors_all["availability"], "pass": bool(errors_all["availability"] >= 0.90)}
    d2 = {"lateral_95_coverage": coverage_all["lateral"]["0.95"], "altitude_95_coverage": coverage_all["altitude"]["0.95"]}
    d2["pass"] = bool(0.90 <= d2["lateral_95_coverage"] <= 0.98 and 0.90 <= d2["altitude_95_coverage"] <= 0.98)
    mace = float(np.mean([abs(coverage_all[axis][f"{q:.2f}"] - q) for axis in ("lateral", "altitude") for q in TARGETS]))
    d3 = {"mean_absolute_coverage_error": mace, "pass": bool(mace <= 0.06)}
    d4 = {}
    for axis in ("lateral", "altitude"):
        p95 = errors_all[f"{axis}_p95"]
        d4[f"{axis}_median_halfwidth_over_p95_error"] = intervals_all[axis]["median_halfwidth_95"] / p95
        d4[f"{axis}_p95_halfwidth_over_p95_error"] = intervals_all[axis]["p95_halfwidth_95"] / p95
    d4["pass"] = bool(
        d4["lateral_median_halfwidth_over_p95_error"] <= 1.25
        and d4["altitude_median_halfwidth_over_p95_error"] <= 1.25
        and d4["lateral_p95_halfwidth_over_p95_error"] <= 2.25
        and d4["altitude_p95_halfwidth_over_p95_error"] <= 2.25
    )
    d5 = {"long_bridge_count": errors_long["count"]}
    if errors_long["count"] >= MIN_GROUP_COUNT:
        d5.update({
            "lateral_95_coverage": coverage_long["lateral"]["0.95"],
            "altitude_95_coverage": coverage_long["altitude"]["0.95"],
            "lateral_p95_halfwidth_over_p95_error": intervals_long["lateral"]["p95_halfwidth_95"] / max(errors_long["lateral_p95"], 1e-12),
            "altitude_p95_halfwidth_over_p95_error": intervals_long["altitude"]["p95_halfwidth_95"] / max(errors_long["altitude_p95"], 1e-12),
        })
        d5["pass"] = bool(
            0.90 <= d5["lateral_95_coverage"] <= 0.99
            and 0.90 <= d5["altitude_95_coverage"] <= 0.99
            and d5["lateral_p95_halfwidth_over_p95_error"] <= 2.50
            and d5["altitude_p95_halfwidth_over_p95_error"] <= 2.50
        )
    else:
        d5["pass"] = False
        d5["insufficient_evidence"] = True
    d6 = {"lateral_95_coverage": coverage_short["lateral"]["0.95"], "altitude_95_coverage": coverage_short["altitude"]["0.95"]}
    d6["pass"] = bool(0.90 <= d6["lateral_95_coverage"] <= 0.98 and 0.90 <= d6["altitude_95_coverage"] <= 0.98)
    d7 = {"trajectory_level_auroc": _shift_auc(calibration, evaluated)}
    d7["pass"] = bool(d7["trajectory_level_auroc"] >= 0.85)
    gates = {
        "d1_availability": d1,
        "d2_overall_coverage": d2,
        "d3_calibration_curve": d3,
        "d4_interval_efficiency": d4,
        "d5_long_bridge_calibration": d5,
        "d6_direct_short_calibration": d6,
        "d7_shift_discrimination": d7,
    }
    return {
        "schema": "aegisland.phase11.p6.result.v1",
        "evidence_role": role,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "evaluated_seed_seen_after_run": seed,
        "all_primary_gates_pass": bool(all(g["pass"] for g in gates.values())),
        "gates": gates,
        "coverage_all": coverage_all,
        "coverage_long": coverage_long,
        "coverage_direct_short": coverage_short,
        "error_stats_all": errors_all,
        "error_stats_long": errors_long,
        "interval_stats_all": intervals_all,
        "interval_stats_long": intervals_long,
    }


def freeze(out: Path, git_sha: str) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    fit_raw = _raw("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS)
    caps = p5.fit_velocity_caps(fit_raw)
    fit = _prepare(fit_raw, caps)
    calibration = _prepare(_raw("calibration", CALIBRATION_SEED, CALIBRATION_FAMILIES, FIT_DOMAINS), caps)
    transfer = _prepare(_raw("transfer", TRANSFER_SEED, TRANSFER_FAMILIES, TRANSFER_DOMAINS), caps)
    candidate = build_candidate(fit, calibration, transfer, caps, git_sha)
    fit.to_csv(out / "fit_frames.csv", index=False)
    calibration.to_csv(out / "calibration_frames.csv", index=False)
    transfer.to_csv(out / "transfer_frames.csv", index=False)
    (out / "candidate_freeze.json").write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("P6_CANDIDATE_FREEZE_JSON=" + json.dumps(candidate, sort_keys=True))
    return candidate


def evaluate(stage: str, out: Path, candidate_path: Path, git_sha: str) -> dict[str, object]:
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    caps = candidate["velocity_caps"]
    calibration = _prepare(_raw("calibration", CALIBRATION_SEED, CALIBRATION_FAMILIES, FIT_DOMAINS), caps)
    if stage == "development":
        expected = DEVELOPMENT_SEED
        if int(candidate.get("development_seed_unseen_at_freeze", -1)) != expected:
            raise SystemExit("candidate freeze does not match P6 development seed")
        evaluated = _prepare(_raw("development", DEVELOPMENT_SEED, DEVELOPMENT_FAMILIES, DEVELOPMENT_DOMAINS), caps)
        role = "phase11_p6_frozen_candidate_development_challenge"
        prefix = "development"
    elif stage == "validation":
        expected = VALIDATION_SEED
        if int(candidate.get("validation_seed_unseen_at_freeze", -1)) != expected:
            raise SystemExit("candidate freeze does not match P6 validation seed")
        evaluated = _prepare(_raw("validation", VALIDATION_SEED, VALIDATION_FAMILIES, VALIDATION_DOMAINS), caps)
        role = "phase11_p6_frozen_candidate_protected_validation"
        prefix = "validation"
    else:
        raise ValueError(stage)
    result = summarize(evaluated, calibration, candidate, role, expected)
    result["git_sha"] = git_sha
    out.mkdir(parents=True, exist_ok=True)
    evaluated.to_csv(out / f"{prefix}_frames.csv", index=False)
    (out / f"{prefix}_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"P6_{prefix.upper()}_GATES=" + json.dumps(result["gates"], sort_keys=True))
    print(f"P6_{prefix.upper()}_OVERALL=" + ("PASS" if result["all_primary_gates_pass"] else "MIXED_OR_FAILED"))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 11 P6 horizon-aware conformal benchmark")
    parser.add_argument("--stage", choices=("freeze", "development", "validation"), required=True)
    parser.add_argument("--out", type=Path, default=Path("results/phase11_p6"))
    parser.add_argument("--candidate", type=Path, default=Path("results/phase11_p6/candidate_freeze.json"))
    parser.add_argument("--git-sha", default="unknown")
    args = parser.parse_args()
    if args.stage == "freeze":
        freeze(args.out, args.git_sha)
    else:
        evaluate(args.stage, args.out, args.candidate, args.git_sha)


if __name__ == "__main__":
    main()
