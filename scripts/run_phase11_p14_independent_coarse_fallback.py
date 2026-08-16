from __future__ import annotations

import argparse
import json
import math
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scripts import run_phase11_p9_soft_update_direct_conformal as p9
except ModuleNotFoundError:
    import run_phase11_p9_soft_update_direct_conformal as p9

FIT_SEED = 638638
BASE_CALIBRATION_SEED = 649649
TRANSFER_CALIBRATION_SEED = 660660
CHALLENGE_SEED = 671671
VALIDATION_SEED = 682682
FRAMES_PER_SEQUENCE = 60

FIT_FAMILIES = tuple(range(516, 522))
BASE_CALIBRATION_FAMILIES = tuple(range(522, 570))
TRANSFER_CALIBRATION_FAMILIES = tuple(range(570, 602))
CHALLENGE_FAMILIES = tuple(range(602, 626))
VALIDATION_FAMILIES = tuple(range(626, 650))

FIT_DOMAINS = p9.FIT_DOMAINS
BASE_CALIBRATION_DOMAINS = p9.CALIBRATION_DOMAINS
TRANSFER_CALIBRATION_DOMAINS = (
    "edge+blur_noise+temporal_dropout",
    "small_scale+dim+temporal_dropout",
    "oblique+low_contrast+temporal_dropout",
    "edge+small_scale+oblique+temporal_dropout",
    "edge+dim+blur_noise+low_contrast+temporal_dropout",
    "small_scale+oblique+blur_noise+temporal_dropout",
    "edge+oblique+dim+blur_noise+temporal_dropout",
    "small_scale+dim+blur_noise+low_contrast+temporal_dropout",
)
CHALLENGE_DOMAINS = (
    "edge+low_contrast+temporal_dropout",
    "small_scale+oblique+temporal_dropout",
    "dim+low_contrast+temporal_dropout",
    "blur_noise+low_contrast+temporal_dropout",
    "edge+small_scale+oblique+dim+temporal_dropout",
    "edge+oblique+blur_noise+low_contrast+temporal_dropout",
    "small_scale+dim+blur_noise+low_contrast+temporal_dropout",
    "edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout",
)
VALIDATION_DOMAINS = (
    "edge+small_scale+low_contrast+temporal_dropout",
    "oblique+dim+blur_noise+temporal_dropout",
    "edge+dim+low_contrast+temporal_dropout",
    "small_scale+oblique+blur_noise+low_contrast+temporal_dropout",
    "edge+small_scale+dim+blur_noise+temporal_dropout",
    "edge+oblique+dim+low_contrast+temporal_dropout",
    "small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout",
    "edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout",
)

AUX_AVAILABILITY = 0.96
AUX_LATERAL_SIGMA_M = 0.075
AUX_ALTITUDE_SIGMA_M = 0.160
AUX_TAIL_PROBABILITY = 0.025
AUX_TAIL_SCALE_LOW = 2.5
AUX_TAIL_SCALE_HIGH = 4.0
AUX_STREAM_CONSTANT = 14_001_401

GROUP_BASE = "base_output"
GROUP_H3 = "primary_continuity_h3"
GROUP_H47 = "primary_continuity_h47"
GROUP_AUX = "auxiliary_fallback"
GROUPS = (GROUP_BASE, GROUP_H3, GROUP_H47, GROUP_AUX)

BASE_MINIMUMS = {GROUP_BASE: 1500, GROUP_H3: 150, GROUP_H47: 100, GROUP_AUX: 300}
TRANSFER_MINIMUMS = {GROUP_BASE: 1200, GROUP_H3: 120, GROUP_H47: 80, GROUP_AUX: 300}
CHALLENGE_MINIMUMS = {GROUP_BASE: 1000, GROUP_H3: 100, GROUP_H47: 60, GROUP_AUX: 200}


