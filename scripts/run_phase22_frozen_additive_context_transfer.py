from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

import numpy as np

try:
    from scripts import run_phase21_orthogonal_context_spectrum as p21
except ModuleNotFoundError:
    import run_phase21_orthogonal_context_spectrum as p21

PHASE22_NAME = "Frozen Additive Context Transfer"
RESULT_SCHEMA_PREFIX = "aegisland.phase22.frozen-additive-context-transfer"

FROZEN_PHASE12_CANDIDATE_SHA256 = p21.FROZEN_PHASE12_CANDIDATE_SHA256
FROZEN_PHASE14_BRIDGE_SHA256 = p21.FROZEN_PHASE14_BRIDGE_SHA256
FROZEN_PHASE17_FIT_CANDIDATE_SHA256 = p21.FROZEN_PHASE17_FIT_CANDIDATE_SHA256
FROZEN_PHASE20_FINAL_RESULT_SHA256 = p21.FROZEN_PHASE20_FINAL_RESULT_SHA256
FROZEN_PHASE21_FINAL_RESULT_SHA256 = "bc85a746cf1b770fb4119feb3979789975ed5201065d94de47c6dcc3a051d9ee"

FACTORS = p21.FACTORS
SIMPLE_DOMAIN = p21.SIMPLE_DOMAIN
HARD_DOMAIN = p21.HARD_DOMAIN

FIT_SEED = 2222220
FIT_FAMILIES = tuple(range(2313, 2337))
STAGE_SEEDS = {
    "dev": 2222221,
    "transfer": 2222222,
    "validation": 2222223,
    "final": 2222224,
}
STAGE_FAMILIES = {
    "dev": tuple(range(2337, 2361)),
    "transfer": tuple(range(2361, 2385)),
    "validation": tuple(range(2385, 2409)),
    "final": tuple(range(2409, 2433)),
}

THRESHOLDS = {
    "minimum_matched_transitions": 500,
    "simple_rmse_advantage_min": 0.05,
    "rmse_endpoint_attenuation_min": 0.08,
    "simple_mae_advantage_min": 0.08,
    "mae_endpoint_attenuation_min": 0.08,
    "first_order_variance_share_min": 0.70,
    "prediction_r2_min": 0.65,
    "prediction_advantage_mae_max": 0.025,
    "stable_sign_margin": 0.02,
    "stable_sign_min_cells": 10,
    "stable_sign_accuracy_min": 0.90,
    "attenuation_abs_error_max": 0.07,
    "simple_p95_error_inflation_min": 1.10,
    "simple_coverage_delta_max": -0.01,
    "hard_p95_error_inflation_min": 1.10,
    "hard_coverage_delta_max": -0.05,
}


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _validate_phase21_final(path: Path) -> dict[str, object]:
    if _sha256_file(path) != FROZEN_PHASE21_FINAL_RESULT_SHA256:
        raise RuntimeError("Phase 22 requires the exact frozen Phase 21 final result")
    result = json.loads(path.read_text(encoding="utf-8"))
    required_true = (
        "phase21_pass",
        "phase20_final_pass_preserved",
        "phase19_final_pass_preserved_via_phase20",
        "phase18_failure_preserved_via_phase20",
        "q90_is_descriptive_only",
        "no_refit",
        "zero_adaptation",
    )
    for field in required_true:
        if result.get(field) is not True:
            raise RuntimeError(f"Phase 22 requires Phase 21 field {field}=true")
    if result.get("phase20_final_result_sha256") != FROZEN_PHASE20_FINAL_RESULT_SHA256:
        raise RuntimeError("Phase 22 Phase 20 lineage mismatch via Phase 21")
    if result.get("factor_order") != list(FACTORS) or result.get("factorial_context_count") != 32:
        raise RuntimeError("Phase 22 requires exact Phase 21 factor identity")
    return result


def _build_cube(
    seed: int,
    families: tuple[int, ...],
    role: str,
    phase12_candidate: dict[str, object],
    phase17_fit: dict[str, object],
) -> dict[str, dict[str, object]]:
    contexts: dict[str, dict[str, object]] = {}
    for subset in p21.p20._all_subsets():
        control, latency = p21._generate_domain(
            seed,
            families,
            role,
            subset,
            phase12_candidate,
        )
        contexts[p21.p20._subset_key(subset)] = p21.p20._context_result(
            control,
            latency,
            phase12_candidate,
            phase17_fit,
            subset,
        )
    return contexts


