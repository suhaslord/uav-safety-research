from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

import numpy as np

try:
    from scripts import run_phase17_context_conditional_coefficient_mismatch as p17
except ModuleNotFoundError:
    import run_phase17_context_conditional_coefficient_mismatch as p17

PHASE19_NAME = "Distribution-Wide Residual Advantage"
RESULT_SCHEMA_PREFIX = "aegisland.phase19.distribution-wide-residual-advantage"
FROZEN_PHASE12_CANDIDATE_SHA256 = p17.FROZEN_PHASE12_CANDIDATE_SHA256
FROZEN_PHASE14_BRIDGE_SHA256 = p17.FROZEN_PHASE14_BRIDGE_SHA256
FROZEN_PHASE17_FIT_CANDIDATE_SHA256 = "2ca52a418f5616e0e83ef84d0c9238ee429260cd4de7a553356b0c1bba44d8e0"
FROZEN_PHASE18_VALIDATION_RESULT_SHA256 = "ad96ca1a5119fcd594a84fd72a04f8efcc377ba788383d90dda9ef7eecad4431"

STAGE_SEEDS = {"dev": 1919191, "transfer": 1919192, "validation": 1919193, "final": 1919194}
STAGE_FAMILIES = {
    "dev": tuple(range(2025, 2049)),
    "transfer": tuple(range(2049, 2073)),
    "validation": tuple(range(2073, 2097)),
    "final": tuple(range(2097, 2121)),
}
THRESHOLDS = {
    "minimum_matched_transitions": 500,
    "simple_rmse_ratio_max": 0.95,
    "hard_rmse_ratio_min": 0.90,
    "hard_rmse_ratio_max": 1.10,
    "rmse_improvement_gap_min": 0.05,
    "simple_mae_ratio_max": 0.95,
    "hard_mae_ratio_min": 0.90,
    "hard_mae_ratio_max": 1.10,
    "mae_improvement_gap_min": 0.05,
    "simple_p95_error_inflation_min": 1.10,
    "simple_coverage_delta_max": -0.01,
    "hard_p95_error_inflation_min": 1.10,
    "hard_coverage_delta_max": -0.05,
}


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _validate_phase17_fit(path: Path) -> dict[str, object]:
    if _sha256_file(path) != FROZEN_PHASE17_FIT_CANDIDATE_SHA256:
        raise RuntimeError("Phase 19 requires the exact frozen Phase 17 fit candidate")
    return p17._validate_fit_candidate(path)


def _residual_metrics(e0: np.ndarray, e1: np.ndarray, a: float) -> dict[str, float]:
    signed = np.asarray(e1, dtype=float) - float(a) * np.asarray(e0, dtype=float)
    absolute = np.abs(signed)
    return {
        "a": float(a),
        "rmse_signed_residual_m": float(np.sqrt(np.mean(np.square(signed)))),
        "mae_abs_residual_m": float(np.mean(absolute)),
        "median_abs_residual_m": float(np.median(absolute)),
        "q90_abs_residual_m_descriptive": p17.p14._finite_upper_quantile(absolute, 0.90),
    }