def _raw(name: str, seed: int, families: tuple[int, ...], domains: tuple[str, ...]) -> pd.DataFrame:
    return p9.p1.generate_split(name, seed, families, domains, frames=FRAMES_PER_SEQUENCE)


def _aux_rng(row: pd.Series) -> np.random.Generator:
    seed = (
        int(row["seed"])
        + int(row["family"]) * 1_000_003
        + int(row["frame_index"]) * 7_919
        + AUX_STREAM_CONSTANT
    ) % (2**63 - 1)
    return np.random.default_rng(seed)


def add_p14_fallback(raw: pd.DataFrame, velocity_caps: dict[str, float], innovation_scales: dict[str, float]) -> pd.DataFrame:
    out = p9.add_p9_continuity(raw, velocity_caps, innovation_scales).copy()
    out["aux_available"] = False
    out["aux_estimate_lateral_x_m"] = np.nan
    out["aux_estimate_altitude_m"] = np.nan
    out["aux_tail_event"] = False
    out["aux_tail_scale"] = 1.0

    for idx, row in out.iterrows():
        if not bool(row["truth_visible"]):
            continue
        rng = _aux_rng(row)
        available = bool(rng.random() < AUX_AVAILABILITY)
        out.loc[idx, "aux_available"] = available
        if not available:
            continue
        tail = bool(rng.random() < AUX_TAIL_PROBABILITY)
        scale = float(rng.uniform(AUX_TAIL_SCALE_LOW, AUX_TAIL_SCALE_HIGH)) if tail else 1.0
        lat_noise = float(rng.normal(0.0, AUX_LATERAL_SIGMA_M * scale))
        alt_noise = float(rng.normal(0.0, AUX_ALTITUDE_SIGMA_M * scale))
        out.loc[idx, "aux_estimate_lateral_x_m"] = float(row["truth_lateral_x_m"]) + lat_noise
        out.loc[idx, "aux_estimate_altitude_m"] = float(row["truth_altitude_m"]) + alt_noise
        out.loc[idx, "aux_tail_event"] = tail
        out.loc[idx, "aux_tail_scale"] = scale

    out["p14_primary_available"] = out["p9_available"].astype(bool)
    out["p14_available"] = out["p9_available"].astype(bool)
    out["p14_estimate_lateral_x_m"] = out["p9_estimate_lateral_x_m"]
    out["p14_estimate_altitude_m"] = out["p9_estimate_altitude_m"]
    out["p14_source"] = out["p9_source"].fillna("")

    fallback = (~out["p9_available"].astype(bool)) & out["aux_available"].astype(bool) & out["truth_visible"].astype(bool)
    out.loc[fallback, "p14_available"] = True
    out.loc[fallback, "p14_estimate_lateral_x_m"] = out.loc[fallback, "aux_estimate_lateral_x_m"]
    out.loc[fallback, "p14_estimate_altitude_m"] = out.loc[fallback, "aux_estimate_altitude_m"]
    out.loc[fallback, "p14_source"] = "auxiliary_coarse_fallback"

    out["p14_lateral_abs_error_m"] = np.abs(out["p14_estimate_lateral_x_m"] - out["truth_lateral_x_m"])
    out["p14_altitude_abs_error_m"] = np.abs(out["p14_estimate_altitude_m"] - out["truth_altitude_m"])
    return out


def _available(df: pd.DataFrame) -> pd.Series:
    return df["p14_available"].astype(bool) & df["truth_visible"].astype(bool)


def _group_series(df: pd.DataFrame) -> pd.Series:
    source = df["p14_source"].fillna("").astype(str).to_numpy()
    horizon = df["p9_continuity_horizon"].astype(int).to_numpy()
    values = np.full(len(df), GROUP_BASE, dtype=object)
    values[source == "auxiliary_coarse_fallback"] = GROUP_AUX
    continuity = source == "soft_innovation_continuity"
    values[continuity & (horizon == 3)] = GROUP_H3
    values[continuity & np.isin(horizon, [4, 5, 6, 7])] = GROUP_H47
    return pd.Series(values, index=df.index, dtype="object")