def _construction_pass(contexts: dict[str, dict[str, object]]) -> bool:
    subsets = p21.p20._all_subsets()
    expected = {p21.p20._subset_key(s) for s in subsets}
    if len(contexts) != 32 or set(contexts) != expected:
        return False
    if contexts["none"]["domain"] != SIMPLE_DOMAIN:
        return False
    if contexts[p21.p20._subset_key(frozenset(FACTORS))]["domain"] != HARD_DOMAIN:
        return False
    return bool(
        all(
            bool(contexts[p21.p20._subset_key(s)]["integrity"]["pass"])
            and bool(contexts[p21.p20._subset_key(s)]["integrity"]["width_identity_pass"])
            and int(contexts[p21.p20._subset_key(s)]["matched_transitions"])
            >= THRESHOLDS["minimum_matched_transitions"]
            for s in subsets
        )
    )


def _endpoint_summary(
    rmse_adv: dict[frozenset[str], float],
    mae_adv: dict[frozenset[str], float],
) -> dict[str, dict[str, float]]:
    empty = frozenset()
    full = frozenset(FACTORS)
    return {
        "rmse": {
            "simple_advantage": float(rmse_adv[empty]),
            "hard_advantage": float(rmse_adv[full]),
            "attenuation": float(rmse_adv[empty] - rmse_adv[full]),
        },
        "mae": {
            "simple_advantage": float(mae_adv[empty]),
            "hard_advantage": float(mae_adv[full]),
            "attenuation": float(mae_adv[empty] - mae_adv[full]),
        },
    }


def _endpoint_phenomenon_pass(endpoint: dict[str, dict[str, float]]) -> bool:
    return bool(
        endpoint["rmse"]["simple_advantage"] >= THRESHOLDS["simple_rmse_advantage_min"]
        and endpoint["rmse"]["attenuation"] >= THRESHOLDS["rmse_endpoint_attenuation_min"]
        and endpoint["mae"]["simple_advantage"] >= THRESHOLDS["simple_mae_advantage_min"]
        and endpoint["mae"]["attenuation"] >= THRESHOLDS["mae_endpoint_attenuation_min"]
    )


def _static_level_pass(contexts: dict[str, dict[str, object]]) -> bool:
    empty = contexts["none"]
    full = contexts[p21.p20._subset_key(frozenset(FACTORS))]
    return bool(
        float(empty["paired_lateral_effects"]["p95_error_inflation"])
        >= THRESHOLDS["simple_p95_error_inflation_min"]
        and float(empty["paired_lateral_effects"]["coverage_delta"])
        <= THRESHOLDS["simple_coverage_delta_max"]
        and float(full["paired_lateral_effects"]["p95_error_inflation"])
        >= THRESHOLDS["hard_p95_error_inflation_min"]
        and float(full["paired_lateral_effects"]["coverage_delta"])
        <= THRESHOLDS["hard_coverage_delta_max"]
    )


def _model_from_spectrum(spectrum: dict[str, object]) -> dict[str, object]:
    return {
        "intercept": float(spectrum["grand_mean"]),
        "main_effects": {
            factor: float(spectrum["first_order_coefficients"][factor]) for factor in FACTORS
        },
    }


def _predict(model: dict[str, object], subset: frozenset[str]) -> float:
    value = float(model["intercept"])
    effects = model["main_effects"]
    for factor in FACTORS:
        value += float(effects[factor]) * (1.0 if factor in subset else -1.0)
    return float(value)


