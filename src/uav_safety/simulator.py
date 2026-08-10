from __future__ import annotations

from dataclasses import dataclass, asdict
import numpy as np

from .config import ControllerConfig, SimConfig, SupervisorConfig
from .controller import LandingController
from .dynamics import State, step_dynamics
from .perception import PerceptionModel
from .supervisor import Decision, SafetySupervisor


@dataclass
class EpisodeResult:
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

    def to_dict(self) -> dict:
        return asdict(self)


def _wind_sample(rng: np.random.Generator, t: float) -> tuple[float, float]:
    """Small simulated disturbance field with occasional smooth gusts."""
    base_x = 0.12 * np.sin(0.7 * t) + rng.normal(0.0, 0.04)
    base_z = 0.05 * np.sin(0.45 * t + 0.8) + rng.normal(0.0, 0.025)

    # Rare short gust impulse in simulation only.
    if rng.random() < 0.004:
        base_x += rng.normal(0.0, 0.75)
    return float(base_x), float(base_z)


def run_episode(
    seed: int,
    profile: str,
    supervised: bool,
    sim_cfg: SimConfig | None = None,
    ctrl_cfg: ControllerConfig | None = None,
    sup_cfg: SupervisorConfig | None = None,
    return_trace: bool = False,
):
    sim_cfg = sim_cfg or SimConfig()
    ctrl_cfg = ctrl_cfg or ControllerConfig()
    sup_cfg = sup_cfg or SupervisorConfig()

    rng = np.random.default_rng(seed)
    state = State(
        x=float(rng.uniform(*sim_cfg.initial_x_range)),
        z=float(rng.uniform(*sim_cfg.initial_z_range)),
        vx=float(rng.normal(0.0, 0.15)),
        vz=0.0,
    )

    perception = PerceptionModel(profile, rng)
    controller = LandingController(ctrl_cfg, sim_cfg)
    supervisor = SafetySupervisor(sup_cfg)

    risks: list[float] = []
    interventions = 0
    dropouts = 0
    trace: list[dict] = []

    steps = int(sim_cfg.max_time / sim_cfg.dt)
    outcome = "timeout"
    aborted = False

    for i in range(steps):
        t = i * sim_cfg.dt
        obs = perception.observe(state)
        dropouts += int(obs.dropped)

        if supervised:
            decision = supervisor.assess(obs)
            risk = decision.risk
        else:
            # Still record an observational risk proxy for fair comparison.
            proxy = SafetySupervisor(sup_cfg).assess(obs)
            decision = proxy
            risk = proxy.risk
            decision = type(proxy)(Decision.PROCEED, risk, "baseline ignores supervisor")

        risks.append(risk)

        if supervised and decision.decision == Decision.ABORT:
            interventions += 1
            aborted = True
            outcome = "safe_abort"
            if return_trace:
                trace.append({
                    "t": t, "x": state.x, "z": state.z, "vx": state.vx, "vz": state.vz,
                    "obs_x": obs.x, "obs_z": obs.z, "confidence": obs.confidence,
                    "risk": risk, "decision": decision.decision.value,
                })
            break

        descent_rate = sim_cfg.target_descent_rate
        if supervised and decision.decision == Decision.HOLD:
            descent_rate = sim_cfg.hold_descent_rate
            interventions += 1

        cmd = controller.command(obs, descent_rate)
        wind_ax, wind_az = _wind_sample(rng, t)
        state = step_dynamics(state, cmd.ax, cmd.az, wind_ax, wind_az, sim_cfg)

        if return_trace:
            trace.append({
                "t": t, "x": state.x, "z": state.z, "vx": state.vx, "vz": state.vz,
                "obs_x": obs.x, "obs_z": obs.z, "confidence": obs.confidence,
                "risk": risk, "decision": decision.decision.value,
            })

        if state.z <= 0.0:
            safe_x = abs(state.x) <= sim_cfg.touchdown_x_tolerance
            safe_vz = abs(state.vz) <= sim_cfg.touchdown_vz_limit
            safe_vx = abs(state.vx) <= sim_cfg.touchdown_vx_limit
            success = bool(safe_x and safe_vz and safe_vx)
            outcome = "success" if success else "unsafe_touchdown"
            break
    else:
        success = False

    if outcome == "safe_abort":
        success = False
    elif outcome == "timeout":
        success = False
    elif outcome == "unsafe_touchdown":
        success = False

    result = EpisodeResult(
        seed=seed,
        profile=profile,
        supervised=supervised,
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
