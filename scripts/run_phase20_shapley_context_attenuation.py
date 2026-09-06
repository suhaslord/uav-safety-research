from __future__ import annotations

import argparse
import itertools
import json
import math
from hashlib import sha256
from pathlib import Path

import numpy as np

try:
    from scripts import run_phase17_context_conditional_coefficient_mismatch as p17
except ModuleNotFoundError:
    import run_phase17_context_conditional_coefficient_mismatch as p17

PHASE20_NAME = "Five-Factor Context Attenuation Shapley Decomposition"
RESULT_SCHEMA_PREFIX = "aegisland.phase20.shapley-context-attenuation"

FROZEN_PHASE12_CANDIDATE_SHA256 = p17.FROZEN_PHASE12_CANDIDATE_SHA256
FROZEN_PHASE14_BRIDGE_SHA256 = p17.FROZEN_PHASE14_BRIDGE_SHA256
FROZEN_PHASE17_FIT_CANDIDATE_SHA256 = "2ca52a418f5616e0e83ef84d0c9238ee429260cd4de7a553356b0c1bba44d8e0"
FROZEN_PHASE19_FINAL_RESULT_SHA256 = "8c23b9b9c8c9fb2f9146bf739e52074f8709d2fe9a81c794e64fb43f360acebf"

FACTORS = ("edge", "oblique", "dim", "blur_noise", "low_contrast")
CANONICAL_TOKENS = ("edge", "small_scale", "oblique", "dim", "blur_noise", "low_contrast", "temporal_dropout")
SIMPLE_DOMAIN = "small_scale+temporal_dropout"
HARD_DOMAIN = "edge+small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout"

STAGE_SEEDS = {
    "dev": 2020201,
    "transfer": 2020202,
    "validation": 2020203,
    "final": 2020204,
}
STAGE_FAMILIES = {
    "dev": tuple(range(2121, 2145)),
    "transfer": tuple(range(2145, 2169)),
    "validation": tuple(range(2169, 2193)),
    "final": tuple(range(2193, 2217)),
}

THRESHOLDS = {
    "minimum_matched_transitions": 500,
    "simple_rmse_advantage_min": 0.05,
    "rmse_endpoint_attenuation_min": 0.08,
    "simple_mae_advantage_min": 0.08,
    "mae_endpoint_attenuation_min": 0.08,
    "shapley_efficiency_abs_tolerance": 1.0e-12,
    "simple_p95_error_inflation_min": 1.10,
    "simple_coverage_delta_max": -0.01,
    "hard_p95_error_inflation_min": 1.10,
    "hard_coverage_delta_max": -0.05,
}


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _validate_phase17_fit(path: Path) -> dict[str, object]:
    if _sha256_file(path) != FROZEN_PHASE17_FIT_CANDIDATE_SHA256:
        raise RuntimeError("Phase 20 requires exact frozen Phase 17 fit candidate")
    return p17._validate_fit_candidate(path)


def _validate_phase19_final(path: Path) -> dict[str, object]:
    if _sha256_file(path) != FROZEN_PHASE19_FINAL_RESULT_SHA256:
        raise RuntimeError("Phase 20 requires exact frozen Phase 19 final result")
    result = json.loads(path.read_text(encoding="utf-8"))
    if result.get("phase19_pass") is not True:
        raise RuntimeError("Phase 20 requires Phase 19 final PASS")
    if result.get("phase18_failure_preserved") is not True:
        raise RuntimeError("Phase 20 requires Phase 18 failure to remain preserved")
    if result.get("q90_is_descriptive_only") is not True:
        raise RuntimeError("Phase 20 requires Phase 19 q90 boundary to remain descriptive-only")
    return result


def _all_subsets() -> tuple[frozenset[str], ...]:
    out: list[frozenset[str]] = []
    for size in range(len(FACTORS) + 1):
        for combo in itertools.combinations(FACTORS, size):
            out.append(frozenset(combo))
    return tuple(out)


def _subset_key(subset: frozenset[str]) -> str:
    if not subset:
        return "none"
    return "+".join(f for f in FACTORS if f in subset)


def _domain_from_subset(subset: frozenset[str]) -> str:
    unknown = set(subset).difference(FACTORS)
    if unknown:
        raise RuntimeError(f"Phase 20 unknown factors: {sorted(unknown)}")
    enabled = set(subset) | {"small_scale", "temporal_dropout"}
    return "+".join(token for token in CANONICAL_TOKENS if token in enabled)


