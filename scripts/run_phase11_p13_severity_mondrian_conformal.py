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

FIT_SEED = 638638
PARTITION_SEED = 649649
CALIBRATION_SEED = 660660
TRANSFER_SEED = 671671
VALIDATION_SEED = 682682
FRAMES_PER_SEQUENCE = p9.FRAMES_PER_SEQUENCE
TARGETS = p9.TARGETS

FIT_FAMILIES = tuple(range(600, 606))
PARTITION_STRATA = {3: tuple(range(606, 612)), 5: tuple(range(612, 618)), 7: tuple(range(618, 624))}
CALIBRATION_STRATA = {3: tuple(range(624, 636)), 5: tuple(range(636, 648)), 7: tuple(range(648, 660))}
TRANSFER_STRATA = {3: tuple(range(660, 666)), 5: tuple(range(666, 672)), 7: tuple(range(672, 678))}
VALIDATION_STRATA = {3: tuple(range(678, 684)), 5: tuple(range(684, 690)), 7: tuple(range(690, 696))}

PARTITION_FAMILIES = tuple(f for g in (3, 5, 7) for f in PARTITION_STRATA[g])
CALIBRATION_FAMILIES = tuple(f for g in (3, 5, 7) for f in CALIBRATION_STRATA[g])
TRANSFER_FAMILIES = tuple(f for g in (3, 5, 7) for f in TRANSFER_STRATA[g])
VALIDATION_FAMILIES = tuple(f for g in (3, 5, 7) for f in VALIDATION_STRATA[g])

FIT_DOMAINS = p9.FIT_DOMAINS
PARTITION_CALIBRATION_DOMAINS = (
    "edge+temporal_dropout",
    "small_scale+dim+temporal_dropout",
    "oblique+low_contrast+temporal_dropout",
    "dim+blur_noise+temporal_dropout",
    "edge+oblique+blur_noise+temporal_dropout",
    "small_scale+dim+low_contrast+temporal_dropout",
    "edge+small_scale+oblique+dim+temporal_dropout",
    "edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout",
)
TRANSFER_DOMAINS = (
    "edge+low_contrast+temporal_dropout",
    "small_scale+oblique+temporal_dropout",
    "dim+low_contrast+temporal_dropout",
    "blur_noise+low_contrast+temporal_dropout",
    "edge+small_scale+blur_noise+temporal_dropout",
    "oblique+dim+blur_noise+temporal_dropout",
    "edge+oblique+dim+low_contrast+temporal_dropout",
    "small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout",
)
VALIDATION_DOMAINS = (
    "edge+dim+temporal_dropout",
    "small_scale+blur_noise+temporal_dropout",
    "oblique+dim+temporal_dropout",
    "edge+small_scale+low_contrast+temporal_dropout",
    "small_scale+oblique+blur_noise+temporal_dropout",
    "edge+dim+blur_noise+low_contrast+temporal_dropout",
    "edge+small_scale+oblique+low_contrast+temporal_dropout",
    "edge+small_scale+dim+blur_noise+low_contrast+temporal_dropout",
)

INTERVENTION_STARTS = {
    "partition": (10, 40),
    "calibration": (12, 42),
    "transfer": (13, 43),
    "validation": (14, 44),
}

SEVERITY_LABELS = ("low", "mid", "high")
CALIBRATION_CELL_MINIMUMS = {
    p9.GROUP_BASE: 500,
    p9.GROUP_H3: 100,
    p9.GROUP_H45: 75,
    p9.GROUP_H67: 50,
}
TRANSFER_CELL_MINIMUMS = {
    p9.GROUP_BASE: 200,
    p9.GROUP_H3: 40,
    p9.GROUP_H45: 30,
    p9.GROUP_H67: 15,
}


def _raw(name: str, seed: int, families: tuple[int, ...], domains: tuple[str, ...]) -> pd.DataFrame:
    return p9.p1.generate_split(name, seed, families, domains, frames=FRAMES_PER_SEQUENCE)


def _family_gap_map(strata: dict[int, tuple[int, ...]]) -> dict[int, int]:
    result: dict[int, int] = {}
    for gap, families in strata.items():
        for family in families:
            if family in result:
                raise RuntimeError(f"duplicate P13 family {family}")
            result[int(family)] = int(gap)
    return result


def forced_dropout_mask(df: pd.DataFrame, strata: dict[int, tuple[int, ...]], starts: tuple[int, int]) -> pd.Series:
    family_to_gap = _family_gap_map(strata)
    gaps = df["family"].map(family_to_gap)
    if gaps.isna().any():
        raise RuntimeError("P13 family missing from preregistered gap stratum")
    frame = df["frame_index"].astype(int)
    gaps = gaps.astype(int)
    mask = pd.Series(False, index=df.index)
    for start in starts:
        mask |= (frame >= start) & (frame < start + gaps)
    return mask