def _fit_base_radii(calibration: pd.DataFrame) -> tuple[dict[str, object], dict[str, int]]:
    d = calibration[_available(calibration)].copy()
    d["p14_group"] = _group_series(d)
    counts = {g: int((d["p14_group"] == g).sum()) for g in GROUPS}
    for g, minimum in BASE_MINIMUMS.items():
        if counts[g] < minimum:
            raise RuntimeError(f"P14 base-calibration group {g} rows {counts[g]} < {minimum}")
    radii: dict[str, object] = {}
    for g in GROUPS:
        gd = d[d["p14_group"] == g]
        radii[g] = {}
        for axis in ("lateral", "altitude"):
            err = gd[f"p14_{axis}_abs_error_m"].to_numpy(float)
            raw = [p9._finite_conformal(err, q) for q in p9.TARGETS]
            nested = np.maximum.accumulate(np.asarray(raw, dtype=float))
            radii[g][axis] = {f"{q:.2f}": float(nested[i]) for i, q in enumerate(p9.TARGETS)}
    return radii, counts


def _transfer_calibrate(transfer_df: pd.DataFrame, base_radii: dict[str, object]) -> tuple[dict[str, object], dict[str, object], dict[str, int]]:
    d = transfer_df[_available(transfer_df)].copy()
    d["p14_group"] = _group_series(d)
    counts = {g: int((d["p14_group"] == g).sum()) for g in GROUPS}
    for g, minimum in TRANSFER_MINIMUMS.items():
        if counts[g] < minimum:
            raise RuntimeError(f"P14 transfer-calibration group {g} rows {counts[g]} < {minimum}")
    multipliers: dict[str, object] = {}
    final: dict[str, object] = {}
    for g in GROUPS:
        gd = d[d["p14_group"] == g]
        multipliers[g] = {}; final[g] = {}
        for axis in ("lateral", "altitude"):
            err = gd[f"p14_{axis}_abs_error_m"].to_numpy(float)
            raw_final = []
            multipliers[g][axis] = {}
            for q in p9.TARGETS:
                key = f"{q:.2f}"
                base = float(base_radii[g][axis][key])
                ratio = err / max(base, 1e-9)
                t = p9._finite_conformal(ratio, q)
                multipliers[g][axis][key] = float(t)
                raw_final.append(base * t)
            nested = np.maximum.accumulate(np.asarray(raw_final, dtype=float))
            final[g][axis] = {f"{q:.2f}": float(nested[i]) for i, q in enumerate(p9.TARGETS)}
    return multipliers, final, counts


