from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from .config import ControllerConfig, SimConfig
from .controller import LandingController
from .dynamics import State
from .dynamics_phase7 import Phase7DynamicsConfig, Phase7PlantMemory, step_phase7_dynamics
from .image_perception import IMAGE_CONDITIONS
from .image_temporal import (
    CalibratedTemporalImagePipeline,
    EmpiricalConfidenceCalibrator,
    Phase6LandingPadRenderer,
    TemporalImageConfig,
)
from .perception import Observation
from .phase6_fusion import Phase6FusionConfig
from .phase6_velocity import RobustImageVelocityFilter, RobustVelocityConfig
from .phase6b_fusion import Phase6BComponentFusionAdapter, Phase6BComponentGateConfig
from .phase7_faults import FaultScenario, Phase7FaultConfig, Phase7FaultInjector
from .phase7_reference import Phase7SensorStackConfig, Phase7SensorStackReferenceEstimator
from .selective_confidence_v2 import ComponentConfidenceCalibrator, SharpnessAwarePadEstimator
from .simulator import _wind_sample
from .supervisor_v3 import DecisionV3, RedundantSafetySupervisorV3, SupervisorV3Config


@dataclass
class Phase7EpisodeResult:
    seed: int
    condition: str
    fault_scenario: str
    architecture: str
    outcome: str
    success: bool
    unsafe_touchdown: bool
    aborted: bool
    duration_s: float
    final_x_error: float
    final_vx: float
    final_vz: float
    frames: int
    fault_active_frames: int
    reference_available_rate: float
    gnss_fresh_rate: float
    baro_fresh_rate: float
    range_fresh_rate: float
    mean_reference_latency_steps: float
    max_abs_reference_bias_x_m: float
    max_abs_shared_vision_bias_x_m: float
    lateral_component_abstention_rate: float
    altitude_component_abstention_rate: float
    mean_interventions: float
    max_risk: float
    mean_risk: float

    def to_dict(self) -> dict:
        return asdict(self)


def _apply_vision_fault(
    obs: Observation,
    fault,
    rng: np.random.Generator,
) -> Observation:
    dropped = bool(obs.dropped)
    confidence = float(obs.confidence)
    sigma_pos = float(obs.sigma_pos)

    if fault.vision_dropout_boost > 0.0 and rng.random() < fault.vision_dropout_boost:
        dropped = True
        confidence = max(0.02, 0.25 * confidence)
        sigma_pos = max(sigma_pos, 1.20)

    return Observation(
        x=float(obs.x + fault.vision_x_bias_m),
        z=float(obs.z),
        vx=float(obs.vx),
        vz=float(obs.vz),
        confidence=confidence,
        sigma_pos=sigma_pos,
        dropped=dropped,
    )


