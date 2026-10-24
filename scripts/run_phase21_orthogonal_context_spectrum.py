from __future__ import annotations

import argparse
import itertools
import json
from hashlib import sha256
from pathlib import Path

import numpy as np

try:
    from scripts import run_phase20_shapley_context_attenuation as p20
except ModuleNotFoundError:
    import run_phase20_shapley_context_attenuation as p20

PHASE21_NAME = "Orthogonal Context Spectrum"
RESULT_SCHEMA_PREFIX = "aegisland.phase21.orthogonal-context-spectrum"

FROZEN_PHASE12_CANDIDATE_SHA256 = p20.FROZEN_PHASE12_CANDIDATE_SHA256
FROZEN_PHASE14_BRIDGE_SHA256 = p20.FROZEN_PHASE14_BRIDGE_SHA256
FROZEN_PHASE17_FIT_CANDIDATE_SHA256 = p20.FROZEN_PHASE17_FIT_CANDIDATE_SHA256
FROZEN_PHASE20_FINAL_RESULT_SHA256 = "f2a0cf4e1cf0765c3194025eb29072f9663f27e3cdd13b0594cde4643f33934e"

FACTORS = p20.FACTORS
SIMPLE_DOMAIN = p20.SIMPLE_DOMAIN
HARD_DOMAIN = p20.HARD_DOMAIN

STAGE_SEEDS = {
    "dev": 2121211,
    "transfer": 2121212,
    "validation": 2121213,
    "final": 2121214,
}
STAGE_FAMILIES = {
    "dev": tuple(range(2217, 2241)),
    "transfer": tuple(range(2241, 2265)),
    "validation": tuple(range(2265, 2289)),
    "final": tuple(range(2289, 2313)),
}

THRESHOLDS = {
    "minimum_matched_transitions": 500,
    "simple_rmse_advantage_min": 0.05,
    "rmse_endpoint_attenuation_min": 0.08,
    "simple_mae_advantage_min": 0.08,
    "mae_endpoint_attenuation_min": 0.08,
    "orthogonal_abs_tolerance": 1.0e-12,
    "first_order_variance_share_min": 0.70,
    "simple_p95_error_inflation_min": 1.10,
    "simple_coverage_delta_max": -0.01,
    "hard_p95_error_inflation_min": 1.10,
    "hard_coverage_delta_max": -0.05,
}


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _validate_phase20_final(path: Path) -> dict[str, object]:
    if _sha256_file(path) != FROZEN_PHASE20_FINAL_RESULT_SHA256:
        raise RuntimeError("Phase 21 requires the exact frozen Phase 20 final result")
    result = json.loads(path.read_text(encoding="utf-8"))
    required_true = (
        "phase20_pass",
        "phase19_final_pass_preserved",
        "phase18_failure_preserved_via_phase19",
        "q90_is_descriptive_only",
        "no_refit",
        "zero_adaptation",
    )
    for field in required_true:
        if result.get(field) is not True:
            raise RuntimeError(f"Phase 21 requires Phase 20 field {field}=true")
    if result.get("factor_order") != list(FACTORS) or result.get("factorial_context_count") != 32:
        raise RuntimeError("Phase 21 requires exact Phase 20 factor identity")
    return result


def _generate_domain(
    seed: int,
    families: tuple[int, ...],
    role: str,
    subset: frozenset[str],
    candidate: dict[str, object],
):
    domain = p20._domain_from_subset(subset)
    key = p20._subset_key(subset).replace("+", "_")
    base = p20.p17.v1._event(
        f"phase21_{role}_{key}_base",
        seed,
        families,
        (domain,),
        p20.p17._strata(families),
        candidate,
    ).copy(deep=True)
    base["phase17_pair_id"] = p20.p17._pair_id(base)
    base["phase17_context"] = f"phase21:{p20._subset_key(subset)}"
    base["phase17_latency_applied"] = False

    control = base.copy(deep=True)
    latency = p20.p17.p13c._apply_component_subset(
        base,
        p20.p17.LATENCY_CONTRAST,
        p20.p17.LATENCY_COMPONENTS,
        seed,
    )
    latency["phase17_context"] = f"phase21:{p20._subset_key(subset)}"
    latency["phase17_latency_applied"] = True
    return control, latency