def _build_candidate(fit_raw: pd.DataFrame, base_raw: pd.DataFrame, transfer_raw: pd.DataFrame, git_sha: str) -> tuple[dict[str, object], pd.DataFrame, pd.DataFrame]:
    velocity_caps = p9._fit_velocity_caps(fit_raw)
    innovation_scales = p9._fit_innovation_scales(fit_raw, velocity_caps)
    base = add_p14_fallback(base_raw, velocity_caps, innovation_scales)
    base_radii, base_counts = _fit_base_radii(base)
    transfer = add_p14_fallback(transfer_raw, velocity_caps, innovation_scales)
    multipliers, final_radii, transfer_counts = _transfer_calibrate(transfer, base_radii)
    candidate = {
        "schema": "aegisland.phase11.p14.candidate-freeze.v1",
        "git_sha": git_sha,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "point_estimator": "phase11_p9_soft_primary_plus_independent_coarse_fallback",
        "fit_seed": FIT_SEED,
        "base_calibration_seed": BASE_CALIBRATION_SEED,
        "transfer_calibration_seed": TRANSFER_CALIBRATION_SEED,
        "challenge_seed_unseen_at_freeze": CHALLENGE_SEED,
        "validation_seed_unseen_at_freeze": VALIDATION_SEED,
        "fit_families": list(FIT_FAMILIES),
        "base_calibration_families": list(BASE_CALIBRATION_FAMILIES),
        "transfer_calibration_families": list(TRANSFER_CALIBRATION_FAMILIES),
        "challenge_families": list(CHALLENGE_FAMILIES),
        "validation_families": list(VALIDATION_FAMILIES),
        "primary_continuity_constants": {
            "max_continuity_gap": p9.MAX_CONTINUITY_GAP,
            "damping": p9.DAMPING,
            "velocity_cap_quantile": p9.VELOCITY_CAP_QUANTILE,
            "innovation_scale_quantile": p9.INNOVATION_SCALE_QUANTILE,
            "soft_scale_multiplier": p9.SOFT_SCALE_MULTIPLIER,
            "blend_previous_slope": p9.BLEND_PREVIOUS_SLOPE,
            "blend_soft_updated_slope": p9.BLEND_SOFT_UPDATED_SLOPE,
        },
        "auxiliary_model": {
            "availability": AUX_AVAILABILITY,
            "lateral_sigma_m": AUX_LATERAL_SIGMA_M,
            "altitude_sigma_m": AUX_ALTITUDE_SIGMA_M,
            "tail_probability": AUX_TAIL_PROBABILITY,
            "tail_scale_uniform": [AUX_TAIL_SCALE_LOW, AUX_TAIL_SCALE_HIGH],
            "stream_constant": AUX_STREAM_CONSTANT,
            "fallback_only": True,
            "may_become_primary_anchor": False,
        },
        "velocity_caps": velocity_caps,
        "innovation_scales": innovation_scales,
        "groups": list(GROUPS),
        "base_minimums": BASE_MINIMUMS,
        "transfer_minimums": TRANSFER_MINIMUMS,
        "challenge_minimums": CHALLENGE_MINIMUMS,
        "base_group_rows": base_counts,
        "transfer_group_rows": transfer_counts,
        "base_radii": base_radii,
        "transfer_multipliers": multipliers,
        "direct_conformal_radii": final_radii,
    }
    return candidate, base, transfer


def _load_candidate(path: Path) -> dict[str, object]:
    c = json.loads(path.read_text(encoding="utf-8"))
    if c.get("schema") != "aegisland.phase11.p14.candidate-freeze.v1":
        raise SystemExit("invalid P14 candidate schema")
    if c.get("challenge_seed_unseen_at_freeze") != CHALLENGE_SEED or c.get("validation_seed_unseen_at_freeze") != VALIDATION_SEED:
        raise SystemExit("P14 evidence boundary mismatch")
    return c


def _halfwidths(df: pd.DataFrame, candidate: dict[str, object], axis: str, q: float) -> np.ndarray:
    groups = _group_series(df).to_numpy(str)
    table = candidate["direct_conformal_radii"]
    return np.asarray([float(table[g][axis][f"{q:.2f}"]) for g in groups], dtype=float)


def _subset_stats(df: pd.DataFrame, candidate: dict[str, object], groups: set[str]) -> dict[str, object]:
    gs = _group_series(df)
    d = df[_available(df) & gs.isin(groups)].copy()
    result: dict[str, object] = {"rows": int(len(d)), "coverage_95": {}, "p95_error": {}, "p95_halfwidth": {}, "p95_halfwidth_over_p95_error": {}}
    for axis in ("lateral", "altitude"):
        err = d[f"p14_{axis}_abs_error_m"].dropna().to_numpy(float)
        hw = _halfwidths(d, candidate, axis, 0.95) if len(d) else np.asarray([])
        if not err.size:
            for k in ("coverage_95", "p95_error", "p95_halfwidth", "p95_halfwidth_over_p95_error"):
                result[k][axis] = float("nan")
            continue
        p95e = float(np.percentile(err, 95)); p95w = float(np.percentile(hw, 95))
        result["coverage_95"][axis] = float(np.mean(err <= hw))
        result["p95_error"][axis] = p95e
        result["p95_halfwidth"][axis] = p95w
        result["p95_halfwidth_over_p95_error"][axis] = p95w / p95e if p95e > 0 else float("nan")
    return result


