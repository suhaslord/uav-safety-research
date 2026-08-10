from __future__ import annotations

import numpy as np

from uav_safety.config import SimConfig
from uav_safety.dynamics import State
from uav_safety.dynamics_phase7 import Phase7PlantMemory, step_phase7_dynamics
from uav_safety.phase7_faults import FaultScenario, Phase7FaultConfig, Phase7FaultInjector, FaultState
from uav_safety.phase7_reference import Phase7SensorStackConfig, Phase7SensorStackReferenceEstimator


def test_shared_bias_fault_moves_both_measurement_streams_same_direction():
    cfg = Phase7FaultConfig(
        onset_fraction_low=0.0,
        onset_fraction_high=0.0,
        duration_fraction_low=1.0,
        duration_fraction_high=1.0,
        shared_lateral_bias_m=0.6,
    )
    injector = Phase7FaultInjector(
        np.random.default_rng(1),
        scenario=FaultScenario.SHARED_LATERAL_BIAS,
        total_steps=20,
        dt=0.1,
        cfg=cfg,
    )
    fault = injector.state(19)
    assert fault.active
    assert fault.vision_x_bias_m > 0.0
    assert fault.reference_x_bias_m == fault.vision_x_bias_m


def test_sensor_stack_is_reproducible_for_identical_seed_and_states():
    states = [State(x=1.0 - 0.01 * i, z=4.0 - 0.02 * i, vx=-0.2, vz=-0.4) for i in range(20)]
    a = Phase7SensorStackReferenceEstimator(np.random.default_rng(22), 0.05)
    b = Phase7SensorStackReferenceEstimator(np.random.default_rng(22), 0.05)
    neutral = FaultState(active=False, scenario=FaultScenario.INDEPENDENT)

    out_a = [a.observe(state, neutral)[0] for state in states]
    out_b = [b.observe(state, neutral)[0] for state in states]

    assert [(o.x, o.z, o.vx, o.vz, o.available) for o in out_a] == [
        (o.x, o.z, o.vx, o.vz, o.available) for o in out_b
    ]


def test_sensor_stack_does_not_expose_exact_truth_as_reference():
    est = Phase7SensorStackReferenceEstimator(np.random.default_rng(33), 0.05)
    state = State(x=1.25, z=3.2, vx=-0.15, vz=-0.5)
    neutral = FaultState(active=False, scenario=FaultScenario.INDEPENDENT)
    observations = [est.observe(state, neutral)[0] for _ in range(12)]
    available = [o for o in observations if o.available]
    assert available
    assert any(abs(o.x - state.x) > 1e-8 or abs(o.z - state.z) > 1e-8 for o in available)


def test_delayed_sensor_acquisition_is_fresh_once_when_delivered():
    cfg = Phase7SensorStackConfig(
        gnss_update_every_steps=1,
        baro_update_every_steps=1,
        range_update_every_steps=1,
        base_latency_steps=2,
        gnss_dropout_prob=0.0,
        baro_dropout_prob=0.0,
        range_dropout_prob=0.0,
    )
    est = Phase7SensorStackReferenceEstimator(np.random.default_rng(34), 0.05, cfg)
    state = State(x=0.5, z=2.0, vx=0.0, vz=-0.2)
    neutral = FaultState(active=False, scenario=FaultScenario.INDEPENDENT)

    samples = [est.observe(state, neutral) for _ in range(6)]
    delivered = [(obs, diag) for obs, diag in samples if obs.available]
    assert delivered
    assert all(obs.age_steps >= cfg.base_latency_steps for obs, _ in delivered)
    assert all(diag.delivered_transport_latency_steps == cfg.base_latency_steps for _, diag in delivered)
    assert all(diag.new_delivery for _, diag in delivered)
    assert all(obs.fresh for obs, _ in delivered)


def test_latency_burst_holds_stale_reference_without_redelivering_old_packet_as_fresh():
    cfg = Phase7SensorStackConfig(
        gnss_update_every_steps=1,
        baro_update_every_steps=1,
        range_update_every_steps=1,
        base_latency_steps=1,
        gnss_dropout_prob=0.0,
        baro_dropout_prob=0.0,
        range_dropout_prob=0.0,
    )
    est = Phase7SensorStackReferenceEstimator(np.random.default_rng(35), 0.05, cfg)
    state = State(x=0.5, z=2.0, vx=0.0, vz=-0.2)
    neutral = FaultState(active=False, scenario=FaultScenario.INDEPENDENT)
    burst = FaultState(
        active=True,
        scenario=FaultScenario.LATENCY_BURST,
        reference_latency_extra_steps=3,
    )

    for _ in range(6):
        est.observe(state, neutral)

    first_obs, first_diag = est.observe(state, burst)
    second_obs, second_diag = est.observe(state, burst)

    assert first_obs.available and second_obs.available
    assert first_diag.applied_latency_steps == 4
    assert second_diag.applied_latency_steps == 4
    assert first_diag.delivered_transport_latency_steps == 1
    assert second_diag.delivered_transport_latency_steps == 1
    assert not first_diag.new_delivery
    assert not second_diag.new_delivery
    assert not first_obs.fresh
    assert not second_obs.fresh
    assert second_obs.age_steps > first_obs.age_steps


def test_latency_burst_packet_is_fresh_when_it_reaches_delivery_time():
    cfg = Phase7SensorStackConfig(
        gnss_update_every_steps=1,
        baro_update_every_steps=1,
        range_update_every_steps=1,
        base_latency_steps=1,
        gnss_dropout_prob=0.0,
        baro_dropout_prob=0.0,
        range_dropout_prob=0.0,
    )
    est = Phase7SensorStackReferenceEstimator(np.random.default_rng(36), 0.05, cfg)
    state = State(x=0.5, z=2.0, vx=0.0, vz=-0.2)
    neutral = FaultState(active=False, scenario=FaultScenario.INDEPENDENT)
    burst = FaultState(
        active=True,
        scenario=FaultScenario.LATENCY_BURST,
        reference_latency_extra_steps=3,
    )

    for _ in range(5):
        est.observe(state, neutral)

    burst_samples = [est.observe(state, burst) for _ in range(8)]
    four_step_deliveries = [
        (obs, diag)
        for obs, diag in burst_samples
        if diag.new_delivery and diag.delivered_transport_latency_steps == 4
    ]
    assert four_step_deliveries
    assert all(obs.fresh for obs, _ in four_step_deliveries)
    assert all(obs.age_steps >= 4 for obs, _ in four_step_deliveries)


def test_phase7_dynamics_has_actuator_lag():
    sim = SimConfig(dt=0.05)
    state = State(x=0.0, z=5.0, vx=0.0, vz=0.0)
    memory = Phase7PlantMemory()
    next_state, next_memory = step_phase7_dynamics(
        state,
        memory,
        ax_cmd=2.0,
        az_cmd=-1.0,
        wind_ax=0.0,
        wind_az=0.0,
        rng=np.random.default_rng(44),
        sim_cfg=sim,
    )
    assert 0.0 < next_memory.actual_ax < 2.0
    assert -1.0 < next_memory.actual_az < 0.0
    assert next_state.vx != 0.0
