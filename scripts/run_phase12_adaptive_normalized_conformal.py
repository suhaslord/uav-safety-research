from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scripts import run_phase11_p14r_robust_group_envelope as p11
except ModuleNotFoundError:
    import run_phase11_p14r_robust_group_envelope as p11

TARGETS = p11.TARGETS
GROUPS = p11.GROUPS

SCALE_FIT_SEED = 880880
CAL_A_SEED = 891891
CAL_B_SEED = 902902
DEV_SEED = 907907
TRANSFER_SEED = 913913
VALIDATION_SEED = 924924
FINAL_SEED = 935935


def _strata(start: int, per: int) -> dict[str, tuple[int, ...]]:
    names = ("bootstrap5", "gap3", "gap7", "gap12")
    return {name: tuple(range(start + i * per, start + (i + 1) * per)) for i, name in enumerate(names)}


def _flatten(strata: dict[str, tuple[int, ...]]) -> tuple[int, ...]:
    return tuple(x for name in ("bootstrap5", "gap3", "gap7", "gap12") for x in strata[name])


SCALE_FIT_STRATA = _strata(957, 8)
CAL_A_STRATA = _strata(989, 8)
CAL_B_STRATA = _strata(1021, 8)
TRANSFER_STRATA = _strata(1053, 6)
VALIDATION_STRATA = _strata(1077, 6)
FINAL_STRATA = _strata(1101, 6)
DEV_STRATA = _strata(1125, 6)

SCALE_FIT_FAMILIES = _flatten(SCALE_FIT_STRATA)
CAL_A_FAMILIES = _flatten(CAL_A_STRATA)
CAL_B_FAMILIES = _flatten(CAL_B_STRATA)
TRANSFER_FAMILIES = _flatten(TRANSFER_STRATA)
VALIDATION_FAMILIES = _flatten(VALIDATION_STRATA)
FINAL_FAMILIES = _flatten(FINAL_STRATA)
DEV_FAMILIES = _flatten(DEV_STRATA)

# Frozen compound-shift environments. All retain temporal dropout because the
# predecessor's bounded-continuity / rescue mechanism is intentionally unchanged.
SCALE_FIT_DOMAINS = (
    "edge+small_scale+temporal_dropout",
    "oblique+blur_noise+temporal_dropout",
    "dim+low_contrast+blur_noise+temporal_dropout",
    "edge+oblique+dim+temporal_dropout",
    "small_scale+blur_noise+low_contrast+temporal_dropout",
    "edge+small_scale+oblique+low_contrast+temporal_dropout",
    "oblique+dim+blur_noise+low_contrast+temporal_dropout",
    "edge+small_scale+dim+blur_noise+temporal_dropout",
)
CAL_A_DOMAINS = (
    "edge+oblique+temporal_dropout",
    "small_scale+dim+blur_noise+temporal_dropout",
    "oblique+dim+low_contrast+temporal_dropout",
    "edge+small_scale+blur_noise+temporal_dropout",
    "edge+dim+blur_noise+low_contrast+temporal_dropout",
    "small_scale+oblique+dim+low_contrast+temporal_dropout",
    "edge+small_scale+oblique+blur_noise+low_contrast+temporal_dropout",
    "edge+oblique+dim+blur_noise+temporal_dropout",
)
CAL_B_DOMAINS = (
    "edge+blur_noise+low_contrast+temporal_dropout",
    "small_scale+oblique+dim+temporal_dropout",
    "oblique+dim+blur_noise+temporal_dropout",
    "edge+small_scale+low_contrast+temporal_dropout",
    "small_scale+dim+blur_noise+low_contrast+temporal_dropout",
    "edge+oblique+dim+low_contrast+temporal_dropout",
    "small_scale+oblique+blur_noise+low_contrast+temporal_dropout",
    "edge+small_scale+oblique+dim+blur_noise+temporal_dropout",
)
DEV_DOMAINS = (
    "edge+dim+low_contrast+temporal_dropout",
    "small_scale+oblique+blur_noise+temporal_dropout",
    "edge+small_scale+dim+temporal_dropout",
    "oblique+blur_noise+low_contrast+temporal_dropout",
    "edge+oblique+dim+blur_noise+low_contrast+temporal_dropout",
    "small_scale+oblique+dim+blur_noise+temporal_dropout",
    "edge+small_scale+blur_noise+low_contrast+temporal_dropout",
    "edge+small_scale+oblique+dim+low_contrast+temporal_dropout",
)
TRANSFER_DOMAINS = (
    "edge+small_scale+oblique+temporal_dropout",
    "small_scale+dim+low_contrast+temporal_dropout",
    "oblique+dim+blur_noise+low_contrast+temporal_dropout",
    "edge+oblique+blur_noise+temporal_dropout",
    "edge+small_scale+dim+blur_noise+low_contrast+temporal_dropout",
    "small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout",
    "edge+oblique+dim+blur_noise+temporal_dropout",
    "edge+small_scale+oblique+low_contrast+temporal_dropout",
    "small_scale+oblique+blur_noise+low_contrast+temporal_dropout",
    "edge+dim+blur_noise+low_contrast+temporal_dropout",
)
VALIDATION_DOMAINS = (
    "edge+low_contrast+temporal_dropout",
    "small_scale+dim+temporal_dropout",
    "oblique+blur_noise+temporal_dropout",
    "edge+oblique+dim+low_contrast+temporal_dropout",
    "small_scale+blur_noise+low_contrast+temporal_dropout",
    "edge+small_scale+oblique+blur_noise+temporal_dropout",
    "oblique+dim+blur_noise+low_contrast+temporal_dropout",
    "edge+small_scale+dim+blur_noise+temporal_dropout",
    "small_scale+oblique+dim+low_contrast+temporal_dropout",
    "edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout",
)
FINAL_DOMAINS = (
    "edge+dim+temporal_dropout",
    "small_scale+low_contrast+temporal_dropout",
    "oblique+dim+temporal_dropout",
    "edge+blur_noise+low_contrast+temporal_dropout",
    "small_scale+oblique+blur_noise+temporal_dropout",
    "edge+small_scale+dim+low_contrast+temporal_dropout",
    "oblique+dim+blur_noise+low_contrast+temporal_dropout",
    "edge+small_scale+oblique+dim+temporal_dropout",
    "small_scale+oblique+dim+blur_noise+temporal_dropout",
    "edge+small_scale+oblique+blur_noise+low_contrast+temporal_dropout",
)

