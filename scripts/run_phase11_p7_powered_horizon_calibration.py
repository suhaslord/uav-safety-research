from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

try:
    from scripts import run_phase11_p6_horizon_calibration as p6
except ModuleNotFoundError:
    import run_phase11_p6_horizon_calibration as p6

FIT_SEED = 308308
CALIBRATION_SEED = 319319
TRANSFER_SEED = 330330
DEVELOPMENT_SEED = 341341
VALIDATION_SEED = 352352
FRAMES_PER_SEQUENCE = 60
FIT_FAMILIES = tuple(range(105, 111))
CALIBRATION_FAMILIES = tuple(range(111, 114))
TRANSFER_FAMILIES = tuple(range(114, 120))
DEVELOPMENT_FAMILIES = tuple(range(120, 123))
VALIDATION_FAMILIES = tuple(range(123, 126))
FIT_DOMAINS = p6.FIT_DOMAINS
TRANSFER_DOMAINS = (
    "edge+temporal_dropout",
    "small_scale+temporal_dropout",
    "oblique+temporal_dropout",
    "dim+temporal_dropout",
    "blur_noise+temporal_dropout",
    "low_contrast+temporal_dropout",
    "edge+blur_noise+temporal_dropout",
    "small_scale+dim+temporal_dropout",
)
DEVELOPMENT_DOMAINS = (
    "edge+dim",
    "small_scale+blur_noise",
    "oblique+low_contrast",
    "edge+small_scale+blur_noise",
    "oblique+dim+temporal_dropout",
    "edge+low_contrast+temporal_dropout",
    "small_scale+oblique+dim",
    "edge+small_scale+oblique+low_contrast+temporal_dropout",
)
VALIDATION_DOMAINS = (
    "edge+small_scale",
    "oblique+dim",
    "blur_noise+low_contrast",
    "small_scale+dim+temporal_dropout",
    "edge+oblique+blur_noise",
    "dim+low_contrast+temporal_dropout",
    "small_scale+oblique+blur_noise+low_contrast",
    "edge+small_scale+oblique+dim+temporal_dropout",
)
MIN_GROUP_COUNT = 40


def _raw(name: str, seed: int, families: tuple[int, ...], domains: tuple[str, ...]) -> pd.DataFrame:
    return p6.p1.generate_split(name, seed, families, domains, frames=FRAMES_PER_SEQUENCE)


def _prepare(raw: pd.DataFrame, velocity_caps: dict[str, float]) -> pd.DataFrame:
    return p6.p1.add_reliability_state(p6.p5.add_continuity_bridge(raw, velocity_caps))


def _available(df: pd.DataFrame) -> pd.Series:
    return p6._available(df)


def build_candidate(fit: pd.DataFrame, calibration: pd.DataFrame, transfer: pd.DataFrame, velocity_caps: dict[str, float], git_sha: str) -> dict[str, object]:
    scale_model = p6.p5.fit_scale_model(fit)
    single = p6.p5.single_factor_calibration(calibration, scale_model)
    transfer_multipliers, counts = p6._horizon_transfer(transfer, scale_model, single)
    if counts["long"] < MIN_GROUP_COUNT or counts["direct_short"] < MIN_GROUP_COUNT:
        raise ValueError(f"P7 insufficient horizon-group calibration rows: {counts}")
    return {
        "schema": "aegisland.phase11.p7.candidate-freeze.v1",
        "git_sha": git_sha,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "development_seed_unseen_at_freeze": DEVELOPMENT_SEED,
        "validation_seed_unseen_at_freeze": VALIDATION_SEED,
        "max_bridge_horizon": p6.p5.MAX_BRIDGE_HORIZON,
        "velocity_caps": velocity_caps,
        "ridge_lambda": p6.p5.RIDGE_LAMBDA,
        "scale_model": scale_model,
        "single_factor_conformal": single,
        "horizon_transfer_multipliers": transfer_multipliers,
        "horizon_group_counts": counts,
        "horizon_groups": {"direct_short": "bridge_horizon<=2", "long": "3<=bridge_horizon<=5"},
    }


def freeze(out: Path, git_sha: str) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    fit_raw = _raw("fit", FIT_SEED, FIT_FAMILIES, FIT_DOMAINS)
    caps = p6.p5.fit_velocity_caps(fit_raw)
    fit = _prepare(fit_raw, caps)
    calibration = _prepare(_raw("calibration", CALIBRATION_SEED, CALIBRATION_FAMILIES, FIT_DOMAINS), caps)
    transfer = _prepare(_raw("transfer", TRANSFER_SEED, TRANSFER_FAMILIES, TRANSFER_DOMAINS), caps)
    candidate = build_candidate(fit, calibration, transfer, caps, git_sha)
    fit.to_csv(out / "fit_frames.csv", index=False)
    calibration.to_csv(out / "calibration_frames.csv", index=False)
    transfer.to_csv(out / "transfer_frames.csv", index=False)
    (out / "candidate_freeze.json").write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("P7_CANDIDATE_FREEZE_JSON=" + json.dumps(candidate, sort_keys=True))
    return candidate


def evaluate(stage: str, out: Path, candidate_path: Path, git_sha: str) -> dict[str, object]:
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    caps = candidate["velocity_caps"]
    calibration = _prepare(_raw("calibration", CALIBRATION_SEED, CALIBRATION_FAMILIES, FIT_DOMAINS), caps)
    if stage == "development":
        if int(candidate.get("development_seed_unseen_at_freeze", -1)) != DEVELOPMENT_SEED:
            raise SystemExit("candidate does not match P7 development seed")
        evaluated = _prepare(_raw("development", DEVELOPMENT_SEED, DEVELOPMENT_FAMILIES, DEVELOPMENT_DOMAINS), caps)
        seed = DEVELOPMENT_SEED
        role = "phase11_p7_frozen_candidate_development_challenge"
        prefix = "development"
    elif stage == "validation":
        if int(candidate.get("validation_seed_unseen_at_freeze", -1)) != VALIDATION_SEED:
            raise SystemExit("candidate does not match P7 validation seed")
        evaluated = _prepare(_raw("validation", VALIDATION_SEED, VALIDATION_FAMILIES, VALIDATION_DOMAINS), caps)
        seed = VALIDATION_SEED
        role = "phase11_p7_frozen_candidate_protected_validation"
        prefix = "validation"
    else:
        raise ValueError(stage)
    result = p6.summarize(evaluated, calibration, candidate, role, seed)
    result["schema"] = "aegisland.phase11.p7.result.v1"
    result["git_sha"] = git_sha
    out.mkdir(parents=True, exist_ok=True)
    evaluated.to_csv(out / f"{prefix}_frames.csv", index=False)
    (out / f"{prefix}_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"P7_{prefix.upper()}_GATES=" + json.dumps(result["gates"], sort_keys=True))
    print(f"P7_{prefix.upper()}_OVERALL=" + ("PASS" if result["all_primary_gates_pass"] else "MIXED_OR_FAILED"))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 11 P7 powered horizon-aware calibration benchmark")
    parser.add_argument("--stage", choices=("freeze", "development", "validation"), required=True)
    parser.add_argument("--out", type=Path, default=Path("results/phase11_p7"))
    parser.add_argument("--candidate", type=Path, default=Path("results/phase11_p7/candidate_freeze.json"))
    parser.add_argument("--git-sha", default="unknown")
    args = parser.parse_args()
    if args.stage == "freeze":
        freeze(args.out, args.git_sha)
    else:
        evaluate(args.stage, args.out, args.candidate, args.git_sha)


if __name__ == "__main__":
    main()
