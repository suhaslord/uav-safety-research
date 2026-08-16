from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scripts import run_phase11_p14_bounded_independent_rescue as p14
except ModuleNotFoundError:
    import run_phase11_p14_bounded_independent_rescue as p14

p9 = p14.p9
TARGETS = p14.TARGETS
FRAMES_PER_SEQUENCE = 60

FIT_SEED = 814814
CAL_A_SEED = 825825
CAL_B_SEED = 836836
TRANSFER_SEED = 847847
VALIDATION_SEED = 858858
FINAL_SEED = 869869

FIT_FAMILIES = tuple(range(815, 821))


def _strata(start: int, per: int) -> dict[str, tuple[int, ...]]:
    names = ("bootstrap5", "gap3", "gap7", "gap12")
    return {name: tuple(range(start + i * per, start + (i + 1) * per)) for i, name in enumerate(names)}


CAL_A_STRATA = _strata(821, 8)
CAL_B_STRATA = _strata(853, 8)
TRANSFER_STRATA = _strata(885, 6)
VALIDATION_STRATA = _strata(909, 6)
FINAL_STRATA = _strata(933, 6)


def _flatten(strata: dict[str, tuple[int, ...]]) -> tuple[int, ...]:
    return tuple(x for name in ("bootstrap5", "gap3", "gap7", "gap12") for x in strata[name])


CAL_A_FAMILIES = _flatten(CAL_A_STRATA)
CAL_B_FAMILIES = _flatten(CAL_B_STRATA)
TRANSFER_FAMILIES = _flatten(TRANSFER_STRATA)
VALIDATION_FAMILIES = _flatten(VALIDATION_STRATA)
FINAL_FAMILIES = _flatten(FINAL_STRATA)

FIT_DOMAINS = p14.FIT_DOMAINS
CAL_A_DOMAINS = (
    "edge+blur_noise+temporal_dropout",
    "small_scale+dim+temporal_dropout",
    "oblique+low_contrast+temporal_dropout",
    "edge+small_scale+dim+temporal_dropout",
    "small_scale+oblique+blur_noise+temporal_dropout",
    "edge+dim+low_contrast+temporal_dropout",
    "oblique+dim+blur_noise+temporal_dropout",
    "edge+small_scale+low_contrast+temporal_dropout",
)
CAL_B_DOMAINS = (
    "edge+small_scale+oblique+temporal_dropout",
    "edge+dim+blur_noise+temporal_dropout",
    "small_scale+dim+blur_noise+low_contrast+temporal_dropout",
    "edge+oblique+dim+low_contrast+temporal_dropout",
    "edge+small_scale+blur_noise+low_contrast+temporal_dropout",
    "small_scale+oblique+dim+blur_noise+temporal_dropout",
    "edge+oblique+dim+blur_noise+low_contrast+temporal_dropout",
    "edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout",
)
TRANSFER_DOMAINS = (
    "edge+oblique+blur_noise+temporal_dropout",
    "small_scale+oblique+low_contrast+temporal_dropout",
    "edge+small_scale+dim+low_contrast+temporal_dropout",
    "small_scale+dim+blur_noise+temporal_dropout",
    "oblique+dim+blur_noise+low_contrast+temporal_dropout",
    "edge+small_scale+oblique+blur_noise+temporal_dropout",
    "edge+dim+blur_noise+low_contrast+temporal_dropout",
    "edge+small_scale+oblique+dim+low_contrast+temporal_dropout",
    "small_scale+oblique+dim+low_contrast+temporal_dropout",
    "edge+small_scale+dim+blur_noise+low_contrast+temporal_dropout",
)
VALIDATION_DOMAINS = (
    "edge+low_contrast+temporal_dropout",
    "small_scale+blur_noise+temporal_dropout",
    "oblique+dim+temporal_dropout",
    "edge+oblique+dim+temporal_dropout",
    "small_scale+oblique+blur_noise+low_contrast+temporal_dropout",
    "edge+small_scale+oblique+dim+temporal_dropout",
    "edge+oblique+blur_noise+low_contrast+temporal_dropout",
    "small_scale+dim+low_contrast+temporal_dropout",
    "edge+small_scale+oblique+low_contrast+temporal_dropout",
    "edge+small_scale+dim+blur_noise+temporal_dropout",
)
FINAL_DOMAINS = (
    "edge+dim+temporal_dropout",
    "small_scale+low_contrast+temporal_dropout",
    "oblique+blur_noise+temporal_dropout",
    "dim+low_contrast+temporal_dropout",
    "edge+oblique+low_contrast+temporal_dropout",
    "small_scale+oblique+dim+temporal_dropout",
    "edge+small_scale+oblique+dim+blur_noise+temporal_dropout",
    "small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout",
    "edge+small_scale+oblique+blur_noise+low_contrast+temporal_dropout",
    "edge+oblique+dim+blur_noise+temporal_dropout",
)

