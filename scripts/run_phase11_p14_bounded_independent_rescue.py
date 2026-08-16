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

FIT_SEED = 704704
PARTITION_SEED = 715715
CALIBRATION_SEED = 726726
TRANSFER_SEED = 737737
VALIDATION_SEED = 748748
FRAMES_PER_SEQUENCE = 60
TARGETS = p9.TARGETS

FIT_FAMILIES = tuple(range(700, 706))
PARTITION_STRATA = {
    "bootstrap5": tuple(range(706, 712)),
    "gap3": tuple(range(712, 718)),
    "gap7": tuple(range(718, 724)),
    "gap12": tuple(range(724, 730)),
}
CALIBRATION_STRATA = {
    "bootstrap5": tuple(range(730, 738)),
    "gap3": tuple(range(738, 746)),
    "gap7": tuple(range(746, 754)),
    "gap12": tuple(range(754, 762)),
}
TRANSFER_STRATA = {
    "bootstrap5": tuple(range(762, 766)),
    "gap3": tuple(range(766, 770)),
    "gap7": tuple(range(770, 774)),
    "gap12": tuple(range(774, 778)),
}
VALIDATION_STRATA = {
    "bootstrap5": tuple(range(778, 782)),
    "gap3": tuple(range(782, 786)),
    "gap7": tuple(range(786, 790)),
    "gap12": tuple(range(790, 794)),
}


def _flatten(strata: dict[str, tuple[int, ...]]) -> tuple[int, ...]:
    return tuple(f for name in ("bootstrap5", "gap3", "gap7", "gap12") for f in strata[name])


PARTITION_FAMILIES = _flatten(PARTITION_STRATA)
CALIBRATION_FAMILIES = _flatten(CALIBRATION_STRATA)
TRANSFER_FAMILIES = _flatten(TRANSFER_STRATA)
VALIDATION_FAMILIES = _flatten(VALIDATION_STRATA)

FIT_DOMAINS = p9.FIT_DOMAINS
PARTITION_CALIBRATION_DOMAINS = (
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
    "small_scale+dim+low_contrast+temporal_dropout",
    "oblique+blur_noise+temporal_dropout",
    "edge+small_scale+dim+temporal_dropout",
    "edge+oblique+low_contrast+temporal_dropout",
    "small_scale+oblique+dim+blur_noise+temporal_dropout",
    "edge+dim+blur_noise+low_contrast+temporal_dropout",
    "edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout",
)
VALIDATION_DOMAINS = (
    "edge+small_scale+low_contrast+temporal_dropout",
    "small_scale+oblique+blur_noise+temporal_dropout",
    "oblique+dim+low_contrast+temporal_dropout",
    "edge+dim+blur_noise+temporal_dropout",
    "small_scale+dim+blur_noise+low_contrast+temporal_dropout",
    "edge+oblique+dim+blur_noise+temporal_dropout",
    "edge+small_scale+oblique+low_contrast+temporal_dropout",
    "edge+small_scale+oblique+dim+low_contrast+temporal_dropout",
)

RESCUE_AVAILABILITY = 0.95
RESCUE_LATERAL_SIGMA_M = 0.10
RESCUE_ALTITUDE_SIGMA_M = 0.20
RESCUE_TAIL_PROBABILITY = 0.02
RESCUE_TAIL_SCALE = 3.0
RESCUE_STREAM_TAG = "aegisland-p14-independent-rescue-v1"

GROUP_BASE = p9.GROUP_BASE
GROUP_H3 = p9.GROUP_H3
GROUP_H45 = p9.GROUP_H45
GROUP_H67 = p9.GROUP_H67
GROUP_RESCUE = "independent_coarse_rescue"
GROUPS = (GROUP_BASE, GROUP_H3, GROUP_H45, GROUP_H67, GROUP_RESCUE)
SEVERITY_LABELS = ("low", "mid", "high")

