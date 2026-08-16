from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scripts import run_phase11_p12_three_group_direct_conformal as p12
except ModuleNotFoundError:
    import run_phase11_p12_three_group_direct_conformal as p12

p9 = p12.p9

FIT_SEED = 583583
BASE_CALIBRATION_SEED = 594594
TRANSFER_CALIBRATION_SEED = 605605
CHALLENGE_SEED = 616616
VALIDATION_SEED = 627627
FRAMES_PER_SEQUENCE = 60

FIT_FAMILIES = tuple(range(398, 404))
BASE_CALIBRATION_FAMILIES = tuple(range(404, 452))
TRANSFER_CALIBRATION_FAMILIES = tuple(range(452, 476))
CHALLENGE_FAMILIES = tuple(range(476, 496))
VALIDATION_FAMILIES = tuple(range(496, 516))

FIT_DOMAINS = p12.FIT_DOMAINS
BASE_CALIBRATION_DOMAINS = p12.CALIBRATION_DOMAINS
TRANSFER_CALIBRATION_DOMAINS = p12.TRANSFER_DOMAINS
CHALLENGE_DOMAINS = (
    "edge+small_scale+low_contrast+temporal_dropout",
    "oblique+blur_noise+temporal_dropout",
    "edge+dim+temporal_dropout",
    "small_scale+oblique+low_contrast+temporal_dropout",
    "edge+blur_noise+low_contrast+temporal_dropout",
    "small_scale+dim+blur_noise+temporal_dropout",
    "oblique+dim+low_contrast+temporal_dropout",
    "edge+small_scale+oblique+blur_noise+temporal_dropout",
)
VALIDATION_DOMAINS = p12.VALIDATION_DOMAINS


def _raw(name: str, seed: int, families: tuple[int, ...], domains: tuple[str, ...]) -> pd.DataFrame:
    return p9.p1.generate_split(name, seed, families, domains, frames=FRAMES_PER_SEQUENCE)


def _prepare(raw: pd.DataFrame, velocity_caps: dict[str, float], innovation_scales: dict[str, float]) -> pd.DataFrame:
    return p9.add_p9_continuity(raw, velocity_caps, innovation_scales)


def _transfer_calibrate(transfer_df: pd.DataFrame, base_radii: dict[str, object]) -> tuple[dict[str, object], dict[str, object], dict[str, int]]:
    d = transfer_df[p12._available(transfer_df)].copy()
    d["p13_group"] = p12._group_series(d)
    counts = {group: int((d["p13_group"] == group).sum()) for group in p12.GROUPS}
    for group, minimum in p12.TRANSFER_MINIMUMS.items():
        if counts[group] < minimum:
            raise RuntimeError(f"P13 transfer-calibration group {group} rows {counts[group]} < {minimum}")

    multipliers: dict[str, object] = {}
    final_radii: dict[str, object] = {}
    for group in p12.GROUPS:
        gd = d[d["p13_group"] == group]
        multipliers[group] = {}
        final_radii[group] = {}
        for axis in ("lateral", "altitude"):
            err = gd[f"p9_{axis}_abs_error_m"].to_numpy(float)
            raw_final = []
            multipliers[group][axis] = {}
            for q in p9.TARGETS:
                key = f"{q:.2f}"
                base = float(base_radii[group][axis][key])
                ratio = err / max(base, 1e-9)
                t = p9._finite_conformal(ratio, q)
                multipliers[group][axis][key] = float(t)
                raw_final.append(base * t)
            nested = np.maximum.accumulate(np.asarray(raw_final, dtype=float))
            final_radii[group][axis] = {f"{q:.2f}": float(nested[i]) for i, q in enumerate(p9.TARGETS)}
    return multipliers, final_radii, counts


def _build_candidate(fit_raw: pd.DataFrame, base_cal_raw: pd.DataFrame, transfer_cal_raw: pd.DataFrame, git_sha: str) -> tuple[dict[str, object], pd.DataFrame, pd.DataFrame]:
    velocity_caps = p9._fit_velocity_caps(fit_raw)
    innovation_scales = p9._fit_innovation_scales(fit_raw, velocity_caps)
    base_cal = _prepare(base_cal_raw, velocity_caps, innovation_scales)
    base_radii, base_counts = p12._fit_direct_radii(base_cal)
    transfer_cal = _prepare(transfer_cal_raw, velocity_caps, innovation_scales)
    multipliers, final_radii, transfer_counts = _transfer_calibrate(transfer_cal, base_radii)
    candidate = {
        "schema": "aegisland.phase11.p13.candidate-freeze.v1",
        "git_sha": git_sha,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "point_estimator": "phase11_p9_soft_update_unchanged",
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
        "groups": list(p12.GROUPS),
        "base_calibration_minimums": p12.CALIBRATION_MINIMUMS,
        "transfer_calibration_minimums": p12.TRANSFER_MINIMUMS,
        "challenge_minimums": p12.TRANSFER_MINIMUMS,
        "base_calibration_group_rows": base_counts,
        "transfer_calibration_group_rows": transfer_counts,
        "base_direct_conformal_radii": base_radii,
        "transfer_multipliers": multipliers,
        "direct_conformal_radii": final_radii,
    }
    return candidate, base_cal, transfer_cal