def apply_intervention(raw: pd.DataFrame, stage: str, strata: dict[int, tuple[int, ...]]) -> pd.DataFrame:
    out = raw.copy()
    family_to_gap = _family_gap_map(strata)
    out["p13_intervention_stage"] = stage
    out["p13_intervention_gap_length"] = out["family"].map(family_to_gap).astype(int)
    forced = forced_dropout_mask(out, strata, INTERVENTION_STARTS[stage])
    out["p13_forced_dropout"] = forced.astype(bool)
    out.loc[forced, "candidate_available"] = False
    out.loc[forced, "candidate_source"] = None
    for col in ("estimate_lateral_x_m", "estimate_altitude_m", "lateral_abs_error_m", "altitude_abs_error_m"):
        out.loc[forced, col] = np.nan
    return out


def _base_group(df: pd.DataFrame) -> pd.Series:
    return p9._group_series(df)


def _fit_severity_cutpoints(partition: pd.DataFrame) -> dict[str, dict[str, float]]:
    available = p9._available(partition)
    groups = _base_group(partition)
    result: dict[str, dict[str, float]] = {}
    for group in p9.GROUPS:
        values = partition.loc[available & (groups == group), "severity"].dropna().to_numpy(float)
        if values.size < 30:
            raise RuntimeError(f"P13 partition group {group} has only {values.size} severity rows")
        lower, upper = np.quantile(values, [1.0 / 3.0, 2.0 / 3.0])
        if not np.isfinite(lower) or not np.isfinite(upper) or upper <= lower:
            raise RuntimeError(f"invalid P13 severity cutpoints for {group}")
        result[group] = {"lower": float(lower), "upper": float(upper), "rows": int(values.size)}
    return result


def _severity_regime(df: pd.DataFrame, cutpoints: dict[str, dict[str, float]]) -> pd.Series:
    groups = _base_group(df)
    severity = df["severity"].to_numpy(float)
    labels: list[str] = []
    for i, group in enumerate(groups.astype(str)):
        cp = cutpoints[group]
        if severity[i] <= cp["lower"]:
            labels.append("low")
        elif severity[i] <= cp["upper"]:
            labels.append("mid")
        else:
            labels.append("high")
    return pd.Series(labels, index=df.index, dtype="object")


def _cell_series(df: pd.DataFrame, cutpoints: dict[str, dict[str, float]]) -> pd.Series:
    groups = _base_group(df).astype(str)
    severity = _severity_regime(df, cutpoints).astype(str)
    return groups + "__" + severity


def _cell_counts(df: pd.DataFrame, cutpoints: dict[str, dict[str, float]]) -> dict[str, int]:
    d = df[p9._available(df)].copy()
    cells = _cell_series(d, cutpoints)
    return {f"{group}__{sev}": int((cells == f"{group}__{sev}").sum()) for group in p9.GROUPS for sev in SEVERITY_LABELS}


def _assert_cell_minimums(counts: dict[str, int], minimums: dict[str, int], label: str) -> None:
    failed: dict[str, dict[str, int]] = {}
    for group in p9.GROUPS:
        for sev in SEVERITY_LABELS:
            cell = f"{group}__{sev}"
            minimum = int(minimums[group])
            if counts.get(cell, 0) < minimum:
                failed[cell] = {"rows": int(counts.get(cell, 0)), "minimum": minimum}
    if failed:
        raise RuntimeError(f"P13 {label} cell minimums failed: {json.dumps(failed, sort_keys=True)}")


def _fit_direct_radii(calibration: pd.DataFrame, cutpoints: dict[str, dict[str, float]]):
    d = calibration[p9._available(calibration)].copy()
    d["p13_cell"] = _cell_series(d, cutpoints)
    counts = _cell_counts(calibration, cutpoints)
    _assert_cell_minimums(counts, CALIBRATION_CELL_MINIMUMS, "calibration")
    radii: dict[str, dict[str, dict[str, float]]] = {}
    for group in p9.GROUPS:
        for sev in SEVERITY_LABELS:
            cell = f"{group}__{sev}"
            gd = d[d["p13_cell"] == cell]
            radii[cell] = {}
            for axis in ("lateral", "altitude"):
                errors = gd[f"p9_{axis}_abs_error_m"].to_numpy(float)
                raw = [p9._finite_conformal(errors, q) for q in TARGETS]
                nested = np.maximum.accumulate(np.asarray(raw, dtype=float))
                radii[cell][axis] = {f"{q:.2f}": float(nested[i]) for i, q in enumerate(TARGETS)}
    return radii, counts


