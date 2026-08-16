from __future__ import annotations

import pandas as pd

from scripts import run_phase11_p12_three_group_direct_conformal as p12
from scripts import run_phase11_p13_two_stage_grouped_conformal as p13


def test_p13_fresh_five_split_boundary():
    seeds = (p13.FIT_SEED, p13.BASE_CALIBRATION_SEED, p13.TRANSFER_CALIBRATION_SEED, p13.CHALLENGE_SEED, p13.VALIDATION_SEED)
    assert seeds == (583583, 594594, 605605, 616616, 627627)
    assert len(set(seeds)) == 5


def test_p13_preserves_three_groups_and_soft_point_estimator():
    assert p12.GROUPS == ("base_output", "continuity_h3", "continuity_h47")
    assert p13.p9.SOFT_SCALE_MULTIPLIER == 3.0
    assert p13.p9.BLEND_PREVIOUS_SLOPE == 0.5
    assert p13.p9.BLEND_SOFT_UPDATED_SLOPE == 0.5
    assert p13.p9.MAX_CONTINUITY_GAP == 7
    assert p13.p9.DAMPING == 0.85


def test_transfer_calibration_multiplies_frozen_base_radii_by_group():
    df = pd.DataFrame({
        "truth_visible": [True] * 6,
        "p9_available": [True] * 6,
        "p9_source": ["known_aruco_refined", "known_aruco_refined", "soft_innovation_continuity", "soft_innovation_continuity", "soft_innovation_continuity", "soft_innovation_continuity"],
        "p9_continuity_horizon": [0, 0, 3, 3, 4, 7],
        "p9_lateral_abs_error_m": [1.0, 2.0, 2.0, 4.0, 3.0, 6.0],
        "p9_altitude_abs_error_m": [2.0, 4.0, 4.0, 8.0, 6.0, 12.0],
    })
    base = {
        g: {
            "lateral": {f"{q:.2f}": 1.0 for q in p13.p9.TARGETS},
            "altitude": {f"{q:.2f}": 2.0 for q in p13.p9.TARGETS},
        }
        for g in p12.GROUPS
    }
    old = p12.TRANSFER_MINIMUMS.copy()
    try:
        p12.TRANSFER_MINIMUMS.update({"base_output": 1, "continuity_h3": 1, "continuity_h47": 1})
        multipliers, final, counts = p13._transfer_calibrate(df, base)
    finally:
        p12.TRANSFER_MINIMUMS.clear(); p12.TRANSFER_MINIMUMS.update(old)
    assert counts == {"base_output": 2, "continuity_h3": 2, "continuity_h47": 2}
    assert final["base_output"]["lateral"]["0.95"] >= base["base_output"]["lateral"]["0.95"]
    assert final["continuity_h47"]["altitude"]["0.95"] >= base["continuity_h47"]["altitude"]["0.95"]
    assert "base_output" in multipliers


def test_p13_family_sets_are_disjoint():
    sets = [set(p13.FIT_FAMILIES), set(p13.BASE_CALIBRATION_FAMILIES), set(p13.TRANSFER_CALIBRATION_FAMILIES), set(p13.CHALLENGE_FAMILIES), set(p13.VALIDATION_FAMILIES)]
    for i, a in enumerate(sets):
        for b in sets[i + 1:]:
            assert a.isdisjoint(b)