PARTITION_MINIMUMS = {
    GROUP_BASE: 1200,
    GROUP_H3: 180,
    GROUP_H45: 120,
    GROUP_H67: 80,
    GROUP_RESCUE: 300,
}
CALIBRATION_CELL_MINIMUMS = {
    GROUP_BASE: 300,
    GROUP_H3: 60,
    GROUP_H45: 45,
    GROUP_H67: 30,
    GROUP_RESCUE: 60,
}
EVALUATION_CELL_MINIMUMS = {
    GROUP_BASE: 120,
    GROUP_H3: 20,
    GROUP_H45: 15,
    GROUP_H67: 10,
    GROUP_RESCUE: 20,
}


def _raw(name: str, seed: int, families: tuple[int, ...], domains: tuple[str, ...]) -> pd.DataFrame:
    return p9.p1.generate_split(name, seed, families, domains, frames=FRAMES_PER_SEQUENCE)


def _family_stratum_map(strata: dict[str, tuple[int, ...]]) -> dict[int, str]:
    out: dict[int, str] = {}
    for name, families in strata.items():
        for family in families:
            if family in out:
                raise RuntimeError(f"duplicate P14 family {family}")
            out[int(family)] = name
    return out


def forced_dropout_mask(df: pd.DataFrame, strata: dict[str, tuple[int, ...]]) -> pd.Series:
    family_to_stratum = _family_stratum_map(strata)
    labels = df["family"].map(family_to_stratum)
    if labels.isna().any():
        raise RuntimeError("P14 family missing from preregistered intervention stratum")
    frame = df["frame_index"].astype(int)
    mask = pd.Series(False, index=df.index)
    mask |= (labels == "bootstrap5") & (frame >= 0) & (frame <= 4)
    for name, gap in (("gap3", 3), ("gap7", 7), ("gap12", 12)):
        for start in (12, 42):
            mask |= (labels == name) & (frame >= start) & (frame < start + gap)
    return mask


def apply_intervention(raw: pd.DataFrame, stage: str, strata: dict[str, tuple[int, ...]]) -> pd.DataFrame:
    out = raw.copy()
    family_to_stratum = _family_stratum_map(strata)
    out["p14_intervention_stage"] = stage
    out["p14_intervention_stratum"] = out["family"].map(family_to_stratum).astype(str)
    forced = forced_dropout_mask(out, strata)
    out["p14_forced_dropout"] = forced.astype(bool)
    out.loc[forced, "candidate_available"] = False
    out.loc[forced, "candidate_source"] = None
    for col in ("estimate_lateral_x_m", "estimate_altitude_m", "lateral_abs_error_m", "altitude_abs_error_m"):
        if col in out.columns:
            out.loc[forced, col] = np.nan
    return out


def _rescue_rng(split_seed: int, sequence_id: str, frame_index: int) -> np.random.Generator:
    token = f"{RESCUE_STREAM_TAG}|{split_seed}|{sequence_id}|{frame_index}".encode("utf-8")
    seed = int.from_bytes(sha256(token).digest()[:8], "little", signed=False)
    return np.random.default_rng(seed)