GROUPS = p14.GROUPS
GROUP_BASE = p14.GROUP_BASE
GROUP_H3 = p14.GROUP_H3
GROUP_H45 = p14.GROUP_H45
GROUP_H67 = p14.GROUP_H67
GROUP_RESCUE = p14.GROUP_RESCUE

CAL_MINIMUMS = {
    GROUP_BASE: 900,
    GROUP_H3: 180,
    GROUP_H45: 135,
    GROUP_H67: 90,
    GROUP_RESCUE: 180,
}
EVAL_MINIMUMS = {
    GROUP_BASE: 360,
    GROUP_H3: 60,
    GROUP_H45: 45,
    GROUP_H67: 30,
    GROUP_RESCUE: 60,
}
FINAL_MINIMUMS = {
    GROUP_BASE: 450,
    GROUP_H3: 75,
    GROUP_H45: 60,
    GROUP_H67: 36,
    GROUP_RESCUE: 75,
}


def _raw(name: str, seed: int, families: tuple[int, ...], domains: tuple[str, ...]) -> pd.DataFrame:
    return p14._raw(name, seed, families, domains)


def _event(name: str, seed: int, families: tuple[int, ...], domains: tuple[str, ...], strata: dict[str, tuple[int, ...]], velocity_caps: dict[str, float], innovation_scales: dict[str, float]) -> pd.DataFrame:
    natural = _raw(name, seed, families, domains)
    forced = p14.apply_intervention(natural, name, strata)
    return p14.add_p14_rescue(forced, seed, velocity_caps, innovation_scales)


def _available(df: pd.DataFrame) -> pd.Series:
    return p14._available(df)


def _groups(df: pd.DataFrame) -> pd.Series:
    return p14._group_series(df)


def _group_counts(df: pd.DataFrame) -> dict[str, int]:
    g = _groups(df)
    a = _available(df)
    return {name: int((a & (g == name)).sum()) for name in GROUPS}


def _assert_minimums(counts: dict[str, int], minimums: dict[str, int], label: str) -> None:
    failed = {g: {"rows": int(counts.get(g, 0)), "minimum": int(minimums[g])} for g in GROUPS if counts.get(g, 0) < minimums[g]}
    if failed:
        raise RuntimeError(f"P14R {label} group minimums failed: {json.dumps(failed, sort_keys=True)}")


def _fit_group_radii(df: pd.DataFrame, label: str) -> tuple[dict[str, object], dict[str, int]]:
    counts = _group_counts(df)
    _assert_minimums(counts, CAL_MINIMUMS, label)
    d = df[_available(df)].copy()
    d["p14r_group"] = _groups(d)
    radii: dict[str, object] = {}
    for group in GROUPS:
        gd = d[d["p14r_group"] == group]
        radii[group] = {}
        for axis in ("lateral", "altitude"):
            err = gd[f"p14_{axis}_abs_error_m"].to_numpy(float)
            raw = [p9._finite_conformal(err, q) for q in TARGETS]
            nested = np.maximum.accumulate(np.asarray(raw, dtype=float))
            radii[group][axis] = {f"{q:.2f}": float(nested[i]) for i, q in enumerate(TARGETS)}
    return radii, counts


def _max_envelope(a: dict[str, object], b: dict[str, object]) -> dict[str, object]:
    out: dict[str, object] = {}
    for group in GROUPS:
        out[group] = {}
        for axis in ("lateral", "altitude"):
            out[group][axis] = {}
            for q in TARGETS:
                key = f"{q:.2f}"
                out[group][axis][key] = float(max(float(a[group][axis][key]), float(b[group][axis][key])))
    return out


