from __future__ import annotations

import numpy as np

from uav_safety.dynamics import State
from uav_safety.perception import Observation
from uav_safety.reference_estimator import IndependentReferenceEstimator, ReferenceObservation
from uav_safety.simulator_v3 import run_episode_v3
from uav_safety.supervisor_v3 import RedundantStateFusion


def _vision(x: float, sigma: float = 0.68) -> Observation:
    return Observation(
        x=x,
        z=4.0,
        vx=0.0,
        vz=-0.5,
        confidence=0.45,
        sigma_pos=sigma,
        dropped=False,
    )


def _reference(x: float) -> ReferenceObservation:
    return ReferenceObservation(
        x=x,
        z=4.0,
        vx=0.0,
        vz=-0.5,
        sigma_pos=0.34,
        fresh=True,
        available=True,
        age_steps=0,
    )


def test_reference_estimator_is_lower_rate_and_reproducible():
    state = State(x=0.4, z=5.0, vx=0.1, vz=-0.2)
    a = IndependentReferenceEstimator(np.random.default_rng(123), dt=0.05)
    b = IndependentReferenceEstimator(np.random.default_rng(123), dt=0.05)

    seq_a = [a.observe(state) for _ in range(20)]
    seq_b = [b.observe(state) for _ in range(20)]

    assert seq_a == seq_b
    fresh_count = sum(obs.fresh for obs in seq_a)
    assert 1 <= fresh_count <= 4
    assert any(obs.available and not obs.fresh for obs in seq_a)


def test_fusion_learns_persistent_lateral_bias():
    fusion = RedundantStateFusion()
    result = None

    for _ in range(30):
        raw = _vision(0.62)
        result = fusion.update(raw, raw, _reference(0.0))

    assert result is not None
    assert result.bias_estimate_x > 0.50
    assert result.bias_confidence > 0.70
    assert result.applied_bias_correction > 0.40
    assert abs(result.control_obs.x) < 0.25


def test_fusion_does_not_invent_large_bias_when_estimators_agree():
    fusion = RedundantStateFusion()
    result = None

    for _ in range(30):
        raw = _vision(0.03, sigma=0.08)
        result = fusion.update(raw, raw, _reference(0.0))

    assert result is not None
    assert abs(result.applied_bias_correction) < 0.08
    assert abs(result.control_obs.x) < 0.08


def test_v3_episode_is_exactly_reproducible_for_same_seed():
    first = run_episode_v3(seed=8128, profile="mixed").to_dict()
    second = run_episode_v3(seed=8128, profile="mixed").to_dict()
    assert first == second


def test_v3_exposes_research_diagnostics():
    result = run_episode_v3(seed=42, profile="occlusion")
    assert result.reference_updates > 0
    assert result.max_normalized_disagreement >= 0.0
    assert 0.0 <= result.final_bias_confidence <= 1.0
    assert 0.0 <= result.mean_reference_weight <= 0.32