SCALE_MINIMUMS = dict(p11.CAL_MINIMUMS)
CAL_MINIMUMS = dict(p11.CAL_MINIMUMS)
EVAL_MINIMUMS = dict(p11.EVAL_MINIMUMS)
FINAL_MINIMUMS = dict(p11.FINAL_MINIMUMS)
SCALE_FLOOR_M = 1.0e-5


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _event(
    name: str,
    seed: int,
    families: tuple[int, ...],
    domains: tuple[str, ...],
    strata: dict[str, tuple[int, ...]],
    candidate: dict[str, object],
) -> pd.DataFrame:
    return p11._event(
        name,
        seed,
        families,
        domains,
        strata,
        candidate["velocity_caps"],
        candidate["innovation_scales"],
    )


def _fit_scale_models(df: pd.DataFrame) -> tuple[dict[str, object], dict[str, int]]:
    counts = p11._group_counts(df)
    p11._assert_minimums(counts, SCALE_MINIMUMS, "phase12 scale-fit")

    d = df[p11._available(df)].copy()
    d["phase12_group"] = p11._groups(d).astype(str)
    models: dict[str, object] = {}

    for group in GROUPS:
        gd = d[d["phase12_group"] == group]
        models[group] = {}
        severity = gd["severity"].to_numpy(float)
        if not severity.size or not np.all(np.isfinite(severity)):
            raise RuntimeError(f"phase12 non-finite or empty severity in scale-fit group {group}")

        sev10, sev90 = np.quantile(severity, [0.10, 0.90])
        sev33, sev67 = np.quantile(severity, [1.0 / 3.0, 2.0 / 3.0])
        if not np.isfinite(sev10) or not np.isfinite(sev90) or sev90 <= sev10:
            raise RuntimeError(f"phase12 invalid severity anchors for {group}: {sev10}, {sev90}")

        low_mask = severity <= sev33
        high_mask = severity >= sev67
        if int(np.sum(low_mask)) < 10 or int(np.sum(high_mask)) < 10:
            raise RuntimeError(f"phase12 underpowered scale tails for {group}")

        for axis in ("lateral", "altitude"):
            errors = gd[f"p14_{axis}_abs_error_m"].to_numpy(float)
            if not np.all(np.isfinite(errors)):
                raise RuntimeError(f"phase12 non-finite {axis} errors in scale-fit group {group}")
            low = max(float(np.median(errors[low_mask])), SCALE_FLOOR_M)
            high = max(float(np.median(errors[high_mask])), low)
            models[group][axis] = {
                "severity_10": float(sev10),
                "severity_90": float(sev90),
                "scale_low_m": low,
                "scale_high_m": high,
                "scale_floor_m": SCALE_FLOOR_M,
                "rows": int(len(gd)),
            }
    return models, counts