def add_p14_rescue(raw: pd.DataFrame, split_seed: int, velocity_caps: dict[str, float], innovation_scales: dict[str, float]) -> pd.DataFrame:
    out = p9.add_p9_continuity(raw, velocity_caps, innovation_scales).copy()
    out["p14_primary_available"] = out["p9_available"].astype(bool)
    out["p14_primary_unavailable_reason"] = out["p9_unavailable_reason"].fillna("").astype(str)
    out["p14_rescue_observation_available"] = False
    out["p14_rescue_tail_event"] = False
    out["p14_rescue_estimate_lateral_x_m"] = np.nan
    out["p14_rescue_estimate_altitude_m"] = np.nan

    for idx, row in out.iterrows():
        if not bool(row["truth_visible"]):
            continue
        rng = _rescue_rng(split_seed, str(row["sequence_id"]), int(row["frame_index"]))
        available = bool(rng.random() < RESCUE_AVAILABILITY)
        out.loc[idx, "p14_rescue_observation_available"] = available
        if not available:
            continue
        tail = bool(rng.random() < RESCUE_TAIL_PROBABILITY)
        scale = RESCUE_TAIL_SCALE if tail else 1.0
        lat_noise = float(rng.normal(0.0, RESCUE_LATERAL_SIGMA_M * scale))
        alt_noise = float(rng.normal(0.0, RESCUE_ALTITUDE_SIGMA_M * scale))
        out.loc[idx, "p14_rescue_tail_event"] = tail
        out.loc[idx, "p14_rescue_estimate_lateral_x_m"] = float(row["truth_lateral_x_m"]) + lat_noise
        out.loc[idx, "p14_rescue_estimate_altitude_m"] = float(row["truth_altitude_m"]) + alt_noise

    out["p14_available"] = out["p9_available"].astype(bool)
    out["p14_estimate_lateral_x_m"] = out["p9_estimate_lateral_x_m"]
    out["p14_estimate_altitude_m"] = out["p9_estimate_altitude_m"]
    out["p14_source"] = out["p9_source"].fillna("").astype(str)

    rescue = (~out["p9_available"].astype(bool)) & out["truth_visible"].astype(bool) & out["p14_rescue_observation_available"].astype(bool)
    out.loc[rescue, "p14_available"] = True
    out.loc[rescue, "p14_estimate_lateral_x_m"] = out.loc[rescue, "p14_rescue_estimate_lateral_x_m"]
    out.loc[rescue, "p14_estimate_altitude_m"] = out.loc[rescue, "p14_rescue_estimate_altitude_m"]
    out.loc[rescue, "p14_source"] = GROUP_RESCUE

    out["p14_lateral_abs_error_m"] = np.abs(out["p14_estimate_lateral_x_m"] - out["truth_lateral_x_m"])
    out["p14_altitude_abs_error_m"] = np.abs(out["p14_estimate_altitude_m"] - out["truth_altitude_m"])
    return out


def _available(df: pd.DataFrame) -> pd.Series:
    return df["p14_available"].astype(bool) & df["truth_visible"].astype(bool)


def _group_series(df: pd.DataFrame) -> pd.Series:
    source = df["p14_source"].fillna("").astype(str).to_numpy()
    horizon = df["p9_continuity_horizon"].astype(int).to_numpy()
    values = np.full(len(df), GROUP_BASE, dtype=object)
    values[source == GROUP_RESCUE] = GROUP_RESCUE
    continuity = source == "soft_innovation_continuity"
    values[continuity & (horizon == 3)] = GROUP_H3
    values[continuity & np.isin(horizon, [4, 5])] = GROUP_H45
    values[continuity & np.isin(horizon, [6, 7])] = GROUP_H67
    return pd.Series(values, index=df.index, dtype="object")


def _fit_severity_cutpoints(partition: pd.DataFrame) -> dict[str, dict[str, float]]:
    avail = _available(partition)
    groups = _group_series(partition)
    result: dict[str, dict[str, float]] = {}
    for group in GROUPS:
        values = partition.loc[avail & (groups == group), "severity"].dropna().to_numpy(float)
        minimum = PARTITION_MINIMUMS[group]
        if values.size < minimum:
            raise RuntimeError(f"P14 partition group {group} rows {values.size} < {minimum}")
        if not np.all(np.isfinite(values)):
            raise RuntimeError(f"non-finite P14 partition severity in {group}")
        lower, upper = np.quantile(values, [1.0 / 3.0, 2.0 / 3.0])
        if not np.isfinite(lower) or not np.isfinite(upper) or upper <= lower:
            raise RuntimeError(f"invalid P14 severity cutpoints for {group}: {lower}, {upper}")
        result[group] = {"lower": float(lower), "upper": float(upper), "rows": int(values.size)}
    return result