def _fit(
    phase12_path: Path,
    phase14_path: Path,
    phase17_fit_path: Path,
    phase21_final_path: Path,
    out: Path,
    git_sha: str,
) -> tuple[dict[str, object], dict[str, object]]:
    phase12_candidate = p21.p20.p17._validate_phase12(phase12_path)
    p21.p20.p17._validate_phase14_bridge(phase14_path)
    phase17_fit = p21.p20._validate_phase17_fit(phase17_fit_path)
    _validate_phase21_final(phase21_final_path)

    contexts = _build_cube(FIT_SEED, FIT_FAMILIES, "fit", phase12_candidate, phase17_fit)
    rmse_adv = p21.p20._advantage_map(contexts, "rmse")
    mae_adv = p21.p20._advantage_map(contexts, "mae")
    rmse_spectrum = p21._walsh_spectrum(rmse_adv)
    mae_spectrum = p21._walsh_spectrum(mae_adv)
    endpoint = _endpoint_summary(rmse_adv, mae_adv)

    rmse_model = _model_from_spectrum(rmse_spectrum)
    mae_model = _model_from_spectrum(mae_spectrum)
    finite_candidate = bool(
        np.isfinite(float(rmse_model["intercept"]))
        and np.isfinite(float(mae_model["intercept"]))
        and all(np.isfinite(float(v)) for v in rmse_model["main_effects"].values())
        and all(np.isfinite(float(v)) for v in mae_model["main_effects"].values())
    )
    direction = bool(
        all(float(v) < 0.0 for v in rmse_model["main_effects"].values())
        and all(float(v) < 0.0 for v in mae_model["main_effects"].values())
    )

    gates = {
        "f22_1_lineage_integrity": True,
        "f22_2_complete_matched_factorial_construction": _construction_pass(contexts),
        "f22_3_fit_endpoint_phenomenon_remains_present": _endpoint_phenomenon_pass(endpoint),
        "f22_4_first_order_fit_structure": bool(
            float(rmse_spectrum["first_order_variance_share"])
            >= THRESHOLDS["first_order_variance_share_min"]
            and float(mae_spectrum["first_order_variance_share"])
            >= THRESHOLDS["first_order_variance_share_min"]
        ),
        "f22_5_balanced_factor_direction": direction,
        "f22_6_finite_frozen_candidate": finite_candidate,
        "f22_7_static_latency_degradation_at_fit_endpoints": _static_level_pass(contexts),
        "f22_8_zero_adaptation_and_claim_boundary": True,
    }
    fit_pass = bool(all(gates.values()))

    fit_result = {
        "schema": f"{RESULT_SCHEMA_PREFIX}.fit-result.v1",
        "phase22_name": PHASE22_NAME,
        "stage": "fit",
        "evaluated_seed_seen_after_run": FIT_SEED,
        "families": list(FIT_FAMILIES),
        "scientific_git_sha": git_sha,
        "phase12_candidate_sha256": FROZEN_PHASE12_CANDIDATE_SHA256,
        "phase14_bridge_sha256": FROZEN_PHASE14_BRIDGE_SHA256,
        "phase17_fit_candidate_sha256": FROZEN_PHASE17_FIT_CANDIDATE_SHA256,
        "phase20_final_result_sha256": FROZEN_PHASE20_FINAL_RESULT_SHA256,
        "phase21_final_result_sha256": FROZEN_PHASE21_FINAL_RESULT_SHA256,
        "phase21_final_pass_preserved": True,
        "phase20_final_pass_preserved_via_phase21": True,
        "phase19_final_pass_preserved_via_phase21": True,
        "phase18_failure_preserved_via_phase21": True,
        "factor_order": list(FACTORS),
        "factorial_context_count": 32,
        "thresholds": THRESHOLDS,
        "contexts": contexts,
        "endpoint": endpoint,
        "rmse_walsh_spectrum": rmse_spectrum,
        "mae_walsh_spectrum": mae_spectrum,
        "candidate_models": {"rmse": rmse_model, "mae": mae_model},
        "gates": gates,
        "phase22_fit_pass": fit_pass,
        "q90_is_descriptive_only": True,
        "no_post_fit_refit": True,
        "interaction_terms_retained": False,
        "zero_adaptation": True,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "interpretation": "simulation-only fit of an additive approximation to a frozen synthetic five-factor context-response surface",
    }

    out.mkdir(parents=True, exist_ok=True)
    fit_result_path = out / "fit_result.json"
    fit_result_path.write_text(json.dumps(fit_result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    candidate = {
        "schema": f"{RESULT_SCHEMA_PREFIX}.fit-candidate.v1",
        "phase22_name": PHASE22_NAME,
        "fit_result_sha256": _sha256_file(fit_result_path),
        "fit_scientific_git_sha": git_sha,
        "fit_seed": FIT_SEED,
        "fit_families": list(FIT_FAMILIES),
        "phase12_candidate_sha256": FROZEN_PHASE12_CANDIDATE_SHA256,
        "phase14_bridge_sha256": FROZEN_PHASE14_BRIDGE_SHA256,
        "phase17_fit_candidate_sha256": FROZEN_PHASE17_FIT_CANDIDATE_SHA256,
        "phase20_final_result_sha256": FROZEN_PHASE20_FINAL_RESULT_SHA256,
        "phase21_final_result_sha256": FROZEN_PHASE21_FINAL_RESULT_SHA256,
        "factor_order": list(FACTORS),
        "models": {"rmse": rmse_model, "mae": mae_model},
        "fit_first_order_variance_share": {
            "rmse": float(rmse_spectrum["first_order_variance_share"]),
            "mae": float(mae_spectrum["first_order_variance_share"]),
        },
        "fit_endpoint": endpoint,
        "fit_eligible": fit_pass,
        "q90_is_descriptive_only": True,
        "no_post_fit_refit": True,
        "interaction_terms_retained": False,
        "zero_adaptation": True,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
    }
    (out / "fit_candidate.json").write_text(
        json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return fit_result, candidate


def _validate_fit_candidate(path: Path, expected_sha256: str) -> dict[str, object]:
    if _sha256_file(path) != expected_sha256:
        raise RuntimeError("Phase 22 confirmation requires the exact frozen fit candidate")
    candidate = json.loads(path.read_text(encoding="utf-8"))
    if candidate.get("schema") != f"{RESULT_SCHEMA_PREFIX}.fit-candidate.v1":
        raise RuntimeError("Phase 22 fit candidate schema mismatch")
    if candidate.get("fit_eligible") is not True:
        raise RuntimeError("Phase 22 fit candidate is not eligible")
    if candidate.get("factor_order") != list(FACTORS):
        raise RuntimeError("Phase 22 fit candidate factor order mismatch")
    if candidate.get("phase21_final_result_sha256") != FROZEN_PHASE21_FINAL_RESULT_SHA256:
        raise RuntimeError("Phase 22 fit candidate Phase 21 lineage mismatch")
    if candidate.get("phase20_final_result_sha256") != FROZEN_PHASE20_FINAL_RESULT_SHA256:
        raise RuntimeError("Phase 22 fit candidate Phase 20 lineage mismatch")
    required_true = (
        "q90_is_descriptive_only",
        "no_post_fit_refit",
        "zero_adaptation",
        "simulation_only",
    )
    for field in required_true:
        if candidate.get(field) is not True:
            raise RuntimeError(f"Phase 22 fit candidate requires {field}=true")
    if candidate.get("interaction_terms_retained") is not False:
        raise RuntimeError("Phase 22 candidate may not retain interaction terms")
    if candidate.get("safety_acceptance") is not False or candidate.get("controller_tuning_allowed") is not False:
        raise RuntimeError("Phase 22 fit candidate claim boundary mismatch")
    return candidate


def _prediction_metrics(
    observed: dict[frozenset[str], float],
    model: dict[str, object],
) -> dict[str, object]:
    subsets = p21.p20._all_subsets()
    y = np.asarray([float(observed[s]) for s in subsets], dtype=float)
    pred = np.asarray([_predict(model, s) for s in subsets], dtype=float)
    if not np.all(np.isfinite(y)) or not np.all(np.isfinite(pred)):
        raise RuntimeError("Phase 22 requires finite observed and predicted advantages")

    centered = y - float(np.mean(y))
    sst = float(np.sum(np.square(centered)))
    sse = float(np.sum(np.square(y - pred)))
    if sst <= 0.0:
        raise RuntimeError("Phase 22 requires positive fresh response-surface variance")
    r2 = float(1.0 - sse / sst)
    prediction_mae = float(np.mean(np.abs(y - pred)))
    prediction_rmse = float(np.sqrt(np.mean(np.square(y - pred))))

    margin = THRESHOLDS["stable_sign_margin"]
    eligible = np.abs(y) >= margin
    eligible_count = int(np.sum(eligible))
    sign_accuracy = (
        float(np.mean(np.sign(y[eligible]) == np.sign(pred[eligible])))
        if eligible_count
        else float("nan")
    )

    empty = frozenset()
    full = frozenset(FACTORS)
    obs_attenuation = float(observed[empty] - observed[full])
    pred_attenuation = float(_predict(model, empty) - _predict(model, full))

    return {
        "r2": r2,
        "prediction_advantage_mae": prediction_mae,
        "prediction_advantage_rmse": prediction_rmse,
        "eligible_stable_sign_cells": eligible_count,
        "stable_sign_accuracy": sign_accuracy,
        "observed_simple_advantage": float(observed[empty]),
        "observed_hard_advantage": float(observed[full]),
        "observed_attenuation": obs_attenuation,
        "predicted_simple_advantage": float(_predict(model, empty)),
        "predicted_hard_advantage": float(_predict(model, full)),
        "predicted_attenuation": pred_attenuation,
        "attenuation_abs_error": float(abs(obs_attenuation - pred_attenuation)),
        "predictions": {
            p21.p20._subset_key(s): float(_predict(model, s)) for s in subsets
        },
    }


def _confirm(
    stage: str,
    phase12_path: Path,
    phase14_path: Path,
    phase17_fit_path: Path,
    phase21_final_path: Path,
    fit_candidate_path: Path,
    expected_fit_sha256: str,
    git_sha: str,
) -> dict[str, object]:
    phase12_candidate = p21.p20.p17._validate_phase12(phase12_path)
    p21.p20.p17._validate_phase14_bridge(phase14_path)
    phase17_fit = p21.p20._validate_phase17_fit(phase17_fit_path)
    _validate_phase21_final(phase21_final_path)
    fit_candidate = _validate_fit_candidate(fit_candidate_path, expected_fit_sha256)

    seed = STAGE_SEEDS[stage]
    families = STAGE_FAMILIES[stage]
    contexts = _build_cube(seed, families, stage, phase12_candidate, phase17_fit)
    rmse_adv = p21.p20._advantage_map(contexts, "rmse")
    mae_adv = p21.p20._advantage_map(contexts, "mae")
    endpoint = _endpoint_summary(rmse_adv, mae_adv)

    rmse_metrics = _prediction_metrics(rmse_adv, fit_candidate["models"]["rmse"])
    mae_metrics = _prediction_metrics(mae_adv, fit_candidate["models"]["mae"])

    gates = {
        "p22_1_lineage_and_frozen_candidate_integrity": True,
        "p22_2_complete_fresh_matched_construction": _construction_pass(contexts),
        "p22_3_rmse_cellwise_predictive_transfer": bool(
            float(rmse_metrics["r2"]) >= THRESHOLDS["prediction_r2_min"]
        ),
        "p22_4_rmse_absolute_prediction_error": bool(
            float(rmse_metrics["prediction_advantage_mae"])
            <= THRESHOLDS["prediction_advantage_mae_max"]
        ),
        "p22_5_mae_cellwise_predictive_transfer": bool(
            float(mae_metrics["r2"]) >= THRESHOLDS["prediction_r2_min"]
        ),
        "p22_6_mae_absolute_prediction_error": bool(
            float(mae_metrics["prediction_advantage_mae"])
            <= THRESHOLDS["prediction_advantage_mae_max"]
        ),
        "p22_7_stable_sign_transfer": bool(
            int(rmse_metrics["eligible_stable_sign_cells"]) >= THRESHOLDS["stable_sign_min_cells"]
            and int(mae_metrics["eligible_stable_sign_cells"]) >= THRESHOLDS["stable_sign_min_cells"]
            and float(rmse_metrics["stable_sign_accuracy"]) >= THRESHOLDS["stable_sign_accuracy_min"]
            and float(mae_metrics["stable_sign_accuracy"]) >= THRESHOLDS["stable_sign_accuracy_min"]
        ),
        "p22_8_endpoint_phenomenon_and_attenuation_transfer": bool(
            _endpoint_phenomenon_pass(endpoint)
            and float(rmse_metrics["attenuation_abs_error"])
            <= THRESHOLDS["attenuation_abs_error_max"]
            and float(mae_metrics["attenuation_abs_error"])
            <= THRESHOLDS["attenuation_abs_error_max"]
        ),
        "p22_9_static_latency_degradation_at_fresh_endpoints": _static_level_pass(contexts),
        "p22_10_zero_adaptation_and_claim_boundary": True,
    }

    return {
        "schema": f"{RESULT_SCHEMA_PREFIX}.{stage}-result.v1",
        "phase22_name": PHASE22_NAME,
        "stage": stage,
        "evaluated_seed_seen_after_run": seed,
        "families": list(families),
        "scientific_git_sha": git_sha,
        "phase12_candidate_sha256": FROZEN_PHASE12_CANDIDATE_SHA256,
        "phase14_bridge_sha256": FROZEN_PHASE14_BRIDGE_SHA256,
        "phase17_fit_candidate_sha256": FROZEN_PHASE17_FIT_CANDIDATE_SHA256,
        "phase20_final_result_sha256": FROZEN_PHASE20_FINAL_RESULT_SHA256,
        "phase21_final_result_sha256": FROZEN_PHASE21_FINAL_RESULT_SHA256,
        "phase22_fit_candidate_sha256": expected_fit_sha256,
        "phase21_final_pass_preserved": True,
        "phase20_final_pass_preserved_via_phase21": True,
        "phase19_final_pass_preserved_via_phase21": True,
        "phase18_failure_preserved_via_phase21": True,
        "factor_order": list(FACTORS),
        "factorial_context_count": 32,
        "thresholds": THRESHOLDS,
        "contexts": contexts,
        "endpoint": endpoint,
        "rmse_prediction": rmse_metrics,
        "mae_prediction": mae_metrics,
        "gates": gates,
        "phase22_pass": bool(all(gates.values())),
        "q90_is_descriptive_only": True,
        "no_refit": True,
        "interaction_terms_retained": False,
        "zero_adaptation": True,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "interpretation": "simulation-only predictive transfer of a frozen additive approximation across fresh synthetic context cubes",
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=PHASE22_NAME)
    p.add_argument("--stage", choices=("fit", "dev", "transfer", "validation", "final"), required=True)
    p.add_argument("--phase12-candidate", type=Path, required=True)
    p.add_argument("--phase14-bridge", type=Path, required=True)
    p.add_argument("--phase17-fit-candidate", type=Path, required=True)
    p.add_argument("--phase21-final-result", type=Path, required=True)
    p.add_argument("--fit-candidate", type=Path)
    p.add_argument("--expected-fit-sha256")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--git-sha", required=True)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.stage == "fit":
        fit_result, candidate = _fit(
            args.phase12_candidate,
            args.phase14_bridge,
            args.phase17_fit_candidate,
            args.phase21_final_result,
            args.out,
            args.git_sha,
        )
        print("PHASE22_FIT_RESULT_SHA256=" + _sha256_file(args.out / "fit_result.json"))
        print("PHASE22_FIT_CANDIDATE_SHA256=" + _sha256_file(args.out / "fit_candidate.json"))
        print("PHASE22_FIT_PASS=" + str(bool(fit_result["phase22_fit_pass"])).lower())
        print(json.dumps(fit_result["gates"], sort_keys=True))
        print(json.dumps(candidate["models"], sort_keys=True))
        return

    if args.fit_candidate is None or not args.expected_fit_sha256:
        raise RuntimeError("post-fit Phase 22 stages require --fit-candidate and --expected-fit-sha256")
    result = _confirm(
        args.stage,
        args.phase12_candidate,
        args.phase14_bridge,
        args.phase17_fit_candidate,
        args.phase21_final_result,
        args.fit_candidate,
        args.expected_fit_sha256,
        args.git_sha,
    )
    path = args.out / f"{args.stage}_result.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PHASE22_{args.stage.upper()}_RESULT_SHA256=" + _sha256_file(path))
    print(f"PHASE22_{args.stage.upper()}_PASS=" + str(bool(result["phase22_pass"])).lower())
    print(json.dumps(result["gates"], sort_keys=True))
    print(json.dumps(result["rmse_prediction"], sort_keys=True))
    print(json.dumps(result["mae_prediction"], sort_keys=True))


if __name__ == "__main__":
    main()
