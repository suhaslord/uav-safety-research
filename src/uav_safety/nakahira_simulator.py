from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from .config import ControllerConfig, SimConfig
from .controller import LandingController
from .dynamics import State, step_dynamics
from .dynamics_phase7 import Phase7DynamicsConfig, Phase7PlantMemory, step_phase7_dynamics
from .image_temporal import (
    CalibratedTemporalImagePipeline,
    EmpiricalConfidenceCalibrator,
    Phase6LandingPadRenderer,
    TemporalImageConfig,
)
from .phase6_fusion import Phase6FusionConfig
from .phase6_velocity import RobustImageVelocityFilter, RobustVelocityConfig
from .phase6b_fusion import Phase6BComponentFusionAdapter, Phase6BComponentGateConfig
from .phase7_faults import FaultScenario, Phase7FaultConfig, Phase7FaultInjector
from .phase7_reference import Phase7SensorStackConfig, Phase7SensorStackReferenceEstimator
from .selective_confidence_v2 import ComponentConfidenceCalibrator, SharpnessAwarePadEstimator
from .simulator import _wind_sample
from .simulator_phase7 import PLANT_MODELS, _apply_vision_fault, _phase7_image_rng
from .supervisor_v3 import DecisionV3, RedundantSafetySupervisorV3, SupervisorV3Config


@dataclass
class NakahiraEpisodeResult:
    seed: int
    condition: str
    fault_scenario: str
    plant_model: str
    outcome: str
    success: bool
    unsafe_touchdown: bool
    aborted: bool
    duration_s: float
    final_x_error: float
    final_vx: float
    final_vz: float
    frames: int
    trace: list[dict]

    def episode_dict(self) -> dict:
        data = asdict(self)
        data.pop("trace", None)
        return data


