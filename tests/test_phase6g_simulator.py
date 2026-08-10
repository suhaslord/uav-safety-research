import numpy as np

from uav_safety.image_temporal import fit_synthetic_calibrator
from uav_safety.phase6e_perception import fit_phase6e_component_calibrator
from uav_safety.simulator_image_phase6g import run_phase6g_episode


def test_phase6g_episode_is_deterministic():
    temporal = fit_synthetic_calibrator(seed=616161, samples_per_condition=24)
    component = fit_phase6e_component_calibrator(seed=616161, samples_per_condition=40)

    a = run_phase6g_episode(123456, "occlusion", temporal, component)
    b = run_phase6g_episode(123456, "occlusion", temporal, component)

    assert a.to_dict() == b.to_dict()
    assert a.architecture == "image_aegis_phase6g"


def test_phase6g_component_metrics_are_bounded():
    temporal = fit_synthetic_calibrator(seed=626161, samples_per_condition=24)
    component = fit_phase6e_component_calibrator(seed=626161, samples_per_condition=40)
    result = run_phase6g_episode(654321, "mixed", temporal, component)

    assert result.frames > 0
    assert 0.0 <= result.image_abstention_rate <= 1.0
    assert 0.0 <= result.lateral_component_abstention_rate <= 1.0
    assert 0.0 <= result.altitude_component_abstention_rate <= 1.0
    assert 0.0 <= result.mean_p_x_good <= 1.0
    assert 0.0 <= result.mean_p_z_good <= 1.0
    assert result.lateral_reference_takeovers <= result.lateral_component_abstentions
    assert result.altitude_reference_takeovers <= result.altitude_component_abstentions
    assert np.isfinite(result.final_x_error)
