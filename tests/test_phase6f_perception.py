import numpy as np

from uav_safety.image_temporal import Phase6LandingPadRenderer
from uav_safety.phase6e_perception import Phase6ERobustPadEstimator
from uav_safety.phase6f_perception import (
    Phase6FDistributionAwarePadEstimator,
    fit_phase6f_component_calibrator,
)
from uav_safety.selective_confidence_v2 import SharpnessAwarePadEstimator


def test_phase6f_preserves_near_ground_clean_alias_fix():
    renderer = Phase6LandingPadRenderer()
    historical = SharpnessAwarePadEstimator()
    candidate = Phase6FDistributionAwarePadEstimator()
    true_z = 0.18
    frame = renderer.render(
        x_offset_m=0.609019,
        altitude_m=true_z,
        rng=np.random.default_rng(1217534381),
        condition="clean",
        severity=1.0,
    )
    old = historical.estimate(frame)
    new = candidate.estimate(frame)
    assert old.valid and new.valid
    assert abs(old.z_m - true_z) > 2.0
    assert abs(new.z_m - true_z) < 0.20


def test_phase6f_preserves_near_ground_occlusion_alias_fix():
    renderer = Phase6LandingPadRenderer()
    candidate = Phase6FDistributionAwarePadEstimator()
    true_z = 0.08
    frame = renderer.render(
        x_offset_m=-0.454723,
        altitude_m=true_z,
        rng=np.random.default_rng(1514818703),
        condition="occlusion",
        severity=1.0,
    )
    new = candidate.estimate(frame)
    assert new.valid
    assert abs(new.z_m - true_z) < 0.20


def test_phase6f_does_not_trigger_p30_on_phase6e_high_altitude_residual():
    renderer = Phase6LandingPadRenderer()
    phase6e = Phase6ERobustPadEstimator()
    candidate = Phase6FDistributionAwarePadEstimator()
    true_z = 6.0
    frame = renderer.render(
        x_offset_m=-0.723186,
        altitude_m=true_z,
        rng=np.random.default_rng(944050995),
        condition="occlusion",
        severity=1.0,
    )

    background, use_p30 = candidate.background_level(frame)
    old_e = phase6e.estimate(frame)
    new_f = candidate.estimate(frame)
    assert not use_p30
    assert np.isclose(background, np.median(frame))
    assert abs(old_e.z_m - true_z) > 0.85
    assert abs(new_f.z_m - true_z) <= 0.85


def test_phase6f_mid_altitude_clean_remains_accurate():
    renderer = Phase6LandingPadRenderer()
    candidate = Phase6FDistributionAwarePadEstimator()
    true_z = 3.0
    frame = renderer.render(
        x_offset_m=0.4,
        altitude_m=true_z,
        rng=np.random.default_rng(7777),
        condition="clean",
        severity=1.0,
    )
    measurement = candidate.estimate(frame)
    assert measurement.valid
    assert abs(measurement.z_m - true_z) < 0.20


def test_phase6f_component_calibrator_is_deterministic_and_bounded():
    a = fit_phase6f_component_calibrator(seed=616161, samples_per_condition=40)
    b = fit_phase6f_component_calibrator(seed=616161, samples_per_condition=40)
    assert np.allclose(a.x_model.weights, b.x_model.weights)
    assert np.allclose(a.z_model.weights, b.z_model.weights)

    renderer = Phase6LandingPadRenderer()
    estimator = Phase6FDistributionAwarePadEstimator()
    frame = renderer.render(0.2, 0.18, np.random.default_rng(2222), "clean", 1.0)
    measurement = estimator.estimate(frame)
    p_x, p_z = a.probabilities(measurement)
    assert 0.0 <= p_x <= 1.0
    assert 0.0 <= p_z <= 1.0
