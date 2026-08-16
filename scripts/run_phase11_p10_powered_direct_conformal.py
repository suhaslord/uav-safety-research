from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

try:
    from scripts import run_phase11_p9_soft_update_direct_conformal as p9
except ModuleNotFoundError:
    import run_phase11_p9_soft_update_direct_conformal as p9

FIT_SEED = 451451
CALIBRATION_SEED = 462462
TRANSFER_SEED = 473473
VALIDATION_SEED = 484484
FRAMES_PER_SEQUENCE = p9.FRAMES_PER_SEQUENCE

FIT_FAMILIES = tuple(range(188, 194))
CALIBRATION_FAMILIES = tuple(range(194, 212))
TRANSFER_FAMILIES = tuple(range(212, 224))
VALIDATION_FAMILIES = tuple(range(224, 236))

FIT_DOMAINS = p9.FIT_DOMAINS
CALIBRATION_DOMAINS = p9.CALIBRATION_DOMAINS
TRANSFER_DOMAINS = p9.TRANSFER_DOMAINS
VALIDATION_DOMAINS = p9.VALIDATION_DOMAINS


def _raw(name: str, seed: int, families: tuple[int, ...], domains: tuple[str, ...]):
    return p9.p1.generate_split(name, seed, families, domains, frames=FRAMES_PER_SEQUENCE)


def _build_candidate(fit_raw, calibration_raw, git_sha: str):
    velocity_caps = p9._fit_velocity_caps(fit_raw)
    innovation_scales = p9._fit_innovation_scales(fit_raw, velocity_caps)
    calibration = p9.add_p9_continuity(calibration_raw, velocity_caps, innovation_scales)
    radii, counts = p9._fit_direct_radii(calibration)
    candidate = {
        "schema": "aegisland.phase11.p10.candidate-freeze.v1",
        "git_sha": git_sha,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "replicates_method": "phase11_p9_soft_update_direct_conformal",
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
        "groups": list(p9.GROUPS),
        "calibration_minimums": p9.CALIBRATION_MINIMUMS,
        "transfer_minimums": p9.TRANSFER_MINIMUMS,
        "calibration_group_rows": counts,
        "direct_conformal_radii": radii,
    }
    return candidate, calibration


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _manifest(out: Path, files: list[str], stage: str, git_sha: str) -> None:
    payload = {
        "schema": "aegisland.phase11.p10.manifest.v1",
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
    calibration_raw = _raw("calibration", CALIBRATION_SEED, CALIBRATION_FAMILIES, CALIBRATION_DOMAINS)
    candidate, calibration = _build_candidate(fit_raw, calibration_raw, git_sha)
    fit_raw.to_csv(out / "fit_frames.csv", index=False)
    calibration.to_csv(out / "calibration_frames.csv", index=False)
    (out / "candidate_freeze.json").write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(out, ["fit_frames.csv", "calibration_frames.csv", "candidate_freeze.json"], "freeze", git_sha)
    return candidate


def _load_candidate(path: Path):
    candidate = json.loads(path.read_text(encoding="utf-8"))
    if candidate.get("schema") != "aegisland.phase11.p10.candidate-freeze.v1":
        raise SystemExit("invalid P10 candidate schema")
    if candidate.get("transfer_seed_unseen_at_freeze") != TRANSFER_SEED:
        raise SystemExit("P10 transfer seed mismatch")
    if candidate.get("validation_seed_unseen_at_freeze") != VALIDATION_SEED:
        raise SystemExit("P10 validation seed mismatch")
    return candidate


def _summarize(evaluated, reference, candidate, role: str, seed: int, require_transfer_minimums: bool):
    result = p9.summarize(evaluated, reference, candidate, role, seed, require_transfer_minimums)
    result["schema"] = "aegisland.phase11.p10.result.v1"
    return result


def transfer(out: Path, candidate_path: Path, git_sha: str):
    candidate = _load_candidate(candidate_path)
    out.mkdir(parents=True, exist_ok=True)
    transfer_raw = _raw("transfer", TRANSFER_SEED, TRANSFER_FAMILIES, TRANSFER_DOMAINS)
    transfer_df = p9.add_p9_continuity(transfer_raw, candidate["velocity_caps"], candidate["innovation_scales"])
    reference_raw = _raw("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS)
    reference = p9.add_p9_continuity(reference_raw, candidate["velocity_caps"], candidate["innovation_scales"])
    result = _summarize(transfer_df, reference, candidate, "phase11_p10_seen_transfer", TRANSFER_SEED, True)
    transfer_df.to_csv(out / "transfer_frames.csv", index=False)
    (out / "transfer_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "candidate_freeze.json").write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(out, ["transfer_frames.csv", "transfer_result.json", "candidate_freeze.json"], "transfer", git_sha)
    return result


def validate(out: Path, candidate_path: Path, git_sha: str):
    candidate = _load_candidate(candidate_path)
    out.mkdir(parents=True, exist_ok=True)
    validation_raw = _raw("validation", VALIDATION_SEED, VALIDATION_FAMILIES, VALIDATION_DOMAINS)
    validation = p9.add_p9_continuity(validation_raw, candidate["velocity_caps"], candidate["innovation_scales"])
    reference_raw = _raw("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS)
    reference = p9.add_p9_continuity(reference_raw, candidate["velocity_caps"], candidate["innovation_scales"])
    result = _summarize(validation, reference, candidate, "phase11_p10_frozen_candidate_validation", VALIDATION_SEED, False)
    validation.to_csv(out / "validation_frames.csv", index=False)
    (out / "validation_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "candidate_freeze.json").write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _manifest(out, ["validation_frames.csv", "validation_result.json", "candidate_freeze.json"], "validation", git_sha)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 11 P10 powered direct-conformal replication")
    parser.add_argument("--stage", choices=("freeze", "transfer", "validation"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--git-sha", default="unknown")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.stage == "freeze":
        candidate = freeze(args.out, args.git_sha)
        print("P10_CANDIDATE_FREEZE=" + json.dumps({
            "calibration_group_rows": candidate["calibration_group_rows"],
            "velocity_caps": candidate["velocity_caps"],
            "innovation_scales": candidate["innovation_scales"],
        }, sort_keys=True))
        return
    if args.candidate is None:
        raise SystemExit("--candidate required")
    if args.stage == "transfer":
        result = transfer(args.out, args.candidate, args.git_sha)
        print("P10_TRANSFER_GATES=" + json.dumps(result["gates"], sort_keys=True))
        return
    result = validate(args.out, args.candidate, args.git_sha)
    print("P10_VALIDATION_GATES=" + json.dumps(result["gates"], sort_keys=True))


if __name__ == "__main__":
    main()
