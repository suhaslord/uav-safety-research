import numpy as np

from uav_safety.perception import Observation
from uav_safety.phase6c_fusion import Phase6CComponentFusionAdapter
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


def _base_control(image, reference):
    adapter = Phase6CComponentFusionAdapter()
    return adapter.base.update(image, reference).control_obs


def test_high_component_confidence_preserves_base_phase6_control():
    image = image_obs()
    reference = ref_obs()
    base = _base_control(image, reference)

    adapter = Phase6CComponentFusionAdapter()
    fused, diag = adapter.update(image, reference, p_x_good=0.95, p_z_good=0.96)

    assert not diag.lateral_abstained
    assert not diag.altitude_abstained
    assert np.isclose(fused.control_obs.x, base.x)
    assert np.isclose(fused.control_obs.z, base.z)
    assert np.isclose(fused.control_obs.vx, base.vx)
    assert np.isclose(fused.control_obs.vz, base.vz)


def test_low_altitude_confidence_blends_z_but_preserves_phase6_vz():
    image = image_obs(vz=-0.62)
    reference = ref_obs(z=3.0, vz=0.35)
    base = _base_control(image, reference)

    adapter = Phase6CComponentFusionAdapter()
    fused, diag = adapter.update(image, reference, p_x_good=0.94, p_z_good=0.35)

    assert not diag.lateral_abstained
    assert diag.altitude_abstained
    assert not diag.lateral_reference_takeover
    assert diag.altitude_reference_takeover
    assert np.isclose(fused.control_obs.x, base.x)
    assert np.isclose(fused.control_obs.vx, base.vx)
    assert abs(fused.control_obs.z - reference.z) < abs(base.z - reference.z)
    # Phase 6C's defining invariant: altitude reliability says nothing about
    # velocity reliability, so z fallback must not inject reference vz.
    assert np.isclose(fused.control_obs.vz, base.vz)
    assert not np.isclose(fused.control_obs.vz, reference.vz)


def test_low_lateral_confidence_keeps_lateral_fallback_and_vertical_state():
    image = image_obs()
    reference = ref_obs()
    base = _base_control(image, reference)

    adapter = Phase6CComponentFusionAdapter()
    fused, diag = adapter.update(image, reference, p_x_good=0.30, p_z_good=0.95)

    assert diag.lateral_abstained
    assert not diag.altitude_abstained
    assert diag.lateral_reference_takeover
    assert not diag.altitude_reference_takeover
    assert abs(fused.control_obs.x - reference.x) < abs(base.x - reference.x)
    assert abs(fused.control_obs.vx - reference.vx) < abs(base.vx - reference.vx)
    assert np.isclose(fused.control_obs.z, base.z)
    assert np.isclose(fused.control_obs.vz, base.vz)


def test_unresolved_component_abstention_remains_explicitly_uncertain():
    image = image_obs(confidence=0.85, sigma=0.18)
    reference = ref_obs(available=False, fresh=False, age=99)
    adapter = Phase6CComponentFusionAdapter()
    fused, diag = adapter.update(image, reference, p_x_good=0.20, p_z_good=0.25)

    assert diag.lateral_abstained and diag.altitude_abstained
    assert not diag.lateral_reference_takeover
    assert not diag.altitude_reference_takeover
    assert fused.control_obs.dropped
    assert fused.control_obs.sigma_pos >= adapter.gate_cfg.unresolved_sigma_floor
    assert fused.control_obs.confidence < image.confidence


def test_threshold_value_is_accepted_not_abstained():
    adapter = Phase6CComponentFusionAdapter()
    fused, diag = adapter.update(image_obs(), ref_obs(), p_x_good=0.80, p_z_good=0.80)
    assert not diag.lateral_abstained
    assert not diag.altitude_abstained
    assert not fused.control_obs.dropped