def _generate_domain(
    seed: int,
    families: tuple[int, ...],
    role: str,
    subset: frozenset[str],
    candidate: dict[str, object],
):
    domain = _domain_from_subset(subset)
    key = _subset_key(subset).replace("+", "_")
    base = p17.v1._event(
        f"phase20_{role}_{key}_base",
        seed,
        families,
        (domain,),
        p17._strata(families),
        candidate,
    ).copy(deep=True)
    base["phase17_pair_id"] = p17._pair_id(base)
    base["phase17_context"] = f"phase20:{_subset_key(subset)}"
    base["phase17_latency_applied"] = False

    control = base.copy(deep=True)
    latency = p17.p13c._apply_component_subset(
        base,
        p17.LATENCY_CONTRAST,
        p17.LATENCY_COMPONENTS,
        seed,
    )
    latency["phase17_context"] = f"phase20:{_subset_key(subset)}"
    latency["phase17_latency_applied"] = True
    return control, latency


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


def _context_result(
    control,
    latency,
    candidate: dict[str, object],
    fit: dict[str, object],
    subset: frozenset[str],
) -> dict[str, object]:
    integrity = p17._integrity_and_width_identity(control, latency, candidate)
    matched = p17._matched_transitions(control, latency, candidate)
    control_static = p17._static_metrics(control, candidate)
    latency_static = p17._static_metrics(latency, candidate)

    e0 = matched["latency_e0_lateral_m"].to_numpy(float)
    e1 = matched["latency_e1_lateral_m"].to_numpy(float)
    a14 = float(fit["phase14_lateral_a"])
    a_simple = float(fit["contexts"]["simple"]["coefficients"]["latency"]["lateral"]["a"])
    a_hard = float(fit["contexts"]["hard"]["coefficients"]["latency"]["lateral"]["a"])

    r14 = _residual_metrics(e0, e1, a14)
    rs = _residual_metrics(e0, e1, a_simple)
    rh = _residual_metrics(e0, e1, a_hard)

    rmse_ratio = float(rs["rmse_signed_residual_m"] / r14["rmse_signed_residual_m"])
    mae_ratio = float(rs["mae_abs_residual_m"] / r14["mae_abs_residual_m"])
    q90_ratio = float(rs["q90_abs_residual_m_descriptive"] / r14["q90_abs_residual_m_descriptive"])

    return {
        "subset": [f for f in FACTORS if f in subset],
        "subset_key": _subset_key(subset),
        "domain": _domain_from_subset(subset),
        "integrity": integrity,
        "matched_transitions": int(len(matched)),
        "control": control_static,
        "latency": latency_static,
        "frozen_coefficients": {
            "phase14_lateral_a": a14,
            "phase17_simple_latency_lateral_a": a_simple,
            "phase17_hard_latency_lateral_a": a_hard,
        },
        "latency_lateral_residuals": {
            "phase14": r14,
            "phase17_simple_latency_fit": rs,
            "phase17_hard_latency_fit": rh,
            "simplefit_over_phase14_rmse": rmse_ratio,
            "simplefit_over_phase14_mae": mae_ratio,
            "simplefit_over_phase14_q90_descriptive": q90_ratio,
            "simplefit_rmse_advantage": 1.0 - rmse_ratio,
            "simplefit_mae_advantage": 1.0 - mae_ratio,
        },
        "paired_lateral_effects": {
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
        },
    }


def _advantage_map(contexts: dict[str, dict[str, object]], statistic: str) -> dict[frozenset[str], float]:
    if statistic not in ("rmse", "mae"):
        raise ValueError(statistic)
    out: dict[frozenset[str], float] = {}
    for subset in _all_subsets():
        key = _subset_key(subset)
        field = f"simplefit_{statistic}_advantage"
        out[subset] = float(contexts[key]["latency_lateral_residuals"][field])
    return out


