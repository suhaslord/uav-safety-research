from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scripts import run_phase11_p14_independent_coarse_fallback as p14
except ModuleNotFoundError:
    import run_phase11_p14_independent_coarse_fallback as p14

p9 = p14.p9

FIT_SEED = 693693
BASE_CALIBRATION_SEED = 704704
TRANSFER_CALIBRATION_SEED = 715715
CHALLENGE_SEED = 726726
VALIDATION_SEED = 737737
FRAMES_PER_SEQUENCE = p14.FRAMES_PER_SEQUENCE

FIT_FAMILIES = tuple(range(650, 656))
BASE_CALIBRATION_FAMILIES = tuple(range(656, 704))
TRANSFER_CALIBRATION_FAMILIES = tuple(range(704, 736))
CHALLENGE_FAMILIES = tuple(range(736, 760))
VALIDATION_FAMILIES = tuple(range(760, 784))

FIT_DOMAINS = p14.FIT_DOMAINS
BASE_CALIBRATION_DOMAINS = p14.BASE_CALIBRATION_DOMAINS
TRANSFER_CALIBRATION_DOMAINS = p14.TRANSFER_CALIBRATION_DOMAINS
CHALLENGE_DOMAINS = p14.CHALLENGE_DOMAINS
VALIDATION_DOMAINS = p14.VALIDATION_DOMAINS

BASE_MINIMUMS = {
    p14.GROUP_BASE: 1500,
    p14.GROUP_H3: 150,
    p14.GROUP_H47: 100,
    p14.GROUP_AUX: 5000,
}
TRANSFER_MINIMUMS = {
    p14.GROUP_BASE: 1200,
    p14.GROUP_H3: 120,
    p14.GROUP_H47: 80,
    p14.GROUP_AUX: 3000,
}
CHALLENGE_MINIMUMS = p14.CHALLENGE_MINIMUMS.copy()


def _raw(name: str, seed: int, families: tuple[int, ...], domains: tuple[str, ...]) -> pd.DataFrame:
    return p9.p1.generate_split(name, seed, families, domains, frames=FRAMES_PER_SEQUENCE)


def _prepare(raw: pd.DataFrame, velocity_caps: dict[str, float], innovation_scales: dict[str, float]) -> pd.DataFrame:
    out = p14.add_p14_fallback(raw, velocity_caps, innovation_scales).copy()
    out["aux_lateral_abs_error_m"] = np.abs(out["aux_estimate_lateral_x_m"] - out["truth_lateral_x_m"])
    out["aux_altitude_abs_error_m"] = np.abs(out["aux_estimate_altitude_m"] - out["truth_altitude_m"])
    return out


def _source_rows(df: pd.DataFrame, group: str) -> pd.DataFrame:
    if group == p14.GROUP_AUX:
        return df[df["truth_visible"].astype(bool) & df["aux_available"].astype(bool)].copy()
    groups = p14._group_series(df)
    return df[p14._available(df) & (groups == group)].copy()


def _source_errors(df: pd.DataFrame, group: str, axis: str) -> np.ndarray:
    rows = _source_rows(df, group)
    if group == p14.GROUP_AUX:
        return rows[f"aux_{axis}_abs_error_m"].dropna().to_numpy(float)
    return rows[f"p14_{axis}_abs_error_m"].dropna().to_numpy(float)


def _fit_base_radii(calibration: pd.DataFrame) -> tuple[dict[str, object], dict[str, int]]:
    counts = {g: int(len(_source_rows(calibration, g))) for g in p14.GROUPS}
    for g, minimum in BASE_MINIMUMS.items():
        if counts[g] < minimum:
            raise RuntimeError(f"P15 base-calibration source {g} rows {counts[g]} < {minimum}")
    radii: dict[str, object] = {}
    for g in p14.GROUPS:
        radii[g] = {}
        for axis in ("lateral", "altitude"):
            err = _source_errors(calibration, g, axis)
            raw = [p9._finite_conformal(err, q) for q in p9.TARGETS]
            nested = np.maximum.accumulate(np.asarray(raw, dtype=float))
            radii[g][axis] = {f"{q:.2f}": float(nested[i]) for i, q in enumerate(p9.TARGETS)}
    return radii, counts


