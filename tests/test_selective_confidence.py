import numpy as np

from uav_safety.image_temporal import Phase6LandingPadRenderer
from uav_safety.selective_confidence import (
    ContextualTemporalImagePipeline,
    fit_contextual_calibrator,
)


def test_contextual_calibrator_is_deterministic_and_bounded():
    a = fit_contextual_calibrator(seed=717171, samples_per_condition=24)
    b = fit_contextual_calibrator(seed=717171, samples_per_condition=24)
    assert np.allclose(a.weights, b.weights)
    assert np.isclose(a.intercept, b.intercept)
    assert np.isclose(a.platt_scale, b.platt_scale)
    assert np.isclose(a.platt_bias, b.platt_bias)

    renderer = Phase6LandingPadRenderer()
    frame = renderer.render(0.4, 3.5, np.random.default_rng(123), "clean", 1.0)
    measurement = ContextualTemporalImagePipeline(a).estimator.estimate(frame)
    p = a.calibrate_measurement(measurement)
    assert 0.0 <= p <= 1.0


def test_contextual_pipeline_abstains_on_blank_frame():
    calibrator = fit_contextual_calibrator(seed=818181, samples_per_condition=24)
    pipeline = ContextualTemporalImagePipeline(calibrator)
    obs, diag = pipeline.update(np.zeros((96, 96), dtype=float))
    assert diag.abstained
    assert obs.dropped
    assert diag.calibrated_confidence == 0.0


def test_clean_high_quality_frame_can_be_accepted():
    calibrator = fit_contextual_calibrator(seed=919191, samples_per_condition=30)
    pipeline = ContextualTemporalImagePipeline(calibrator)
    renderer = Phase6LandingPadRenderer()
    frame = renderer.render(0.2, 2.5, np.random.default_rng(44), "clean", 1.0)
    obs, diag = pipeline.update(frame)
    assert not obs.dropped
    assert diag.accepted
    assert diag.calibrated_confidence >= pipeline.cfg.min_calibrated_confidence
