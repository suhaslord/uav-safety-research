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

FIT_SEED = 253253
CALIBRATION_SEED = 264264
TRANSFER_SEED = 275275
VALIDATION_SEED = 286286
FRAMES_PER_SEQUENCE = 60
TARGETS = p5.TARGETS

FIT_FAMILIES = tuple(range(87, 93))
CALIBRATION_FAMILIES = tuple(range(93, 96))
TRANSFER_FAMILIES = tuple(range(96, 99))
VALIDATION_FAMILIES = tuple(range(99, 102))

FIT_DOMAINS = p5.FIT_DOMAINS
TRANSFER_DOMAINS = (
    "edge+small_scale",
    "oblique+temporal_dropout",
    "dim+blur_noise",
    "small_scale+low_contrast",
    "edge+dim+temporal_dropout",
    "small_scale+oblique+blur_noise",
    "edge+blur_noise+low_contrast",
    "oblique+dim+low_contrast+temporal_dropout",
)
VALIDATION_DOMAINS = (
    "edge+oblique",
    "small_scale+blur_noise",
    "dim+temporal_dropout",
    "edge+low_contrast+temporal_dropout",
    "small_scale+oblique+dim",
    "edge+small_scale+blur_noise+low_contrast",
    "oblique+dim+blur_noise+temporal_dropout",
    "edge+small_scale+oblique+dim+temporal_dropout",
)

MIN_CONTINUITY_TRANSFER_ROWS = 40
MIN_BASE_TRANSFER_ROWS = 200
GROUPS = ("base_output", "continuity_extension")


def _raw(name: str, seed: int, families: tuple[int, ...], domains: tuple[str, ...]) -> pd.DataFrame:
    return p5._generate_raw(name, seed, families, domains)


def _prepare(raw: pd.DataFrame, caps: dict[str, float]) -> pd.DataFrame:
    return p5.add_p5_continuity(raw, caps)


def _available(df: pd.DataFrame) -> pd.Series:
    return p5._available(df)


def _group_series(df: pd.DataFrame) -> pd.Series:
    return pd.Series(
        np.where(
            df["p5_source"].astype(str).to_numpy() == "continuity_extension",
            "continuity_extension",
            "base_output",
        ),
        index=df.index,
        dtype="object",
    )


def _finite_conformal(values: np.ndarray | pd.Series, q: float) -> float:
    arr = np.asarray(values, dtype=float)
    arr = np.sort(arr[np.isfinite(arr)])
    if arr.size == 0:
        return float("nan")
    k = int(math.ceil((arr.size + 1) * q))
    return float(arr[min(arr.size - 1, max(0, k - 1))])


def _provisional(df: pd.DataFrame, candidate: dict[str, object], axis: str, q: float) -> np.ndarray:
    predicted = p5._predicted_scale(df, candidate["scale_model"])[axis]
    return predicted * float(candidate["single_factor_conformal"][axis][f"{q:.2f}"])


def _group_counts(transfer_df: pd.DataFrame) -> dict[str, int]:
    d = transfer_df[_available(transfer_df)].copy()
    groups = _group_series(d)
    return {group: int((groups == group).sum()) for group in GROUPS}


def _source_conditional_transfer(
    transfer_df: pd.DataFrame,
    model: dict[str, object],
    single: dict[str, dict[str, float]],
) -> tuple[dict[str, dict[str, dict[str, float]]], dict[str, int]]:
    d = transfer_df[_available(transfer_df)].copy()
    d["p6_group"] = _group_series(d)
    counts = {group: int((d["p6_group"] == group).sum()) for group in GROUPS}
    if counts["continuity_extension"] < MIN_CONTINUITY_TRANSFER_ROWS:
        raise RuntimeError(
            f"P6 continuity transfer group too small: {counts['continuity_extension']} < {MIN_CONTINUITY_TRANSFER_ROWS}"
        )
    if counts["base_output"] < MIN_BASE_TRANSFER_ROWS:
        raise RuntimeError(
            f"P6 base transfer group too small: {counts['base_output']} < {MIN_BASE_TRANSFER_ROWS}"
        )

    provisional_candidate = {
        "scale_model": model,
        "single_factor_conformal": single,
    }
    result: dict[str, dict[str, dict[str, float]]] = {}
    for group in GROUPS:
        g = d[d["p6_group"] == group].copy()
        result[group] = {}
        for axis in ("lateral", "altitude"):
            error = g[f"p5_{axis}_abs_error_m"].to_numpy(float)
            result[group][axis] = {}
            for q in TARGETS:
                radius = _provisional(g, provisional_candidate, axis, q)
                ratios = error / np.maximum(radius, 1e-9)
                result[group][axis][f"{q:.2f}"] = _finite_conformal(ratios, q)
    return result, counts