def _severity_thresholds(a: pd.DataFrame, b: pd.DataFrame) -> dict[str, float]:
    d = pd.concat([a, b], ignore_index=True)
    avail = _available(d)
    groups = _groups(d)
    out: dict[str, float] = {}
    for group in GROUPS:
        vals = d.loc[avail & (groups == group), "severity"].dropna().to_numpy(float)
        if vals.size < CAL_MINIMUMS[group] * 2:
            raise RuntimeError(f"P14R severity threshold group {group} is underpowered")
        out[group] = float(np.quantile(vals, 2.0 / 3.0))
    return out


def _halfwidths(df: pd.DataFrame, candidate: dict[str, object], axis: str, q: float) -> np.ndarray:
    groups = _groups(df).astype(str).to_numpy()
    table = candidate["robust_group_radii"]
    key = f"{q:.2f}"
    return np.asarray([float(table[g][axis][key]) for g in groups], dtype=float)


def _coverage(df: pd.DataFrame, candidate: dict[str, object]) -> dict[str, dict[str, float]]:
    d = df[_available(df)].copy()
    out: dict[str, dict[str, float]] = {}
    for axis in ("lateral", "altitude"):
        err = d[f"p14_{axis}_abs_error_m"].to_numpy(float)
        out[axis] = {}
        for q in TARGETS:
            hw = _halfwidths(d, candidate, axis, q)
            out[axis][f"{q:.2f}"] = float(np.mean(err <= hw)) if err.size else float("nan")
    return out


def _subset_stats(df: pd.DataFrame, candidate: dict[str, object], mask: pd.Series) -> dict[str, object]:
    d = df[_available(df) & mask].copy()
    result: dict[str, object] = {"rows": int(len(d)), "coverage_95": {}, "mae": {}, "p95_error": {}, "p95_halfwidth": {}, "p95_halfwidth_over_p95_error": {}}
    for axis in ("lateral", "altitude"):
        err = d[f"p14_{axis}_abs_error_m"].dropna().to_numpy(float)
        if not err.size:
            for key in ("coverage_95", "mae", "p95_error", "p95_halfwidth", "p95_halfwidth_over_p95_error"):
                result[key][axis] = float("nan")
            continue
        hw = _halfwidths(d, candidate, axis, 0.95)
        p95e = float(np.percentile(err, 95))
        p95w = float(np.percentile(hw, 95))
        result["coverage_95"][axis] = float(np.mean(err <= hw))
        result["mae"][axis] = float(np.mean(err))
        result["p95_error"][axis] = p95e
        result["p95_halfwidth"][axis] = p95w
        result["p95_halfwidth_over_p95_error"][axis] = p95w / p95e if p95e > 0 else float("nan")
    return result


def _overall_stats(df: pd.DataFrame, candidate: dict[str, object]) -> tuple[dict[str, float], dict[str, dict[str, float]]]:
    d = df[_available(df)].copy()
    truth_rows = int(df["truth_visible"].astype(bool).sum())
    errors: dict[str, float] = {"available_fraction": float(len(d) / truth_rows) if truth_rows else float("nan"), "available_rows": int(len(d)), "truth_visible_rows": truth_rows}
    intervals: dict[str, dict[str, float]] = {}
    for axis in ("lateral", "altitude"):
        err = d[f"p14_{axis}_abs_error_m"].to_numpy(float)
        hw = _halfwidths(d, candidate, axis, 0.95)
        errors[f"{axis}_mae"] = float(np.mean(err)) if err.size else float("nan")
        errors[f"{axis}_p95"] = float(np.percentile(err, 95)) if err.size else float("nan")
        intervals[axis] = {"median_halfwidth_95": float(np.median(hw)) if hw.size else float("nan"), "p95_halfwidth_95": float(np.percentile(hw, 95)) if hw.size else float("nan")}
    return errors, intervals


def _reference(candidate: dict[str, object]) -> pd.DataFrame:
    raw = _raw("p14r_fit_reference", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS)
    return p9.add_p9_continuity(raw, candidate["velocity_caps"], candidate["innovation_scales"])


