from __future__ import annotations

from scripts import run_phase19_distribution_wide_residual_advantage as p19


def _ctx(rmse: float, mae: float, p95: float, cov: float) -> dict[str, object]:
    return {
        "integrity": {"pass": True, "width_identity_pass": True},
        "matched_transitions": 900,
        "latency_lateral_residuals": {
            "latencyfit_over_phase14_rmse": rmse,
            "latencyfit_over_phase14_mae": mae,
        },
        "paired_lateral_effects": {"p95_error_inflation": p95, "coverage_delta": cov},
    }


def test_fresh_partitions_are_disjoint():
    roles=[set(v) for v in p19.STAGE_FAMILIES.values()]
    for i,a in enumerate(roles):
        for b in roles[i+1:]: assert a.isdisjoint(b)
    assert p19.STAGE_SEEDS=={"dev":1919191,"transfer":1919192,"validation":1919193,"final":1919194}


def test_gates_accept_distribution_wide_pattern():
    gates=p19._gates({"simple":_ctx(0.92,0.91,1.4,-0.03),"hard":_ctx(1.00,0.99,1.2,-0.08)})
    assert all(gates.values())


def test_gates_reject_rmse_only_without_mae_confirmation():
    gates=p19._gates({"simple":_ctx(0.92,0.99,1.4,-0.03),"hard":_ctx(1.00,1.00,1.2,-0.08)})
    assert gates["d19_3_simple_context_rmse_advantage"]
    assert not gates["d19_6_simple_context_mae_advantage"]
    assert not gates["d19_8_mae_context_advantage_gap"]


def test_exact_failed_phase18_identity_is_frozen():
    assert p19.FROZEN_PHASE18_VALIDATION_RESULT_SHA256=="ad96ca1a5119fcd594a84fd72a04f8efcc377ba788383d90dda9ef7eecad4431"
    assert p19.FROZEN_PHASE17_FIT_CANDIDATE_SHA256=="2ca52a418f5616e0e83ef84d0c9238ee429260cd4de7a553356b0c1bba44d8e0"