def run_nakahira_episode(
    seed: int,
    condition: str,
    temporal_calibrator: EmpiricalConfidenceCalibrator,
    component_calibrator: ComponentConfidenceCalibrator,
    *,
    fault_scenario: FaultScenario | str = FaultScenario.INDEPENDENT,
    plant_model: str = "phase7",
    severity: float = 1.0,
    sim_cfg: SimConfig | None = None,
    ctrl_cfg: ControllerConfig | None = None,
    image_cfg: TemporalImageConfig | None = None,
    sup_cfg: SupervisorV3Config | None = None,
    phase6_fusion_cfg: Phase6FusionConfig | None = None,
    component_gate_cfg: Phase6BComponentGateConfig | None = None,
    velocity_cfg: RobustVelocityConfig | None = None,
    sensor_cfg: Phase7SensorStackConfig | None = None,
    fault_cfg: Phase7FaultConfig | None = None,
    dynamics_cfg: Phase7DynamicsConfig | None = None,
) -> NakahiraEpisodeResult:
    """Trace-capable copy of the frozen Phase-7 landing loop.

    The controller, supervisor, fusion, image pipeline, reference stack, plant
    dynamics, random-stream separation, and terminal touchdown definitions are
    intentionally inherited from the Phase-7 implementation. This wrapper only
    records step-level evidence required to measure failure/recovery under
    uncertainty; it is not a new controller.
    """

    if plant_model not in PLANT_MODELS:
        raise ValueError(f"unknown plant model: {plant_model}")
    scenario = FaultScenario(fault_scenario)

    sim_cfg = sim_cfg or SimConfig()
    ctrl_cfg = ctrl_cfg or ControllerConfig()
    image_cfg = image_cfg or TemporalImageConfig(dt=sim_cfg.dt)
    sup_cfg = sup_cfg or SupervisorV3Config(dt=sim_cfg.dt)
    velocity_cfg = velocity_cfg or RobustVelocityConfig(dt=sim_cfg.dt)

    env_rng = np.random.default_rng(seed)
    reference_rng = np.random.default_rng(np.random.SeedSequence([seed, 7007]))
    fault_rng = np.random.default_rng(np.random.SeedSequence([seed, 7070]))
    fault_effect_rng = np.random.default_rng(np.random.SeedSequence([seed, 7071]))
    dynamics_rng = np.random.default_rng(np.random.SeedSequence([seed, 7072]))

    state = State(
        x=float(env_rng.uniform(*sim_cfg.initial_x_range)),
        z=float(env_rng.uniform(*sim_cfg.initial_z_range)),
        vx=float(env_rng.normal(0.0, 0.15)),
        vz=0.0,
    )
    plant_memory = Phase7PlantMemory()

    renderer = Phase6LandingPadRenderer()
    image_pipeline = CalibratedTemporalImagePipeline(temporal_calibrator, image_cfg)
    component_estimator = SharpnessAwarePadEstimator(
        image_cfg.min_component_pixels,
        image_cfg.min_bbox_width_px,
    )
    velocity_filter = RobustImageVelocityFilter(velocity_cfg)
    controller = LandingController(ctrl_cfg, sim_cfg)
    reference = Phase7SensorStackReferenceEstimator(reference_rng, sim_cfg.dt, sensor_cfg)
    fusion = Phase6BComponentFusionAdapter(sup_cfg, phase6_fusion_cfg, component_gate_cfg)
    supervisor = RedundantSafetySupervisorV3(sup_cfg)

    total_steps = int(sim_cfg.max_time / sim_cfg.dt)
    fault_injector = Phase7FaultInjector(
        fault_rng,
        scenario=scenario,
        total_steps=total_steps,
        dt=sim_cfg.dt,
        cfg=fault_cfg,
    )

    trace: list[dict] = []
    aborted = False
    outcome = "timeout"
    frames = 0

    for i in range(total_steps):
        t = i * sim_cfg.dt
        fault = fault_injector.state(i)

        frame = renderer.render(
            x_offset_m=state.x,
            altitude_m=max(0.08, state.z),
            rng=_phase7_image_rng(seed, i),
            condition=condition,
            severity=severity,
        )
        image_obs, _ = image_pipeline.update(frame)
        image_obs, _ = velocity_filter.update(image_obs)
        image_obs = _apply_vision_fault(image_obs, fault, fault_effect_rng)

        component_measurement = component_estimator.estimate(frame)
        p_x_good, p_z_good = component_calibrator.probabilities(component_measurement)
        if image_obs.dropped:
            p_x_good = 0.0
            p_z_good = 0.0

        ref_obs, ref_diag = reference.observe(state, fault)
        fused, component_diag = fusion.update(
            image_obs,
            ref_obs,
            p_x_good=p_x_good,
            p_z_good=p_z_good,
        )

        decision = supervisor.assess(image_obs, fused, ref_obs)
        frames += 1
        trace.append(
            {
                "step": i,
                "time_s": float(t),
                "state_x_m": float(state.x),
                "state_z_m": float(state.z),
                "state_vx_mps": float(state.vx),
                "state_vz_mps": float(state.vz),
                "decision": decision.decision.value,
                "risk": float(decision.risk),
                "instantaneous_risk": float(decision.instantaneous_risk),
                "control_x_m": float(fused.control_obs.x),
                "control_z_m": float(fused.control_obs.z),
                "control_confidence": float(fused.control_obs.confidence),
                "control_sigma_pos_m": float(fused.control_obs.sigma_pos),
                "image_dropped": bool(image_obs.dropped),
                "reference_available": bool(ref_obs.available),
                "reference_age_steps": int(ref_obs.age_steps),
                "reference_transport_latency_steps": int(ref_diag.delivered_transport_latency_steps),
                "reference_new_delivery": bool(ref_diag.new_delivery),
                "lateral_abstained": bool(component_diag.lateral_abstained),
                "altitude_abstained": bool(component_diag.altitude_abstained),
                "fault_active": bool(fault.active),
            }
        )

        descent_rate = sim_cfg.target_descent_rate
        if decision.decision == DecisionV3.ABORT:
            aborted = True
            outcome = "safe_abort"
            break
        if decision.decision == DecisionV3.HOLD:
            # Preserve Phase-7's exact behavior rather than substituting the
            # older SimConfig hold rate.
            descent_rate = -0.30

        cmd = controller.command(fused.control_obs, descent_rate)
        wind_ax, wind_az = _wind_sample(env_rng, t)
        if plant_model == "legacy":
            state = step_dynamics(
                state,
                cmd.ax,
                cmd.az,
                wind_ax,
                wind_az,
                sim_cfg,
            )
        else:
            state, plant_memory = step_phase7_dynamics(
                state,
                plant_memory,
                cmd.ax,
                cmd.az,
                wind_ax,
                wind_az,
                dynamics_rng,
                sim_cfg,
                dynamics_cfg,
            )

        if state.z <= 0.0:
            safe_x = abs(state.x) <= sim_cfg.touchdown_x_tolerance
            safe_vz = abs(state.vz) <= sim_cfg.touchdown_vz_limit
            safe_vx = abs(state.vx) <= sim_cfg.touchdown_vx_limit
            outcome = "success" if (safe_x and safe_vz and safe_vx) else "unsafe_touchdown"
            break

    return NakahiraEpisodeResult(
        seed=int(seed),
        condition=condition,
        fault_scenario=scenario.value,
        plant_model=plant_model,
        outcome=outcome,
        success=bool(outcome == "success"),
        unsafe_touchdown=bool(outcome == "unsafe_touchdown"),
        aborted=bool(aborted),
        duration_s=float(min(sim_cfg.max_time, (i + 1) * sim_cfg.dt)),
        final_x_error=float(abs(state.x)),
        final_vx=float(state.vx),
        final_vz=float(state.vz),
        frames=int(frames),
        trace=trace,
    )