def _shapley_attenuation(advantages: dict[frozenset[str], float]) -> dict[str, object]:
    expected = set(_all_subsets())
    if set(advantages) != expected:
        raise RuntimeError("Phase 20 Shapley map requires exact 32-subset power set")
    n = len(FACTORS)
    factorial_n = math.factorial(n)
    contributions: dict[str, float] = {}
    for factor in FACTORS:
        phi = 0.0
        others = tuple(f for f in FACTORS if f != factor)
        for size in range(len(others) + 1):
            weight = math.factorial(size) * math.factorial(n - size - 1) / factorial_n
            for combo in itertools.combinations(others, size):
                s = frozenset(combo)
                with_factor = frozenset(set(s) | {factor})
                phi += weight * (float(advantages[s]) - float(advantages[with_factor]))
        contributions[factor] = float(phi)

    empty = frozenset()
    full = frozenset(FACTORS)
    attenuation = float(advantages[empty] - advantages[full])
    contribution_sum = float(sum(contributions.values()))
    return {
        "base_advantage": float(advantages[empty]),
        "full_advantage": float(advantages[full]),
        "endpoint_attenuation": attenuation,
        "contributions": contributions,
        "contribution_sum": contribution_sum,
        "efficiency_abs_error": float(abs(contribution_sum - attenuation)),
        "largest_attenuator": max(contributions, key=contributions.get),
        "largest_contribution": float(max(contributions.values())),
        "smallest_contributor": min(contributions, key=contributions.get),
        "smallest_contribution": float(min(contributions.values())),
    }


def _gates(
    contexts: dict[str, dict[str, object]],
    rmse_shapley: dict[str, object],
    mae_shapley: dict[str, object],
) -> dict[str, bool]:
    subsets = _all_subsets()
    expected_keys = {_subset_key(s) for s in subsets}
    complete = bool(len(contexts) == 32 and set(contexts) == expected_keys)
    construction = complete and all(
        bool(contexts[_subset_key(s)]["integrity"]["pass"])
        and bool(contexts[_subset_key(s)]["integrity"]["width_identity_pass"])
        and int(contexts[_subset_key(s)]["matched_transitions"]) >= THRESHOLDS["minimum_matched_transitions"]
        for s in subsets
    )

    empty = contexts["none"]
    full = contexts[_subset_key(frozenset(FACTORS))]
    endpoint_identity = bool(empty["domain"] == SIMPLE_DOMAIN and full["domain"] == HARD_DOMAIN)

    base_rmse = float(rmse_shapley["base_advantage"])
    delta_rmse = float(rmse_shapley["endpoint_attenuation"])
    base_mae = float(mae_shapley["base_advantage"])
    delta_mae = float(mae_shapley["endpoint_attenuation"])
    tol = THRESHOLDS["shapley_efficiency_abs_tolerance"]
    efficiency = bool(
        all(np.isfinite(float(v)) for v in rmse_shapley["contributions"].values())
        and all(np.isfinite(float(v)) for v in mae_shapley["contributions"].values())
        and float(rmse_shapley["efficiency_abs_error"]) <= tol
        and float(mae_shapley["efficiency_abs_error"]) <= tol
    )

    def metric(ctx: dict[str, object], model: str, statistic: str) -> float:
        return float(ctx["latency_lateral_residuals"][model][statistic])

    crossover = bool(
        metric(empty, "phase17_simple_latency_fit", "rmse_signed_residual_m")
        < metric(empty, "phase17_hard_latency_fit", "rmse_signed_residual_m")
        and metric(empty, "phase17_simple_latency_fit", "mae_abs_residual_m")
        < metric(empty, "phase17_hard_latency_fit", "mae_abs_residual_m")
        and metric(full, "phase17_hard_latency_fit", "rmse_signed_residual_m")
        < metric(full, "phase17_simple_latency_fit", "rmse_signed_residual_m")
        and metric(full, "phase17_hard_latency_fit", "mae_abs_residual_m")
        < metric(full, "phase17_simple_latency_fit", "mae_abs_residual_m")
    )

    level = bool(
        float(empty["paired_lateral_effects"]["p95_error_inflation"]) >= THRESHOLDS["simple_p95_error_inflation_min"]
        and float(empty["paired_lateral_effects"]["coverage_delta"]) <= THRESHOLDS["simple_coverage_delta_max"]
        and float(full["paired_lateral_effects"]["p95_error_inflation"]) >= THRESHOLDS["hard_p95_error_inflation_min"]
        and float(full["paired_lateral_effects"]["coverage_delta"]) <= THRESHOLDS["hard_coverage_delta_max"]
    )

    return {
        "a20_1_lineage_integrity": True,
        "a20_2_complete_factorial_matched_construction": bool(construction and endpoint_identity),
        "a20_3_simple_endpoint_rmse_advantage": base_rmse >= THRESHOLDS["simple_rmse_advantage_min"],
        "a20_4_rmse_endpoint_attenuation": delta_rmse >= THRESHOLDS["rmse_endpoint_attenuation_min"],
        "a20_5_simple_endpoint_mae_advantage": base_mae >= THRESHOLDS["simple_mae_advantage_min"],
        "a20_6_mae_endpoint_attenuation": delta_mae >= THRESHOLDS["mae_endpoint_attenuation_min"],
        "a20_7_exact_shapley_efficiency": efficiency,
        "a20_8_frozen_coefficient_context_crossover": crossover,
        "a20_9_static_latency_degradation_at_endpoints": level,
        "a20_10_zero_adaptation_and_claim_boundary": True,
    }