def _high_mask(df: pd.DataFrame, candidate: dict[str, object]) -> pd.Series:
    groups = _groups(df).astype(str)
    sev = df["severity"].to_numpy(float)
    thresholds = candidate["high_severity_thresholds"]
    return pd.Series([bool(np.isfinite(sev[i]) and sev[i] > float(thresholds[g])) for i, g in enumerate(groups)], index=df.index)


def summarize(df: pd.DataFrame, candidate: dict[str, object], role: str, seed: int, minimums: dict[str, int]) -> dict[str, object]:
    counts = _group_counts(df)
    power_pass = True
    try:
        _assert_minimums(counts, minimums, role)
    except RuntimeError:
        power_pass = False

    coverage = _coverage(df, candidate)
    errors, intervals = _overall_stats(df, candidate)
    groups = _groups(df)
    continuity = _subset_stats(df, candidate, groups.isin({GROUP_H3, GROUP_H45, GROUP_H67}))
    base = _subset_stats(df, candidate, groups == GROUP_BASE)
    high = _subset_stats(df, candidate, _high_mask(df, candidate))
    rescue = _subset_stats(df, candidate, groups == GROUP_RESCUE)

    h1 = {"available_fraction": errors["available_fraction"], "pass": bool(errors["available_fraction"] >= 0.92)}
    h2 = {"lateral_95_coverage": coverage["lateral"]["0.95"], "altitude_95_coverage": coverage["altitude"]["0.95"]}
    h2["pass"] = bool(0.90 <= h2["lateral_95_coverage"] <= 0.98 and 0.90 <= h2["altitude_95_coverage"] <= 0.98)
    mace = float(np.mean([abs(coverage[a][f"{q:.2f}"] - q) for a in ("lateral", "altitude") for q in TARGETS]))
    h3 = {"mean_absolute_coverage_error": mace, "pass": bool(mace <= 0.06)}
    h4: dict[str, object] = {}
    for axis in ("lateral", "altitude"):
        p95e = errors[f"{axis}_p95"]
        h4[f"{axis}_median_halfwidth_over_p95_error"] = intervals[axis]["median_halfwidth_95"] / p95e
        h4[f"{axis}_p95_halfwidth_over_p95_error"] = intervals[axis]["p95_halfwidth_95"] / p95e
    h4["pass"] = bool(all(h4[f"{axis}_median_halfwidth_over_p95_error"] <= 1.25 and h4[f"{axis}_p95_halfwidth_over_p95_error"] <= 2.25 for axis in ("lateral", "altitude")))

    def honesty(stats: dict[str, object], lo: float, hi: float, ratio: float) -> dict[str, object]:
        out = {
            "rows": stats["rows"],
            "lateral_95_coverage": stats["coverage_95"]["lateral"],
            "altitude_95_coverage": stats["coverage_95"]["altitude"],
            "lateral_p95_halfwidth_over_p95_error": stats["p95_halfwidth_over_p95_error"]["lateral"],
            "altitude_p95_halfwidth_over_p95_error": stats["p95_halfwidth_over_p95_error"]["altitude"],
        }
        out["pass"] = bool(out["rows"] > 0 and lo <= out["lateral_95_coverage"] <= hi and lo <= out["altitude_95_coverage"] <= hi and out["lateral_p95_halfwidth_over_p95_error"] <= ratio and out["altitude_p95_halfwidth_over_p95_error"] <= ratio)
        return out

    h5 = honesty(continuity, 0.88, 0.99, 2.75)
    h6 = honesty(base, 0.90, 0.98, 2.25)
    h7 = {"trajectory_level_auroc": p9._shift_auc(_reference(candidate), df)}
    h7["pass"] = bool(h7["trajectory_level_auroc"] >= 0.85)
    h8 = honesty(high, 0.88, 0.99, 2.75)
    h9 = honesty(rescue, 0.90, 0.98, 2.25)
    h10 = {
        "lateral_mae": rescue["mae"]["lateral"],
        "altitude_mae": rescue["mae"]["altitude"],
        "lateral_p95_error": rescue["p95_error"]["lateral"],
        "altitude_p95_error": rescue["p95_error"]["altitude"],
    }
    h10["pass"] = bool(h10["lateral_mae"] <= 0.15 and h10["altitude_mae"] <= 0.30 and h10["lateral_p95_error"] <= 0.35 and h10["altitude_p95_error"] <= 0.70)
    primary_unavailable = df["truth_visible"].astype(bool) & (~df["p14_primary_available"].astype(bool))
    rescued = primary_unavailable & (df["p14_source"].astype(str) == GROUP_RESCUE)
    recovered = float(rescued.sum() / primary_unavailable.sum()) if primary_unavailable.sum() else 1.0
    h11 = {"primary_unavailable_rows": int(primary_unavailable.sum()), "rescued_rows": int(rescued.sum()), "recovered_fraction": recovered, "pass": bool(recovered >= 0.85)}

    gates = {
        "group_minimums": {"counts": counts, "required": minimums, "pass": bool(power_pass)},
        "h1_useful_availability": h1,
        "h2_overall_coverage": h2,
        "h3_calibration_curve": h3,
        "h4_overall_interval_efficiency": h4,
        "h5_primary_continuity_honesty": h5,
        "h6_base_output_honesty": h6,
        "h7_shift_discrimination": h7,
        "h8_high_severity_honesty": h8,
        "h9_rescue_output_honesty": h9,
        "h10_rescue_accuracy_floor": h10,
        "h11_rescue_effectiveness": h11,
    }
    required = ("h1_useful_availability", "h2_overall_coverage", "h3_calibration_curve", "h4_overall_interval_efficiency", "h5_primary_continuity_honesty", "h6_base_output_honesty", "h8_high_severity_honesty", "h9_rescue_output_honesty", "h10_rescue_accuracy_floor", "h11_rescue_effectiveness")
    return {
        "schema": "aegisland.phase11.p14r.result.v1",
        "evidence_role": role,
        "evaluated_seed_seen_after_run": seed,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "all_primary_gates_pass": bool(power_pass and all(bool(gates[k]["pass"]) for k in required)),
        "coverage": coverage,
        "error_stats": errors,
        "interval_stats": intervals,
        "gates": gates,
    }


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _manifest(out: Path, files: list[str], stage: str, git_sha: str) -> None:
    payload = {
        "schema": "aegisland.phase11.p14r.manifest.v1",
        "stage": stage,
        "git_sha": git_sha,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "files": {name: {"sha256": _hash_file(out / name), "bytes": (out / name).stat().st_size} for name in files},
    }
    (out / "manifest.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def freeze(out: Path, git_sha: str) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    fit_raw = _raw("p14r_fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS)
    velocity_caps = p9._fit_velocity_caps(fit_raw)
    innovation_scales = p9._fit_innovation_scales(fit_raw, velocity_caps)
    cal_a = _event("p14r_calibration_a", CAL_A_SEED, CAL_A_FAMILIES, CAL_A_DOMAINS, CAL_A_STRATA, velocity_caps, innovation_scales)
    cal_b = _event("p14r_calibration_b", CAL_B_SEED, CAL_B_FAMILIES, CAL_B_DOMAINS, CAL_B_STRATA, velocity_caps, innovation_scales)
    radii_a, counts_a = _fit_group_radii(cal_a, "calibration_a")
    radii_b, counts_b = _fit_group_radii(cal_b, "calibration_b")
    robust = _max_envelope(radii_a, radii_b)
    thresholds = _severity_thresholds(cal_a, cal_b)
    candidate = {
        "schema": "aegisland.phase11.p14r.candidate-freeze.v1",
        "git_sha": git_sha,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "point_estimator": "unchanged_p14_bounded_primary_plus_independent_coarse_rescue",
        "uncertainty_calibration": "groupwise_max_of_two_disjoint_direct_conformal_environments",
        "fit_seed": FIT_SEED,
        "calibration_a_seed": CAL_A_SEED,
        "calibration_b_seed": CAL_B_SEED,
        "transfer_seed_unseen_at_freeze": TRANSFER_SEED,
        "validation_seed_unseen_at_freeze": VALIDATION_SEED,
        "final_seed_unseen_at_freeze": FINAL_SEED,
        "velocity_caps": velocity_caps,
        "innovation_scales": innovation_scales,
        "calibration_a_group_rows": counts_a,
        "calibration_b_group_rows": counts_b,
        "calibration_a_radii": radii_a,
        "calibration_b_radii": radii_b,
        "robust_group_radii": robust,
        "high_severity_thresholds": thresholds,
        "rescue_model": {
            "availability": p14.RESCUE_AVAILABILITY,
            "lateral_sigma_m": p14.RESCUE_LATERAL_SIGMA_M,
            "altitude_sigma_m": p14.RESCUE_ALTITUDE_SIGMA_M,
            "tail_probability": p14.RESCUE_TAIL_PROBABILITY,
            "tail_scale": p14.RESCUE_TAIL_SCALE,
            "stream_tag": p14.RESCUE_STREAM_TAG,
            "fallback_only": True,
            "may_become_primary_anchor": False,
        },
    }
    fit_raw.to_csv(out / "fit_frames.csv", index=False)
    cal_a.to_csv(out / "calibration_a_frames.csv", index=False)
    cal_b.to_csv(out / "calibration_b_frames.csv", index=False)
    (out / "candidate_freeze.json").write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(out, ["fit_frames.csv", "calibration_a_frames.csv", "calibration_b_frames.csv", "candidate_freeze.json"], "freeze", git_sha)
    return candidate


