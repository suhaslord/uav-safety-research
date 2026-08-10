import numpy as np

from uav_safety.perception import Observation
from uav_safety.phase6_fusion import Phase6RedundantFusionAdapter
from uav_safety.reference_estimator import ReferenceObservation


def image_obs(*, x=0.4, z=2.0, vx=0.1, vz=-0.5, confidence=0.85, sigma=0.18, dropped=False):
    return Observation(
        x=x,
        z=z,
        vx=vx,
        vz=vz,
        confidence=confidence,
        sigma_pos=sigma,
        dropped=dropped,
    )


def ref_obs(*, x=0.8, z=3.5, vx=-0.7, vz=0.2, fresh=True, age=0):
    return ReferenceObservation(
        x=x,
        z=z,
        vx=vx,
        vz=vz,
        sigma_pos=0.34,
        fresh=fresh,
        available=True,
        age_steps=age,
    )


def test_accepted_image_keeps_vertical_state_primary_before_bias_evidence():
    adapter = Phase6RedundantFusionAdapter()
    image = image_obs()
    fused = adapter.update(image, ref_obs())
    assert np.isclose(fused.control_obs.x, image.x)
    assert np.isclose(fused.control_obs.z, image.z)
    assert np.isclose(fused.control_obs.vx, image.vx)
    assert np.isclose(fused.control_obs.vz, image.vz)
    assert fused.reference_weight == 0.0


def test_dropped_image_uses_fresh_reference_as_fallback():
    adapter = Phase6RedundantFusionAdapter()
    image = image_obs(x=1.2, z=2.5, dropped=True, confidence=0.15, sigma=1.2)
    reference = ref_obs(x=0.1, z=2.4, vx=0.0, vz=-0.4)
    fused = adapter.update(image, reference)
    assert fused.reference_weight > 0.45
    assert abs(fused.control_obs.x - reference.x) < abs(image.x - reference.x)
    assert fused.control_obs.confidence > image.confidence


def test_persistent_lateral_disagreement_eventually_enables_bias_correction():
    adapter = Phase6RedundantFusionAdapter()
    corrections = []
    weights = []
    for _ in range(24):
        image = image_obs(x=0.85, z=2.0, vx=0.0, vz=-0.5)
        reference = ref_obs(x=0.05, z=2.0, vx=0.0, vz=-0.5)
        fused = adapter.update(image, reference)
        corrections.append(fused.applied_bias_correction)
        weights.append(fused.reference_weight)

    assert max(corrections) > 0.25
    assert fused.control_obs.x < image.x - 0.20
    assert max(weights) <= 0.10 + 1e-12