def _scale_values(df: pd.DataFrame, models: dict[str, object], axis: str) -> np.ndarray:
    groups = p11._groups(df).astype(str).to_numpy()
    severity = df["severity"].to_numpy(float)
    out = np.empty(len(df), dtype=float)

    for i, group in enumerate(groups):
        if not np.isfinite(severity[i]):
            raise RuntimeError("phase12 inference-visible severity is non-finite")
        m = models[group][axis]
        lo_s = float(m["severity_10"])
        hi_s = float(m["severity_90"])
        t = float(np.clip((severity[i] - lo_s) / (hi_s - lo_s), 0.0, 1.0))
        lo = float(m["scale_low_m"])
        hi = float(m["scale_high_m"])
        floor = float(m["scale_floor_m"])
        out[i] = max(floor, lo + t * (hi - lo))
    return out


def _fit_normalized_radii(
    df: pd.DataFrame,
    models: dict[str, object],
    label: str,
) -> tuple[dict[str, object], dict[str, int]]:
    counts = p11._group_counts(df)
    p11._assert_minimums(counts, CAL_MINIMUMS, label)

    d = df[p11._available(df)].copy()
    d["phase12_group"] = p11._groups(d).astype(str)
    radii: dict[str, object] = {}

    for group in GROUPS:
        gd = d[d["phase12_group"] == group]
        radii[group] = {}
        for axis in ("lateral", "altitude"):
            err = gd[f"p14_{axis}_abs_error_m"].to_numpy(float)
            scale = _scale_values(gd, models, axis)
            score = err / scale
            raw = [p11.p9._finite_conformal(score, q) for q in TARGETS]
            nested = np.maximum.accumulate(np.asarray(raw, dtype=float))
            radii[group][axis] = {
                f"{q:.2f}": float(nested[i]) for i, q in enumerate(TARGETS)
            }
    return radii, counts


def _max_envelope(a: dict[str, object], b: dict[str, object]) -> dict[str, object]:
    out: dict[str, object] = {}
    for group in GROUPS:
        out[group] = {}
        for axis in ("lateral", "altitude"):
            out[group][axis] = {}
            for q in TARGETS:
                key = f"{q:.2f}"
                out[group][axis][key] = float(
                    max(float(a[group][axis][key]), float(b[group][axis][key]))
                )
    return out


def _halfwidths(df: pd.DataFrame, candidate: dict[str, object], axis: str, q: float) -> np.ndarray:
    groups = p11._groups(df).astype(str).to_numpy()
    scales = _scale_values(df, candidate["scale_models"], axis)
    table = candidate["robust_normalized_radii"]
    key = f"{q:.2f}"
    multipliers = np.asarray([float(table[g][axis][key]) for g in groups], dtype=float)
    return scales * multipliers


def _summarize(
    df: pd.DataFrame,
    candidate: dict[str, object],
    role: str,
    seed: int,
    minimums: dict[str, int],
) -> dict[str, object]:
    original = p11._halfwidths
    p11._halfwidths = _halfwidths
    try:
        return p11.summarize(df, candidate, role, seed, minimums)
    finally:
        p11._halfwidths = original