def _transfer_calibrate(transfer: pd.DataFrame, base_radii: dict[str, object]) -> tuple[dict[str, object], dict[str, object], dict[str, int]]:
    counts = {g: int(len(_source_rows(transfer, g))) for g in p14.GROUPS}
    for g, minimum in TRANSFER_MINIMUMS.items():
        if counts[g] < minimum:
            raise RuntimeError(f"P15 transfer-calibration source {g} rows {counts[g]} < {minimum}")
    multipliers: dict[str, object] = {}; final: dict[str, object] = {}
    for g in p14.GROUPS:
        multipliers[g] = {}; final[g] = {}
        for axis in ("lateral", "altitude"):
            err = _source_errors(transfer, g, axis)
            raw_final = []; multipliers[g][axis] = {}
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


def _build_candidate(fit_raw: pd.DataFrame, base_raw: pd.DataFrame, transfer_raw: pd.DataFrame, git_sha: str):
    velocity_caps = p9._fit_velocity_caps(fit_raw)
    innovation_scales = p9._fit_innovation_scales(fit_raw, velocity_caps)
    base = _prepare(base_raw, velocity_caps, innovation_scales)
    base_radii, base_counts = _fit_base_radii(base)
    transfer = _prepare(transfer_raw, velocity_caps, innovation_scales)
    multipliers, final_radii, transfer_counts = _transfer_calibrate(transfer, base_radii)
    candidate = {
        "schema": "aegisland.phase11.p15.candidate-freeze.v1",
        "git_sha": git_sha,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "real_sensor_performance_claim": False,
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
            "availability": p14.AUX_AVAILABILITY,
            "lateral_sigma_m": p14.AUX_LATERAL_SIGMA_M,
            "altitude_sigma_m": p14.AUX_ALTITUDE_SIGMA_M,
            "tail_probability": p14.AUX_TAIL_PROBABILITY,
            "tail_scale_uniform": [p14.AUX_TAIL_SCALE_LOW, p14.AUX_TAIL_SCALE_HIGH],
            "stream_constant": p14.AUX_STREAM_CONSTANT,
            "fallback_only_at_runtime": True,
            "calibration_uses_all_available_auxiliary_observations": True,
            "may_become_primary_anchor": False,
        },
        "velocity_caps": velocity_caps,
        "innovation_scales": innovation_scales,
        "groups": list(p14.GROUPS),
        "base_minimums": BASE_MINIMUMS,
        "transfer_minimums": TRANSFER_MINIMUMS,
        "challenge_minimums": CHALLENGE_MINIMUMS,
        "base_source_rows": base_counts,
        "transfer_source_rows": transfer_counts,
        "base_radii": base_radii,
        "transfer_multipliers": multipliers,
        "direct_conformal_radii": final_radii,
    }
    return candidate, base, transfer


def _load_candidate(path: Path) -> dict[str, object]:
    c = json.loads(path.read_text(encoding="utf-8"))
    if c.get("schema") != "aegisland.phase11.p15.candidate-freeze.v1": raise SystemExit("invalid P15 candidate schema")
    if c.get("challenge_seed_unseen_at_freeze") != CHALLENGE_SEED or c.get("validation_seed_unseen_at_freeze") != VALIDATION_SEED: raise SystemExit("P15 evidence boundary mismatch")
    return c


