from __future__ import annotations

from scripts import run_phase18_residual_advantage_confirmation as p18


def _context(q14_ratio: float, qc_ratio: float, rmse_ratio: float, p95: float, cov: float) -> dict[str, object]:
    return {
        "integrity": {"pass": True, "width_identity_pass": True},
        "matched_transitions": 900,
        "latency_lateral_residuals": {
            "latencyfit_over_phase14_q90": q14_ratio,
            "latencyfit_over_controlfit_q90": qc_ratio,
            "latencyfit_over_phase14_rmse": rmse_ratio,
            "q90_relative_improvement_vs_phase14": 1.0 - q14_ratio,
            "rmse_relative_improvement_vs_phase14": 1.0 - rmse_ratio,
        },
        "paired_lateral_effects": {
            "p95_error_inflation": p95,
            "coverage_delta": cov,
        },
    }


def test_phase18_evidence_partitions_are_fresh_and_disjoint():
    roles = [set(v) for v in p18.STAGE_FAMILIES.values()]
    for i, left in enumerate(roles):
        for right in roles[i + 1 :]:
            assert left.isdisjoint(right)
    assert p18.STAGE_SEEDS == {
        "dev": 1818181,
        "transfer": 1818182,
        "validation": 1818183,
        "final": 1818184,
    }


def test_phase18_gates_accept_preregistered_residual_pattern():
    contexts = {
        "simple": _context(0.86, 0.84, 0.92, 1.4, -0.03),
        "hard": _context(1.00, 0.91, 1.00, 1.2, -0.08),
    }
    gates = p18._gates(contexts)
    assert all(gates.values())


def test_phase18_rejects_universal_residual_advantage():
    contexts = {
        "simple": _context(0.86, 0.84, 0.92, 1.4, -0.03),
        "hard": _context(0.84, 0.90, 0.90, 1.2, -0.08),
    }
    gates = p18._gates(contexts)
    assert not gates["r18_5_hard_q90_advantage_remains_limited"]
    assert not gates["r18_6_simple_vs_hard_q90_improvement_gap"]
    assert not gates["r18_7_independent_rmse_confirmation"]


def test_phase18_rejects_q90_only_effect_without_rmse_confirmation():
    contexts = {
        "simple": _context(0.86, 0.84, 0.99, 1.4, -0.03),
        "hard": _context(1.00, 0.91, 1.00, 1.2, -0.08),
    }
    gates = p18._gates(contexts)
    assert gates["r18_3_simple_q90_advantage_vs_phase14"]
    assert not gates["r18_7_independent_rmse_confirmation"]


def test_frozen_phase17_fit_identity_is_exact():
    assert p18.FROZEN_PHASE17_FIT_CANDIDATE_SHA256 == "2ca52a418f5616e0e83ef84d0c9238ee429260cd4de7a553356b0c1bba44d8e0"
    assert p18.PHASE17_RECORDED_RESULT_SHA256 == "24aeed60003b3111c9d3dd24cee992f8bac539531d38923b9a205a1423e8d029"