def _context(control, latency, phase12: dict[str, object], fit: dict[str, object], context: str) -> dict[str, object]:
    integrity = p17._integrity_and_width_identity(control, latency, phase12)
    matched = p17._matched_transitions(control, latency, phase12)
    control_static = p17._static_metrics(control, phase12)
    latency_static = p17._static_metrics(latency, phase12)
    diagnostics = p17._fit_context_coefficients(matched)

    e0 = matched["latency_e0_lateral_m"].to_numpy(float)
    e1 = matched["latency_e1_lateral_m"].to_numpy(float)
    a14 = float(fit["phase14_lateral_a"])
    ac = float(fit["contexts"][context]["coefficients"]["control"]["lateral"]["a"])
    al = float(fit["contexts"][context]["coefficients"]["latency"]["lateral"]["a"])
    r14 = _residual_metrics(e0, e1, a14)
    rc = _residual_metrics(e0, e1, ac)
    rl = _residual_metrics(e0, e1, al)

    rmse_ratio = float(rl["rmse_signed_residual_m"] / r14["rmse_signed_residual_m"])
    mae_ratio = float(rl["mae_abs_residual_m"] / r14["mae_abs_residual_m"])
    q90_ratio = float(rl["q90_abs_residual_m_descriptive"] / r14["q90_abs_residual_m_descriptive"])

    return {
        "base_domain": p17.CONTEXTS[context],
        "integrity": integrity,
        "matched_transitions": int(len(matched)),
        "control": control_static,
        "latency": latency_static,
        "diagnostic_coefficients_descriptive_only": diagnostics,
        "frozen_coefficients": {"phase14_lateral_a": a14, "phase17_control_lateral_a": ac, "phase17_latency_lateral_a": al},
        "latency_lateral_residuals": {
            "phase14": r14,
            "phase17_control_fit": rc,
            "phase17_latency_fit": rl,
            "latencyfit_over_phase14_rmse": rmse_ratio,
            "latencyfit_over_phase14_mae": mae_ratio,
            "latencyfit_over_phase14_q90_descriptive": q90_ratio,
            "rmse_relative_improvement_vs_phase14": 1.0 - rmse_ratio,
            "mae_relative_improvement_vs_phase14": 1.0 - mae_ratio,
        },
        "paired_lateral_effects": {
            "p95_error_inflation": float(latency_static["lateral"]["p95_abs_error_m"] / control_static["lateral"]["p95_abs_error_m"]),
            "coverage_delta": float(latency_static["lateral"]["coverage95"] - control_static["lateral"]["coverage95"]),
            "median_error_inflation": float(latency_static["lateral"]["median_abs_error_m"] / control_static["lateral"]["median_abs_error_m"]),
        },
    }


def _gates(contexts: dict[str, dict[str, object]]) -> dict[str, bool]:
    s, h = contexts["simple"], contexts["hard"]
    construction = all(
        bool(c["integrity"]["pass"])
        and bool(c["integrity"]["width_identity_pass"])
        and int(c["matched_transitions"]) >= THRESHOLDS["minimum_matched_transitions"]
        for c in contexts.values()
    )
    sr = float(s["latency_lateral_residuals"]["latencyfit_over_phase14_rmse"])
    hr = float(h["latency_lateral_residuals"]["latencyfit_over_phase14_rmse"])
    sm = float(s["latency_lateral_residuals"]["latencyfit_over_phase14_mae"])
    hm = float(h["latency_lateral_residuals"]["latencyfit_over_phase14_mae"])
    sir = 1.0 - sr; hir = 1.0 - hr; sim = 1.0 - sm; him = 1.0 - hm
    level = bool(
        float(s["paired_lateral_effects"]["p95_error_inflation"]) >= THRESHOLDS["simple_p95_error_inflation_min"]
        and float(s["paired_lateral_effects"]["coverage_delta"]) <= THRESHOLDS["simple_coverage_delta_max"]
        and float(h["paired_lateral_effects"]["p95_error_inflation"]) >= THRESHOLDS["hard_p95_error_inflation_min"]
        and float(h["paired_lateral_effects"]["coverage_delta"]) <= THRESHOLDS["hard_coverage_delta_max"]
    )
    return {
        "d19_1_lineage_integrity": True,
        "d19_2_matched_construction_and_width_identity": construction,
        "d19_3_simple_context_rmse_advantage": sr <= THRESHOLDS["simple_rmse_ratio_max"],
        "d19_4_hard_context_rmse_neutrality": THRESHOLDS["hard_rmse_ratio_min"] <= hr <= THRESHOLDS["hard_rmse_ratio_max"],
        "d19_5_rmse_context_advantage_gap": sir - hir >= THRESHOLDS["rmse_improvement_gap_min"],
        "d19_6_simple_context_mae_advantage": sm <= THRESHOLDS["simple_mae_ratio_max"],
        "d19_7_hard_context_mae_neutrality": THRESHOLDS["hard_mae_ratio_min"] <= hm <= THRESHOLDS["hard_mae_ratio_max"],
        "d19_8_mae_context_advantage_gap": sim - him >= THRESHOLDS["mae_improvement_gap_min"],
        "d19_9_static_latency_degradation_remains_present": level,
        "d19_10_zero_adaptation_and_claim_boundary": True,
    }


