from __future__ import annotations

import pandas as pd

from scripts import run_phase11_p9_soft_update_direct_conformal as p9
from scripts import run_phase11_p13_severity_mondrian_conformal as p13


def test_p13_fresh_seed_and_family_boundaries_are_disjoint():
    assert (p13.FIT_SEED, p13.PARTITION_SEED, p13.CALIBRATION_SEED, p13.TRANSFER_SEED, p13.VALIDATION_SEED) == (638638, 649649, 660660, 671671, 682682)
    assert len({p13.FIT_SEED, p13.PARTITION_SEED, p13.CALIBRATION_SEED, p13.TRANSFER_SEED, p13.VALIDATION_SEED}) == 5
    roles = [set(p13.FIT_FAMILIES), set(p13.PARTITION_FAMILIES), set(p13.CALIBRATION_FAMILIES), set(p13.TRANSFER_FAMILIES), set(p13.VALIDATION_FAMILIES)]
    for i, left in enumerate(roles):
        for right in roles[i + 1:]:
            assert left.isdisjoint(right)


def test_p13_preserves_p9_point_estimator_constants_and_four_base_groups():
    assert p9.MAX_CONTINUITY_GAP == 7
    assert p9.DAMPING == 0.85
    assert p9.VELOCITY_CAP_QUANTILE == 0.99
    assert p9.INNOVATION_SCALE_QUANTILE == 0.95
    assert p9.SOFT_SCALE_MULTIPLIER == 3.0
    assert p9.BLEND_PREVIOUS_SLOPE == 0.5
    assert p9.BLEND_SOFT_UPDATED_SLOPE == 0.5
    assert p9.GROUPS == ("base_output", "continuity_h3", "continuity_h45", "continuity_h67")


def test_intervention_mask_ignores_truth_and_error_columns():
    df = pd.DataFrame({
        "family": [606, 606, 612, 612, 618, 618],
        "frame_index": [9, 10, 10, 14, 10, 16],
        "truth_lateral_x_m": [1, 2, 3, 4, 5, 6],
        "lateral_abs_error_m": [9, 8, 7, 6, 5, 4],
    })
    other = df.copy()
    other["truth_lateral_x_m"] *= 10000
    other["lateral_abs_error_m"] += 9999
    a = p13.forced_dropout_mask(df, p13.PARTITION_STRATA, p13.INTERVENTION_STARTS["partition"])
    b = p13.forced_dropout_mask(other, p13.PARTITION_STRATA, p13.INTERVENTION_STARTS["partition"])
    assert a.tolist() == b.tolist()
    assert a.tolist() == [False, True, True, True, True, True]


def test_severity_cell_assignment_uses_only_group_severity_and_frozen_cutpoints():
    df = pd.DataFrame({
        "p9_source": ["known_aruco_refined", "known_aruco_refined", "soft_innovation_continuity", "soft_innovation_continuity"],
        "p9_continuity_horizon": [0, 0, 3, 7],
        "severity": [0.1, 0.5, 0.4, 0.9],
    })
    cutpoints = {
        "base_output": {"lower": 0.2, "upper": 0.4, "rows": 100},
        "continuity_h3": {"lower": 0.3, "upper": 0.6, "rows": 100},
        "continuity_h45": {"lower": 0.3, "upper": 0.6, "rows": 100},
        "continuity_h67": {"lower": 0.3, "upper": 0.6, "rows": 100},
    }
    assert p13._cell_series(df, cutpoints).tolist() == [
        "base_output__low",
        "base_output__high",
        "continuity_h3__mid",
        "continuity_h67__high",
    ]


def test_calibration_and_transfer_cell_minimums_are_predeclared_for_all_groups():
    assert p13.CALIBRATION_CELL_MINIMUMS == {
        "base_output": 500,
        "continuity_h3": 100,
        "continuity_h45": 75,
        "continuity_h67": 50,
    }
    assert p13.TRANSFER_CELL_MINIMUMS == {
        "base_output": 200,
        "continuity_h3": 40,
        "continuity_h45": 30,
        "continuity_h67": 15,
    }