def _build_candidate(predecessor_path: Path, git_sha: str | None) -> dict[str, object]:
    predecessor = _load_json(predecessor_path)
    for key in ("velocity_caps", "innovation_scales"):
        if key not in predecessor:
            raise RuntimeError(f"phase12 predecessor is missing required key {key}")

    base = {
        "velocity_caps": predecessor["velocity_caps"],
        "innovation_scales": predecessor["innovation_scales"],
    }
    scale_fit = _event(
        "phase12_scale_fit",
        SCALE_FIT_SEED,
        SCALE_FIT_FAMILIES,
        SCALE_FIT_DOMAINS,
        SCALE_FIT_STRATA,
        base,
    )
    cal_a = _event(
        "phase12_calibration_a",
        CAL_A_SEED,
        CAL_A_FAMILIES,
        CAL_A_DOMAINS,
        CAL_A_STRATA,
        base,
    )
    cal_b = _event(
        "phase12_calibration_b",
        CAL_B_SEED,
        CAL_B_FAMILIES,
        CAL_B_DOMAINS,
        CAL_B_STRATA,
        base,
    )

    scale_models, scale_counts = _fit_scale_models(scale_fit)
    rad_a, cal_a_counts = _fit_normalized_radii(cal_a, scale_models, "phase12 calibration A")
    rad_b, cal_b_counts = _fit_normalized_radii(cal_b, scale_models, "phase12 calibration B")
    robust = _max_envelope(rad_a, rad_b)
    severity_thresholds = p11._severity_thresholds(cal_a, cal_b)

    return {
        "schema": "aegisland.phase12.adaptive-normalized-conformal.candidate.v1",
        "method": "adaptive_normalized_robust_conformal",
        "simulation_only": True,
        "safety_acceptance": False,
        "scientific_git_sha": git_sha,
        "predecessor_candidate_sha256": _sha256_file(predecessor_path),
        "predecessor_phase": "phase11_p14r_closed",
        "velocity_caps": predecessor["velocity_caps"],
        "innovation_scales": predecessor["innovation_scales"],
        "scale_models": scale_models,
        "normalized_radii_calibration_a": rad_a,
        "normalized_radii_calibration_b": rad_b,
        "robust_normalized_radii": robust,
        "high_severity_thresholds": severity_thresholds,
        "group_counts": {
            "scale_fit": scale_counts,
            "calibration_a": cal_a_counts,
            "calibration_b": cal_b_counts,
        },
        "seeds": {
            "scale_fit": SCALE_FIT_SEED,
            "calibration_a": CAL_A_SEED,
            "calibration_b": CAL_B_SEED,
            "development_smoke": DEV_SEED,
            "seen_transfer": TRANSFER_SEED,
            "protected_validation": VALIDATION_SEED,
            "final_holdout": FINAL_SEED,
        },
        "phase11_protected_seed_forbidden": 858858,
        "phase11_retired_p15_v2_seed_forbidden": 869869,
    }


def _stage_config(stage: str):
    if stage == "dev":
        return DEV_SEED, DEV_FAMILIES, DEV_DOMAINS, DEV_STRATA, EVAL_MINIMUMS, "development_result.json"
    if stage == "transfer":
        return TRANSFER_SEED, TRANSFER_FAMILIES, TRANSFER_DOMAINS, TRANSFER_STRATA, EVAL_MINIMUMS, "transfer_result.json"
    if stage == "validation":
        return VALIDATION_SEED, VALIDATION_FAMILIES, VALIDATION_DOMAINS, VALIDATION_STRATA, EVAL_MINIMUMS, "validation_result.json"
    if stage == "final":
        return FINAL_SEED, FINAL_FAMILIES, FINAL_DOMAINS, FINAL_STRATA, FINAL_MINIMUMS, "final_result.json"
    raise ValueError(stage)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase 12 adaptive normalized robust conformal study")
    p.add_argument("--stage", choices=("freeze", "dev", "transfer", "validation", "final"), required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--predecessor", type=Path)
    p.add_argument("--candidate", type=Path)
    p.add_argument("--git-sha")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    if args.stage == "freeze":
        if args.predecessor is None:
            raise SystemExit("--predecessor is required for --stage freeze")
        candidate = _build_candidate(args.predecessor, args.git_sha)
        path = args.out / "candidate_freeze.json"
        path.write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("PHASE12_CANDIDATE_SHA256=" + _sha256_file(path))
        print("PHASE12_SCALE_COUNTS=" + json.dumps(candidate["group_counts"], sort_keys=True))
        return

    if args.candidate is None:
        raise SystemExit("--candidate is required for evaluation stages")
    candidate = _load_json(args.candidate)
    if candidate.get("schema") != "aegisland.phase12.adaptive-normalized-conformal.candidate.v1":
        raise RuntimeError("unexpected Phase 12 candidate schema")

    seed, families, domains, strata, minimums, filename = _stage_config(args.stage)
    df = _event(f"phase12_{args.stage}", seed, families, domains, strata, candidate)
    result = _summarize(df, candidate, f"phase12_{args.stage}", seed, minimums)
    result["schema"] = f"aegisland.phase12.{args.stage}-result.v1"
    result["candidate_sha256"] = _sha256_file(args.candidate)
    result["scientific_git_sha"] = args.git_sha
    result["simulation_only"] = True
    result["safety_acceptance"] = False
    if args.stage == "dev":
        result["development_only"] = True
        result["eligible_for_progression"] = False

    (args.out / "candidate_freeze.json").write_text(
        args.candidate.read_text(encoding="utf-8"), encoding="utf-8"
    )
    result_path = args.out / filename
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PHASE12_{args.stage.upper()}_RESULT_SHA256=" + _sha256_file(result_path))
    print(
        f"PHASE12_{args.stage.upper()}_ALL_PRIMARY_GATES_PASS="
        + str(bool(result.get("all_primary_gates_pass", False))).lower()
    )
    print(json.dumps(result.get("gates", {}), sort_keys=True))


if __name__ == "__main__":
    main()
