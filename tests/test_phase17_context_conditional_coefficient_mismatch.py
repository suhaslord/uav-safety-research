from __future__ import annotations

import numpy as np

from scripts import run_phase17_context_conditional_coefficient_mismatch as p17


def _context(control_a: float, latency_a: float, rows: int = 900) -> dict[str, object]:
    return {
        "integrity": {"pass": True, "width_identity_pass": True},
        "matched_transitions": rows,
        "coefficients": {
            "control": {
                "lateral": {"a": control_a},
                "altitude": {"a": 0.55},
            },
            "latency": {
                "lateral": {"a": latency_a},
                "altitude": {"a": 0.60},
            },
        },
    }


def test_phase17_evidence_partitions_are_fresh_and_disjoint():
    roles = [set(p17.FIT_FAMILIES)] + [set(v) for v in p17.STAGE_FAMILIES.values()]
    for i, left in enumerate(roles):
        for right in roles[i + 1 :]:
            assert left.isdisjoint(right)
    assert p17.FIT_SEED == 1717170
    assert p17.STAGE_SEEDS == {
        "dev": 1717171,
        "transfer": 1717172,
        "validation": 1717173,
        "final": 1717174,
    }


def test_ols_no_intercept_recovers_known_coefficient():
    e0 = np.array([-2.0, -1.0, 0.5, 1.0, 2.5])
    e1 = 0.72 * e0
    assert abs(p17._ols_no_intercept(e0, e1) - 0.72) < 1.0e-12


def test_residual_metrics_are_zero_for_exact_model():
    e0 = np.array([-1.0, -0.5, 0.5, 1.0])
    e1 = 0.8 * e0
    metrics = p17._residual_metrics(e0, e1, 0.8)
    assert metrics["q90_abs_residual_m"] == 0.0
    assert metrics["rmse_signed_residual_m"] == 0.0
    assert metrics["median_abs_residual_m"] == 0.0


def test_fit_gates_accept_preregistered_heterogeneous_pattern():
    phase14_a = 0.6102677720
    contexts = {
        "simple": _context(control_a=0.55, latency_a=0.82),
        "hard": _context(control_a=0.10, latency_a=0.59),
    }
    gates = p17._fit_gates(contexts, phase14_a)
    assert all(gates.values())


def test_fit_gates_reject_universal_large_mismatch():
    phase14_a = 0.6102677720
    contexts = {
        "simple": _context(control_a=0.55, latency_a=0.82),
        "hard": _context(control_a=0.20, latency_a=0.80),
    }
    gates = p17._fit_gates(contexts, phase14_a)
    assert gates["f17_3_simple_context_large_latency_shift"]
    assert not gates["f17_4_hard_context_phase14_proximity"]
    assert not gates["f17_5_mismatch_heterogeneity"]


def test_claim_boundaries_and_intervention_are_frozen():
    assert p17.LATENCY_CONTRAST == "latency_only"
    assert p17.LATENCY_COMPONENTS == frozenset({"A"})
    assert p17.REFERENCE_HALF_WIDTH_M == {"lateral": 0.30, "altitude": 0.85}
    assert p17.FROZEN_PHASE12_CANDIDATE_SHA256 == "e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991"
    assert p17.FROZEN_PHASE14_BRIDGE_SHA256 == "0443d4e45a1966c77544c5c9965de8caec6e622c79ef8c2ce47aee82a3c95981"