def run_phase7_episode(
    seed: int,
    condition: str,
    temporal_calibrator: EmpiricalConfidenceCalibrator,
    component_calibrator: ComponentConfidenceCalibrator,
    *,
    fault_scenario: FaultScenario | str = FaultScenario.INDEPENDENT,
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
) -> Phase7EpisodeResult:
    """Run the Phase 7 simulation-only external-validity stress architecture."""

    if condition not in IMAGE_CONDITIONS:
        raise ValueError(f"Unknown image condition: {condition}")
    scenario = FaultScenario(fault_scenario)

    sim_cfg = sim_cfg or SimConfig()
    ctrl_cfg = ctrl_cfg or ControllerConfig()
    image_cfg = image_cfg or TemporalImageConfig(dt=sim_cfg.dt)
    sup_cfg = sup_cfg or SupervisorV3Config(dt=sim_cfg.dt)
    velocity_cfg = velocity_cfg or RobustVelocityConfig(dt=sim_cfg.dt)

    env_rng = np.random.default_rng(seed)
    image_rng = np.random.default_rng(np.random.SeedSequence([seed, 6006]))
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

    fault_active_frames = 0
    reference_available = 0
    gnss_fresh = 0
    baro_fresh = 0
    range_fresh = 0
    latency_steps: list[int] = []
    reference_biases: list[float] = []
    shared_vision_biases: list[float] = []
    lateral_abstentions = 0
    altitude_abstentions = 0
    interventions = 0
    risks: list[float] = []
    frames = 0
    aborted = False
    outcome = "timeout"

    for i in range(total_steps):
        t = i * sim_cfg.dt
        fault = fault_injector.state(i)
        fault_active_frames += int(fault.active)
        shared_vision_biases.append(abs(float(fault.vision_x_bias_m)))

        frame = renderer.render(
            x_offset_m=state.x,
            altitude_m=max(0.08, state.z),
            rng=image_rng,
            condition=condition,
            severity=severity,
        )
        image_obs, _ = image_pipeline.update(frame)
        image_obs, _ = velocity_filter.update(image_obs)
        image_obs = _apply_vision_fault(image_obs, fault, fault_effect_rng)

        component_measurement = component_estimator.estimate(frame)
        p_x_good, p_z_good = component_calibrator.probabilities(component_measurement)

        ref_obs, ref_diag = reference.observe(state, fault)
        reference_available += int(ref_obs.available)
        gnss_fresh += int(ref_diag.gnss_fresh)
        baro_fresh += int(ref_diag.baro_fresh)
        range_fresh += int(ref_diag.range_fresh)
        latency_steps.append(int(ref_diag.applied_latency_steps))
        reference_biases.append(abs(float(ref_diag.gnss_bias_m)))

        fused, component_diag = fusion.update(
            image_obs,
            ref_obs,
            p_x_good=p_x_good,
            p_z_good=p_z_good,
        )
        lateral_abstentions += int(component_diag.lateral_abstained)
        altitude_abstentions += int(component_diag.altitude_abstained)
        frames += 1

        decision = supervisor.assess(image_obs, fused, ref_obs)
        risk = float(decision.risk)
        risks.append(risk)
        descent_rate = sim_cfg.target_descent_rate

        if decision.decision == DecisionV3.ABORT:
            interventions += 1
            aborted = True
            outcome = "safe_abort"
            break
        if decision.decision == DecisionV3.HOLD:
            interventions += 1
            descent_rate = -0.30

        cmd = controller.command(fused.control_obs, descent_rate)
        wind_ax, wind_az = _wind_sample(env_rng, t)
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

    return Phase7EpisodeResult(
        seed=seed,
        condition=condition,
        fault_scenario=scenario.value,
        architecture="image_aegis_phase7_external",
        outcome=outcome,
        success=bool(outcome == "success"),
        unsafe_touchdown=bool(outcome == "unsafe_touchdown"),
        aborted=aborted,
        duration_s=float(min(sim_cfg.max_time, (i + 1) * sim_cfg.dt)),
        final_x_error=float(abs(state.x)),
        final_vx=float(state.vx),
        final_vz=float(state.vz),
        frames=int(frames),
        fault_active_frames=int(fault_active_frames),
        reference_available_rate=float(reference_available / max(1, frames)),
        gnss_fresh_rate=float(gnss_fresh / max(1, frames)),
        baro_fresh_rate=float(baro_fresh / max(1, frames)),
        range_fresh_rate=float(range_fresh / max(1, frames)),
        mean_reference_latency_steps=float(np.mean(latency_steps) if latency_steps else 0.0),
        max_abs_reference_bias_x_m=float(max(reference_biases) if reference_biases else 0.0),
        max_abs_shared_vision_bias_x_m=float(max(shared_vision_biases) if shared_vision_biases else 0.0),
        lateral_component_abstention_rate=float(lateral_abstentions / max(1, frames)),
        altitude_component_abstention_rate=float(altitude_abstentions / max(1, frames)),
        mean_interventions=float(interventions),
        max_risk=float(max(risks) if risks else 0.0),
        mean_risk=float(np.mean(risks) if risks else 0.0),
    )
