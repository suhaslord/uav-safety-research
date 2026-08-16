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

FIT_SEED = 583583
CALIBRATION_SEED = 594594
TRANSFER_SEED = 605605
VALIDATION_SEED = 616616
FRAMES_PER_SEQUENCE = p9.FRAMES_PER_SEQUENCE

FIT_FAMILIES = tuple(range(500, 506))
CALIBRATION_STRATA = {
    3: tuple(range(506, 514)),
    5: tuple(range(514, 522)),
    7: tuple(range(522, 530)),
}
TRANSFER_STRATA = {
    3: tuple(range(530, 534)),
    5: tuple(range(534, 538)),
    7: tuple(range(538, 542)),
}
VALIDATION_STRATA = {
    3: tuple(range(542, 546)),
    5: tuple(range(546, 550)),
    7: tuple(range(550, 554)),
}

CALIBRATION_FAMILIES = tuple(f for gap in (3, 5, 7) for f in CALIBRATION_STRATA[gap])
TRANSFER_FAMILIES = tuple(f for gap in (3, 5, 7) for f in TRANSFER_STRATA[gap])
VALIDATION_FAMILIES = tuple(f for gap in (3, 5, 7) for f in VALIDATION_STRATA[gap])

FIT_DOMAINS = p9.FIT_DOMAINS
CALIBRATION_DOMAINS = p9.CALIBRATION_DOMAINS
TRANSFER_DOMAINS = p9.TRANSFER_DOMAINS
VALIDATION_DOMAINS = p9.VALIDATION_DOMAINS

INTERVENTION_STARTS = {
    "calibration": (12, 42),
    "transfer": (13, 43),
    "validation": (14, 44),
}

CALIBRATION_POWER_MINIMUMS = {
    p9.GROUP_BASE: 2000,
    p9.GROUP_H3: 240,
    p9.GROUP_H45: 120,
    p9.GROUP_H67: 60,
}
TRANSFER_POWER_MINIMUMS = {
    p9.GROUP_BASE: 1200,
    p9.GROUP_H3: 150,
    p9.GROUP_H45: 75,
    p9.GROUP_H67: 30,
}


def _raw(name: str, seed: int, families: tuple[int, ...], domains: tuple[str, ...]) -> pd.DataFrame:
    return p9.p1.generate_split(name, seed, families, domains, frames=FRAMES_PER_SEQUENCE)


def _family_gap_map(strata: dict[int, tuple[int, ...]]) -> dict[int, int]:
    result: dict[int, int] = {}
    for gap, families in strata.items():
        for family in families:
            if family in result:
                raise RuntimeError(f"family {family} appears in multiple P12 gap strata")
            result[family] = int(gap)
    return result


def forced_dropout_mask(
    df: pd.DataFrame,
    strata: dict[int, tuple[int, ...]],
    starts: tuple[int, int],
) -> pd.Series:
    family_to_gap = _family_gap_map(strata)
    gaps = df["family"].map(family_to_gap)
    if gaps.isna().any():
        missing = sorted(set(df.loc[gaps.isna(), "family"].astype(int)))
        raise RuntimeError(f"P12 family missing from gap stratum: {missing}")
    frame = df["frame_index"].astype(int)
    gap_values = gaps.astype(int)
    mask = pd.Series(False, index=df.index)
    for start in starts:
        mask |= (frame >= int(start)) & (frame < int(start) + gap_values)
    return mask


def apply_event_intervention(
    raw: pd.DataFrame,
    stage: str,
    strata: dict[int, tuple[int, ...]],
) -> pd.DataFrame:
    if stage not in INTERVENTION_STARTS:
        raise ValueError(f"unknown P12 intervention stage {stage}")
    out = raw.copy()
    family_to_gap = _family_gap_map(strata)
    out["p12_intervention_stage"] = stage
    out["p12_intervention_gap_length"] = out["family"].map(family_to_gap).astype(int)
    forced = forced_dropout_mask(out, strata, INTERVENTION_STARTS[stage])
    out["p12_forced_dropout"] = forced.astype(bool)

    out.loc[forced, "candidate_available"] = False
    out.loc[forced, "candidate_source"] = None
    for col in (
        "estimate_lateral_x_m",
        "estimate_altitude_m",
        "lateral_abs_error_m",
        "altitude_abs_error_m",
    ):
        out.loc[forced, col] = np.nan
    return out


def _group_counts(evaluated: pd.DataFrame) -> dict[str, int]:
    d = evaluated[p9._available(evaluated)].copy()
    groups = p9._group_series(d)
    return {group: int((groups == group).sum()) for group in p9.GROUPS}


def _assert_minimums(counts: dict[str, int], minimums: dict[str, int], label: str) -> None:
    failed = {
        group: {"rows": counts.get(group, 0), "minimum": minimum}
        for group, minimum in minimums.items()
        if counts.get(group, 0) < minimum
    }
    if failed:
        raise RuntimeError(f"P12 {label} power minimums failed: {json.dumps(failed, sort_keys=True)}")


