from __future__ import annotations

import math

import pandas as pd

from scripts import run_phase11_p9_soft_update_direct_conformal as p9


def test_p9_seed_boundary_is_fresh_and_disjoint():
    assert p9.FIT_SEED == 407407
    assert p9.CALIBRATION_SEED == 418418
    assert p9.TRANSFER_SEED == 429429
    assert p9.VALIDATION_SEED == 440440
    assert len({p9.FIT_SEED, p9.CALIBRATION_SEED, p9.TRANSFER_SEED, p9.VALIDATION_SEED}) == 4


def test_p9_constants_and_group_minimums_match_preregistration():
    assert p9.MAX_CONTINUITY_GAP == 7
    assert p9.DAMPING == 0.85
    assert p9.VELOCITY_CAP_QUANTILE == 0.99
    assert p9.INNOVATION_SCALE_QUANTILE == 0.95
    assert p9.SOFT_SCALE_MULTIPLIER == 3.0
    assert p9.BLEND_PREVIOUS_SLOPE == 0.5
    assert p9.BLEND_SOFT_UPDATED_SLOPE == 0.5
    assert p9.CALIBRATION_MINIMUMS == {
        "base_output": 1000,
        "continuity_h3": 120,
        "continuity_h45": 60,
        "continuity_h67": 30,
    }
    assert p9.TRANSFER_MINIMUMS == {
        "base_output": 800,
        "continuity_h3": 100,
        "continuity_h45": 50,
        "continuity_h67": 20,
    }


def test_soft_update_is_continuous_and_less_aggressive_than_p8_hard_clip_counterexample():
    state = p9._axis_state(
        [(0, 0.0), (1, 1.0), (2, 10.0)],
        velocity_cap=100.0,
        innovation_scale=1.0,
    )
    assert state["innovation_available"] is True
    assert state["innovation_abs"] == 8.0
    assert 0.0 < state["gain"] < 1.0
    # P8's unit-cap hard clip put the state at 3.0. P9 moves farther toward
    # the observed anchor but remains well below the raw 10.0 observation.
    assert 3.0 < state["state"] < 10.0

    small = p9._axis_state(
        [(0, 0.0), (1, 1.0), (2, 2.1)],
        velocity_cap=100.0,
        innovation_scale=1.0,
    )
    assert small["gain"] > 0.99
    assert math.isclose(float(small["state"]), 2.1, rel_tol=0.0, abs_tol=1e-3)


def test_group_assignment_is_fixed_by_source_and_horizon_only():
    df = pd.DataFrame(
        {
            "p9_source": ["known_aruco_refined", "soft_innovation_continuity", "soft_innovation_continuity", "soft_innovation_continuity", "soft_innovation_continuity"],
            "p9_continuity_horizon": [0, 3, 4, 5, 7],
        }
    )
    assert p9._group_series(df).tolist() == [
        "base_output",
        "continuity_h3",
        "continuity_h45",
        "continuity_h45",
        "continuity_h67",
    ]
