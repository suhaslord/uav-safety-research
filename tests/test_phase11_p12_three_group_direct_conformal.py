from __future__ import annotations

import pandas as pd

from scripts import run_phase11_p9_soft_update_direct_conformal as p9
from scripts import run_phase11_p12_three_group_direct_conformal as p12


def test_p12_fresh_seed_boundary():
    assert (p12.FIT_SEED, p12.CALIBRATION_SEED, p12.TRANSFER_SEED, p12.VALIDATION_SEED) == (539539, 550550, 561561, 572572)
    assert len({p12.FIT_SEED, p12.CALIBRATION_SEED, p12.TRANSFER_SEED, p12.VALIDATION_SEED}) == 4


def test_p12_preserves_soft_point_estimator_constants():
    assert p9.MAX_CONTINUITY_GAP == 7
    assert p9.DAMPING == 0.85
    assert p9.VELOCITY_CAP_QUANTILE == 0.99
    assert p9.INNOVATION_SCALE_QUANTILE == 0.95
    assert p9.SOFT_SCALE_MULTIPLIER == 3.0
    assert p9.BLEND_PREVIOUS_SLOPE == 0.5
    assert p9.BLEND_SOFT_UPDATED_SLOPE == 0.5


def test_p12_grouping_is_exactly_three_fixed_groups():
    df = pd.DataFrame({
        "p9_source": ["known_aruco_refined", "soft_innovation_continuity", "soft_innovation_continuity", "soft_innovation_continuity", "soft_innovation_continuity", "soft_innovation_continuity"],
        "p9_continuity_horizon": [0, 3, 4, 5, 6, 7],
    })
    assert p12._group_series(df).tolist() == [
        "base_output", "continuity_h3", "continuity_h47", "continuity_h47", "continuity_h47", "continuity_h47"
    ]
    assert p12.CALIBRATION_MINIMUMS == {"base_output": 1500, "continuity_h3": 150, "continuity_h47": 100}
    assert p12.TRANSFER_MINIMUMS == {"base_output": 1000, "continuity_h3": 100, "continuity_h47": 60}


def test_p12_family_sets_are_disjoint_and_powered():
    assert len(p12.CALIBRATION_FAMILIES) == 48
    sets = [set(p12.FIT_FAMILIES), set(p12.CALIBRATION_FAMILIES), set(p12.TRANSFER_FAMILIES), set(p12.VALIDATION_FAMILIES)]
    for i, a in enumerate(sets):
        for b in sets[i + 1:]:
            assert a.isdisjoint(b)
