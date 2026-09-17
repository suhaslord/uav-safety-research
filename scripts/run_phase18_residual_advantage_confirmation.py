from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

import numpy as np

try:
    from scripts import run_phase14_uncertainty_recoverability_bridge as p14
    from scripts import run_phase17_context_conditional_coefficient_mismatch as p17
except ModuleNotFoundError:
    import run_phase14_uncertainty_recoverability_bridge as p14
    import run_phase17_context_conditional_coefficient_mismatch as p17

PHASE18_NAME = "Residual Advantage Confirmation"
RESULT_SCHEMA_PREFIX = "aegisland.phase18.residual-advantage-confirmation"

FROZEN_PHASE12_CANDIDATE_SHA256 = p17.FROZEN_PHASE12_CANDIDATE_SHA256
FROZEN_PHASE14_BRIDGE_SHA256 = p17.FROZEN_PHASE14_BRIDGE_SHA256
FROZEN_PHASE17_FIT_CANDIDATE_SHA256 = "2ca52a418f5616e0e83ef84d0c9238ee429260cd4de7a553356b0c1bba44d8e0"
PHASE17_RECORDED_RESULT_SHA256 = "24aeed60003b3111c9d3dd24cee992f8bac539531d38923b9a205a1423e8d029"

STAGE_SEEDS = {
    "dev": 1818181,
    "transfer": 1818182,
    "validation": 1818183,
    "final": 1818184,
}
STAGE_FAMILIES = {
    "dev": tuple(range(1929, 1953)),
    "transfer": tuple(range(1953, 1977)),
    "validation": tuple(range(1977, 2001)),
    "final": tuple(range(2001, 2025)),
}

THRESHOLDS = {
    "minimum_matched_transitions": 500,
    "simple_latencyfit_over_phase14_q90_max": 0.90,
    "simple_latencyfit_over_controlfit_q90_max": 0.95,
    "hard_latencyfit_over_phase14_q90_min": 0.90,
    "hard_latencyfit_over_phase14_q90_max": 1.10,
    "q90_improvement_gap_min": 0.08,
    "simple_latencyfit_over_phase14_rmse_max": 0.95,
    "hard_latencyfit_over_phase14_rmse_min": 0.90,
    "hard_latencyfit_over_phase14_rmse_max": 1.10,
    "rmse_improvement_gap_min": 0.05,
    "simple_p95_error_inflation_min": 1.10,
    "simple_coverage_delta_max": -0.01,
    "hard_p95_error_inflation_min": 1.10,
    "hard_coverage_delta_max": -0.05,
}


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _validate_fit_candidate(path: Path) -> dict[str, object]:
    if _sha256_file(path) != FROZEN_PHASE17_FIT_CANDIDATE_SHA256:
        raise RuntimeError("Phase 18 requires the exact frozen Phase 17 fit candidate")
    fit = p17._validate_fit_candidate(path)
    if fit.get("fit_eligible_for_development") is not True:
        raise RuntimeError("Phase 18 requires the exact Phase 17 fit candidate that passed fit eligibility")
    return fit