def evaluate(stage: str, phase12_path: Path, phase14_path: Path, phase17_fit_path: Path, phase18_validation_path: Path, git_sha: str) -> dict[str, object]:
    phase12 = p17._validate_phase12(phase12_path)
    p17._validate_phase14_bridge(phase14_path)
    fit = _validate_phase17_fit(phase17_fit_path)
    if _sha256_file(phase18_validation_path) != FROZEN_PHASE18_VALIDATION_RESULT_SHA256:
        raise RuntimeError("Phase 19 requires the exact failed Phase 18 protected result")
    p18 = json.loads(phase18_validation_path.read_text(encoding="utf-8"))
    if p18.get("phase18_pass") is not False:
        raise RuntimeError("Phase 19 requires Phase 18 to remain recorded as FAIL")

    seed, families = STAGE_SEEDS[stage], STAGE_FAMILIES[stage]
    contexts: dict[str, dict[str, object]] = {}
    for context in p17.CONTEXTS:
        control, latency = p17._generate_context(seed, families, stage, context, phase12)
        contexts[context] = _context(control, latency, phase12, fit, context)
    gates = _gates(contexts)
    return {
        "schema": f"{RESULT_SCHEMA_PREFIX}.{stage}-result.v1",
        "phase19_name": PHASE19_NAME,
        "stage": stage,
        "evaluated_seed_seen_after_run": seed,
        "families": list(families),
        "scientific_git_sha": git_sha,
        "phase12_candidate_sha256": FROZEN_PHASE12_CANDIDATE_SHA256,
        "phase14_bridge_sha256": FROZEN_PHASE14_BRIDGE_SHA256,
        "phase17_fit_candidate_sha256": FROZEN_PHASE17_FIT_CANDIDATE_SHA256,
        "phase18_validation_result_sha256": FROZEN_PHASE18_VALIDATION_RESULT_SHA256,
        "phase18_failure_preserved": True,
        "thresholds": THRESHOLDS,
        "contexts": contexts,
        "gates": gates,
        "phase19_pass": bool(all(gates.values())),
        "q90_is_descriptive_only": True,
        "no_refit": True,
        "zero_adaptation": True,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "interpretation": "simulation-only distribution-wide residual advantage confirmation; not a physical latency or safety claim",
    }


def parse_args() -> argparse.Namespace:
    p=argparse.ArgumentParser(description=PHASE19_NAME)
    p.add_argument("--stage",choices=("dev","transfer","validation","final"),required=True)
    p.add_argument("--phase12-candidate",type=Path,required=True)
    p.add_argument("--phase14-bridge",type=Path,required=True)
    p.add_argument("--phase17-fit-candidate",type=Path,required=True)
    p.add_argument("--phase18-validation-result",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--git-sha",required=True)
    return p.parse_args()


def main() -> None:
    args=parse_args(); args.out.mkdir(parents=True,exist_ok=True)
    r=evaluate(args.stage,args.phase12_candidate,args.phase14_bridge,args.phase17_fit_candidate,args.phase18_validation_result,args.git_sha)
    p=args.out/f"{args.stage}_result.json"; p.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(f"PHASE19_{args.stage.upper()}_RESULT_SHA256="+_sha256_file(p))
    print(f"PHASE19_{args.stage.upper()}_PASS="+str(bool(r["phase19_pass"])).lower())
    print(json.dumps(r["gates"],sort_keys=True)); print(json.dumps(r["contexts"],sort_keys=True))

if __name__=="__main__": main()
