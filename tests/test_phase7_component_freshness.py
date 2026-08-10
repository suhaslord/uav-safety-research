from __future__ import annotations

import pytest

from uav_safety.perception import Observation
from uav_safety.phase6b_fusion import Phase6BComponentFusionAdapter
from uav_safety.reference_estimator import ReferenceObservation


def _image() -> Observation:
    return Observation(
        x=1.0,
        z=1.0,
        vx=0.0,
        vz=-0.2,
        confidence=0.9,
        sigma_pos=0.2,
        dropped=False,
    )


def _reference(*, fresh: bool = False) -> ReferenceObservation:
    return ReferenceObservation(
        x=0.0,
        z=0.8,
        vx=0.0,
        vz=-0.1,
        sigma_pos=0.2,
        fresh=fresh,
        available=True,
        age_steps=0,
    )


def test_phase7_component_freshness_weights_are_independent():
    adapter = Phase6BComponentFusionAdapter()
    _, diag = adapter.update(
        _image(),
        _reference(fresh=False),
        p_x_good=0.1,
        p_z_good=0.1,
        lateral_reference_fresh=False,
        altitude_reference_fresh=True,
    )

    assert diag.lateral_reference_takeover
    assert diag.altitude_reference_takeover
    assert diag.altitude_reference_weight > diag.lateral_reference_weight


def test_omitted_component_freshness_preserves_historical_scalar_behavior():
    image = _image()
    reference = _reference(fresh=True)

    historical_adapter = Phase6BComponentFusionAdapter()
    explicit_adapter = Phase6BComponentFusionAdapter()

    historical_fused, historical_diag = historical_adapter.update(
        image,
        reference,
        p_x_good=0.1,
        p_z_good=0.1,
    )
    explicit_fused, explicit_diag = explicit_adapter.update(
        image,
        reference,
        p_x_good=0.1,
        p_z_good=0.1,
        lateral_reference_fresh=reference.fresh,
        altitude_reference_fresh=reference.fresh,
    )

    assert historical_diag.lateral_reference_weight == pytest.approx(explicit_diag.lateral_reference_weight)
    assert historical_diag.altitude_reference_weight == pytest.approx(explicit_diag.altitude_reference_weight)
    assert historical_fused.control_obs.x == pytest.approx(explicit_fused.control_obs.x)
    assert historical_fused.control_obs.z == pytest.approx(explicit_fused.control_obs.z)
    assert historical_fused.control_obs.vx == pytest.approx(explicit_fused.control_obs.vx)
    assert historical_fused.control_obs.vz == pytest.approx(explicit_fused.control_obs.vz)
    assert historical_fused.control_obs.confidence == pytest.approx(explicit_fused.control_obs.confidence)
    assert historical_fused.control_obs.sigma_pos == pytest.approx(explicit_fused.control_obs.sigma_pos)
    assert historical_fused.control_obs.dropped == explicit_fused.control_obs.dropped