def _power_margin(counts: dict[str, int], minimums: dict[str, int]) -> dict[str, dict[str, float | int]]:
    return {
        group: {
            "rows": int(counts[group]),
            "minimum": int(minimums[group]),
            "margin": int(counts[group] - minimums[group]),
            "ratio": float(counts[group] / minimums[group]),
        }
        for group in minimums
    }


def _build_candidate(fit_raw: pd.DataFrame, calibration_raw: pd.DataFrame, git_sha: str):
    velocity_caps = p9._fit_velocity_caps(fit_raw)
    innovation_scales = p9._fit_innovation_scales(fit_raw, velocity_caps)
    calibration = p9.add_p9_continuity(calibration_raw, velocity_caps, innovation_scales)
    radii, counts = p9._fit_direct_radii(calibration)
    _assert_minimums(counts, CALIBRATION_POWER_MINIMUMS, "calibration")
    candidate = {
        "schema": "aegisland.phase11.p12.candidate-freeze.v1",
        "git_sha": git_sha,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "estimator": "phase11_p9_soft_update_direct_conformal_unchanged",
        "study_design": "truth_independent_event_stratified_observation_outage",
        "fit_seed": FIT_SEED,
        "calibration_seed": CALIBRATION_SEED,
        "transfer_seed_unseen_at_freeze": TRANSFER_SEED,
        "validation_seed_unseen_at_freeze": VALIDATION_SEED,
        "fit_families": list(FIT_FAMILIES),
        "calibration_strata": {str(k): list(v) for k, v in CALIBRATION_STRATA.items()},
        "transfer_strata": {str(k): list(v) for k, v in TRANSFER_STRATA.items()},
        "validation_strata": {str(k): list(v) for k, v in VALIDATION_STRATA.items()},
        "intervention_starts": {k: list(v) for k, v in INTERVENTION_STARTS.items()},
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
        "groups": list(p9.GROUPS),
        "original_calibration_minimums": p9.CALIBRATION_MINIMUMS,
        "p12_calibration_power_minimums": CALIBRATION_POWER_MINIMUMS,
        "p12_transfer_power_minimums": TRANSFER_POWER_MINIMUMS,
        "calibration_group_rows": counts,
        "calibration_power_margin": _power_margin(counts, CALIBRATION_POWER_MINIMUMS),
        "direct_conformal_radii": radii,
    }
    return candidate, calibration


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _manifest(out: Path, files: list[str], stage: str, git_sha: str) -> None:
    payload = {
        "schema": "aegisland.phase11.p12.manifest.v1",
        "stage": stage,
        "git_sha": git_sha,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "files": {
            name: {"sha256": _hash_file(out / name), "bytes": (out / name).stat().st_size}
            for name in files
        },
    }
    (out / "manifest.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def freeze(out: Path, git_sha: str):
    out.mkdir(parents=True, exist_ok=True)
    fit_raw = _raw("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS)
    calibration_natural = _raw("calibration", CALIBRATION_SEED, CALIBRATION_FAMILIES, CALIBRATION_DOMAINS)
    calibration_raw = apply_event_intervention(calibration_natural, "calibration", CALIBRATION_STRATA)
    candidate, calibration = _build_candidate(fit_raw, calibration_raw, git_sha)
    fit_raw.to_csv(out / "fit_frames.csv", index=False)
    calibration.to_csv(out / "calibration_frames.csv", index=False)
    (out / "candidate_freeze.json").write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(out, ["fit_frames.csv", "calibration_frames.csv", "candidate_freeze.json"], "freeze", git_sha)
    return candidate


def _load_candidate(path: Path) -> dict[str, object]:
    candidate = json.loads(path.read_text(encoding="utf-8"))
    if candidate.get("schema") != "aegisland.phase11.p12.candidate-freeze.v1":
        raise SystemExit("invalid P12 candidate schema")
    if candidate.get("transfer_seed_unseen_at_freeze") != TRANSFER_SEED:
        raise SystemExit("P12 transfer seed mismatch")
    if candidate.get("validation_seed_unseen_at_freeze") != VALIDATION_SEED:
        raise SystemExit("P12 validation seed mismatch")
    return candidate


def _reference(candidate: dict[str, object]) -> pd.DataFrame:
    raw = _raw("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS)
    return p9.add_p9_continuity(raw, candidate["velocity_caps"], candidate["innovation_scales"])


def _evaluate_pair(
    raw_natural: pd.DataFrame,
    stage: str,
    strata: dict[int, tuple[int, ...]],
    candidate: dict[str, object],
    role_prefix: str,
    seed: int,
):
    stratified_raw = apply_event_intervention(raw_natural, stage, strata)
    stratified = p9.add_p9_continuity(stratified_raw, candidate["velocity_caps"], candidate["innovation_scales"])
    natural = p9.add_p9_continuity(raw_natural, candidate["velocity_caps"], candidate["innovation_scales"])
    reference = _reference(candidate)

    stratified_result = p9.summarize(
        stratified,
        reference,
        candidate,
        f"{role_prefix}_event_stratified",
        seed,
        True,
    )
    stratified_result["schema"] = "aegisland.phase11.p12.result.v1"
    counts = _group_counts(stratified)
    stratified_result["p12_event_power_counts"] = counts
    stratified_result["p12_event_power_margin"] = _power_margin(counts, TRANSFER_POWER_MINIMUMS)
    stratified_result["p12_event_power_margin_pass"] = all(
        counts[g] >= TRANSFER_POWER_MINIMUMS[g] for g in TRANSFER_POWER_MINIMUMS
    )

    natural_result = p9.summarize(
        natural,
        reference,
        candidate,
        f"{role_prefix}_natural_diagnostic",
        seed,
        False,
    )
    natural_result["schema"] = "aegisland.phase11.p12.natural-diagnostic.v1"
    natural_result["diagnostic_only"] = True
    return stratified, natural, stratified_result, natural_result


def transfer(out: Path, candidate_path: Path, git_sha: str):
    candidate = _load_candidate(candidate_path)
    out.mkdir(parents=True, exist_ok=True)
    raw = _raw("transfer", TRANSFER_SEED, TRANSFER_FAMILIES, TRANSFER_DOMAINS)
    stratified, natural, result, natural_result = _evaluate_pair(
        raw, "transfer", TRANSFER_STRATA, candidate, "phase11_p12_seen_transfer", TRANSFER_SEED
    )
    _assert_minimums(result["p12_event_power_counts"], TRANSFER_POWER_MINIMUMS, "seen-transfer")
    stratified.to_csv(out / "transfer_event_stratified_frames.csv", index=False)
    natural.to_csv(out / "transfer_natural_frames.csv", index=False)
    (out / "transfer_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "transfer_natural_diagnostic.json").write_text(json.dumps(natural_result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "candidate_freeze.json").write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(
        out,
        [
            "transfer_event_stratified_frames.csv",
            "transfer_natural_frames.csv",
            "transfer_result.json",
            "transfer_natural_diagnostic.json",
            "candidate_freeze.json",
        ],
        "transfer",
        git_sha,
    )
    return result


def validate(out: Path, candidate_path: Path, git_sha: str):
    candidate = _load_candidate(candidate_path)
    out.mkdir(parents=True, exist_ok=True)
    raw = _raw("validation", VALIDATION_SEED, VALIDATION_FAMILIES, VALIDATION_DOMAINS)
    stratified, natural, result, natural_result = _evaluate_pair(
        raw,
        "validation",
        VALIDATION_STRATA,
        candidate,
        "phase11_p12_frozen_candidate_validation",
        VALIDATION_SEED,
    )
    stratified.to_csv(out / "validation_event_stratified_frames.csv", index=False)
    natural.to_csv(out / "validation_natural_frames.csv", index=False)
    (out / "validation_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "validation_natural_diagnostic.json").write_text(json.dumps(natural_result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "candidate_freeze.json").write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(
        out,
        [
            "validation_event_stratified_frames.csv",
            "validation_natural_frames.csv",
            "validation_result.json",
            "validation_natural_diagnostic.json",
            "candidate_freeze.json",
        ],
        "validation",
        git_sha,
    )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 11 P12 event-stratified direct conformal study")
    parser.add_argument("--stage", choices=("freeze", "transfer", "validation"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--git-sha", default="unknown")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.stage == "freeze":
        candidate = freeze(args.out, args.git_sha)
        print("P12_CANDIDATE_FREEZE=" + json.dumps({
            "calibration_group_rows": candidate["calibration_group_rows"],
            "calibration_power_margin": candidate["calibration_power_margin"],
            "velocity_caps": candidate["velocity_caps"],
            "innovation_scales": candidate["innovation_scales"],
        }, sort_keys=True))
        return
    if args.candidate is None:
        raise SystemExit("--candidate required")
    if args.stage == "transfer":
        result = transfer(args.out, args.candidate, args.git_sha)
        print("P12_TRANSFER_GATES=" + json.dumps({
            "all_primary_gates_pass": result.get("all_primary_gates_pass"),
            "p12_event_power_margin_pass": result.get("p12_event_power_margin_pass"),
            "gates": result.get("gates"),
        }, sort_keys=True))
        return
    result = validate(args.out, args.candidate, args.git_sha)
    print("P12_VALIDATION_GATES=" + json.dumps({
        "all_primary_gates_pass": result.get("all_primary_gates_pass"),
        "p12_event_power_margin_pass": result.get("p12_event_power_margin_pass"),
        "gates": result.get("gates"),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
