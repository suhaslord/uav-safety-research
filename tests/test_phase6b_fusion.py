import numpy as np

from uav_safety.perception import Observation
from uav_safety.phase6b_fusion import Phase6BComponentFusionAdapter
from uav_safety.reference_estimator import ReferenceObservation


def image_obs(*, x=0.45, z=2.2, vx=0.25, vz=-0.55, confidence=0.88, sigma=0.16, dropped=False):
    return Observation(
        x=x,
        z=z,
        vx=vx,
        vz=vz,
        confidence=confidence,
        sigma_pos=sigma,
        dropped=dropped,
    )


def ref_obs(*, x=-0.20, z=2.7, vx=-0.35, vz=-0.25, fresh=True, available=True, age=0):
    return ReferenceObservation(
        x=x,
        z=z,
        vx=vx,
        vz=vz,
        sigma_pos=0.30,
        fresh=fresh,
        available=available,
        age_steps=age,
    )


def test_high_component_confidence_preserves_base_phase6_control():
    adapter_a = Phase6BComponentFusionAdapter()
    adapter_b = Phase6BComponentFusionAdapter()
    image = image_obs()
    reference = ref_obs()

    base = adapter_a.base.update(image, reference)
    fused, diag = adapter_b.update(image, reference, p_x_good=0.95, p_z_good=0.96)

    assert not diag.lateral_abstained
    assert not diag.altitude_abstained
    assert not diag.lateral_reference_takeover
    assert not diag.altitude_reference_takeover
    assert np.isclose(fused.control_obs.x, base.control_obs.x)
    assert np.isclose(fused.control_obs.z, base.control_obs.z)
    assert np.isclose(fused.control_obs.vx, base.control_obs.vx)
    assert np.isclose(fused.control_obs.vz, base.control_obs.vz)


def test_low_altitude_confidence_replaces_only_vertical_components():
    adapter = Phase6BComponentFusionAdapter()
    image = image_obs()
    reference = ref_obs()
    base = adapter.base.update(image, reference)

    # Use a fresh adapter for the actual comparison so internal bias history is equal.
    adapter = Phase6BComponentFusionAdapter()
    fused, diag = adapter.update(image, reference, p_x_good=0.94, p_z_good=0.35)

    assert not diag.lateral_abstained
    assert diag.altitude_abstained
    assert not diag.lateral_reference_takeover
    assert diag.altitude_reference_takeover
    assert np.isclose(fused.control_obs.x, base.control_obs.x)
    assert np.isclose(fused.control_obs.vx, base.control_obs.vx)
    assert abs(fused.control_obs.z - reference.z) < abs(base.control_obs.z - reference.z)
    assert abs(fused.control_obs.vz - reference.vz) < abs(base.control_obs.vz - reference.vz)


def test_low_lateral_confidence_replaces_only_lateral_components():
    image = image_obs()
    reference = ref_obs()
    base_adapter = Phase6BComponentFusionAdapter()
    base = base_adapter.base.update(image, reference)

    adapter = Phase6BComponentFusionAdapter()
    fused, diag = adapter.update(image, reference, p_x_good=0.30, p_z_good=0.95)

    assert diag.lateral_abstained
    assert not diag.altitude_abstained
    assert diag.lateral_reference_takeover
    assert not diag.altitude_reference_takeover
    assert abs(fused.control_obs.x - reference.x) < abs(base.control_obs.x - reference.x)
    assert abs(fused.control_obs.vx - reference.vx) < abs(base.control_obs.vx - reference.vx)
    assert np.isclose(fused.control_obs.z, base.control_obs.z)
    assert np.isclose(fused.control_obs.vz, base.control_obs.vz)


def test_unresolved_component_abstention_marks_control_state_dropped():
    adapter = Phase6BComponentFusionAdapter()
    image = image_obs(confidence=0.85, sigma=0.18)
    reference = ref_obs(available=False, fresh=False, age=99)
    fused, diag = adapter.update(image, reference, p_x_good=0.20, p_z_good=0.25)

    assert diag.lateral_abstained and diag.altitude_abstained
    assert not diag.lateral_reference_takeover
    assert not diag.altitude_reference_takeover
    assert fused.control_obs.dropped
    assert fused.control_obs.sigma_pos >= adapter.gate_cfg.unresolved_sigma_floor
    assert fused.control_obs.confidence < image.confidence


def test_threshold_value_is_accepted_not_abstained():
    adapter = Phase6BComponentFusionAdapter()
    fused, diag = adapter.update(image_obs(), ref_obs(), p_x_good=0.80, p_z_good=0.80)
    assert not diag.lateral_abstained
    assert not diag.altitude_abstained
    assert not fused.control_obs.dropped