def final_halfwidths(
    df: pd.DataFrame, candidate: dict[str, object], axis: str
) -> dict[str, np.ndarray]:
    groups = _group_series(df).to_numpy(str)
    cols: list[np.ndarray] = []
    for q in TARGETS:
        provisional = _provisional(df, candidate, axis, q)
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
    transfer_df: pd.DataFrame,
    velocity_caps: dict[str, float],
    git_sha: str,
) -> dict[str, object]:
    model = p5._fit_models(fit)
    single = p5._single_factor_calibration(calibration, model)
    transfer, counts = _source_conditional_transfer(transfer_df, model, single)
    return {
        "schema": "aegisland.phase11.p6.candidate-freeze.v1",
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
        "continuity_constants": {
            "max_continuity_gap": p5.MAX_CONTINUITY_GAP,
            "damping": p5.DAMPING,
            "velocity_cap_quantile": p5.VELOCITY_CAP_QUANTILE,
        },
        "velocity_caps": velocity_caps,
        "ridge_lambda": p5.RIDGE_LAMBDA,
        "scale_model": model,
        "single_factor_conformal": single,
        "transfer_groups": list(GROUPS),
        "minimum_transfer_group_rows": {
            "continuity_extension": MIN_CONTINUITY_TRANSFER_ROWS,
            "base_output": MIN_BASE_TRANSFER_ROWS,
        },
        "transfer_group_rows": counts,
        "transfer_multipliers": transfer,
    }


def _subset_stats(
    df: pd.DataFrame,
    candidate: dict[str, object],
    group: str,
) -> dict[str, object]:
    available = _available(df)
    groups = _group_series(df)
    d = df[available & (groups == group)].copy()
    out: dict[str, object] = {
        "rows": int(len(d)),
        "fraction_of_truth_visible": float(len(d) / len(df)) if len(df) else float("nan"),
        "coverage_95": {},
        "p95_error": {},
        "p95_halfwidth": {},
        "p95_halfwidth_over_p95_error": {},
    }
    for axis in ("lateral", "altitude"):
        error = d[f"p5_{axis}_abs_error_m"].dropna().to_numpy(float)
        if not error.size:
            for key in ("coverage_95", "p95_error", "p95_halfwidth", "p95_halfwidth_over_p95_error"):
                out[key][axis] = float("nan")
            continue
        widths = final_halfwidths(d, candidate, axis)["0.95"]
        p95_error = float(np.percentile(error, 95))
        p95_width = float(np.percentile(widths, 95))
        out["coverage_95"][axis] = float(np.mean(error <= widths))
        out["p95_error"][axis] = p95_error
        out["p95_halfwidth"][axis] = p95_width
        out["p95_halfwidth_over_p95_error"][axis] = (
            p95_width / p95_error if p95_error > 0 else float("nan")
        )
    return out


def _coverage(df: pd.DataFrame, candidate: dict[str, object]) -> dict[str, dict[str, float]]:
    d = df[_available(df)].copy()
    result: dict[str, dict[str, float]] = {}
    for axis in ("lateral", "altitude"):
        error = d[f"p5_{axis}_abs_error_m"].to_numpy(float)
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
    result: dict[str, float] = {"available_fraction": float(mask.mean())}
    for axis in ("lateral", "altitude"):
        values = d[f"p5_{axis}_abs_error_m"].dropna().to_numpy(float)
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


def _auc(labels: np.ndarray, scores: np.ndarray) -> float:
    positive = scores[labels == 1]
    negative = scores[labels == 0]
    if not len(positive) or not len(negative):
        return float("nan")
    wins = sum(
        float(np.sum(score > negative)) + 0.5 * float(np.sum(score == negative))
        for score in positive
    )
    return float(wins / (len(positive) * len(negative)))