def _load_candidate(path: Path) -> dict[str, object]:
    c = json.loads(path.read_text(encoding="utf-8"))
    if c.get("schema") != "aegisland.phase11.p14r.candidate-freeze.v1":
        raise SystemExit("invalid P14R candidate schema")
    if c.get("transfer_seed_unseen_at_freeze") != TRANSFER_SEED or c.get("validation_seed_unseen_at_freeze") != VALIDATION_SEED or c.get("final_seed_unseen_at_freeze") != FINAL_SEED:
        raise SystemExit("P14R evidence boundary mismatch")
    return c


def evaluate(stage: str, out: Path, candidate_path: Path, git_sha: str) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    c = _load_candidate(candidate_path)
    if stage == "transfer":
        seed, families, domains, strata, minimums = TRANSFER_SEED, TRANSFER_FAMILIES, TRANSFER_DOMAINS, TRANSFER_STRATA, EVAL_MINIMUMS
    elif stage == "validation":
        seed, families, domains, strata, minimums = VALIDATION_SEED, VALIDATION_FAMILIES, VALIDATION_DOMAINS, VALIDATION_STRATA, EVAL_MINIMUMS
    elif stage == "final":
        seed, families, domains, strata, minimums = FINAL_SEED, FINAL_FAMILIES, FINAL_DOMAINS, FINAL_STRATA, FINAL_MINIMUMS
    else:
        raise SystemExit(f"invalid stage {stage}")
    frames = _event(f"p14r_{stage}", seed, families, domains, strata, c["velocity_caps"], c["innovation_scales"])
    result = summarize(frames, c, f"phase11_p14r_{stage}", seed, minimums)
    frames.to_csv(out / f"{stage}_frames.csv", index=False)
    (out / f"{stage}_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "candidate_freeze.json").write_text(json.dumps(c, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(out, [f"{stage}_frames.csv", f"{stage}_result.json", "candidate_freeze.json"], stage, git_sha)
    return result


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase 11 P14R robust groupwise conformal envelope")
    p.add_argument("--stage", choices=("freeze", "transfer", "validation", "final"), required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--candidate", type=Path)
    p.add_argument("--git-sha", default="unknown")
    return p.parse_args()


def main() -> None:
    a = parse_args()
    if a.stage == "freeze":
        c = freeze(a.out, a.git_sha)
        print("P14R_CANDIDATE_FREEZE=" + json.dumps({"calibration_a_group_rows": c["calibration_a_group_rows"], "calibration_b_group_rows": c["calibration_b_group_rows"], "high_severity_thresholds": c["high_severity_thresholds"]}, sort_keys=True))
    else:
        if a.candidate is None:
            raise SystemExit("--candidate required")
        r = evaluate(a.stage, a.out, a.candidate, a.git_sha)
        print(f"P14R_{a.stage.upper()}_GATES=" + json.dumps({"all_primary_gates_pass": r["all_primary_gates_pass"], "gates": r["gates"]}, sort_keys=True))


if __name__ == "__main__":
    main()
