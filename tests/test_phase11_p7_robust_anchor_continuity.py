from __future__ import annotations

import numpy as np

from scripts import run_phase11_p7_robust_anchor_continuity as p7


def test_p7_exposure_ledger_keeps_protected_seed_distinct():
    development = {
        p7.FIT_SEED,
        p7.CALIBRATION_SEED,
        p7.ADAPTATION_SEED,
        p7.TRANSFER_SEED,
    }
    assert development == {297297, 308308, 319319, 330330}
    assert p7.VALIDATION_SEED == 341341
    assert p7.VALIDATION_SEED not in development


def test_p7_frozen_method_constants_match_preregistration():
    assert p7.MAX_CONTINUITY_GAP == 7
    assert p7.DAMPING == 0.85
    assert p7.VELOCITY_CAP_QUANTILE == 0.99
    assert p7.MIN_ADAPTATION_CONTINUITY_ROWS == 80
    assert p7.MIN_TRANSFER_CONTINUITY_ROWS == 50
    assert p7.MIN_TRANSFER_BASE_ROWS == 200
    assert p7.RIDGE_LAMBDA == 4.0


def test_p7_known_three_anchor_counterexample_is_preserved():
    # This is the frozen counterexample that caused P7 to stop before candidate freeze.
    values = [(0, 0.0), (1, 1.0), (2, 10.0)]
    slope, trend_latest = p7._robust_axis_state(values, cap=100.0)

    assert np.isfinite(slope)
    assert trend_latest == 10.0


def test_anchor_innovation_exposes_same_counterexample_causally():
    anchors = [(0, 0.0, 0.0), (1, 1.0, 1.0), (2, 10.0, 10.0)]
    lat, alt, available = p7._anchor_innovation(anchors)

    assert available is True
    assert lat == 8.0
    assert alt == 8.0