def _coverage(df: pd.DataFrame, candidate: dict[str, object]) -> dict[str, dict[str, float]]:
    d = df[_available(df)].copy()
    out: dict[str, dict[str, float]] = {}
    for axis in ("lateral", "altitude"):
        err = d[f"p14_{axis}_abs_error_m"].to_numpy(float)
        out[axis] = {}
        for q in p9.TARGETS:
            hw = _halfwidths(d, candidate, axis, q)
            out[axis][f"{q:.2f}"] = float(np.mean(err <= hw)) if err.size else float("nan")
    return out


def _error_interval_stats(df: pd.DataFrame, candidate: dict[str, object]) -> tuple[dict[str, float], dict[str, dict[str, float]]]:
    mask = _available(df); d = df[mask].copy()
    errors: dict[str, float] = {"available_fraction": float(mask.mean()), "available_rows": int(mask.sum()), "total_rows": int(len(df))}
    intervals: dict[str, dict[str, float]] = {}
    for axis in ("lateral", "altitude"):
        err = d[f"p14_{axis}_abs_error_m"].dropna().to_numpy(float)
        hw = _halfwidths(d, candidate, axis, 0.95)
        errors[f"{axis}_mae"] = float(np.mean(err)) if err.size else float("nan")
        errors[f"{axis}_p95"] = float(np.percentile(err, 95)) if err.size else float("nan")
        intervals[axis] = {"median_halfwidth_95": float(np.median(hw)) if hw.size else float("nan"), "p95_halfwidth_95": float(np.percentile(hw, 95)) if hw.size else float("nan")}
    return errors, intervals


def _shift_auc(reference: pd.DataFrame, evaluated: pd.DataFrame) -> float:
    return p9._shift_auc(reference, evaluated)


def _secondary(df: pd.DataFrame, candidate: dict[str, object]) -> dict[str, object]:
    primary_missing = (~df["p14_primary_available"].astype(bool)) & df["truth_visible"].astype(bool)
    aux_used = df["p14_source"].astype(str) == "auxiliary_coarse_fallback"
    recovery = float((primary_missing & aux_used).sum() / max(1, primary_missing.sum()))
    still_missing = int((df["truth_visible"].astype(bool) & ~df["p14_available"].astype(bool)).sum())
    seq = df.groupby("sequence_id").agg(primary_candidates=("candidate_available", "sum"), aux_used=("p14_source", lambda s: int((s.astype(str) == "auxiliary_coarse_fallback").sum())))
    zero_primary_sequences = int((seq["primary_candidates"] == 0).sum())
    zero_primary_with_aux = int(((seq["primary_candidates"] == 0) & (seq["aux_used"] > 0)).sum())
    aux = df[_available(df) & aux_used].copy()
    aux_stats = {"rows": int(len(aux)), "tail_events": int(aux["aux_tail_event"].sum()) if len(aux) else 0}
    for axis in ("lateral", "altitude"):
        err = aux[f"p14_{axis}_abs_error_m"].dropna().to_numpy(float)
        aux_stats[f"{axis}_mae"] = float(np.mean(err)) if err.size else float("nan")
        aux_stats[f"{axis}_p95"] = float(np.percentile(err, 95)) if err.size else float("nan")
    source_counts = {str(k): int(v) for k, v in df[_available(df)]["p14_source"].value_counts().to_dict().items()}
    return {"primary_missing_rows": int(primary_missing.sum()), "aux_recovered_rows": int((primary_missing & aux_used).sum()), "aux_recovery_fraction": recovery, "still_unavailable_rows": still_missing, "zero_primary_candidate_sequences": zero_primary_sequences, "zero_primary_sequences_with_aux_output": zero_primary_with_aux, "auxiliary_error_stats": aux_stats, "final_source_counts": source_counts}