def _context_result(
    control,
    latency,
    phase12_candidate: dict[str, object],
    fit: dict[str, object],
    context: str,
) -> dict[str, object]:
    integrity = p17._integrity_and_width_identity(control, latency, phase12_candidate)
    matched = p17._matched_transitions(control, latency, phase12_candidate)
    control_static = p17._static_metrics(control, phase12_candidate)
    latency_static = p17._static_metrics(latency, phase12_candidate)
    diagnostics = p17._fit_context_coefficients(matched)

    e0 = matched["latency_e0_lateral_m"].to_numpy(float)
    e1 = matched["latency_e1_lateral_m"].to_numpy(float)
    phase14_a = float(fit["phase14_lateral_a"])
    control_a = float(fit["contexts"][context]["coefficients"]["control"]["lateral"]["a"])
    latency_a = float(fit["contexts"][context]["coefficients"]["latency"]["lateral"]["a"])

    r14 = p17._residual_metrics(e0, e1, phase14_a)
    rc = p17._residual_metrics(e0, e1, control_a)
    rl = p17._residual_metrics(e0, e1, latency_a)

    q90_ratio_14 = float(rl["q90_abs_residual_m"] / r14["q90_abs_residual_m"])
    q90_ratio_control = float(rl["q90_abs_residual_m"] / rc["q90_abs_residual_m"])
    rmse_ratio_14 = float(rl["rmse_signed_residual_m"] / r14["rmse_signed_residual_m"])

    paired = {
        "p95_error_inflation": float(
            latency_static["lateral"]["p95_abs_error_m"]
            / control_static["lateral"]["p95_abs_error_m"]
        ),
        "coverage_delta": float(
            latency_static["lateral"]["coverage95"]
            - control_static["lateral"]["coverage95"]
        ),
        "median_error_inflation": float(
            latency_static["lateral"]["median_abs_error_m"]
            / control_static["lateral"]["median_abs_error_m"]
        ),
    }

    return {
        "base_domain": p17.CONTEXTS[context],
        "integrity": integrity,
        "matched_transitions": int(len(matched)),
        "control": control_static,
        "latency": latency_static,
        "development_diagnostic_coefficients_descriptive_only": diagnostics,
        "frozen_coefficients": {
            "phase14_lateral_a": phase14_a,
            "phase17_control_lateral_a": control_a,
            "phase17_latency_lateral_a": latency_a,
        },
        "latency_lateral_residuals": {
            "phase14": r14,
            "phase17_control_fit": rc,
            "phase17_latency_fit": rl,
            "latencyfit_over_phase14_q90": q90_ratio_14,
            "latencyfit_over_controlfit_q90": q90_ratio_control,
            "latencyfit_over_phase14_rmse": rmse_ratio_14,
            "q90_relative_improvement_vs_phase14": 1.0 - q90_ratio_14,
            "rmse_relative_improvement_vs_phase14": 1.0 - rmse_ratio_14,
        },
        "paired_lateral_effects": paired,
    }


def _gates(contexts: dict[str, dict[str, object]]) -> dict[str, bool]:
    s = contexts["simple"]
    h = contexts["hard"]

    construction = all(
        bool(c["integrity"]["pass"])
        and bool(c["integrity"]["width_identity_pass"])
        and int(c["matched_transitions"]) >= THRESHOLDS["minimum_matched_transitions"]
        for c in contexts.values()
    )

    s_q14 = float(s["latency_lateral_residuals"]["latencyfit_over_phase14_q90"])
    s_qc = float(s["latency_lateral_residuals"]["latencyfit_over_controlfit_q90"])
    h_q14 = float(h["latency_lateral_residuals"]["latencyfit_over_phase14_q90"])
    s_iq = float(s["latency_lateral_residuals"]["q90_relative_improvement_vs_phase14"])
    h_iq = float(h["latency_lateral_residuals"]["q90_relative_improvement_vs_phase14"])

    s_r14 = float(s["latency_lateral_residuals"]["latencyfit_over_phase14_rmse"])
    h_r14 = float(h["latency_lateral_residuals"]["latencyfit_over_phase14_rmse"])
    s_ir = float(s["latency_lateral_residuals"]["rmse_relative_improvement_vs_phase14"])
    h_ir = float(h["latency_lateral_residuals"]["rmse_relative_improvement_vs_phase14"])

    level = bool(
        float(s["paired_lateral_effects"]["p95_error_inflation"])
        >= THRESHOLDS["simple_p95_error_inflation_min"]
        and float(s["paired_lateral_effects"]["coverage_delta"])
        <= THRESHOLDS["simple_coverage_delta_max"]
        and float(h["paired_lateral_effects"]["p95_error_inflation"])
        >= THRESHOLDS["hard_p95_error_inflation_min"]
        and float(h["paired_lateral_effects"]["coverage_delta"])
        <= THRESHOLDS["hard_coverage_delta_max"]
    )

    return {
        "r18_1_lineage_integrity": True,
        "r18_2_matched_construction_and_width_identity": construction,
        "r18_3_simple_q90_advantage_vs_phase14": bool(
            s_q14 <= THRESHOLDS["simple_latencyfit_over_phase14_q90_max"]
        ),
        "r18_4_simple_q90_advantage_vs_control_fit": bool(
            s_qc <= THRESHOLDS["simple_latencyfit_over_controlfit_q90_max"]
        ),
        "r18_5_hard_q90_advantage_remains_limited": bool(
            h_q14 >= THRESHOLDS["hard_latencyfit_over_phase14_q90_min"]
            and h_q14 <= THRESHOLDS["hard_latencyfit_over_phase14_q90_max"]
        ),
        "r18_6_simple_vs_hard_q90_improvement_gap": bool(
            s_iq - h_iq >= THRESHOLDS["q90_improvement_gap_min"]
        ),
        "r18_7_independent_rmse_confirmation": bool(
            s_r14 <= THRESHOLDS["simple_latencyfit_over_phase14_rmse_max"]
            and h_r14 >= THRESHOLDS["hard_latencyfit_over_phase14_rmse_min"]
            and h_r14 <= THRESHOLDS["hard_latencyfit_over_phase14_rmse_max"]
            and s_ir - h_ir >= THRESHOLDS["rmse_improvement_gap_min"]
        ),
        "r18_8_static_latency_degradation_remains_present": level,
        "r18_9_cross_statistic_context_ordering": bool(s_iq > h_iq and s_ir > h_ir),
        "r18_10_zero_adaptation_and_claim_boundary": True,
    }