def _severity_regime(df: pd.DataFrame, cutpoints: dict[str, dict[str, float]]) -> pd.Series:
    groups = _group_series(df).astype(str)
    severity = df["severity"].to_numpy(float)
    labels: list[str] = []
    for i, group in enumerate(groups):
        if not np.isfinite(severity[i]):
            raise RuntimeError("non-finite inference-visible severity on P14 evaluated row")
        cp = cutpoints[group]
        if severity[i] <= float(cp["lower"]):
            labels.append("low")
        elif severity[i] <= float(cp["upper"]):
            labels.append("mid")
        else:
            labels.append("high")
    return pd.Series(labels, index=df.index, dtype="object")


def _cell_series(df: pd.DataFrame, cutpoints: dict[str, dict[str, float]]) -> pd.Series:
    return _group_series(df).astype(str) + "__" + _severity_regime(df, cutpoints).astype(str)


def _cell_counts(df: pd.DataFrame, cutpoints: dict[str, dict[str, float]]) -> dict[str, int]:
    d = df[_available(df)].copy()
    cells = _cell_series(d, cutpoints)
    return {f"{g}__{s}": int((cells == f"{g}__{s}").sum()) for g in GROUPS for s in SEVERITY_LABELS}


def _assert_cell_minimums(counts: dict[str, int], minimums: dict[str, int], label: str) -> None:
    failed: dict[str, dict[str, int]] = {}
    for group in GROUPS:
        for sev in SEVERITY_LABELS:
            cell = f"{group}__{sev}"
            minimum = minimums[group]
            if counts.get(cell, 0) < minimum:
                failed[cell] = {"rows": int(counts.get(cell, 0)), "minimum": int(minimum)}
    if failed:
        raise RuntimeError(f"P14 {label} cell minimums failed: {json.dumps(failed, sort_keys=True)}")


def _fit_direct_radii(calibration: pd.DataFrame, cutpoints: dict[str, dict[str, float]]) -> tuple[dict[str, object], dict[str, int]]:
    d = calibration[_available(calibration)].copy()
    d["p14_cell"] = _cell_series(d, cutpoints)
    counts = _cell_counts(calibration, cutpoints)
    _assert_cell_minimums(counts, CALIBRATION_CELL_MINIMUMS, "calibration")
    radii: dict[str, object] = {}
    for group in GROUPS:
        for sev in SEVERITY_LABELS:
            cell = f"{group}__{sev}"
            gd = d[d["p14_cell"] == cell]
            radii[cell] = {}
            for axis in ("lateral", "altitude"):
                errors = gd[f"p14_{axis}_abs_error_m"].to_numpy(float)
                raw = [p9._finite_conformal(errors, q) for q in TARGETS]
                nested = np.maximum.accumulate(np.asarray(raw, dtype=float))
                radii[cell][axis] = {f"{q:.2f}": float(nested[i]) for i, q in enumerate(TARGETS)}
    return radii, counts


def _halfwidths(df: pd.DataFrame, candidate: dict[str, object], axis: str, q: float) -> np.ndarray:
    cells = _cell_series(df, candidate["severity_cutpoints"]).astype(str)
    table = candidate["direct_mondrian_radii"]
    return np.asarray([float(table[cell][axis][f"{q:.2f}"]) for cell in cells], dtype=float)


