from __future__ import annotations

import numpy as np

from .config import ControllerConfig, SimConfig
from .controller import LandingController
from .dynamics import State, step_dynamics
from .perception import PerceptionModel, PerceptionProfile
from .simulator import EpisodeResult, _wind_sample
from .supervisor_v2 import (
    DecisionV2,
    SupervisorV2Config,
    TemporalObservationFilter,
    TemporalSafetySupervisorV2,
)


def run_episode_v2(
    seed: int,
    profile: str,
    sim_cfg: SimConfig | None = None,
    ctrl_cfg: ControllerConfig | None = None,
    sup_cfg: SupervisorV2Config | None = None,
    perception_profile: PerceptionProfile | None = None,
    return_trace: bool = False,
):
    """Run one Aegis V2 episode.

    V2 keeps the same plant, initial-state distribution, disturbance process,
    touchdown criteria, and perception profiles as V1. Robustness studies may
    supply an explicit perception profile without modifying the historical named
    profiles.
    """

    sim_cfg = sim_cfg or SimConfig()
    ctrl_cfg = ctrl_cfg or ControllerConfig()
    sup_cfg = sup_cfg or SupervisorV2Config(dt=sim_cfg.dt)

    rng = np.random.default_rng(seed)
    state = State(
        x=float(rng.uniform(*sim_cfg.initial_x_range)),
        z=float(rng.uniform(*sim_cfg.initial_z_range)),
        vx=float(rng.normal(0.0, 0.15)),
        vz=0.0,
    )

    perception = PerceptionModel(
        perception_profile if perception_profile is not None else profile,
        rng,
        profile_name=profile if perception_profile is not None else None,
    )
    controller = LandingController(ctrl_cfg, sim_cfg)
    supervisor = TemporalSafetySupervisorV2(sup_cfg)
    obs_filter = TemporalObservationFilter(dt=sim_cfg.dt)

    risks: list[float] = []
    interventions = 0
    dropouts = 0
    trace: list[dict] = []

    steps = int(sim_cfg.max_time / sim_cfg.dt)
    outcome = "timeout"
    aborted = False

    for i in range(steps):
        t = i * sim_cfg.dt
        raw_obs = perception.observe(state)
        dropouts += int(raw_obs.dropped)
        decision = supervisor.assess(raw_obs)
        control_obs = obs_filter.update(raw_obs)
        risks.append(decision.risk)

        if decision.decision == DecisionV2.ABORT:
            interventions += 1
            aborted = True
            outcome = "safe_abort"
            if return_trace:
                trace.append(_trace_row(t, state, raw_obs, control_obs, decision))
            break

        descent_rate = sim_cfg.target_descent_rate
        if decision.decision == DecisionV2.HOLD:
            descent_rate = -0.28
            interventions += 1

        cmd = controller.command(control_obs, descent_rate)
        wind_ax, wind_az = _wind_sample(rng, t)
        state = step_dynamics(state, cmd.ax, cmd.az, wind_ax, wind_az, sim_cfg)

        if return_trace:
            trace.append(_trace_row(t, state, raw_obs, control_obs, decision))

        if state.z <= 0.0:
            safe_x = abs(state.x) <= sim_cfg.touchdown_x_tolerance
            safe_vz = abs(state.vz) <= sim_cfg.touchdown_vz_limit
            safe_vx = abs(state.vx) <= sim_cfg.touchdown_vx_limit
            success = bool(safe_x and safe_vz and safe_vx)
            outcome = "success" if success else "unsafe_touchdown"
            break

    result = EpisodeResult(
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
        dropouts=int(dropouts),
    )

    return (result, trace) if return_trace else result


def _trace_row(t, state, raw_obs, control_obs, decision) -> dict:
    return {
        "t": t,
        "x": state.x,
        "z": state.z,
        "vx": state.vx,
        "vz": state.vz,
        "raw_obs_x": raw_obs.x,
        "raw_obs_z": raw_obs.z,
        "filtered_obs_x": control_obs.x,
        "filtered_obs_z": control_obs.z,
        "confidence": raw_obs.confidence,
        "risk": decision.risk,
        "instantaneous_risk": decision.instantaneous_risk,
        "decision": decision.decision.value,
    }