def _halfwidths(df: pd.DataFrame, candidate: dict[str, object], axis: str, q: float) -> np.ndarray:
    cells = _cell_series(df, candidate["severity_cutpoints"]).astype(str)
    table = candidate["direct_mondrian_radii"]
    return np.asarray([float(table[cell][axis][f"{q:.2f}"]) for cell in cells], dtype=float)


def _coverage(df: pd.DataFrame, candidate: dict[str, object]) -> dict[str, dict[str, float]]:
    d = df[p9._available(df)].copy()
    result: dict[str, dict[str, float]] = {}
    for axis in ("lateral", "altitude"):
        err = d[f"p9_{axis}_abs_error_m"].to_numpy(float)
        result[axis] = {}
        for q in TARGETS:
            hw = _halfwidths(d, candidate, axis, q)
            result[axis][f"{q:.2f}"] = float(np.mean(err <= hw)) if err.size else float("nan")
    return result


def _subset_stats(df: pd.DataFrame, candidate: dict[str, object], mask: pd.Series) -> dict[str, object]:
    d = df[p9._available(df) & mask].copy()
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


def _error_interval_stats(df: pd.DataFrame, candidate: dict[str, object]):
    mask = p9._available(df); d = df[mask].copy()
    errors: dict[str, float] = {"available_fraction": float(mask.mean()), "available_rows": int(mask.sum()), "total_rows": int(len(df))}
    intervals: dict[str, dict[str, float]] = {}
    for axis in ("lateral", "altitude"):
        err = d[f"p9_{axis}_abs_error_m"].dropna().to_numpy(float)
        hw = _halfwidths(d, candidate, axis, 0.95)
        errors[f"{axis}_mae"] = float(np.mean(err)) if err.size else float("nan")
        errors[f"{axis}_p95"] = float(np.percentile(err, 95)) if err.size else float("nan")
        intervals[axis] = {"median_halfwidth_95": float(np.median(hw)) if hw.size else float("nan"), "p95_halfwidth_95": float(np.percentile(hw, 95)) if hw.size else float("nan")}
    return errors, intervals