def _shift_auc(calibration: pd.DataFrame, evaluated: pd.DataFrame) -> float:
    left = calibration.groupby("sequence_id", as_index=False)["severity"].mean()
    left["label"] = 0
    right = evaluated.groupby("sequence_id", as_index=False)["severity"].mean()
    right["label"] = 1
    combined = pd.concat([left, right], ignore_index=True)
    return _auc(combined["label"].to_numpy(int), combined["severity"].to_numpy(float))


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
    continuity = _subset_stats(evaluated, candidate, "continuity_extension")
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
        p95 = errors[f"{axis}_p95"]
        h4[f"{axis}_median_halfwidth_over_p95_error"] = intervals[axis]["median_halfwidth_95"] / p95
        h4[f"{axis}_p95_halfwidth_over_p95_error"] = intervals[axis]["p95_halfwidth_95"] / p95
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
        "h5_continuity_specific_honesty": h5,
        "h6_base_output_honesty": h6,
        "h7_shift_discrimination": h7,
    }
    primary = (
        "h1_useful_availability",
        "h2_overall_coverage_transfer",
        "h3_overall_calibration_curve",
        "h4_overall_interval_efficiency",
        "h5_continuity_specific_honesty",
        "h6_base_output_honesty",
    )
    return {
        "schema": "aegisland.phase11.p6.result.v1",
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
    }


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_manifest(out: Path, names: list[str], git_sha: str, stage: str) -> None:
    manifest = {
        "schema": "aegisland.phase11.p6.manifest.v1",
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
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def freeze(out: Path, git_sha: str) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    fit_raw = _raw("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS)
    caps = p5._fit_velocity_caps(fit_raw)
    fit = _prepare(fit_raw, caps)
    calibration = _prepare(_raw("calibration", CALIBRATION_SEED, CALIBRATION_FAMILIES, FIT_DOMAINS), caps)
    transfer_df = _prepare(_raw("transfer", TRANSFER_SEED, TRANSFER_FAMILIES, TRANSFER_DOMAINS), caps)

    candidate = _build_candidate(fit, calibration, transfer_df, caps, git_sha)
    result = summarize(
        transfer_df,
        calibration,
        candidate,
        "phase11_p6_seen_source_conditional_transfer",
        TRANSFER_SEED,
    )

    fit.to_csv(out / "fit_frames.csv", index=False)
    calibration.to_csv(out / "calibration_frames.csv", index=False)
    transfer_df.to_csv(out / "transfer_frames.csv", index=False)
    (out / "candidate_freeze.json").write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "transfer_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_manifest(
        out,
        ["fit_frames.csv", "calibration_frames.csv", "transfer_frames.csv", "candidate_freeze.json", "transfer_result.json"],
        git_sha,
        "freeze",
    )
    return result


def validate(out: Path, candidate_path: Path, git_sha: str) -> dict[str, object]:
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    if candidate.get("schema") != "aegisland.phase11.p6.candidate-freeze.v1":
        raise SystemExit("invalid P6 candidate schema")
    if candidate.get("validation_seed_unseen_at_freeze") != VALIDATION_SEED:
        raise SystemExit("candidate validation seed mismatch")
    constants = candidate.get("continuity_constants", {})
    if constants.get("max_continuity_gap") != p5.MAX_CONTINUITY_GAP:
        raise SystemExit("P5 max continuity gap changed")
    if float(constants.get("damping")) != p5.DAMPING:
        raise SystemExit("P5 damping changed")
    if float(constants.get("velocity_cap_quantile")) != p5.VELOCITY_CAP_QUANTILE:
        raise SystemExit("P5 velocity cap quantile changed")

    out.mkdir(parents=True, exist_ok=True)
    validation = _prepare(_raw("validation", VALIDATION_SEED, VALIDATION_FAMILIES, VALIDATION_DOMAINS), candidate["velocity_caps"])
    calibration = _prepare(_raw("calibration", CALIBRATION_SEED, CALIBRATION_FAMILIES, FIT_DOMAINS), candidate["velocity_caps"])
    result = summarize(
        validation,
        calibration,
        candidate,
        "phase11_p6_frozen_candidate_validation",
        VALIDATION_SEED,
    )
    validation.to_csv(out / "validation_frames.csv", index=False)
    (out / "validation_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "candidate_freeze.json").write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_manifest(out, ["validation_frames.csv", "validation_result.json", "candidate_freeze.json"], git_sha, "validation")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run preregistered Phase 11 P6 source-conditional calibration.")
    parser.add_argument("--stage", choices=("freeze", "validation"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--git-sha", default="unknown")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.stage == "freeze":
        result = freeze(args.out, args.git_sha)
        print("P6_TRANSFER_GATES=" + json.dumps(result["gates"], sort_keys=True))
        return
    if args.candidate is None:
        raise SystemExit("--candidate is required for validation stage")
    result = validate(args.out, args.candidate, args.git_sha)
    print("P6_VALIDATION_GATES=" + json.dumps(result["gates"], sort_keys=True))


if __name__ == "__main__":
    main()
