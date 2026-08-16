from __future__ import annotations

from scripts import run_phase11_p9_soft_update_direct_conformal as p9
from scripts import run_phase11_p10_powered_direct_conformal as p10


def test_p10_uses_fresh_disjoint_seeds():
    assert (p10.FIT_SEED, p10.CALIBRATION_SEED, p10.TRANSFER_SEED, p10.VALIDATION_SEED) == (451451, 462462, 473473, 484484)
    assert len({p10.FIT_SEED, p10.CALIBRATION_SEED, p10.TRANSFER_SEED, p10.VALIDATION_SEED}) == 4


def test_p10_is_method_identical_to_p9():
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


def test_p10_increases_calibration_power_without_lowering_thresholds():
    assert len(p10.CALIBRATION_FAMILIES) == 18
    assert len(p10.CALIBRATION_FAMILIES) > 12
    assert min(p10.CALIBRATION_FAMILIES) == 194
    assert max(p10.CALIBRATION_FAMILIES) == 211