def _reference(candidate: dict[str, object]) -> pd.DataFrame:
    raw = _raw("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS)
    return p9.add_p9_continuity(raw, candidate["velocity_caps"], candidate["innovation_scales"])


def summarize(evaluated: pd.DataFrame, candidate: dict[str, object], role: str, seed: int, require_cells: bool) -> dict[str, object]:
    available = p9._available(evaluated)
    groups = _base_group(evaluated)
    regimes = _severity_regime(evaluated, candidate["severity_cutpoints"])
    counts = _cell_counts(evaluated, candidate["severity_cutpoints"])
    cells_pass = True
    if require_cells:
        try:
            _assert_cell_minimums(counts, TRANSFER_CELL_MINIMUMS, "evaluation")
        except RuntimeError:
            cells_pass = False
    coverage = _coverage(evaluated, candidate)
    errors, intervals = _error_interval_stats(evaluated, candidate)
    continuity = _subset_stats(evaluated, candidate, groups.isin({p9.GROUP_H3, p9.GROUP_H45, p9.GROUP_H67}))
    base = _subset_stats(evaluated, candidate, groups == p9.GROUP_BASE)
    high = _subset_stats(evaluated, candidate, regimes == "high")

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
    h5 = {"rows": continuity["rows"], "lateral_95_coverage": continuity["coverage_95"]["lateral"], "altitude_95_coverage": continuity["coverage_95"]["altitude"], "lateral_p95_halfwidth_over_p95_error": continuity["p95_halfwidth_over_p95_error"]["lateral"], "altitude_p95_halfwidth_over_p95_error": continuity["p95_halfwidth_over_p95_error"]["altitude"]}
    h5["pass"] = bool(h5["rows"] > 0 and 0.88 <= h5["lateral_95_coverage"] <= 0.99 and 0.88 <= h5["altitude_95_coverage"] <= 0.99 and h5["lateral_p95_halfwidth_over_p95_error"] <= 2.75 and h5["altitude_p95_halfwidth_over_p95_error"] <= 2.75)
    h6 = {"rows": base["rows"], "lateral_95_coverage": base["coverage_95"]["lateral"], "altitude_95_coverage": base["coverage_95"]["altitude"], "lateral_p95_halfwidth_over_p95_error": base["p95_halfwidth_over_p95_error"]["lateral"], "altitude_p95_halfwidth_over_p95_error": base["p95_halfwidth_over_p95_error"]["altitude"]}
    h6["pass"] = bool(h6["rows"] > 0 and 0.90 <= h6["lateral_95_coverage"] <= 0.98 and 0.90 <= h6["altitude_95_coverage"] <= 0.98 and h6["lateral_p95_halfwidth_over_p95_error"] <= 2.25 and h6["altitude_p95_halfwidth_over_p95_error"] <= 2.25)
    reference = _reference(candidate)
    h7 = {"trajectory_level_auroc": p9._shift_auc(reference, evaluated)}
    h7["pass"] = bool(h7["trajectory_level_auroc"] >= 0.85)
    h8 = {"rows": high["rows"], "lateral_95_coverage": high["coverage_95"]["lateral"], "altitude_95_coverage": high["coverage_95"]["altitude"], "lateral_p95_halfwidth_over_p95_error": high["p95_halfwidth_over_p95_error"]["lateral"], "altitude_p95_halfwidth_over_p95_error": high["p95_halfwidth_over_p95_error"]["altitude"]}
    h8["pass"] = bool(h8["rows"] > 0 and 0.88 <= h8["lateral_95_coverage"] <= 0.99 and 0.88 <= h8["altitude_95_coverage"] <= 0.99 and h8["lateral_p95_halfwidth_over_p95_error"] <= 2.75 and h8["altitude_p95_halfwidth_over_p95_error"] <= 2.75)
    gates = {"cell_minimums": {"counts": counts, "required_per_base_group": TRANSFER_CELL_MINIMUMS, "pass": bool(cells_pass)}, "h1_useful_availability": h1, "h2_overall_coverage": h2, "h3_calibration_curve": h3, "h4_overall_interval_efficiency": h4, "h5_continuity_specific_honesty": h5, "h6_base_output_honesty": h6, "h7_shift_discrimination": h7, "h8_high_severity_honesty": h8}
    return {"schema": "aegisland.phase11.p13.result.v1", "evidence_role": role, "evaluated_seed_seen_after_run": seed, "simulation_only": True, "safety_acceptance": False, "controller_tuning_allowed": False, "all_primary_gates_pass": bool(cells_pass and all(gates[k]["pass"] for k in ("h1_useful_availability", "h2_overall_coverage", "h3_calibration_curve", "h4_overall_interval_efficiency", "h5_continuity_specific_honesty", "h6_base_output_honesty", "h8_high_severity_honesty"))), "coverage": coverage, "error_stats": errors, "interval_stats": intervals, "gates": gates}


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _manifest(out: Path, files: list[str], stage: str, git_sha: str) -> None:
    payload = {"schema": "aegisland.phase11.p13.manifest.v1", "stage": stage, "git_sha": git_sha, "simulation_only": True, "safety_acceptance": False, "controller_tuning_allowed": False, "files": {name: {"sha256": _hash_file(out / name), "bytes": (out / name).stat().st_size} for name in files}}
    (out / "manifest.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def partition(out: Path, git_sha: str) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    fit_raw = _raw("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS)
    velocity_caps = p9._fit_velocity_caps(fit_raw)
    innovation_scales = p9._fit_innovation_scales(fit_raw, velocity_caps)
    partition_natural = _raw("partition", PARTITION_SEED, PARTITION_FAMILIES, PARTITION_CALIBRATION_DOMAINS)
    partition_raw = apply_intervention(partition_natural, "partition", PARTITION_STRATA)
    partition_eval = p9.add_p9_continuity(partition_raw, velocity_caps, innovation_scales)
    cutpoints = _fit_severity_cutpoints(partition_eval)
    freeze = {"schema": "aegisland.phase11.p13.partition-freeze.v1", "git_sha": git_sha, "simulation_only": True, "safety_acceptance": False, "controller_tuning_allowed": False, "fit_seed": FIT_SEED, "partition_seed": PARTITION_SEED, "calibration_seed_unseen_at_partition_freeze": CALIBRATION_SEED, "transfer_seed_unseen_at_partition_freeze": TRANSFER_SEED, "validation_seed_unseen_at_partition_freeze": VALIDATION_SEED, "velocity_caps": velocity_caps, "innovation_scales": innovation_scales, "severity_cutpoints": cutpoints}
    fit_raw.to_csv(out / "fit_frames.csv", index=False)
    partition_eval.to_csv(out / "partition_frames.csv", index=False)
    (out / "partition_freeze.json").write_text(json.dumps(freeze, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(out, ["fit_frames.csv", "partition_frames.csv", "partition_freeze.json"], "partition", git_sha)
    return freeze


def _load_partition(path: Path) -> dict[str, object]:
    p = json.loads(path.read_text(encoding="utf-8"))
    if p.get("schema") != "aegisland.phase11.p13.partition-freeze.v1":
        raise SystemExit("invalid P13 partition freeze")
    return p


def freeze(out: Path, partition_path: Path, git_sha: str) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    frozen = _load_partition(partition_path)
    natural = _raw("calibration", CALIBRATION_SEED, CALIBRATION_FAMILIES, PARTITION_CALIBRATION_DOMAINS)
    raw = apply_intervention(natural, "calibration", CALIBRATION_STRATA)
    calibration = p9.add_p9_continuity(raw, frozen["velocity_caps"], frozen["innovation_scales"])
    radii, counts = _fit_direct_radii(calibration, frozen["severity_cutpoints"])
    candidate = {"schema": "aegisland.phase11.p13.candidate-freeze.v1", "git_sha": git_sha, "simulation_only": True, "safety_acceptance": False, "controller_tuning_allowed": False, "fit_seed": FIT_SEED, "partition_seed": PARTITION_SEED, "calibration_seed": CALIBRATION_SEED, "transfer_seed_unseen_at_freeze": TRANSFER_SEED, "validation_seed_unseen_at_freeze": VALIDATION_SEED, "velocity_caps": frozen["velocity_caps"], "innovation_scales": frozen["innovation_scales"], "severity_cutpoints": frozen["severity_cutpoints"], "calibration_cell_rows": counts, "direct_mondrian_radii": radii}
    calibration.to_csv(out / "calibration_frames.csv", index=False)
    (out / "candidate_freeze.json").write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "partition_freeze.json").write_text(json.dumps(frozen, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(out, ["calibration_frames.csv", "candidate_freeze.json", "partition_freeze.json"], "freeze", git_sha)
    return candidate


def _load_candidate(path: Path) -> dict[str, object]:
    c = json.loads(path.read_text(encoding="utf-8"))
    if c.get("schema") != "aegisland.phase11.p13.candidate-freeze.v1":
        raise SystemExit("invalid P13 candidate")
    return c


def _evaluate(stage: str, seed: int, families: tuple[int, ...], domains: tuple[str, ...], strata: dict[int, tuple[int, ...]], candidate: dict[str, object]):
    natural_raw = _raw(stage, seed, families, domains)
    event_raw = apply_intervention(natural_raw, stage, strata)
    event = p9.add_p9_continuity(event_raw, candidate["velocity_caps"], candidate["innovation_scales"])
    natural = p9.add_p9_continuity(natural_raw, candidate["velocity_caps"], candidate["innovation_scales"])
    event_result = summarize(event, candidate, f"phase11_p13_{stage}_event_stratified", seed, True)
    natural_result = summarize(natural, candidate, f"phase11_p13_{stage}_natural_diagnostic", seed, False)
    natural_result["diagnostic_only"] = True
    return event, natural, event_result, natural_result


def transfer(out: Path, candidate_path: Path, git_sha: str):
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


def validate(out: Path, candidate_path: Path, git_sha: str):
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
    parser = argparse.ArgumentParser(description="Run Phase 11 P13 severity-conditioned Mondrian direct conformal")
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
        print("P13_PARTITION_FREEZE=" + json.dumps({"severity_cutpoints": r["severity_cutpoints"], "velocity_caps": r["velocity_caps"], "innovation_scales": r["innovation_scales"]}, sort_keys=True))
    elif a.stage == "freeze":
        if a.partition is None:
            raise SystemExit("--partition required")
        c = freeze(a.out, a.partition, a.git_sha)
        print("P13_CANDIDATE_FREEZE=" + json.dumps({"calibration_cell_rows": c["calibration_cell_rows"], "severity_cutpoints": c["severity_cutpoints"]}, sort_keys=True))
    elif a.stage == "transfer":
        if a.candidate is None:
            raise SystemExit("--candidate required")
        r = transfer(a.out, a.candidate, a.git_sha)
        print("P13_TRANSFER_GATES=" + json.dumps({"all_primary_gates_pass": r["all_primary_gates_pass"], "gates": r["gates"]}, sort_keys=True))
    else:
        if a.candidate is None:
            raise SystemExit("--candidate required")
        r = validate(a.out, a.candidate, a.git_sha)
        print("P13_VALIDATION_GATES=" + json.dumps({"all_primary_gates_pass": r["all_primary_gates_pass"], "gates": r["gates"]}, sort_keys=True))


if __name__ == "__main__":
    main()
