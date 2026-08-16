from __future__ import annotations

from scripts import run_phase11_p9_soft_update_direct_conformal as p9
from scripts import run_phase11_p11_powered_direct_conformal as p11


def test_p11_uses_fresh_disjoint_seeds():
    assert (p11.FIT_SEED, p11.CALIBRATION_SEED, p11.TRANSFER_SEED, p11.VALIDATION_SEED) == (495495, 506506, 517517, 528528)
    assert len({p11.FIT_SEED, p11.CALIBRATION_SEED, p11.TRANSFER_SEED, p11.VALIDATION_SEED}) == 4


def test_p11_preserves_p9_method_and_thresholds():
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


def test_p11_uses_thirty_fresh_calibration_families():
    assert len(p11.CALIBRATION_FAMILIES) == 30
    assert p11.CALIBRATION_FAMILIES == tuple(range(242, 272))
    assert set(p11.FIT_FAMILIES).isdisjoint(p11.CALIBRATION_FAMILIES)
    assert set(p11.CALIBRATION_FAMILIES).isdisjoint(p11.TRANSFER_FAMILIES)
    assert set(p11.TRANSFER_FAMILIES).isdisjoint(p11.VALIDATION_FAMILIES)
