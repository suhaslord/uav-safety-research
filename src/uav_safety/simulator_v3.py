from __future__ import annotations

from dataclasses import asdict, dataclass
import numpy as np

from .config import ControllerConfig, SimConfig
from .controller import LandingController
from .dynamics import State, step_dynamics
from .perception import PerceptionModel
from .reference_estimator import IndependentReferenceEstimator, ReferenceEstimatorConfig
from .simulator import _wind_sample
from .supervisor_v2 import TemporalObservationFilter
from .supervisor_v3 import (
    DecisionV3,
    RedundantSafetySupervisorV3,
    RedundantStateFusion,
    SupervisorV3Config,
)


@dataclass
class EpisodeResultV3:
    seed: int
    profile: str
    supervised: bool
    outcome: str
    success: bool
    unsafe_touchdown: bool
    aborted: bool
    duration_s: float
    final_x_error: float
    final_vx: float
    final_vz: float
    max_risk: float
    mean_risk: float
    interventions: int
    dropouts: int
    reference_updates: int
    reference_unavailable_steps: int
    mean_normalized_disagreement: float
    max_normalized_disagreement: float
    final_bias_estimate_x: float
    final_bias_confidence: float
    mean_reference_weight: float

    def to_dict(self) -> dict:
        return asdict(self)


def run_episode_v3(
    seed: int,
    profile: str,
    sim_cfg: SimConfig | None = None,
    ctrl_cfg: ControllerConfig | None = None,
    sup_cfg: SupervisorV3Config | None = None,
    ref_cfg: ReferenceEstimatorConfig | None = None,
    return_trace: bool = False,
):
    """Run one simulation-only Aegis V3 landing episode.

    The legacy environment RNG remains seeded exactly as in V1/V2. The new
    redundant estimator uses an independent RNG stream, so adding V3 cannot
    perturb vision noise, dropout draws, or the disturbance sequence.
    """

    sim_cfg = sim_cfg or SimConfig()
    ctrl_cfg = ctrl_cfg or ControllerConfig()
    sup_cfg = sup_cfg or SupervisorV3Config(dt=sim_cfg.dt)

    env_rng = np.random.default_rng(seed)
    reference_rng = np.random.default_rng(np.random.SeedSequence([seed, 3003]))

    state = State(
        x=float(env_rng.uniform(*sim_cfg.initial_x_range)),
        z=float(env_rng.uniform(*sim_cfg.initial_z_range)),
        vx=float(env_rng.normal(0.0, 0.15)),
        vz=0.0,
    )

    perception = PerceptionModel(profile, env_rng)
    reference = IndependentReferenceEstimator(reference_rng, sim_cfg.dt, ref_cfg)
    vision_filter = TemporalObservationFilter(dt=sim_cfg.dt)
    fusion = RedundantStateFusion(sup_cfg)
    supervisor = RedundantSafetySupervisorV3(sup_cfg)
    controller = LandingController(ctrl_cfg, sim_cfg)

    risks: list[float] = []
    disagreements: list[float] = []
    reference_weights: list[float] = []
    interventions = 0
    vision_dropouts = 0
    reference_updates = 0
    reference_unavailable_steps = 0
    trace: list[dict] = []
    last_fusion = None

    steps = int(sim_cfg.max_time / sim_cfg.dt)
    outcome = "timeout"
    aborted = False

    for i in range(steps):
        t = i * sim_cfg.dt

        raw_vision = perception.observe(state)
        vision_dropouts += int(raw_vision.dropped)
        filtered_vision = vision_filter.update(raw_vision)

        ref_obs = reference.observe(state)
        reference_updates += int(ref_obs.fresh)
        reference_unavailable_steps += int(not ref_obs.available)

        fused = fusion.update(raw_vision, filtered_vision, ref_obs)
        last_fusion = fused
        decision = supervisor.assess(raw_vision, fused, ref_obs)

        risks.append(decision.risk)
        disagreements.append(fused.normalized_disagreement)
        reference_weights.append(fused.reference_weight)

        if decision.decision == DecisionV3.ABORT:
            interventions += 1
            aborted = True
            outcome = "safe_abort"
            if return_trace:
                trace.append(_trace_row(t, state, raw_vision, ref_obs, fused, decision))
            break

        descent_rate = sim_cfg.target_descent_rate
        if decision.decision == DecisionV3.HOLD:
            # A hold slows the simulated descent while state evidence settles;
            # it does not command a physical aircraft or expose flight settings.
            descent_rate = -0.30
            interventions += 1

        cmd = controller.command(fused.control_obs, descent_rate)
        wind_ax, wind_az = _wind_sample(env_rng, t)
        state = step_dynamics(state, cmd.ax, cmd.az, wind_ax, wind_az, sim_cfg)

        if return_trace:
            trace.append(_trace_row(t, state, raw_vision, ref_obs, fused, decision))

        if state.z <= 0.0:
            safe_x = abs(state.x) <= sim_cfg.touchdown_x_tolerance
            safe_vz = abs(state.vz) <= sim_cfg.touchdown_vz_limit
            safe_vx = abs(state.vx) <= sim_cfg.touchdown_vx_limit
            outcome = "success" if (safe_x and safe_vz and safe_vx) else "unsafe_touchdown"
            break

    result = EpisodeResultV3(
        seed=seed,
        profile=profile,
        supervised=True,
        outcome=outcome,
        success=bool(outcome == "success"),
        unsafe_touchdown=bool(outcome == "unsafe_touchdown"),
        aborted=aborted,
        duration_s=float(min(sim_cfg.max_time, (i + 1) * sim_cfg.dt)),
        final_x_error=float(abs(state.x)),
        final_vx=float(state.vx),
        final_vz=float(state.vz),
        max_risk=float(max(risks) if risks else 0.0),
        mean_risk=float(np.mean(risks) if risks else 0.0),
        interventions=int(interventions),
        dropouts=int(vision_dropouts),
        reference_updates=int(reference_updates),
        reference_unavailable_steps=int(reference_unavailable_steps),
        mean_normalized_disagreement=float(np.mean(disagreements) if disagreements else 0.0),
        max_normalized_disagreement=float(max(disagreements) if disagreements else 0.0),
        final_bias_estimate_x=float(last_fusion.bias_estimate_x if last_fusion else 0.0),
        final_bias_confidence=float(last_fusion.bias_confidence if last_fusion else 0.0),
        mean_reference_weight=float(np.mean(reference_weights) if reference_weights else 0.0),
    )

    return (result, trace) if return_trace else result