def _walsh_spectrum(advantages: dict[frozenset[str], float]) -> dict[str, object]:
    expected = set(p20._all_subsets())
    if set(advantages) != expected:
        raise RuntimeError("Phase 21 Walsh spectrum requires the exact 32-cell power set")

    coefficients: dict[frozenset[str], float] = {}
    for order in range(len(FACTORS) + 1):
        for combo in itertools.combinations(FACTORS, order):
            term = frozenset(combo)
            total = 0.0
            for cell, value in advantages.items():
                sign = 1.0
                for factor in term:
                    sign *= 1.0 if factor in cell else -1.0
                total += float(value) * sign
            coefficients[term] = float(total / len(expected))

    values = np.asarray([float(advantages[s]) for s in p20._all_subsets()], dtype=float)
    direct_variance = float(np.mean(np.square(values - float(np.mean(values)))))
    spectral_variance = float(sum(v * v for s, v in coefficients.items() if s))
    order_variance = {
        order: float(sum(v * v for s, v in coefficients.items() if len(s) == order))
        for order in range(1, len(FACTORS) + 1)
    }
    if not np.isfinite(spectral_variance) or spectral_variance <= 0.0:
        raise RuntimeError("Phase 21 requires finite positive centered surface variance")
    order_shares = {order: float(mass / spectral_variance) for order, mass in order_variance.items()}
    first_order = float(order_shares[1])

    def term_key(term: frozenset[str]) -> str:
        return p20._subset_key(term)

    return {
        "grand_mean": float(coefficients[frozenset()]),
        "coefficients": {term_key(s): float(coefficients[s]) for s in p20._all_subsets()},
        "first_order_coefficients": {factor: float(coefficients[frozenset({factor})]) for factor in FACTORS},
        "direct_centered_population_variance": direct_variance,
        "spectral_centered_variance": spectral_variance,
        "parseval_abs_error": float(abs(direct_variance - spectral_variance)),
        "order_variance_mass": {str(k): float(v) for k, v in order_variance.items()},
        "order_variance_share": {str(k): float(v) for k, v in order_shares.items()},
        "order_share_sum": float(sum(order_shares.values())),
        "first_order_variance_share": first_order,
        "interaction_variance_share": float(1.0 - first_order),
    }


def _gates(
    contexts: dict[str, dict[str, object]],
    rmse_adv: dict[frozenset[str], float],
    mae_adv: dict[frozenset[str], float],
    rmse_spectrum: dict[str, object],
    mae_spectrum: dict[str, object],
) -> dict[str, bool]:
    subsets = p20._all_subsets()
    expected_keys = {p20._subset_key(s) for s in subsets}
    complete = bool(len(contexts) == 32 and set(contexts) == expected_keys)
    construction = complete and all(
        bool(contexts[p20._subset_key(s)]["integrity"]["pass"])
        and bool(contexts[p20._subset_key(s)]["integrity"]["width_identity_pass"])
        and int(contexts[p20._subset_key(s)]["matched_transitions"]) >= THRESHOLDS["minimum_matched_transitions"]
        for s in subsets
    )

    empty_set = frozenset()
    full_set = frozenset(FACTORS)
    empty = contexts["none"]
    full = contexts[p20._subset_key(full_set)]
    endpoint_identity = bool(empty["domain"] == SIMPLE_DOMAIN and full["domain"] == HARD_DOMAIN)

    rmse_delta = float(rmse_adv[empty_set] - rmse_adv[full_set])
    mae_delta = float(mae_adv[empty_set] - mae_adv[full_set])

    tol = THRESHOLDS["orthogonal_abs_tolerance"]
    closure = bool(
        float(rmse_spectrum["parseval_abs_error"]) <= tol
        and float(mae_spectrum["parseval_abs_error"]) <= tol
        and abs(float(rmse_spectrum["order_share_sum"]) - 1.0) <= tol
        and abs(float(mae_spectrum["order_share_sum"]) - 1.0) <= tol
        and all(np.isfinite(float(v)) for v in rmse_spectrum["coefficients"].values())
        and all(np.isfinite(float(v)) for v in mae_spectrum["coefficients"].values())
        and float(rmse_spectrum["direct_centered_population_variance"]) > 0.0
        and float(mae_spectrum["direct_centered_population_variance"]) > 0.0
    )

    rmse_direction = all(float(v) < 0.0 for v in rmse_spectrum["first_order_coefficients"].values())
    mae_direction = all(float(v) < 0.0 for v in mae_spectrum["first_order_coefficients"].values())

    level = bool(
        float(empty["paired_lateral_effects"]["p95_error_inflation"]) >= THRESHOLDS["simple_p95_error_inflation_min"]
        and float(empty["paired_lateral_effects"]["coverage_delta"]) <= THRESHOLDS["simple_coverage_delta_max"]
        and float(full["paired_lateral_effects"]["p95_error_inflation"]) >= THRESHOLDS["hard_p95_error_inflation_min"]
        and float(full["paired_lateral_effects"]["coverage_delta"]) <= THRESHOLDS["hard_coverage_delta_max"]
    )

    return {
        "o21_1_lineage_integrity": True,
        "o21_2_complete_factorial_matched_construction": bool(construction and endpoint_identity),
        "o21_3_endpoint_attenuation_remains_present": bool(
            float(rmse_adv[empty_set]) >= THRESHOLDS["simple_rmse_advantage_min"]
            and rmse_delta >= THRESHOLDS["rmse_endpoint_attenuation_min"]
            and float(mae_adv[empty_set]) >= THRESHOLDS["simple_mae_advantage_min"]
            and mae_delta >= THRESHOLDS["mae_endpoint_attenuation_min"]
        ),
        "o21_4_exact_orthogonal_closure": closure,
        "o21_5_rmse_first_order_dominance": float(rmse_spectrum["first_order_variance_share"]) >= THRESHOLDS["first_order_variance_share_min"],
        "o21_6_mae_first_order_dominance": float(mae_spectrum["first_order_variance_share"]) >= THRESHOLDS["first_order_variance_share_min"],
        "o21_7_all_rmse_first_order_effects_attenuate": bool(rmse_direction),
        "o21_8_all_mae_first_order_effects_attenuate": bool(mae_direction),
        "o21_9_static_latency_degradation_at_endpoints": level,
        "o21_10_zero_adaptation_and_claim_boundary": True,
    }


