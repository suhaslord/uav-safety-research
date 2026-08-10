import numpy as np

from uav_safety.dynamics import State
from uav_safety.image_perception import SyntheticLandingPadRenderer, ThresholdPadEstimator
from uav_safety.perception import PROFILES, PerceptionModel
from uav_safety.robustness import (
    bias_magnitude_scenarios,
    degradation_scenarios,
    reference_dropout_scenarios,
    reference_quality_scenarios,
    scale_perception,
    seed_family_scenarios,
)
from uav_safety.simulator_v3 import run_episode_v3


def test_frozen_named_profiles_are_not_mutated_by_scaling():
    original = PROFILES["mixed"]
    scaled = scale_perception(original, 1.4)
    assert PROFILES["mixed"].bias_x == 0.62
    assert scaled is not original
    assert scaled.sigma_x > original.sigma_x
    assert scaled.dropout_prob > original.dropout_prob


def test_robustness_scenario_matrix_is_explicit_and_ordered():
    assert len(degradation_scenarios()) == 6
    assert len(reference_quality_scenarios()) == 4
    assert len(reference_dropout_scenarios()) == 6
    assert len(bias_magnitude_scenarios()) == 7
    assert len(seed_family_scenarios()) == 2
    assert bias_magnitude_scenarios()[3].perception_profile.bias_x == 0.62


def test_custom_perception_profile_is_deterministic():
    custom = scale_perception(PROFILES["occlusion"], 1.25)
    state = State(x=0.5, z=2.0, vx=0.1, vz=-0.2)
    a = PerceptionModel(custom, np.random.default_rng(123), profile_name="stress")
    b = PerceptionModel(custom, np.random.default_rng(123), profile_name="stress")
    assert a.observe(state) == b.observe(state)


def test_v3_accepts_explicit_robustness_profile():
    custom = scale_perception(PROFILES["mixed"], 1.1)
    result = run_episode_v3(777, "custom_mixed", perception_profile=custom)
    assert result.profile == "custom_mixed"
    assert result.outcome in {"success", "unsafe_touchdown", "safe_abort", "timeout"}
    assert np.isfinite(result.final_x_error)


def test_synthetic_image_estimator_tracks_clean_lateral_offset():
    renderer = SyntheticLandingPadRenderer()
    estimator = ThresholdPadEstimator()
    image = renderer.render(
        x_offset_m=1.0,
        altitude_m=2.0,
        rng=np.random.default_rng(42),
        condition="clean",
    )
    estimate = estimator.estimate(image)
    assert estimate.valid
    assert abs(estimate.x_m - 1.0) < 0.45
    assert 0.0 <= estimate.confidence <= 1.0


def test_synthetic_image_conditions_are_bounded_grayscale():
    renderer = SyntheticLandingPadRenderer()
    for condition in ("clean", "blur", "low_light", "occlusion", "mixed"):
        image = renderer.render(
            x_offset_m=-0.7,
            altitude_m=3.0,
            rng=np.random.default_rng(100 + len(condition)),
            condition=condition,
        )
        assert image.shape == (96, 96)
        assert float(image.min()) >= 0.0
        assert float(image.max()) <= 1.0
