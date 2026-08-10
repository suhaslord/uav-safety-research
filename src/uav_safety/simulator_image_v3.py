from __future__ import annotations

from dataclasses import asdict, dataclass

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
from .reference_estimator import IndependentReferenceEstimator, ReferenceEstimatorConfig
from .simulator import _wind_sample
from .supervisor_v3 import DecisionV3, RedundantSafetySupervisorV3, RedundantStateFusion, SupervisorV3Config


@dataclass
class ImageEpisodeResult:
    seed: int
    condition: str
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
    image_abstentions: int
    image_abstention_rate: float
    mean_calibrated_confidence: float
    mean_image_x_error_m: float
    p95_image_x_error_m: float
    interventions: int
    reference_updates: int
    max_risk: float
    mean_risk: float
    final_bias_estimate_x: float
    final_bias_confidence: float

    def to_dict(self) -> dict:
        return asdict(self)


def run_image_episode(
    seed: int,
    condition: str,
    calibrator: EmpiricalConfidenceCalibrator,
    *,
    architecture: str = "image_aegis_v3",
    severity: float = 1.0,
    sim_cfg: SimConfig | None = None,
    ctrl_cfg: ControllerConfig | None = None,
    image_cfg: TemporalImageConfig | None = None,
    sup_cfg: SupervisorV3Config | None = None,
    ref_cfg: ReferenceEstimatorConfig | None = None,
    return_trace: bool = False,
):
    """Run a landing episode whose primary perception comes from rendered pixels.

    ``image_temporal`` uses only the calibrated temporal image observation.
    ``image_aegis_v3`` feeds that same observation into frozen V3 redundant fusion
    and supervision. Environment, image, and reference RNG streams are isolated.
    """

    if condition not in IMAGE_CONDITIONS:
        raise ValueError(f"Unknown image condition: {condition}")
    if architecture not in {"image_temporal", "image_aegis_v3"}:
        raise ValueError(f"Unknown image architecture: {architecture}")
    if severity <= 0:
        raise ValueError("severity must be > 0")

    sim_cfg = sim_cfg or SimConfig()
    ctrl_cfg = ctrl_cfg or ControllerConfig()
    image_cfg = image_cfg or TemporalImageConfig(dt=sim_cfg.dt)
    sup_cfg = sup_cfg or SupervisorV3Config(dt=sim_cfg.dt)

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
    image_pipeline = CalibratedTemporalImagePipeline(calibrator, image_cfg)
    controller = LandingController(ctrl_cfg, sim_cfg)

    reference = None
    fusion = None
    supervisor = None
    if architecture == "image_aegis_v3":
        reference = IndependentReferenceEstimator(reference_rng, sim_cfg.dt, ref_cfg)
        fusion = RedundantStateFusion(sup_cfg)
        supervisor = RedundantSafetySupervisorV3(sup_cfg)

    frame_count = 0
    abstentions = 0
    interventions = 0
    reference_updates = 0
    calibrated_confidences: list[float] = []
    accepted_x_errors: list[float] = []
    risks: list[float] = []
    trace: list[dict] = []
    last_fusion = None
    aborted = False
    outcome = "timeout"

    steps = int(sim_cfg.max_time / sim_cfg.dt)
    for i in range(steps):
        t = i * sim_cfg.dt
        frame = renderer.render(
            x_offset_m=state.x,
            altitude_m=max(0.08, state.z),
            rng=image_rng,
            condition=condition,
            severity=severity,
        )
        image_obs, diag = image_pipeline.update(frame)
        frame_count += 1
        abstentions += int(diag.abstained)
        calibrated_confidences.append(diag.calibrated_confidence)
        if not image_obs.dropped:
            accepted_x_errors.append(abs(image_obs.x - state.x))

        descent_rate = sim_cfg.target_descent_rate
        risk = 0.0
        decision_value = "proceed"
        reference_fresh = False

        if architecture == "image_aegis_v3":
            assert reference is not None and fusion is not None and supervisor is not None
            ref_obs = reference.observe(state)
            reference_updates += int(ref_obs.fresh)
            reference_fresh = bool(ref_obs.fresh)

            # The image pipeline already performs temporal filtering, so this is
            # the visual state used by V3 without an abstract PerceptionModel.
            fused = fusion.update(image_obs, image_obs, ref_obs)
            last_fusion = fused
            decision = supervisor.assess(image_obs, fused, ref_obs)
            risk = float(decision.risk)
            risks.append(risk)
            decision_value = decision.decision.value

            if decision.decision == DecisionV3.ABORT:
                interventions += 1
                aborted = True
                outcome = "safe_abort"
                if return_trace:
                    trace.append(_trace_row(t, state, image_obs, diag, fused.control_obs.x, risk, decision_value, reference_fresh))
                break
            if decision.decision == DecisionV3.HOLD:
                descent_rate = -0.30
                interventions += 1
            control_obs = fused.control_obs
        else:
            control_obs = image_obs

        cmd = controller.command(control_obs, descent_rate)
        wind_ax, wind_az = _wind_sample(env_rng, t)
        state = step_dynamics(state, cmd.ax, cmd.az, wind_ax, wind_az, sim_cfg)

        if return_trace:
            trace.append(_trace_row(t, state, image_obs, diag, control_obs.x, risk, decision_value, reference_fresh))

        if state.z <= 0.0:
            safe_x = abs(state.x) <= sim_cfg.touchdown_x_tolerance
            safe_vz = abs(state.vz) <= sim_cfg.touchdown_vz_limit
            safe_vx = abs(state.vx) <= sim_cfg.touchdown_vx_limit
            outcome = "success" if (safe_x and safe_vz and safe_vx) else "unsafe_touchdown"
            break

    result = ImageEpisodeResult(
        seed=seed,
        condition=condition,
        architecture=architecture,
        outcome=outcome,
        success=bool(outcome == "success"),
        unsafe_touchdown=bool(outcome == "unsafe_touchdown"),
        aborted=aborted,
        duration_s=float(min(sim_cfg.max_time, (i + 1) * sim_cfg.dt)),
        final_x_error=float(abs(state.x)),
        final_vx=float(state.vx),
        final_vz=float(state.vz),
        frames=int(frame_count),
        image_abstentions=int(abstentions),
        image_abstention_rate=float(abstentions / max(1, frame_count)),
        mean_calibrated_confidence=float(np.mean(calibrated_confidences) if calibrated_confidences else 0.0),
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


def _trace_row(t, state, image_obs, diag, control_x, risk, decision, reference_fresh) -> dict:
    return {
        "t": float(t),
        "true_x": float(state.x),
        "true_z": float(state.z),
        "image_x": float(image_obs.x),
        "image_z": float(image_obs.z),
        "image_vx": float(image_obs.vx),
        "image_vz": float(image_obs.vz),
        "image_dropped": bool(image_obs.dropped),
        "raw_confidence": float(diag.raw_confidence),
        "calibrated_confidence": float(diag.calibrated_confidence),
        "geometry_score": float(diag.geometry_score),
        "abstained": bool(diag.abstained),
        "abstain_reason": diag.reason,
        "innovation_score": float(diag.innovation_score),
        "control_x": float(control_x),
        "reference_fresh": bool(reference_fresh),
        "risk": float(risk),
        "decision": decision,
    }