def evaluate(
    stage: str,
    phase12_path: Path,
    phase14_path: Path,
    phase17_fit_path: Path,
    phase20_final_path: Path,
    git_sha: str,
) -> dict[str, object]:
    candidate = p20.p17._validate_phase12(phase12_path)
    p20.p17._validate_phase14_bridge(phase14_path)
    fit = p20._validate_phase17_fit(phase17_fit_path)
    _validate_phase20_final(phase20_final_path)

    seed = STAGE_SEEDS[stage]
    families = STAGE_FAMILIES[stage]
    contexts: dict[str, dict[str, object]] = {}
    for subset in p20._all_subsets():
        control, latency = _generate_domain(seed, families, stage, subset, candidate)
        contexts[p20._subset_key(subset)] = p20._context_result(control, latency, candidate, fit, subset)

    rmse_adv = p20._advantage_map(contexts, "rmse")
    mae_adv = p20._advantage_map(contexts, "mae")
    rmse_spectrum = _walsh_spectrum(rmse_adv)
    mae_spectrum = _walsh_spectrum(mae_adv)
    gates = _gates(contexts, rmse_adv, mae_adv, rmse_spectrum, mae_spectrum)

    empty = frozenset()
    full = frozenset(FACTORS)
    return {
        "schema": f"{RESULT_SCHEMA_PREFIX}.{stage}-result.v1",
        "phase21_name": PHASE21_NAME,
        "stage": stage,
        "evaluated_seed_seen_after_run": seed,
        "families": list(families),
        "scientific_git_sha": git_sha,
        "phase12_candidate_sha256": FROZEN_PHASE12_CANDIDATE_SHA256,
        "phase14_bridge_sha256": FROZEN_PHASE14_BRIDGE_SHA256,
        "phase17_fit_candidate_sha256": FROZEN_PHASE17_FIT_CANDIDATE_SHA256,
        "phase20_final_result_sha256": FROZEN_PHASE20_FINAL_RESULT_SHA256,
        "phase20_final_pass_preserved": True,
        "phase19_final_pass_preserved_via_phase20": True,
        "phase18_failure_preserved_via_phase20": True,
        "factor_order": list(FACTORS),
        "factorial_context_count": 32,
        "thresholds": THRESHOLDS,
        "contexts": contexts,
        "rmse_endpoint": {
            "simple_advantage": float(rmse_adv[empty]),
            "hard_advantage": float(rmse_adv[full]),
            "attenuation": float(rmse_adv[empty] - rmse_adv[full]),
        },
        "mae_endpoint": {
            "simple_advantage": float(mae_adv[empty]),
            "hard_advantage": float(mae_adv[full]),
            "attenuation": float(mae_adv[empty] - mae_adv[full]),
        },
        "rmse_walsh_spectrum": rmse_spectrum,
        "mae_walsh_spectrum": mae_spectrum,
        "gates": gates,
        "phase21_pass": bool(all(gates.values())),
        "q90_is_descriptive_only": True,
        "no_refit": True,
        "zero_adaptation": True,
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "interpretation": "simulation-only orthogonal decomposition of the five-factor context attenuation surface; not a physical causal or safety claim",
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=PHASE21_NAME)
    p.add_argument("--stage", choices=("dev", "transfer", "validation", "final"), required=True)
    p.add_argument("--phase12-candidate", type=Path, required=True)
    p.add_argument("--phase14-bridge", type=Path, required=True)
    p.add_argument("--phase17-fit-candidate", type=Path, required=True)
    p.add_argument("--phase20-final-result", type=Path, required=True)
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
        args.phase20_final_result,
        args.git_sha,
    )
    path = args.out / f"{args.stage}_result.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PHASE21_{args.stage.upper()}_RESULT_SHA256=" + _sha256_file(path))
    print(f"PHASE21_{args.stage.upper()}_PASS=" + str(bool(result["phase21_pass"])).lower())
    print(json.dumps(result["gates"], sort_keys=True))
    print(json.dumps(result["rmse_walsh_spectrum"], sort_keys=True))
    print(json.dumps(result["mae_walsh_spectrum"], sort_keys=True))


if __name__ == "__main__":
    main()
