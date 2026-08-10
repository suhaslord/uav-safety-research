from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import SimConfig
from .dynamics import State


@dataclass(frozen=True)
class Phase7DynamicsConfig:
    """Higher-order planar dynamics used for simulation-only robustness tests.

    This is intentionally still not a vehicle-identification model. It adds
    actuator lag, quadratic drag, and colored disturbance coupling so the
    controller no longer acts on an instantaneous point-mass acceleration plant.
    """

    actuator_time_constant_s: float = 0.24
    quadratic_drag_x: float = 0.035
    quadratic_drag_z: float = 0.025
    acceleration_rate_limit_mps3: float = 5.0
    disturbance_memory: float = 0.82
    disturbance_sigma_ax: float = 0.07
    disturbance_sigma_az: float = 0.05


@dataclass
class Phase7PlantMemory:
    actual_ax: float = 0.0
    actual_az: float = 0.0
    colored_wind_ax: float = 0.0
    colored_wind_az: float = 0.0


def step_phase7_dynamics(
    state: State,
    memory: Phase7PlantMemory,
    ax_cmd: float,
    az_cmd: float,
    wind_ax: float,
    wind_az: float,
    rng: np.random.Generator,
    sim_cfg: SimConfig,
    dyn_cfg: Phase7DynamicsConfig | None = None,
) -> tuple[State, Phase7PlantMemory]:
    """Advance a lagged nonlinear planar plant by one timestep."""

    c = dyn_cfg or Phase7DynamicsConfig()
    dt = sim_cfg.dt
    tau = max(dt, c.actuator_time_constant_s)
    alpha = float(np.clip(dt / tau, 0.0, 1.0))

    target_ax = float(np.clip(ax_cmd, -sim_cfg.max_ax, sim_cfg.max_ax))
    target_az = float(np.clip(az_cmd, -sim_cfg.max_az, sim_cfg.max_az))

    desired_ax = memory.actual_ax + alpha * (target_ax - memory.actual_ax)
    desired_az = memory.actual_az + alpha * (target_az - memory.actual_az)
    max_delta = c.acceleration_rate_limit_mps3 * dt
    actual_ax = float(memory.actual_ax + np.clip(desired_ax - memory.actual_ax, -max_delta, max_delta))
    actual_az = float(memory.actual_az + np.clip(desired_az - memory.actual_az, -max_delta, max_delta))

    colored_wind_ax = float(
        c.disturbance_memory * memory.colored_wind_ax
        + (1.0 - c.disturbance_memory) * wind_ax
        + rng.normal(0.0, c.disturbance_sigma_ax)
    )
    colored_wind_az = float(
        c.disturbance_memory * memory.colored_wind_az
        + (1.0 - c.disturbance_memory) * wind_az
        + rng.normal(0.0, c.disturbance_sigma_az)
    )

    drag_ax = sim_cfg.drag * state.vx + c.quadratic_drag_x * state.vx * abs(state.vx)
    drag_az = sim_cfg.drag * state.vz + c.quadratic_drag_z * state.vz * abs(state.vz)

    net_ax = float(np.clip(actual_ax + colored_wind_ax - drag_ax, -sim_cfg.max_ax, sim_cfg.max_ax))
    net_az = float(np.clip(actual_az + colored_wind_az - drag_az, -sim_cfg.max_az, sim_cfg.max_az))

    vx = float(state.vx + net_ax * dt)
    vz = float(state.vz + net_az * dt)
    x = float(state.x + vx * dt)
    z = float(max(0.0, state.z + vz * dt))

    return (
        State(x=x, z=z, vx=vx, vz=vz),
        Phase7PlantMemory(
            actual_ax=actual_ax,
            actual_az=actual_az,
            colored_wind_ax=colored_wind_ax,
            colored_wind_az=colored_wind_az,
        ),
    )