def _trace_row(t, state, raw_vision, ref_obs, fused, decision) -> dict:
    return {
        "t": float(t),
        "x": float(state.x),
        "z": float(state.z),
        "vx": float(state.vx),
        "vz": float(state.vz),
        "vision_x": float(raw_vision.x),
        "vision_z": float(raw_vision.z),
        "vision_confidence": float(raw_vision.confidence),
        "vision_dropped": bool(raw_vision.dropped),
        "reference_x": float(ref_obs.x),
        "reference_z": float(ref_obs.z),
        "reference_fresh": bool(ref_obs.fresh),
        "reference_available": bool(ref_obs.available),
        "reference_age_steps": int(ref_obs.age_steps),
        "fused_x": float(fused.control_obs.x),
        "fused_z": float(fused.control_obs.z),
        "bias_estimate_x": float(fused.bias_estimate_x),
        "bias_confidence": float(fused.bias_confidence),
        "applied_bias_correction": float(fused.applied_bias_correction),
        "normalized_disagreement": float(fused.normalized_disagreement),
        "unexplained_disagreement": float(fused.unexplained_disagreement),
        "reference_weight": float(fused.reference_weight),
        "risk": float(decision.risk),
        "instantaneous_risk": float(decision.instantaneous_risk),
        "decision": decision.decision.value,
    }