def evaluate(
    stage: str,
    phase12_candidate_path: Path,
    phase14_bridge_path: Path,
    phase17_fit_candidate_path: Path,
    phase17_result_path: Path,
    scientific_git_sha: str,
) -> dict[str, object]:
    phase12 = p17._validate_phase12(phase12_candidate_path)
    p17._validate_phase14_bridge(phase14_bridge_path)
    fit = _validate_fit_candidate(phase17_fit_candidate_path)

    if _sha256_file(phase17_result_path) != PHASE17_RECORDED_RESULT_SHA256:
        raise RuntimeError("Phase 18 requires the exact recorded Phase 17 development result")
    phase17_result = json.loads(phase17_result_path.read_text(encoding="utf-8"))
    if phase17_result.get("phase17_pass") is not False:
        raise RuntimeError("Phase 18 requires Phase 17 to remain recorded as FAIL")

    seed = STAGE_SEEDS[stage]
    families = STAGE_FAMILIES[stage]
    contexts: dict[str, dict[str, object]] = {}
    for context in p17.CONTEXTS:
        control, latency = p17._generate_context(seed, families, stage, context, phase12)
        contexts[context] = _context_result(control, latency, phase12, fit, context)

    gates = _gates(contexts)
    return {
        "schema": f"{RESULT_SCHEMA_PREFIX}.{stage}-result.v1",
        "phase18_name": PHASE18_NAME,
        "stage": stage,
        "evaluated_seed_seen_after_run": seed,
        "families": list(families),
        "scientific_git_sha": scientific_git_sha,
        "phase12_candidate_sha256": FROZEN_PHASE12_CANDIDATE_SHA256,
        "phase14_bridge_sha256": FROZEN_PHASE14_BRIDGE_SHA256,
        "phase17_fit_candidate_sha256": FROZEN_PHASE17_FIT_CANDIDATE_SHA256,
        "phase17_recorded_result_sha256": PHASE17_RECORDED_RESULT_SHA256,
        "phase17_failure_preserved": True,
        "latency_intervention": fit["latency_intervention"],
        "thresholds": THRESHOLDS,
        "contexts": contexts,
        "gates": gates,
        "phase18_pass": bool(all(gates.values())),
        "no_refit": True,
        "zero_adaptation": True,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "interpretation": "simulation-only frozen-coefficient residual-advantage confirmation; not physical latency causality or a safety proof",
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=PHASE18_NAME)
    p.add_argument("--stage", choices=("dev", "transfer", "validation", "final"), required=True)
    p.add_argument("--phase12-candidate", type=Path, required=True)
    p.add_argument("--phase14-bridge", type=Path, required=True)
    p.add_argument("--phase17-fit-candidate", type=Path, required=True)
    p.add_argument("--phase17-result", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--git-sha", required=True)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    result = evaluate(
        args.stage,
        args.phase12_candidate,
        args.phase14_bridge,
        args.phase17_fit_candidate,
        args.phase17_result,
        args.git_sha,
    )
    result_path = args.out / f"{args.stage}_result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PHASE18_{args.stage.upper()}_RESULT_SHA256=" + _sha256_file(result_path))
    print(f"PHASE18_{args.stage.upper()}_PASS=" + str(bool(result["phase18_pass"])).lower())
    print(json.dumps(result["gates"], sort_keys=True))
    print(json.dumps(result["contexts"], sort_keys=True))


if __name__ == "__main__":
    main()
