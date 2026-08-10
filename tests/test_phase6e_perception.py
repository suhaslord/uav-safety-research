import numpy as np

from uav_safety.image_temporal import Phase6LandingPadRenderer
from uav_safety.phase6e_perception import (
    Phase6ERobustPadEstimator,
    fit_phase6e_component_calibrator,
)
from uav_safety.selective_confidence_v2 import SharpnessAwarePadEstimator


def test_phase6e_fixes_known_clean_near_ground_alias_frame():
    renderer = Phase6LandingPadRenderer()
    historical = SharpnessAwarePadEstimator()
    candidate = Phase6ERobustPadEstimator()
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


def test_phase6e_fixes_archived_occlusion_near_ground_alias_frame():
    renderer = Phase6LandingPadRenderer()
    historical = SharpnessAwarePadEstimator()
    candidate = Phase6ERobustPadEstimator()
    true_z = 0.08
    frame = renderer.render(
        x_offset_m=-0.454723,
        altitude_m=true_z,
        rng=np.random.default_rng(1514818703),
        condition="occlusion",
        severity=1.0,
    )

    old = historical.estimate(frame)
    new = candidate.estimate(frame)
    assert old.valid and new.valid
    assert abs(old.z_m - true_z) > 4.0
    assert abs(new.z_m - true_z) < 0.20


def test_phase6e_mid_altitude_clean_estimate_remains_accurate():
    renderer = Phase6LandingPadRenderer()
    candidate = Phase6ERobustPadEstimator()
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


def test_phase6e_component_calibrator_is_deterministic_and_bounded():
    a = fit_phase6e_component_calibrator(seed=616161, samples_per_condition=40)
    b = fit_phase6e_component_calibrator(seed=616161, samples_per_condition=40)
    assert np.allclose(a.x_model.weights, b.x_model.weights)
    assert np.allclose(a.z_model.weights, b.z_model.weights)

    renderer = Phase6LandingPadRenderer()
    estimator = Phase6ERobustPadEstimator()
    frame = renderer.render(0.2, 0.18, np.random.default_rng(2222), "clean", 1.0)
    measurement = estimator.estimate(frame)
    p_x, p_z = a.probabilities(measurement)
    assert 0.0 <= p_x <= 1.0
    assert 0.0 <= p_z <= 1.0