def evaluate(
    stage: str,
    phase12_path: Path,
    phase14_path: Path,
    phase17_fit_path: Path,
    phase19_final_path: Path,
    git_sha: str,
) -> dict[str, object]:
    candidate = p17._validate_phase12(phase12_path)
    p17._validate_phase14_bridge(phase14_path)
    fit = _validate_phase17_fit(phase17_fit_path)
    _validate_phase19_final(phase19_final_path)

    seed = STAGE_SEEDS[stage]
    families = STAGE_FAMILIES[stage]
    contexts: dict[str, dict[str, object]] = {}
    for subset in _all_subsets():
        control, latency = _generate_domain(seed, families, stage, subset, candidate)
        contexts[_subset_key(subset)] = _context_result(control, latency, candidate, fit, subset)

    rmse_shapley = _shapley_attenuation(_advantage_map(contexts, "rmse"))
    mae_shapley = _shapley_attenuation(_advantage_map(contexts, "mae"))
    gates = _gates(contexts, rmse_shapley, mae_shapley)

    return {
        "schema": f"{RESULT_SCHEMA_PREFIX}.{stage}-result.v1",
        "phase20_name": PHASE20_NAME,
        "stage": stage,
        "evaluated_seed_seen_after_run": seed,
        "families": list(families),
        "scientific_git_sha": git_sha,
        "phase12_candidate_sha256": FROZEN_PHASE12_CANDIDATE_SHA256,
        "phase14_bridge_sha256": FROZEN_PHASE14_BRIDGE_SHA256,
        "phase17_fit_candidate_sha256": FROZEN_PHASE17_FIT_CANDIDATE_SHA256,
        "phase19_final_result_sha256": FROZEN_PHASE19_FINAL_RESULT_SHA256,
        "phase19_final_pass_preserved": True,
        "phase18_failure_preserved_via_phase19": True,
        "factor_order": list(FACTORS),
        "factorial_context_count": 32,
        "thresholds": THRESHOLDS,
        "contexts": contexts,
        "rmse_shapley_attenuation": rmse_shapley,
        "mae_shapley_attenuation": mae_shapley,
        "gates": gates,
        "phase20_pass": bool(all(gates.values())),
        "q90_is_descriptive_only": True,
        "no_refit": True,
        "zero_adaptation": True,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "interpretation": "simulation-only exact five-factor Shapley attribution of context attenuation; not a physical causal or safety claim",
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=PHASE20_NAME)
    p.add_argument("--stage", choices=("dev", "transfer", "validation", "final"), required=True)
    p.add_argument("--phase12-candidate", type=Path, required=True)
    p.add_argument("--phase14-bridge", type=Path, required=True)
    p.add_argument("--phase17-fit-candidate", type=Path, required=True)
    p.add_argument("--phase19-final-result", type=Path, required=True)
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
        args.phase19_final_result,
        args.git_sha,
    )
    path = args.out / f"{args.stage}_result.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PHASE20_{args.stage.upper()}_RESULT_SHA256=" + _sha256_file(path))
    print(f"PHASE20_{args.stage.upper()}_PASS=" + str(bool(result["phase20_pass"])).lower())
    print(json.dumps(result["gates"], sort_keys=True))
    print(json.dumps(result["rmse_shapley_attenuation"], sort_keys=True))
    print(json.dumps(result["mae_shapley_attenuation"], sort_keys=True))


if __name__ == "__main__":
    main()
