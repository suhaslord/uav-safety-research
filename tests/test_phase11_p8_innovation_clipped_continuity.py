from __future__ import annotations

import math

from scripts import run_phase11_p8_innovation_clipped_continuity as p8


def test_p8_protected_seed_is_disjoint_from_all_development_seeds():
    development = {
        p8.FIT_SEED,
        p8.CALIBRATION_SEED,
        p8.ADAPTATION_SEED,
        p8.TRANSFER_SEED,
    }
    assert development == {352352, 363363, 374374, 385385}
    assert p8.VALIDATION_SEED == 396396
    assert p8.VALIDATION_SEED not in development


def test_p8_frozen_constants_match_preregistration():
    assert p8.MAX_CONTINUITY_GAP == 7
    assert p8.DAMPING == 0.85
    assert p8.VELOCITY_CAP_QUANTILE == 0.99
    assert p8.INNOVATION_CAP_QUANTILE == 0.95
    assert p8.INNOVATION_UTILIZATION_MAX == 3.0
    assert p8.BLEND_PREVIOUS_SLOPE == 0.5
    assert p8.BLEND_CORRECTED_SLOPE == 0.5
    assert p8.RIDGE_LAMBDA == 4.0
    assert p8.MIN_ADAPTATION_CONTINUITY_ROWS == 90
    assert p8.MIN_TRANSFER_CONTINUITY_ROWS == 60
    assert p8.MIN_TRANSFER_BASE_ROWS == 400


def test_innovation_clipping_blocks_p7_bad_newest_anchor_counterexample():
    state = p8._axis_state(
        [(0, 0.0), (1, 1.0), (2, 10.0)],
        velocity_cap=100.0,
        innovation_cap=1.0,
    )

    assert state["innovation_available"] is True
    assert state["raw_innovation_abs"] == 8.0
    assert state["innovation_clipped"] is True
    assert state["innovation_utilization"] == 3.0
    assert state["state"] == 3.0
    assert state["state"] != 10.0
    assert math.isclose(float(state["slope"]), 1.5)


def test_two_anchor_state_has_no_fake_innovation_signal():
    state = p8._axis_state(
        [(4, 1.0), (6, 1.4)],
        velocity_cap=1.0,
        innovation_cap=0.2,
    )

    assert state["innovation_available"] is False
    assert state["raw_innovation_abs"] == 0.0
    assert state["innovation_utilization"] == 0.0
    assert state["state"] == 1.4
    assert math.isclose(float(state["slope"]), 0.2)
