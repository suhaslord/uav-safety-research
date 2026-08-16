from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scripts import run_phase11_p9_soft_update_direct_conformal as p9
except ModuleNotFoundError:
    import run_phase11_p9_soft_update_direct_conformal as p9

FIT_SEED = 539539
CALIBRATION_SEED = 550550
TRANSFER_SEED = 561561
VALIDATION_SEED = 572572
FRAMES_PER_SEQUENCE = p9.FRAMES_PER_SEQUENCE

FIT_FAMILIES = tuple(range(304, 310))
CALIBRATION_FAMILIES = tuple(range(310, 358))
TRANSFER_FAMILIES = tuple(range(358, 378))
VALIDATION_FAMILIES = tuple(range(378, 398))

FIT_DOMAINS = p9.FIT_DOMAINS
CALIBRATION_DOMAINS = p9.CALIBRATION_DOMAINS
TRANSFER_DOMAINS = p9.TRANSFER_DOMAINS
VALIDATION_DOMAINS = p9.VALIDATION_DOMAINS

GROUP_BASE = "base_output"
GROUP_H3 = "continuity_h3"
GROUP_H47 = "continuity_h47"
GROUPS = (GROUP_BASE, GROUP_H3, GROUP_H47)
CALIBRATION_MINIMUMS = {GROUP_BASE: 1500, GROUP_H3: 150, GROUP_H47: 100}
TRANSFER_MINIMUMS = {GROUP_BASE: 1000, GROUP_H3: 100, GROUP_H47: 60}


def _raw(name: str, seed: int, families: tuple[int, ...], domains: tuple[str, ...]) -> pd.DataFrame:
    return p9.p1.generate_split(name, seed, families, domains, frames=FRAMES_PER_SEQUENCE)


def _prepare(raw: pd.DataFrame, velocity_caps: dict[str, float], innovation_scales: dict[str, float]) -> pd.DataFrame:
    return p9.add_p9_continuity(raw, velocity_caps, innovation_scales)


def _available(df: pd.DataFrame) -> pd.Series:
    return p9._available(df)


def _group_series(df: pd.DataFrame) -> pd.Series:
    source = df["p9_source"].fillna("").astype(str).to_numpy()
    horizon = df["p9_continuity_horizon"].astype(int).to_numpy()
    values = np.full(len(df), GROUP_BASE, dtype=object)
    continuity = source == "soft_innovation_continuity"
    values[continuity & (horizon == 3)] = GROUP_H3
    values[continuity & np.isin(horizon, [4, 5, 6, 7])] = GROUP_H47
    return pd.Series(values, index=df.index, dtype="object")


def _fit_direct_radii(calibration: pd.DataFrame) -> tuple[dict[str, dict[str, dict[str, float]]], dict[str, int]]:
    d = calibration[_available(calibration)].copy()
    d["p12_group"] = _group_series(d)
    counts = {group: int((d["p12_group"] == group).sum()) for group in GROUPS}
    for group, minimum in CALIBRATION_MINIMUMS.items():
        if counts[group] < minimum:
            raise RuntimeError(f"P12 calibration group {group} rows {counts[group]} < {minimum}")
    radii: dict[str, dict[str, dict[str, float]]] = {}
    for group in GROUPS:
        gd = d[d["p12_group"] == group]
        radii[group] = {}
        for axis in ("lateral", "altitude"):
            errors = gd[f"p9_{axis}_abs_error_m"].to_numpy(float)
            raw = [p9._finite_conformal(errors, q) for q in p9.TARGETS]
            nested = np.maximum.accumulate(np.asarray(raw, dtype=float))
            radii[group][axis] = {f"{q:.2f}": float(nested[i]) for i, q in enumerate(p9.TARGETS)}
    return radii, counts