def _coverage(df: pd.DataFrame, candidate: dict[str, object]) -> dict[str, dict[str, float]]:
    d = df[_available(df)].copy()
    result: dict[str, dict[str, float]] = {}
    for axis in ("lateral", "altitude"):
        err = d[f"p14_{axis}_abs_error_m"].to_numpy(float)
        result[axis] = {}
        for q in TARGETS:
            hw = _halfwidths(d, candidate, axis, q)
            result[axis][f"{q:.2f}"] = float(np.mean(err <= hw)) if err.size else float("nan")
    return result


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
    errors: dict[str, float] = {"available_fraction": float(_available(df).mean()), "available_rows": int(len(d)), "total_rows": int(df["truth_visible"].sum())}
    intervals: dict[str, dict[str, float]] = {}
    for axis in ("lateral", "altitude"):
        err = d[f"p14_{axis}_abs_error_m"].to_numpy(float)
        hw = _halfwidths(d, candidate, axis, 0.95)
        errors[f"{axis}_mae"] = float(np.mean(err)) if err.size else float("nan")
        errors[f"{axis}_p95"] = float(np.percentile(err, 95)) if err.size else float("nan")
        intervals[axis] = {"median_halfwidth_95": float(np.median(hw)) if hw.size else float("nan"), "p95_halfwidth_95": float(np.percentile(hw, 95)) if hw.size else float("nan")}
    return errors, intervals


def _reference(candidate: dict[str, object]) -> pd.DataFrame:
    raw = _raw("fit_reference", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS)
    return p9.add_p9_continuity(raw, candidate["velocity_caps"], candidate["innovation_scales"])


