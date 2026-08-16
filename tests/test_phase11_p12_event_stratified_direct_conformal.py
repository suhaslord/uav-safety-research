from __future__ import annotations

import pandas as pd

from scripts import run_phase11_p9_soft_update_direct_conformal as p9
from scripts import run_phase11_p12_event_stratified_direct_conformal as p12


def test_p12_uses_fresh_disjoint_evidence_boundaries():
    assert (p12.FIT_SEED, p12.CALIBRATION_SEED, p12.TRANSFER_SEED, p12.VALIDATION_SEED) == (
        583583,
        594594,
        605605,
        616616,
    )
    assert len({p12.FIT_SEED, p12.CALIBRATION_SEED, p12.TRANSFER_SEED, p12.VALIDATION_SEED}) == 4
    sets = [
        set(p12.FIT_FAMILIES),
        set(p12.CALIBRATION_FAMILIES),
        set(p12.TRANSFER_FAMILIES),
        set(p12.VALIDATION_FAMILIES),
    ]
    for i, left in enumerate(sets):
        for right in sets[i + 1 :]:
            assert left.isdisjoint(right)


def test_p12_preserves_p9_estimator_and_four_conformal_groups():
    assert p9.MAX_CONTINUITY_GAP == 7
    assert p9.DAMPING == 0.85
    assert p9.VELOCITY_CAP_QUANTILE == 0.99
    assert p9.INNOVATION_SCALE_QUANTILE == 0.95
    assert p9.SOFT_SCALE_MULTIPLIER == 3.0
    assert p9.BLEND_PREVIOUS_SLOPE == 0.5
    assert p9.BLEND_SOFT_UPDATED_SLOPE == 0.5
    assert p9.GROUPS == (
        "base_output",
        "continuity_h3",
        "continuity_h45",
        "continuity_h67",
    )


def test_p12_gap_strata_and_windows_are_fixed_before_generation():
    assert p12.CALIBRATION_STRATA == {
        3: tuple(range(506, 514)),
        5: tuple(range(514, 522)),
        7: tuple(range(522, 530)),
    }
    assert p12.TRANSFER_STRATA == {
        3: tuple(range(530, 534)),
        5: tuple(range(534, 538)),
        7: tuple(range(538, 542)),
    }
    assert p12.VALIDATION_STRATA == {
        3: tuple(range(542, 546)),
        5: tuple(range(546, 550)),
        7: tuple(range(550, 554)),
    }
    assert p12.INTERVENTION_STARTS == {
        "calibration": (12, 42),
        "transfer": (13, 43),
        "validation": (14, 44),
    }


def test_forced_dropout_mask_depends_only_on_family_and_frame():
    a = pd.DataFrame(
        {
            "family": [506, 506, 506, 514, 514, 522, 522],
            "frame_index": [11, 12, 14, 12, 16, 12, 18],
            "truth_lateral_x_m": [0, 999, -20, 4, 7, 123, -50],
            "lateral_abs_error_m": [0, 1000, 5, 2, 99, 8, 11],
        }
    )
    b = a.copy()
    b["truth_lateral_x_m"] *= -123
    b["lateral_abs_error_m"] += 5000
    mask_a = p12.forced_dropout_mask(a, p12.CALIBRATION_STRATA, p12.INTERVENTION_STARTS["calibration"])
    mask_b = p12.forced_dropout_mask(b, p12.CALIBRATION_STRATA, p12.INTERVENTION_STARTS["calibration"])
    assert mask_a.tolist() == mask_b.tolist()
    assert mask_a.tolist() == [False, True, True, True, True, True, True]


def test_p12_power_margins_are_stricter_than_original_p9_minimums():
    for group, minimum in p9.CALIBRATION_MINIMUMS.items():
        assert p12.CALIBRATION_POWER_MINIMUMS[group] >= 2 * minimum
    assert p12.TRANSFER_POWER_MINIMUMS == {
        "base_output": 1200,
        "continuity_h3": 150,
        "continuity_h45": 75,
        "continuity_h67": 30,
    }