def _summarize(evaluated: pd.DataFrame, reference: pd.DataFrame, candidate: dict[str, object], role: str, seed: int):
    result = p14.summarize(evaluated, reference, candidate, role, seed, CHALLENGE_MINIMUMS)
    result["schema"] = "aegisland.phase11.p15.result.v1"
    result["auxiliary_calibration_rule"] = "all_available_auxiliary_observations"
    return result


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _manifest(out: Path, files: list[str], stage: str, git_sha: str) -> None:
    payload = {"schema": "aegisland.phase11.p15.manifest.v1", "stage": stage, "git_sha": git_sha, "simulation_only": True, "safety_acceptance": False, "controller_tuning_allowed": False, "files": {n: {"sha256": _hash_file(out / n), "bytes": (out / n).stat().st_size} for n in files}}
    (out / "manifest.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def freeze(out: Path, git_sha: str):
    out.mkdir(parents=True, exist_ok=True)
    fit = _raw("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS)
    base_raw = _raw("base_calibration", BASE_CALIBRATION_SEED, BASE_CALIBRATION_FAMILIES, BASE_CALIBRATION_DOMAINS)
    transfer_raw = _raw("transfer_calibration", TRANSFER_CALIBRATION_SEED, TRANSFER_CALIBRATION_FAMILIES, TRANSFER_CALIBRATION_DOMAINS)
    c, base, transfer = _build_candidate(fit, base_raw, transfer_raw, git_sha)
    fit.to_csv(out / "fit_frames.csv", index=False); base.to_csv(out / "base_calibration_frames.csv", index=False); transfer.to_csv(out / "transfer_calibration_frames.csv", index=False)
    (out / "candidate_freeze.json").write_text(json.dumps(c, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(out, ["fit_frames.csv", "base_calibration_frames.csv", "transfer_calibration_frames.csv", "candidate_freeze.json"], "freeze", git_sha)
    return c


def challenge(out: Path, candidate_path: Path, git_sha: str):
    c = _load_candidate(candidate_path); out.mkdir(parents=True, exist_ok=True)
    evaluated = _prepare(_raw("challenge", CHALLENGE_SEED, CHALLENGE_FAMILIES, CHALLENGE_DOMAINS), c["velocity_caps"], c["innovation_scales"])
    reference = _prepare(_raw("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS), c["velocity_caps"], c["innovation_scales"])
    r = _summarize(evaluated, reference, c, "phase11_p15_seen_challenge", CHALLENGE_SEED)
    evaluated.to_csv(out / "challenge_frames.csv", index=False); (out / "challenge_result.json").write_text(json.dumps(r, indent=2, sort_keys=True) + "\n", encoding="utf-8"); (out / "candidate_freeze.json").write_text(json.dumps(c, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(out, ["challenge_frames.csv", "challenge_result.json", "candidate_freeze.json"], "challenge", git_sha)
    return r


def validate(out: Path, candidate_path: Path, git_sha: str):
    c = _load_candidate(candidate_path); out.mkdir(parents=True, exist_ok=True)
    evaluated = _prepare(_raw("validation", VALIDATION_SEED, VALIDATION_FAMILIES, VALIDATION_DOMAINS), c["velocity_caps"], c["innovation_scales"])
    reference = _prepare(_raw("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS), c["velocity_caps"], c["innovation_scales"])
    r = _summarize(evaluated, reference, c, "phase11_p15_frozen_candidate_validation", VALIDATION_SEED)
    evaluated.to_csv(out / "validation_frames.csv", index=False); (out / "validation_result.json").write_text(json.dumps(r, indent=2, sort_keys=True) + "\n", encoding="utf-8"); (out / "candidate_freeze.json").write_text(json.dumps(c, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(out, ["validation_frames.csv", "validation_result.json", "candidate_freeze.json"], "validation", git_sha)
    return r


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 11 P15 source-observation calibration simulation benchmark")
    parser.add_argument("--stage", choices=("freeze", "challenge", "validation"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--git-sha", default="unknown")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.stage == "freeze":
        c = freeze(args.out, args.git_sha); print("P15_CANDIDATE_FREEZE=" + json.dumps({"base_source_rows": c["base_source_rows"], "transfer_source_rows": c["transfer_source_rows"]}, sort_keys=True)); return
    if args.candidate is None: raise SystemExit("--candidate required")
    if args.stage == "challenge":
        r = challenge(args.out, args.candidate, args.git_sha); print("P15_CHALLENGE_GATES=" + json.dumps(r["gates"], sort_keys=True)); return
    r = validate(args.out, args.candidate, args.git_sha); print("P15_VALIDATION_GATES=" + json.dumps(r["gates"], sort_keys=True))


if __name__ == "__main__":
    main()
