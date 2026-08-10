import numpy as np

from uav_safety.image_temporal import Phase6LandingPadRenderer
from uav_safety.selective_confidence_v2 import (
    SharpnessAwarePadEstimator,
    altitude_observability_cap,
    altitude_scale_bin_width_m,
    fit_component_calibrator,
)


def test_sharpness_feature_is_lower_after_blur_for_same_scene():
    renderer = Phase6LandingPadRenderer()
    estimator = SharpnessAwarePadEstimator()
    clean = renderer.render(0.3, 3.0, np.random.default_rng(1234), "clean", 1.0)
    blur = renderer.render(0.3, 3.0, np.random.default_rng(1234), "blur", 1.0)
    m_clean = estimator.estimate(clean)
    m_blur = estimator.estimate(blur)
    assert m_clean.valid and m_blur.valid
    assert m_clean.sharpness_score > m_blur.sharpness_score


def test_component_calibrator_is_deterministic_and_bounded():
    a = fit_component_calibrator(seed=515151, samples_per_condition=36)
    b = fit_component_calibrator(seed=515151, samples_per_condition=36)
    assert np.allclose(a.x_model.weights, b.x_model.weights)
    assert np.allclose(a.z_model.weights, b.z_model.weights)

    renderer = Phase6LandingPadRenderer()
    estimator = SharpnessAwarePadEstimator()
    frame = renderer.render(-0.4, 2.8, np.random.default_rng(99), "clean", 1.0)
    m = estimator.estimate(frame)
    px, pz = a.probabilities(m)
    assert 0.0 <= px <= 1.0
    assert 0.0 <= pz <= 1.0
    assert 0.0 <= a.joint_probability_lower_bound(m) <= 1.0


def test_invalid_measurement_has_zero_component_confidence():
    cal = fit_component_calibrator(seed=525252, samples_per_condition=32)
    estimator = SharpnessAwarePadEstimator()
    m = estimator.estimate(np.zeros((96, 96), dtype=float))
    assert not m.valid
    assert cal.probabilities(m) == (0.0, 0.0)


def test_scale_quantization_uncertainty_increases_at_high_altitude():
    renderer = Phase6LandingPadRenderer()
    estimator = SharpnessAwarePadEstimator()
    low = estimator.estimate(renderer.render(0.0, 3.0, np.random.default_rng(11), "clean", 1.0))
    high = estimator.estimate(renderer.render(0.0, 7.2, np.random.default_rng(12), "clean", 1.0))
    assert low.valid and high.valid
    assert altitude_scale_bin_width_m(high) > altitude_scale_bin_width_m(low)
    assert altitude_observability_cap(high) < altitude_observability_cap(low)
    assert altitude_observability_cap(high) < 0.80


def test_reported_altitude_probability_respects_observability_cap():
    calibrator = fit_component_calibrator(seed=535353, samples_per_condition=40)
    renderer = Phase6LandingPadRenderer()
    estimator = SharpnessAwarePadEstimator()
    measurement = estimator.estimate(
        renderer.render(0.1, 7.0, np.random.default_rng(77), "clean", 1.0)
    )
    learned_x, learned_z = calibrator.learned_probabilities(measurement)
    px, pz = calibrator.probabilities(measurement)
    cap = altitude_observability_cap(measurement, calibrator.tolerance_z_m)
    assert np.isclose(px, learned_x)
    assert pz <= learned_z + 1e-12
    assert pz <= cap + 1e-12
