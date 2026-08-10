import numpy as np

from uav_safety.image_perception import SyntheticLandingPadRenderer
from uav_safety.image_temporal import (
    CalibratedTemporalImagePipeline,
    EmpiricalConfidenceCalibrator,
    Phase6PadEstimator,
    fit_synthetic_calibrator,
)
from uav_safety.simulator_image_v3 import run_image_episode


def _high_conf_calibrator():
    return EmpiricalConfidenceCalibrator(
        bin_edges=np.linspace(0.0, 1.0, 11),
        probability_good=np.full(10, 0.95),
        expected_x_error_m=np.full(10, 0.08),
        expected_z_error_m=np.full(10, 0.20),
    )


def test_phase6_clean_frame_estimates_lateral_position_and_altitude():
    renderer = SyntheticLandingPadRenderer()
    estimator = Phase6PadEstimator()
    image = renderer.render(0.9, 2.4, np.random.default_rng(42), "clean")
    measurement = estimator.estimate(image)
    assert measurement.valid
    assert abs(measurement.x_m - 0.9) < 0.35
    assert abs(measurement.z_m - 2.4) < 1.1
    assert 0.0 <= measurement.raw_confidence <= 1.0


def test_calibrator_is_monotone_in_raw_confidence():
    conf = np.linspace(0.02, 0.98, 200)
    xerr = np.linspace(1.2, 0.02, 200)
    zerr = np.linspace(2.0, 0.05, 200)
    calibrator = EmpiricalConfidenceCalibrator.fit(conf, xerr, zerr)
    calibrated = [calibrator.calibrate(v) for v in np.linspace(0.0, 1.0, 50)]
    assert np.all(np.diff(calibrated) >= -1e-12)


def test_temporal_pipeline_abstains_on_blank_frame():
    pipeline = CalibratedTemporalImagePipeline(_high_conf_calibrator())
    obs, diag = pipeline.update(np.zeros((96, 96), dtype=float))
    assert diag.abstained
    assert obs.dropped
    assert obs.confidence <= 0.05


def test_temporal_pipeline_accepts_clean_sequence():
    renderer = SyntheticLandingPadRenderer()
    pipeline = CalibratedTemporalImagePipeline(_high_conf_calibrator())
    rng = np.random.default_rng(8)
    accepted = 0
    last = None
    for k in range(6):
        image = renderer.render(0.6 - 0.01 * k, 3.0 - 0.03 * k, rng, "clean")
        obs, diag = pipeline.update(image)
        accepted += int(diag.accepted)
        last = obs
    assert accepted >= 4
    assert last is not None
    assert abs(last.x - 0.55) < 0.55


def test_default_synthetic_calibration_is_deterministic():
    a = fit_synthetic_calibrator(seed=1234, samples_per_condition=10)
    b = fit_synthetic_calibrator(seed=1234, samples_per_condition=10)
    assert np.allclose(a.probability_good, b.probability_good)
    assert np.allclose(a.expected_x_error_m, b.expected_x_error_m)


def test_image_aegis_episode_smoke_is_deterministic():
    calibrator = fit_synthetic_calibrator(seed=4321, samples_per_condition=10)
    a = run_image_episode(999, "clean", calibrator, architecture="image_aegis_v3")
    b = run_image_episode(999, "clean", calibrator, architecture="image_aegis_v3")
    assert a.outcome == b.outcome
    assert a.image_abstentions == b.image_abstentions
    assert np.isclose(a.final_x_error, b.final_x_error)
    assert 0.0 <= a.image_abstention_rate <= 1.0