def summarize(evaluated: pd.DataFrame, candidate: dict[str, object], role: str, seed: int, require_cells: bool) -> dict[str, object]:
    available = _available(evaluated)
    groups = _group_series(evaluated)
    regimes = _severity_regime(evaluated, candidate["severity_cutpoints"])
    counts = _cell_counts(evaluated, candidate["severity_cutpoints"])
    cells_pass = True
    if require_cells:
        try:
            _assert_cell_minimums(counts, EVALUATION_CELL_MINIMUMS, "evaluation")
        except RuntimeError:
            cells_pass = False

    coverage = _coverage(evaluated, candidate)
    errors, intervals = _overall_stats(evaluated, candidate)
    continuity = _subset_stats(evaluated, candidate, groups.isin({GROUP_H3, GROUP_H45, GROUP_H67}))
    base = _subset_stats(evaluated, candidate, groups == GROUP_BASE)
    high = _subset_stats(evaluated, candidate, regimes == "high")
    rescue = _subset_stats(evaluated, candidate, groups == GROUP_RESCUE)

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
        result = {
            "rows": stats["rows"],
            "lateral_95_coverage": stats["coverage_95"]["lateral"],
            "altitude_95_coverage": stats["coverage_95"]["altitude"],
            "lateral_p95_halfwidth_over_p95_error": stats["p95_halfwidth_over_p95_error"]["lateral"],
            "altitude_p95_halfwidth_over_p95_error": stats["p95_halfwidth_over_p95_error"]["altitude"],
        }
        result["pass"] = bool(result["rows"] > 0 and lo <= result["lateral_95_coverage"] <= hi and lo <= result["altitude_95_coverage"] <= hi and result["lateral_p95_halfwidth_over_p95_error"] <= ratio and result["altitude_p95_halfwidth_over_p95_error"] <= ratio)
        return result

    h5 = honesty(continuity, 0.88, 0.99, 2.75)
    h6 = honesty(base, 0.90, 0.98, 2.25)
    h7 = {"trajectory_level_auroc": p9._shift_auc(_reference(candidate), evaluated)}
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
    primary_unavailable = evaluated["truth_visible"].astype(bool) & (~evaluated["p14_primary_available"].astype(bool))
    rescued = primary_unavailable & (evaluated["p14_source"].astype(str) == GROUP_RESCUE)
    rescue_fraction = float(rescued.sum() / primary_unavailable.sum()) if primary_unavailable.sum() else 1.0
    h11 = {"primary_unavailable_rows": int(primary_unavailable.sum()), "rescued_rows": int(rescued.sum()), "recovered_fraction": rescue_fraction, "pass": bool(rescue_fraction >= 0.85)}

    reason_counts = evaluated.loc[primary_unavailable, "p14_primary_unavailable_reason"].value_counts().to_dict()
    rescued_reason_counts = evaluated.loc[rescued, "p14_primary_unavailable_reason"].value_counts().to_dict()
    gates = {
        "cell_minimums": {"counts": counts, "required_per_group": EVALUATION_CELL_MINIMUMS, "pass": bool(cells_pass)},
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
        "schema": "aegisland.phase11.p14.result.v1",
        "evidence_role": role,
        "evaluated_seed_seen_after_run": seed,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "all_primary_gates_pass": bool(cells_pass and all(bool(gates[k]["pass"]) for k in required)),
        "coverage": coverage,
        "error_stats": errors,
        "interval_stats": intervals,
        "gates": gates,
        "diagnostics": {
            "primary_unavailable_reason_counts": {str(k): int(v) for k, v in reason_counts.items()},
            "rescued_reason_counts": {str(k): int(v) for k, v in rescued_reason_counts.items()},
            "rescue_tail_rows": int((evaluated["p14_rescue_tail_event"].astype(bool) & rescued).sum()),
            "remaining_unavailable_truth_visible_rows": int((evaluated["truth_visible"].astype(bool) & (~evaluated["p14_available"].astype(bool))).sum()),
            "source_counts": {str(k): int(v) for k, v in evaluated.loc[available, "p14_source"].value_counts().to_dict().items()},
        },
    }


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _manifest(out: Path, files: list[str], stage: str, git_sha: str) -> None:
    payload = {
        "schema": "aegisland.phase11.p14.manifest.v1",
        "stage": stage,
        "git_sha": git_sha,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "files": {name: {"sha256": _hash_file(out / name), "bytes": (out / name).stat().st_size} for name in files},
    }
    (out / "manifest.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def partition(out: Path, git_sha: str) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    fit_raw = _raw("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS)
    velocity_caps = p9._fit_velocity_caps(fit_raw)
    innovation_scales = p9._fit_innovation_scales(fit_raw, velocity_caps)
    natural = _raw("partition", PARTITION_SEED, PARTITION_FAMILIES, PARTITION_CALIBRATION_DOMAINS)
    raw = apply_intervention(natural, "partition", PARTITION_STRATA)
    evaluated = add_p14_rescue(raw, PARTITION_SEED, velocity_caps, innovation_scales)
    cutpoints = _fit_severity_cutpoints(evaluated)
    freeze = {
        "schema": "aegisland.phase11.p14.partition-freeze.v1",
        "git_sha": git_sha,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "fit_seed": FIT_SEED,
        "partition_seed": PARTITION_SEED,
        "calibration_seed_unseen_at_partition_freeze": CALIBRATION_SEED,
        "transfer_seed_unseen_at_partition_freeze": TRANSFER_SEED,
        "validation_seed_unseen_at_partition_freeze": VALIDATION_SEED,
        "velocity_caps": velocity_caps,
        "innovation_scales": innovation_scales,
        "severity_cutpoints": cutpoints,
        "rescue_model": {"availability": RESCUE_AVAILABILITY, "lateral_sigma_m": RESCUE_LATERAL_SIGMA_M, "altitude_sigma_m": RESCUE_ALTITUDE_SIGMA_M, "tail_probability": RESCUE_TAIL_PROBABILITY, "tail_scale": RESCUE_TAIL_SCALE, "stream_tag": RESCUE_STREAM_TAG},
    }
    fit_raw.to_csv(out / "fit_frames.csv", index=False)
    evaluated.to_csv(out / "partition_frames.csv", index=False)
    (out / "partition_freeze.json").write_text(json.dumps(freeze, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(out, ["fit_frames.csv", "partition_frames.csv", "partition_freeze.json"], "partition", git_sha)
    return freeze


def _load_partition(path: Path) -> dict[str, object]:
    p = json.loads(path.read_text(encoding="utf-8"))
    if p.get("schema") != "aegisland.phase11.p14.partition-freeze.v1":
        raise SystemExit("invalid P14 partition freeze")
    if p.get("calibration_seed_unseen_at_partition_freeze") != CALIBRATION_SEED or p.get("transfer_seed_unseen_at_partition_freeze") != TRANSFER_SEED or p.get("validation_seed_unseen_at_partition_freeze") != VALIDATION_SEED:
        raise SystemExit("P14 partition evidence boundary mismatch")
    return p


def freeze(out: Path, partition_path: Path, git_sha: str) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    frozen = _load_partition(partition_path)
    natural = _raw("calibration", CALIBRATION_SEED, CALIBRATION_FAMILIES, PARTITION_CALIBRATION_DOMAINS)
    raw = apply_intervention(natural, "calibration", CALIBRATION_STRATA)
    calibration = add_p14_rescue(raw, CALIBRATION_SEED, frozen["velocity_caps"], frozen["innovation_scales"])
    radii, counts = _fit_direct_radii(calibration, frozen["severity_cutpoints"])
    candidate = {
        "schema": "aegisland.phase11.p14.candidate-freeze.v1",
        "git_sha": git_sha,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "fit_seed": FIT_SEED,
        "partition_seed": PARTITION_SEED,
        "calibration_seed": CALIBRATION_SEED,
        "transfer_seed_unseen_at_freeze": TRANSFER_SEED,
        "validation_seed_unseen_at_freeze": VALIDATION_SEED,
        "velocity_caps": frozen["velocity_caps"],
        "innovation_scales": frozen["innovation_scales"],
        "severity_cutpoints": frozen["severity_cutpoints"],
        "rescue_model": frozen["rescue_model"],
        "primary_constants": {"max_continuity_gap": p9.MAX_CONTINUITY_GAP, "damping": p9.DAMPING, "soft_scale_multiplier": p9.SOFT_SCALE_MULTIPLIER, "blend_previous_slope": p9.BLEND_PREVIOUS_SLOPE, "blend_soft_updated_slope": p9.BLEND_SOFT_UPDATED_SLOPE},
        "groups": list(GROUPS),
        "calibration_cell_rows": counts,
        "direct_mondrian_radii": radii,
    }
    calibration.to_csv(out / "calibration_frames.csv", index=False)
    (out / "candidate_freeze.json").write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "partition_freeze.json").write_text(json.dumps(frozen, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(out, ["calibration_frames.csv", "candidate_freeze.json", "partition_freeze.json"], "freeze", git_sha)
    return candidate


def _load_candidate(path: Path) -> dict[str, object]:
    c = json.loads(path.read_text(encoding="utf-8"))
    if c.get("schema") != "aegisland.phase11.p14.candidate-freeze.v1":
        raise SystemExit("invalid P14 candidate")
    if c.get("transfer_seed_unseen_at_freeze") != TRANSFER_SEED or c.get("validation_seed_unseen_at_freeze") != VALIDATION_SEED:
        raise SystemExit("P14 candidate evidence boundary mismatch")
    model = c.get("rescue_model", {})
    expected = {"availability": RESCUE_AVAILABILITY, "lateral_sigma_m": RESCUE_LATERAL_SIGMA_M, "altitude_sigma_m": RESCUE_ALTITUDE_SIGMA_M, "tail_probability": RESCUE_TAIL_PROBABILITY, "tail_scale": RESCUE_TAIL_SCALE, "stream_tag": RESCUE_STREAM_TAG}
    if model != expected:
        raise SystemExit("P14 rescue model mismatch")
    return c


def _evaluate(stage: str, seed: int, families: tuple[int, ...], domains: tuple[str, ...], strata: dict[str, tuple[int, ...]], candidate: dict[str, object]):
    natural_raw = _raw(stage, seed, families, domains)
    event_raw = apply_intervention(natural_raw, stage, strata)
    event = add_p14_rescue(event_raw, seed, candidate["velocity_caps"], candidate["innovation_scales"])
    natural = add_p14_rescue(natural_raw, seed, candidate["velocity_caps"], candidate["innovation_scales"])
    event_result = summarize(event, candidate, f"phase11_p14_{stage}_event_stratified", seed, True)
    natural_result = summarize(natural, candidate, f"phase11_p14_{stage}_natural_diagnostic", seed, False)
    natural_result["diagnostic_only"] = True
    return event, natural, event_result, natural_result


def transfer(out: Path, candidate_path: Path, git_sha: str) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    c = _load_candidate(candidate_path)
    event, natural, result, natural_result = _evaluate("transfer", TRANSFER_SEED, TRANSFER_FAMILIES, TRANSFER_DOMAINS, TRANSFER_STRATA, c)
    event.to_csv(out / "transfer_event_frames.csv", index=False)
    natural.to_csv(out / "transfer_natural_frames.csv", index=False)
    (out / "transfer_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "transfer_natural_diagnostic.json").write_text(json.dumps(natural_result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "candidate_freeze.json").write_text(json.dumps(c, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(out, ["transfer_event_frames.csv", "transfer_natural_frames.csv", "transfer_result.json", "transfer_natural_diagnostic.json", "candidate_freeze.json"], "transfer", git_sha)
    return result


def validate(out: Path, candidate_path: Path, git_sha: str) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    c = _load_candidate(candidate_path)
    event, natural, result, natural_result = _evaluate("validation", VALIDATION_SEED, VALIDATION_FAMILIES, VALIDATION_DOMAINS, VALIDATION_STRATA, c)
    event.to_csv(out / "validation_event_frames.csv", index=False)
    natural.to_csv(out / "validation_natural_frames.csv", index=False)
    (out / "validation_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "validation_natural_diagnostic.json").write_text(json.dumps(natural_result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "candidate_freeze.json").write_text(json.dumps(c, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(out, ["validation_event_frames.csv", "validation_natural_frames.csv", "validation_result.json", "validation_natural_diagnostic.json", "candidate_freeze.json"], "validation", git_sha)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 11 P14 bounded primary continuity plus independent rescue")
    parser.add_argument("--stage", choices=("partition", "freeze", "transfer", "validation"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--partition", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--git-sha", default="unknown")
    return parser.parse_args()


def main() -> None:
    a = parse_args()
    if a.stage == "partition":
        r = partition(a.out, a.git_sha)
        print("P14_PARTITION_FREEZE=" + json.dumps({"severity_cutpoints": r["severity_cutpoints"], "velocity_caps": r["velocity_caps"], "innovation_scales": r["innovation_scales"]}, sort_keys=True))
    elif a.stage == "freeze":
        if a.partition is None:
            raise SystemExit("--partition required")
        c = freeze(a.out, a.partition, a.git_sha)
        print("P14_CANDIDATE_FREEZE=" + json.dumps({"calibration_cell_rows": c["calibration_cell_rows"], "severity_cutpoints": c["severity_cutpoints"]}, sort_keys=True))
    elif a.stage == "transfer":
        if a.candidate is None:
            raise SystemExit("--candidate required")
        r = transfer(a.out, a.candidate, a.git_sha)
        print("P14_TRANSFER_GATES=" + json.dumps({"all_primary_gates_pass": r["all_primary_gates_pass"], "gates": r["gates"]}, sort_keys=True))
    else:
        if a.candidate is None:
            raise SystemExit("--candidate required")
        r = validate(a.out, a.candidate, a.git_sha)
        print("P14_VALIDATION_GATES=" + json.dumps({"all_primary_gates_pass": r["all_primary_gates_pass"], "gates": r["gates"]}, sort_keys=True))


if __name__ == "__main__":
    main()