def _load_candidate(path: Path) -> dict[str, object]:
    c = json.loads(path.read_text(encoding="utf-8"))
    if c.get("schema") != "aegisland.phase11.p13.candidate-freeze.v1":
        raise SystemExit("invalid P13 candidate schema")
    if c.get("challenge_seed_unseen_at_freeze") != CHALLENGE_SEED:
        raise SystemExit("P13 challenge seed mismatch")
    if c.get("validation_seed_unseen_at_freeze") != VALIDATION_SEED:
        raise SystemExit("P13 validation seed mismatch")
    return c


def _summarize(evaluated: pd.DataFrame, reference: pd.DataFrame, candidate: dict[str, object], role: str, seed: int) -> dict[str, object]:
    result = p12.summarize(evaluated, reference, candidate, role, seed, True)
    result["schema"] = "aegisland.phase11.p13.result.v1"
    return result


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _manifest(out: Path, files: list[str], stage: str, git_sha: str) -> None:
    payload = {"schema": "aegisland.phase11.p13.manifest.v1", "stage": stage, "git_sha": git_sha, "simulation_only": True, "safety_acceptance": False, "controller_tuning_allowed": False, "files": {name: {"sha256": _hash_file(out / name), "bytes": (out / name).stat().st_size} for name in files}}
    (out / "manifest.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def freeze(out: Path, git_sha: str) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    fit_raw = _raw("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS)
    base_cal_raw = _raw("base_calibration", BASE_CALIBRATION_SEED, BASE_CALIBRATION_FAMILIES, BASE_CALIBRATION_DOMAINS)
    transfer_cal_raw = _raw("transfer_calibration", TRANSFER_CALIBRATION_SEED, TRANSFER_CALIBRATION_FAMILIES, TRANSFER_CALIBRATION_DOMAINS)
    candidate, base_cal, transfer_cal = _build_candidate(fit_raw, base_cal_raw, transfer_cal_raw, git_sha)
    fit_raw.to_csv(out / "fit_frames.csv", index=False)
    base_cal.to_csv(out / "base_calibration_frames.csv", index=False)
    transfer_cal.to_csv(out / "transfer_calibration_frames.csv", index=False)
    (out / "candidate_freeze.json").write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(out, ["fit_frames.csv", "base_calibration_frames.csv", "transfer_calibration_frames.csv", "candidate_freeze.json"], "freeze", git_sha)
    return candidate


def challenge(out: Path, candidate_path: Path, git_sha: str) -> dict[str, object]:
    c = _load_candidate(candidate_path); out.mkdir(parents=True, exist_ok=True)
    evaluated = _prepare(_raw("challenge", CHALLENGE_SEED, CHALLENGE_FAMILIES, CHALLENGE_DOMAINS), c["velocity_caps"], c["innovation_scales"])
    reference = _prepare(_raw("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS), c["velocity_caps"], c["innovation_scales"])
    result = _summarize(evaluated, reference, c, "phase11_p13_seen_challenge", CHALLENGE_SEED)
    evaluated.to_csv(out / "challenge_frames.csv", index=False)
    (out / "challenge_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "candidate_freeze.json").write_text(json.dumps(c, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(out, ["challenge_frames.csv", "challenge_result.json", "candidate_freeze.json"], "challenge", git_sha)
    return result


def validate(out: Path, candidate_path: Path, git_sha: str) -> dict[str, object]:
    c = _load_candidate(candidate_path); out.mkdir(parents=True, exist_ok=True)
    evaluated = _prepare(_raw("validation", VALIDATION_SEED, VALIDATION_FAMILIES, VALIDATION_DOMAINS), c["velocity_caps"], c["innovation_scales"])
    reference = _prepare(_raw("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS), c["velocity_caps"], c["innovation_scales"])
    result = _summarize(evaluated, reference, c, "phase11_p13_frozen_candidate_validation", VALIDATION_SEED)
    evaluated.to_csv(out / "validation_frames.csv", index=False)
    (out / "validation_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "candidate_freeze.json").write_text(json.dumps(c, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(out, ["validation_frames.csv", "validation_result.json", "candidate_freeze.json"], "validation", git_sha)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 11 P13 two-stage grouped-conformal simulation benchmark")
    parser.add_argument("--stage", choices=("freeze", "challenge", "validation"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--git-sha", default="unknown")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.stage == "freeze":
        c = freeze(args.out, args.git_sha)
        print("P13_CANDIDATE_FREEZE=" + json.dumps({"base_group_rows": c["base_calibration_group_rows"], "transfer_group_rows": c["transfer_calibration_group_rows"], "transfer_multipliers": c["transfer_multipliers"]}, sort_keys=True)); return
    if args.candidate is None: raise SystemExit("--candidate required")
    if args.stage == "challenge":
        r = challenge(args.out, args.candidate, args.git_sha); print("P13_CHALLENGE_GATES=" + json.dumps(r["gates"], sort_keys=True)); return
    r = validate(args.out, args.candidate, args.git_sha); print("P13_VALIDATION_GATES=" + json.dumps(r["gates"], sort_keys=True))


if __name__ == "__main__":
    main()