def _build_candidate(fit_raw: pd.DataFrame, calibration_raw: pd.DataFrame, git_sha: str) -> tuple[dict[str, object], pd.DataFrame]:
    velocity_caps = p9._fit_velocity_caps(fit_raw)
    innovation_scales = p9._fit_innovation_scales(fit_raw, velocity_caps)
    calibration = _prepare(calibration_raw, velocity_caps, innovation_scales)
    radii, counts = _fit_direct_radii(calibration)
    candidate = {
        "schema": "aegisland.phase11.p12.candidate-freeze.v1",
        "git_sha": git_sha,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "point_estimator": "phase11_p9_soft_update_unchanged",
        "fit_seed": FIT_SEED,
        "calibration_seed": CALIBRATION_SEED,
        "transfer_seed_unseen_at_freeze": TRANSFER_SEED,
        "validation_seed_unseen_at_freeze": VALIDATION_SEED,
        "fit_families": list(FIT_FAMILIES),
        "calibration_families": list(CALIBRATION_FAMILIES),
        "transfer_families": list(TRANSFER_FAMILIES),
        "validation_families": list(VALIDATION_FAMILIES),
        "continuity_constants": {
            "max_continuity_gap": p9.MAX_CONTINUITY_GAP,
            "damping": p9.DAMPING,
            "velocity_cap_quantile": p9.VELOCITY_CAP_QUANTILE,
            "innovation_scale_quantile": p9.INNOVATION_SCALE_QUANTILE,
            "soft_scale_multiplier": p9.SOFT_SCALE_MULTIPLIER,
            "blend_previous_slope": p9.BLEND_PREVIOUS_SLOPE,
            "blend_soft_updated_slope": p9.BLEND_SOFT_UPDATED_SLOPE,
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


def _load_candidate(path: Path) -> dict[str, object]:
    c = json.loads(path.read_text(encoding="utf-8"))
    if c.get("schema") != "aegisland.phase11.p12.candidate-freeze.v1":
        raise SystemExit("invalid P12 candidate schema")
    if c.get("transfer_seed_unseen_at_freeze") != TRANSFER_SEED:
        raise SystemExit("P12 transfer seed mismatch")
    if c.get("validation_seed_unseen_at_freeze") != VALIDATION_SEED:
        raise SystemExit("P12 validation seed mismatch")
    return c


def _halfwidths(df: pd.DataFrame, candidate: dict[str, object], axis: str, q: float) -> np.ndarray:
    groups = _group_series(df).to_numpy(str)
    table = candidate["direct_conformal_radii"]
    return np.asarray([float(table[group][axis][f"{q:.2f}"]) for group in groups], dtype=float)


def _coverage(df: pd.DataFrame, candidate: dict[str, object]) -> dict[str, dict[str, float]]:
    d = df[_available(df)].copy()
    out: dict[str, dict[str, float]] = {}
    for axis in ("lateral", "altitude"):
        errors = d[f"p9_{axis}_abs_error_m"].to_numpy(float)
        out[axis] = {}
        for q in p9.TARGETS:
            hw = _halfwidths(d, candidate, axis, q)
            out[axis][f"{q:.2f}"] = float(np.mean(errors <= hw)) if errors.size else float("nan")
    return out


def _subset_stats(df: pd.DataFrame, candidate: dict[str, object], groups: set[str]) -> dict[str, object]:
    gs = _group_series(df)
    d = df[_available(df) & gs.isin(groups)].copy()
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
        result["p95_error"][axis] = p95e
        result["p95_halfwidth"][axis] = p95w
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


def _shift_auc(reference: pd.DataFrame, evaluated: pd.DataFrame) -> float:
    return p9._shift_auc(reference, evaluated)


def _secondary(df: pd.DataFrame, candidate: dict[str, object]) -> dict[str, object]:
    d = df[_available(df)].copy(); d["p12_group"] = _group_series(d)
    group_stats = {group: _subset_stats(df, candidate, {group}) for group in GROUPS}
    continuity = d[d["p9_source"].astype(str) == "soft_innovation_continuity"]
    horizon = []
    for h in range(3, 8):
        hd = continuity[continuity["p9_continuity_horizon"].astype(int) == h]
        row: dict[str, object] = {"horizon": h, "rows": int(len(hd))}
        for axis in ("lateral", "altitude"):
            err = hd[f"p9_{axis}_abs_error_m"].dropna().to_numpy(float)
            row[f"{axis}_mae"] = float(np.mean(err)) if err.size else float("nan")
            row[f"{axis}_p95"] = float(np.percentile(err, 95)) if err.size else float("nan")
        horizon.append(row)
    gains = {}
    for axis in ("lateral", "altitude"):
        arr = continuity[f"p9_{axis}_gain"].dropna().to_numpy(float)
        gains[axis] = {"median": float(np.median(arr)) if arr.size else float("nan"), "fraction_lt_0_90": float(np.mean(arr < 0.90)) if arr.size else float("nan"), "fraction_lt_0_75": float(np.mean(arr < 0.75)) if arr.size else float("nan"), "fraction_lt_0_50": float(np.mean(arr < 0.50)) if arr.size else float("nan")}
    unavailable = df[~df["p9_available"].astype(bool)]["p9_unavailable_reason"].value_counts().to_dict()
    return {"groups": group_stats, "continuity_by_horizon": horizon, "gain": gains, "unavailable_reason_counts": {str(k): int(v) for k, v in unavailable.items()}}


def summarize(evaluated: pd.DataFrame, reference: pd.DataFrame, candidate: dict[str, object], role: str, seed: int, require_transfer_minimums: bool) -> dict[str, object]:
    d = evaluated[_available(evaluated)].copy(); gs = _group_series(d)
    counts = {group: int((gs == group).sum()) for group in GROUPS}
    minima_pass = True if not require_transfer_minimums else all(counts[g] >= TRANSFER_MINIMUMS[g] for g in GROUPS)
    coverage = _coverage(evaluated, candidate)
    errors, intervals = _error_interval_stats(evaluated, candidate)
    continuity = _subset_stats(evaluated, candidate, {GROUP_H3, GROUP_H47})
    base = _subset_stats(evaluated, candidate, {GROUP_BASE})
    h1 = {"available_fraction": errors["available_fraction"], "pass": bool(errors["available_fraction"] >= 0.92)}
    h2 = {"lateral_95_coverage": coverage["lateral"]["0.95"], "altitude_95_coverage": coverage["altitude"]["0.95"]}
    h2["pass"] = bool(0.90 <= h2["lateral_95_coverage"] <= 0.98 and 0.90 <= h2["altitude_95_coverage"] <= 0.98)
    mace = float(np.mean([abs(coverage[a][f"{q:.2f}"] - q) for a in ("lateral", "altitude") for q in p9.TARGETS]))
    h3 = {"mean_absolute_coverage_error": mace, "pass": bool(mace <= 0.06)}
    h4: dict[str, object] = {}
    for axis in ("lateral", "altitude"):
        p95e = errors[f"{axis}_p95"]
        h4[f"{axis}_median_halfwidth_over_p95_error"] = intervals[axis]["median_halfwidth_95"] / p95e
        h4[f"{axis}_p95_halfwidth_over_p95_error"] = intervals[axis]["p95_halfwidth_95"] / p95e
    h4["pass"] = bool(h4["lateral_median_halfwidth_over_p95_error"] <= 1.25 and h4["altitude_median_halfwidth_over_p95_error"] <= 1.25 and h4["lateral_p95_halfwidth_over_p95_error"] <= 2.25 and h4["altitude_p95_halfwidth_over_p95_error"] <= 2.25)
    h5 = {"rows": continuity["rows"], "lateral_95_coverage": continuity["coverage_95"]["lateral"], "altitude_95_coverage": continuity["coverage_95"]["altitude"], "lateral_p95_halfwidth_over_p95_error": continuity["p95_halfwidth_over_p95_error"]["lateral"], "altitude_p95_halfwidth_over_p95_error": continuity["p95_halfwidth_over_p95_error"]["altitude"]}
    h5["pass"] = bool(h5["rows"] > 0 and 0.88 <= h5["lateral_95_coverage"] <= 0.99 and 0.88 <= h5["altitude_95_coverage"] <= 0.99 and h5["lateral_p95_halfwidth_over_p95_error"] <= 2.75 and h5["altitude_p95_halfwidth_over_p95_error"] <= 2.75)
    h6 = {"rows": base["rows"], "lateral_95_coverage": base["coverage_95"]["lateral"], "altitude_95_coverage": base["coverage_95"]["altitude"], "lateral_p95_halfwidth_over_p95_error": base["p95_halfwidth_over_p95_error"]["lateral"], "altitude_p95_halfwidth_over_p95_error": base["p95_halfwidth_over_p95_error"]["altitude"]}
    h6["pass"] = bool(h6["rows"] > 0 and 0.90 <= h6["lateral_95_coverage"] <= 0.98 and 0.90 <= h6["altitude_95_coverage"] <= 0.98 and h6["lateral_p95_halfwidth_over_p95_error"] <= 2.25 and h6["altitude_p95_halfwidth_over_p95_error"] <= 2.25)
    h7 = {"trajectory_level_auroc": _shift_auc(reference, evaluated)}; h7["pass"] = bool(h7["trajectory_level_auroc"] >= 0.85)
    gates = {"transfer_group_minimums": {"counts": counts, "required": TRANSFER_MINIMUMS, "pass": bool(minima_pass)}, "h1_useful_availability": h1, "h2_overall_coverage": h2, "h3_calibration_curve": h3, "h4_overall_interval_efficiency": h4, "h5_continuity_specific_honesty": h5, "h6_base_output_honesty": h6, "h7_shift_discrimination": h7}
    primary = ("h1_useful_availability", "h2_overall_coverage", "h3_calibration_curve", "h4_overall_interval_efficiency", "h5_continuity_specific_honesty", "h6_base_output_honesty")
    return {"schema": "aegisland.phase11.p12.result.v1", "evidence_role": role, "simulation_only": True, "safety_acceptance": False, "controller_tuning_allowed": False, "evaluated_seed_seen_after_run": seed, "all_primary_gates_pass": bool(minima_pass and all(gates[g]["pass"] for g in primary)), "gates": gates, "coverage": coverage, "error_stats": errors, "interval_stats": intervals, "continuity_stats": continuity, "base_output_stats": base, "secondary_diagnostics": _secondary(evaluated, candidate)}


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _manifest(out: Path, files: list[str], stage: str, git_sha: str) -> None:
    payload = {"schema": "aegisland.phase11.p12.manifest.v1", "stage": stage, "git_sha": git_sha, "simulation_only": True, "safety_acceptance": False, "controller_tuning_allowed": False, "files": {name: {"sha256": _hash_file(out / name), "bytes": (out / name).stat().st_size} for name in files}}
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


def transfer(out: Path, candidate_path: Path, git_sha: str) -> dict[str, object]:
    candidate = _load_candidate(candidate_path); out.mkdir(parents=True, exist_ok=True)
    transfer_df = _prepare(_raw("transfer", TRANSFER_SEED, TRANSFER_FAMILIES, TRANSFER_DOMAINS), candidate["velocity_caps"], candidate["innovation_scales"])
    reference = _prepare(_raw("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS), candidate["velocity_caps"], candidate["innovation_scales"])
    result = summarize(transfer_df, reference, candidate, "phase11_p12_seen_transfer", TRANSFER_SEED, True)
    transfer_df.to_csv(out / "transfer_frames.csv", index=False)
    (out / "transfer_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "candidate_freeze.json").write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(out, ["transfer_frames.csv", "transfer_result.json", "candidate_freeze.json"], "transfer", git_sha)
    return result


def validate(out: Path, candidate_path: Path, git_sha: str) -> dict[str, object]:
    candidate = _load_candidate(candidate_path); out.mkdir(parents=True, exist_ok=True)
    validation = _prepare(_raw("validation", VALIDATION_SEED, VALIDATION_FAMILIES, VALIDATION_DOMAINS), candidate["velocity_caps"], candidate["innovation_scales"])
    reference = _prepare(_raw("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS), candidate["velocity_caps"], candidate["innovation_scales"])
    result = summarize(validation, reference, candidate, "phase11_p12_frozen_candidate_validation", VALIDATION_SEED, False)
    validation.to_csv(out / "validation_frames.csv", index=False)
    (out / "validation_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "candidate_freeze.json").write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(out, ["validation_frames.csv", "validation_result.json", "candidate_freeze.json"], "validation", git_sha)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 11 P12 three-group direct-conformal simulation benchmark")
    parser.add_argument("--stage", choices=("freeze", "transfer", "validation"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--git-sha", default="unknown")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.stage == "freeze":
        c = freeze(args.out, args.git_sha)
        print("P12_CANDIDATE_FREEZE=" + json.dumps({"calibration_group_rows": c["calibration_group_rows"], "velocity_caps": c["velocity_caps"], "innovation_scales": c["innovation_scales"]}, sort_keys=True)); return
    if args.candidate is None: raise SystemExit("--candidate required")
    if args.stage == "transfer":
        r = transfer(args.out, args.candidate, args.git_sha); print("P12_TRANSFER_GATES=" + json.dumps(r["gates"], sort_keys=True)); return
    r = validate(args.out, args.candidate, args.git_sha); print("P12_VALIDATION_GATES=" + json.dumps(r["gates"], sort_keys=True))


if __name__ == "__main__":
    main()
