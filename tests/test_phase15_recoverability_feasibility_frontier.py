from __future__ import annotations

import numpy as np

from scripts import run_phase15_recoverability_feasibility_frontier as p15


def test_phase15_locked_reference_and_evidence_roles():
    assert p15.REFERENCE_HALF_WIDTH_M == {"lateral": 0.30, "altitude": 0.85}
    assert p15.QUANTILES == (0.90, 0.95, 0.975, 0.99)
    assert p15.STAGE_SEEDS == {
        "dev": 1515151,
        "transfer": 1515152,
        "validation": 1515153,
        "final": 1515154,
    }
    assert p15.STAGE_FAMILIES["dev"] == tuple(range(1617, 1641))
    assert p15.STAGE_FAMILIES["final"] == tuple(range(1689, 1713))
    assert p15.LATENCY_PROFILE == "fixed_latency_2f"


def test_finite_conformal_rank_matches_preregistration():
    x = np.arange(1.0, 201.0)
    assert p15._finite_conformal(x, 0.90) == 181.0
    assert p15._finite_conformal(x, 0.95) == 191.0
    assert p15._finite_conformal(x, 0.975) == 196.0
    assert p15._finite_conformal(x, 0.99) == 199.0


def test_minimal_rpi_frontier_formula():
    a = 0.6
    bounds = np.array([0.20, 0.30, 0.40, 0.50])
    r = bounds / (1.0 - abs(a))
    assert np.allclose(r, [0.5, 0.75, 1.0, 1.25])
    assert np.all(np.diff(r) >= 0.0)


def test_coverage_gate_checks_every_axis_and_quantile():
    cohort = {
        "axes": {
            axis: {
                "frozen_residual_coverage": {
                    p15._qkey(0.90): 0.90,
                    p15._qkey(0.95): 0.95,
                    p15._qkey(0.975): 0.975,
                    p15._qkey(0.99): 0.99,
                }
            }
            for axis in ("lateral", "altitude")
        }
    }
    assert p15._coverage_gate(cohort, p15.NATURAL_COVERAGE_FLOORS)
    cohort["axes"]["lateral"]["frozen_residual_coverage"][p15._qkey(0.99)] = 0.95
    assert not p15._coverage_gate(cohort, p15.NATURAL_COVERAGE_FLOORS)


def test_q90_infeasibility_requires_both_axes_above_reference():
    cohort = {
        "axes": {
            "lateral": {
                "fresh_diagnostic_minimal_rpi_half_width_m": {p15._qkey(0.90): 0.31}
            },
            "altitude": {
                "fresh_diagnostic_minimal_rpi_half_width_m": {p15._qkey(0.90): 0.86}
            },
        }
    }
    assert p15._q90_infeasible(cohort)
    cohort["axes"]["altitude"]["fresh_diagnostic_minimal_rpi_half_width_m"][p15._qkey(0.90)] = 0.84
    assert not p15._q90_infeasible(cohort)


def test_direction_stable_rejects_nonmonotone_frontier():
    good = [0.5, 0.7, 1.0, 1.8]
    cohort = {
        "axes": {
            axis: {
                "fresh_diagnostic_minimal_rpi_half_width_m": {
                    p15._qkey(q): good[i] for i, q in enumerate(p15.QUANTILES)
                }
            }
            for axis in ("lateral", "altitude")
        }
    }
    assert p15._direction_stable(cohort)
    cohort["axes"]["lateral"]["fresh_diagnostic_minimal_rpi_half_width_m"][p15._qkey(0.975)] = 0.6
    assert not p15._direction_stable(cohort)
