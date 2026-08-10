import numpy as np

from uav_safety.perception import Observation
from uav_safety.phase6d_fusion import Phase6DComponentFusionAdapter
from uav_safety.reference_estimator import ReferenceObservation


def image_obs(*, z=2.0, vz=-0.55, sigma=0.18):
    return Observation(x=0.3, z=z, vx=0.2, vz=vz, confidence=0.9, sigma_pos=sigma, dropped=False)


def ref_obs(*, z=2.1, vz=-0.30, sigma=0.25, age=0, fresh=True, available=True):
    return ReferenceObservation(
        x=0.25, z=z, vx=0.15, vz=vz, sigma_pos=sigma,
        fresh=fresh, available=available, age_steps=age,
    )


def test_compatible_altitudes_do_not_trigger_hard_alias():
    adapter = Phase6DComponentFusionAdapter()
    image = image_obs(z=2.0)
    reference = ref_obs(z=2.1)
    base = adapter.base.update(image, reference).control_obs

    adapter = Phase6DComponentFusionAdapter()
    fused, diag = adapter.update(image, reference, p_x_good=0.95, p_z_good=0.95)
    assert not diag.hard_altitude_alias
    assert not diag.altitude_abstained
    assert np.isclose(fused.control_obs.vz, base.vz)


def test_soft_low_pz_blends_position_without_overwriting_vertical_rate():
    adapter = Phase6DComponentFusionAdapter()
    image = image_obs(z=2.0, vz=-0.60)
    reference = ref_obs(z=2.15, vz=0.25)
    base = adapter.base.update(image, reference).control_obs

    adapter = Phase6DComponentFusionAdapter()
    fused, diag = adapter.update(image, reference, p_x_good=0.95, p_z_good=0.35)
    assert diag.altitude_abstained
    assert not diag.hard_altitude_alias
    assert diag.altitude_reference_takeover
    assert abs(fused.control_obs.z - reference.z) < abs(base.z - reference.z)
    assert np.isclose(fused.control_obs.vz, base.vz)


def test_hard_altitude_contradiction_blends_both_z_and_vz():
    adapter = Phase6DComponentFusionAdapter()
    image = image_obs(z=4.8, vz=1.2, sigma=0.20)
    reference = ref_obs(z=0.25, vz=-0.25, sigma=0.22)
    base = adapter.base.update(image, reference).control_obs

    adapter = Phase6DComponentFusionAdapter()
    fused, diag = adapter.update(image, reference, p_x_good=0.95, p_z_good=0.98)
    assert diag.hard_altitude_alias
    assert diag.altitude_disagreement_sigma > 3.0
    assert diag.altitude_abstained
    assert diag.altitude_reference_takeover
    assert abs(fused.control_obs.z - reference.z) < abs(base.z - reference.z)
    assert abs(fused.control_obs.vz - reference.vz) < abs(base.vz - reference.vz)


def test_hard_alias_requires_usable_reference():
    image = image_obs(z=5.0, vz=1.2)
    reference = ref_obs(z=0.2, available=False, fresh=False, age=99)
    adapter = Phase6DComponentFusionAdapter()
    fused, diag = adapter.update(image, reference, p_x_good=0.95, p_z_good=0.95)
    assert not diag.hard_altitude_alias
    assert not diag.altitude_reference_takeover
    assert not fused.control_obs.dropped