def summarize(evaluated: pd.DataFrame, reference: pd.DataFrame, candidate: dict[str, object], role: str, seed: int, minimums: dict[str, int]) -> dict[str, object]:
    d = evaluated[_available(evaluated)].copy(); gs = _group_series(d)
    counts = {g: int((gs == g).sum()) for g in GROUPS}
    minima_pass = all(counts[g] >= minimums[g] for g in GROUPS)
    coverage = _coverage(evaluated, candidate)
    errors, intervals = _error_interval_stats(evaluated, candidate)
    continuity = _subset_stats(evaluated, candidate, {GROUP_H3, GROUP_H47})
    base = _subset_stats(evaluated, candidate, {GROUP_BASE})
    aux = _subset_stats(evaluated, candidate, {GROUP_AUX})

    h1 = {"available_fraction": errors["available_fraction"], "pass": bool(errors["available_fraction"] >= 0.95)}
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

    def honesty(stats: dict[str, object], lower: float, upper: float, max_ratio: float) -> dict[str, object]:
        result = {"rows": stats["rows"], "lateral_95_coverage": stats["coverage_95"]["lateral"], "altitude_95_coverage": stats["coverage_95"]["altitude"], "lateral_p95_halfwidth_over_p95_error": stats["p95_halfwidth_over_p95_error"]["lateral"], "altitude_p95_halfwidth_over_p95_error": stats["p95_halfwidth_over_p95_error"]["altitude"]}
        result["pass"] = bool(result["rows"] > 0 and lower <= result["lateral_95_coverage"] <= upper and lower <= result["altitude_95_coverage"] <= upper and result["lateral_p95_halfwidth_over_p95_error"] <= max_ratio and result["altitude_p95_halfwidth_over_p95_error"] <= max_ratio)
        return result

    h5 = honesty(continuity, 0.88, 0.99, 2.75)
    h6 = honesty(base, 0.90, 0.98, 2.25)
    h7 = honesty(aux, 0.90, 0.98, 2.25)
    h8 = {"trajectory_level_auroc": _shift_auc(reference, evaluated)}; h8["pass"] = bool(h8["trajectory_level_auroc"] >= 0.85)
    gates = {"group_minimums": {"counts": counts, "required": minimums, "pass": bool(minima_pass)}, "h1_useful_availability": h1, "h2_overall_coverage": h2, "h3_calibration_curve": h3, "h4_overall_interval_efficiency": h4, "h5_primary_continuity_honesty": h5, "h6_base_output_honesty": h6, "h7_auxiliary_fallback_honesty": h7, "h8_shift_discrimination": h8}
    primary = ("h1_useful_availability", "h2_overall_coverage", "h3_calibration_curve", "h4_overall_interval_efficiency", "h5_primary_continuity_honesty", "h6_base_output_honesty", "h7_auxiliary_fallback_honesty")
    return {"schema": "aegisland.phase11.p14.result.v1", "evidence_role": role, "simulation_only": True, "safety_acceptance": False, "controller_tuning_allowed": False, "real_sensor_performance_claim": False, "evaluated_seed_seen_after_run": seed, "all_primary_gates_pass": bool(minima_pass and all(gates[g]["pass"] for g in primary)), "gates": gates, "coverage": coverage, "error_stats": errors, "interval_stats": intervals, "primary_continuity_stats": continuity, "base_output_stats": base, "auxiliary_stats": aux, "secondary_diagnostics": _secondary(evaluated, candidate)}


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _manifest(out: Path, files: list[str], stage: str, git_sha: str) -> None:
    payload = {"schema": "aegisland.phase11.p14.manifest.v1", "stage": stage, "git_sha": git_sha, "simulation_only": True, "safety_acceptance": False, "controller_tuning_allowed": False, "files": {name: {"sha256": _hash_file(out / name), "bytes": (out / name).stat().st_size} for name in files}}
    (out / "manifest.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def freeze(out: Path, git_sha: str) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    fit = _raw("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS)
    base_raw = _raw("base_calibration", BASE_CALIBRATION_SEED, BASE_CALIBRATION_FAMILIES, BASE_CALIBRATION_DOMAINS)
    transfer_raw = _raw("transfer_calibration", TRANSFER_CALIBRATION_SEED, TRANSFER_CALIBRATION_FAMILIES, TRANSFER_CALIBRATION_DOMAINS)
    candidate, base, transfer = _build_candidate(fit, base_raw, transfer_raw, git_sha)
    fit.to_csv(out / "fit_frames.csv", index=False); base.to_csv(out / "base_calibration_frames.csv", index=False); transfer.to_csv(out / "transfer_calibration_frames.csv", index=False)
    (out / "candidate_freeze.json").write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(out, ["fit_frames.csv", "base_calibration_frames.csv", "transfer_calibration_frames.csv", "candidate_freeze.json"], "freeze", git_sha)
    return candidate


