from __future__ import annotations

import numpy as np

from .config import ControllerConfig, SimConfig
from .controller import LandingController
from .dynamics import State, step_dynamics
from .image_perception import IMAGE_CONDITIONS
from .image_temporal import (
    CalibratedTemporalImagePipeline,
    EmpiricalConfidenceCalibrator,
    Phase6LandingPadRenderer,
    TemporalImageConfig,
)
from .phase6_fusion import Phase6FusionConfig
from .phase6_velocity import RobustImageVelocityFilter, RobustVelocityConfig
from .phase6b_fusion import Phase6BComponentGateConfig
from .phase6c_fusion import Phase6CComponentFusionAdapter
from .phase6e_perception import Phase6ERobustPadEstimator
from .reference_estimator import IndependentReferenceEstimator, ReferenceEstimatorConfig
from .selective_confidence_v2 import ComponentConfidenceCalibrator
from .simulator import _wind_sample
from .simulator_image_phase6b import Phase6BEpisodeResult, _trace_row
from .supervisor_v3 import DecisionV3, RedundantSafetySupervisorV3, SupervisorV3Config


def run_phase6g_episode(
    seed: int,
    condition: str,
    temporal_calibrator: EmpiricalConfidenceCalibrator,
    component_calibrator: ComponentConfidenceCalibrator,
    *,
    severity: float = 1.0,
    sim_cfg: SimConfig | None = None,
    ctrl_cfg: ControllerConfig | None = None,
    image_cfg: TemporalImageConfig | None = None,
    sup_cfg: SupervisorV3Config | None = None,
    phase6_fusion_cfg: Phase6FusionConfig | None = None,
    component_gate_cfg: Phase6BComponentGateConfig | None = None,
    velocity_cfg: RobustVelocityConfig | None = None,
    ref_cfg: ReferenceEstimatorConfig | None = None,
    return_trace: bool = False,
):
    """Run Phase 6G: frozen Phase 6E perception plus Phase 6C fusion.

    Phase 6G changes the landing loop only at the image-measurement boundary:
    the frozen Phase 6E robust-background estimator is injected into the existing
    Phase 6 temporal tracker and used for component confidence. Temporal logic,
    robust image-derived velocity filtering, independent reference estimation,
    Phase 6C z-only altitude fallback, controller, frozen V3 supervisor, dynamics,
    and RNG isolation are otherwise unchanged.

    The historical Phase 6 empirical temporal calibrator is intentionally reused
    so Phase 6G does not introduce an additional scalar-gate retuning alongside
    the frozen perception change. Component selectivity uses the independently
    confirmed Phase 6E component calibrator supplied by the caller.
    """

    if condition not in IMAGE_CONDITIONS:
        raise ValueError(f"Unknown image condition: {condition}")
    if severity <= 0:
        raise ValueError("severity must be > 0")

    sim_cfg = sim_cfg or SimConfig()
    ctrl_cfg = ctrl_cfg or ControllerConfig()
    image_cfg = image_cfg or TemporalImageConfig(dt=sim_cfg.dt)
    sup_cfg = sup_cfg or SupervisorV3Config(dt=sim_cfg.dt)
    velocity_cfg = velocity_cfg or RobustVelocityConfig(dt=sim_cfg.dt)

    env_rng = np.random.default_rng(seed)
    image_rng = np.random.default_rng(np.random.SeedSequence([seed, 6006]))
    reference_rng = np.random.default_rng(np.random.SeedSequence([seed, 3003]))

    state = State(
        x=float(env_rng.uniform(*sim_cfg.initial_x_range)),
        z=float(env_rng.uniform(*sim_cfg.initial_z_range)),
        vx=float(env_rng.normal(0.0, 0.15)),
        vz=0.0,
    )

    renderer = Phase6LandingPadRenderer()
    frozen_estimator = Phase6ERobustPadEstimator(
        image_cfg.min_component_pixels,
        image_cfg.min_bbox_width_px,
    )
    image_pipeline = CalibratedTemporalImagePipeline(
        temporal_calibrator,
        image_cfg,
        estimator=frozen_estimator,
    )
    component_estimator = Phase6ERobustPadEstimator(
        image_cfg.min_component_pixels,
        image_cfg.min_bbox_width_px,
    )
    velocity_filter = RobustImageVelocityFilter(velocity_cfg)
    controller = LandingController(ctrl_cfg, sim_cfg)
    reference = IndependentReferenceEstimator(reference_rng, sim_cfg.dt, ref_cfg)
    fusion = Phase6CComponentFusionAdapter(
        sup_cfg,
        phase6_fusion_cfg,
        component_gate_cfg,
    )
    supervisor = RedundantSafetySupervisorV3(sup_cfg)

    frame_count = 0
    image_abstentions = 0
    lateral_component_abstentions = 0
    altitude_component_abstentions = 0
    lateral_reference_takeovers = 0
    altitude_reference_takeovers = 0
    unresolved_component_frames = 0
    interventions = 0
    reference_updates = 0
    temporal_confidences: list[float] = []
    px_values: list[float] = []
    pz_values: list[float] = []
    accepted_x_errors: list[float] = []
    risks: list[float] = []
    trace: list[dict] = []
    last_fusion = None
    aborted = False
    outcome = "timeout"

    steps = int(sim_cfg.max_time / sim_cfg.dt)
    for i in range(steps):
        t = i * sim_cfg.dt
        pre_state = state
        frame = renderer.render(
            x_offset_m=state.x,
            altitude_m=max(0.08, state.z),
            rng=image_rng,
            condition=condition,
            severity=severity,
        )

        image_obs, temporal_diag = image_pipeline.update(frame)
        image_obs, velocity_diag = velocity_filter.update(image_obs)
        component_measurement = component_estimator.estimate(frame)
        p_x_good, p_z_good = component_calibrator.probabilities(component_measurement)

        frame_count += 1
        image_abstentions += int(temporal_diag.abstained)
        temporal_confidences.append(float(temporal_diag.calibrated_confidence))
        px_values.append(float(p_x_good))
        pz_values.append(float(p_z_good))
        if not image_obs.dropped:
            accepted_x_errors.append(abs(image_obs.x - state.x))

        ref_obs = reference.observe(state)
        reference_updates += int(ref_obs.fresh)
        fused, component_diag = fusion.update(
            image_obs,
            ref_obs,
            p_x_good=p_x_good,
            p_z_good=p_z_good,
        )
        last_fusion = fused

        lateral_component_abstentions += int(component_diag.lateral_abstained)
        altitude_component_abstentions += int(component_diag.altitude_abstained)
        lateral_reference_takeovers += int(component_diag.lateral_reference_takeover)
        altitude_reference_takeovers += int(component_diag.altitude_reference_takeover)
        unresolved_component_frames += int(
            (component_diag.lateral_abstained and not component_diag.lateral_reference_takeover)
            or (component_diag.altitude_abstained and not component_diag.altitude_reference_takeover)
        )

        decision = supervisor.assess(image_obs, fused, ref_obs)
        risk = float(decision.risk)
        risks.append(risk)
        descent_rate = sim_cfg.target_descent_rate

        if decision.decision == DecisionV3.ABORT:
            interventions += 1
            aborted = True
            outcome = "safe_abort"
            if return_trace:
                trace.append(_trace_row(
                    t, pre_state, pre_state, image_obs, temporal_diag, velocity_diag,
                    component_diag, fused, ref_obs, risk, decision.decision.value,
                ))
            break
        if decision.decision == DecisionV3.HOLD:
            descent_rate = -0.30
            interventions += 1

        control_obs = fused.control_obs
        cmd = controller.command(control_obs, descent_rate)
        wind_ax, wind_az = _wind_sample(env_rng, t)
        state = step_dynamics(state, cmd.ax, cmd.az, wind_ax, wind_az, sim_cfg)

        if return_trace:
            trace.append(_trace_row(
                t, pre_state, state, image_obs, temporal_diag, velocity_diag,
                component_diag, fused, ref_obs, risk, decision.decision.value,
            ))

        if state.z <= 0.0:
            safe_x = abs(state.x) <= sim_cfg.touchdown_x_tolerance
            safe_vz = abs(state.vz) <= sim_cfg.touchdown_vz_limit
            safe_vx = abs(state.vx) <= sim_cfg.touchdown_vx_limit
            outcome = "success" if (safe_x and safe_vz and safe_vx) else "unsafe_touchdown"
            break

    result = Phase6BEpisodeResult(
        seed=seed,
        condition=condition,
        architecture="image_aegis_phase6g",
        outcome=outcome,
        success=bool(outcome == "success"),
        unsafe_touchdown=bool(outcome == "unsafe_touchdown"),
        aborted=aborted,
        duration_s=float(min(sim_cfg.max_time, (i + 1) * sim_cfg.dt)),
        final_x_error=float(abs(state.x)),
        final_vx=float(state.vx),
        final_vz=float(state.vz),
        frames=int(frame_count),
        image_abstentions=int(image_abstentions),
        image_abstention_rate=float(image_abstentions / max(1, frame_count)),
        lateral_component_abstentions=int(lateral_component_abstentions),
        lateral_component_abstention_rate=float(lateral_component_abstentions / max(1, frame_count)),
        altitude_component_abstentions=int(altitude_component_abstentions),
        altitude_component_abstention_rate=float(altitude_component_abstentions / max(1, frame_count)),
        lateral_reference_takeovers=int(lateral_reference_takeovers),
        altitude_reference_takeovers=int(altitude_reference_takeovers),
        unresolved_component_frames=int(unresolved_component_frames),
        mean_p_x_good=float(np.mean(px_values) if px_values else 0.0),
        mean_p_z_good=float(np.mean(pz_values) if pz_values else 0.0),
        mean_calibrated_confidence=float(np.mean(temporal_confidences) if temporal_confidences else 0.0),
        mean_image_x_error_m=float(np.mean(accepted_x_errors) if accepted_x_errors else np.nan),
        p95_image_x_error_m=float(np.quantile(accepted_x_errors, 0.95) if accepted_x_errors else np.nan),
        interventions=int(interventions),
        reference_updates=int(reference_updates),
        max_risk=float(max(risks) if risks else 0.0),
        mean_risk=float(np.mean(risks) if risks else 0.0),
        final_bias_estimate_x=float(last_fusion.bias_estimate_x if last_fusion else 0.0),
        final_bias_confidence=float(last_fusion.bias_confidence if last_fusion else 0.0),
    )
    return (result, trace) if return_trace else result