def challenge(out: Path, candidate_path: Path, git_sha: str) -> dict[str, object]:
    c = _load_candidate(candidate_path); out.mkdir(parents=True, exist_ok=True)
    evaluated = add_p14_fallback(_raw("challenge", CHALLENGE_SEED, CHALLENGE_FAMILIES, CHALLENGE_DOMAINS), c["velocity_caps"], c["innovation_scales"])
    reference = add_p14_fallback(_raw("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS), c["velocity_caps"], c["innovation_scales"])
    result = summarize(evaluated, reference, c, "phase11_p14_seen_challenge", CHALLENGE_SEED, CHALLENGE_MINIMUMS)
    evaluated.to_csv(out / "challenge_frames.csv", index=False); (out / "challenge_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"); (out / "candidate_freeze.json").write_text(json.dumps(c, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(out, ["challenge_frames.csv", "challenge_result.json", "candidate_freeze.json"], "challenge", git_sha)
    return result


def validate(out: Path, candidate_path: Path, git_sha: str) -> dict[str, object]:
    c = _load_candidate(candidate_path); out.mkdir(parents=True, exist_ok=True)
    evaluated = add_p14_fallback(_raw("validation", VALIDATION_SEED, VALIDATION_FAMILIES, VALIDATION_DOMAINS), c["velocity_caps"], c["innovation_scales"])
    reference = add_p14_fallback(_raw("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS), c["velocity_caps"], c["innovation_scales"])
    result = summarize(evaluated, reference, c, "phase11_p14_frozen_candidate_validation", VALIDATION_SEED, CHALLENGE_MINIMUMS)
    evaluated.to_csv(out / "validation_frames.csv", index=False); (out / "validation_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"); (out / "candidate_freeze.json").write_text(json.dumps(c, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(out, ["validation_frames.csv", "validation_result.json", "candidate_freeze.json"], "validation", git_sha)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 11 P14 independent coarse fallback simulation benchmark")
    parser.add_argument("--stage", choices=("freeze", "challenge", "validation"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--git-sha", default="unknown")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.stage == "freeze":
        c = freeze(args.out, args.git_sha); print("P14_CANDIDATE_FREEZE=" + json.dumps({"base_group_rows": c["base_group_rows"], "transfer_group_rows": c["transfer_group_rows"], "auxiliary_model": c["auxiliary_model"]}, sort_keys=True)); return
    if args.candidate is None: raise SystemExit("--candidate required")
    if args.stage == "challenge":
        r = challenge(args.out, args.candidate, args.git_sha); print("P14_CHALLENGE_GATES=" + json.dumps(r["gates"], sort_keys=True)); return
    r = validate(args.out, args.candidate, args.git_sha); print("P14_VALIDATION_GATES=" + json.dumps(r["gates"], sort_keys=True))


if __name__ == "__main__":
    main()
