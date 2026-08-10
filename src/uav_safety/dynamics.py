from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from .config import SimConfig


@dataclass
class State:
    x: float
    z: float
    vx: float
    vz: float

    def as_array(self) -> np.ndarray:
        return np.array([self.x, self.z, self.vx, self.vz], dtype=float)


def step_dynamics(
    state: State,
    ax_cmd: float,
    az_cmd: float,
    wind_ax: float,
    wind_az: float,
    cfg: SimConfig,
) -> State:
    """Advance a simple planar point-mass model by one timestep."""
    ax = float(np.clip(ax_cmd + wind_ax - cfg.drag * state.vx, -cfg.max_ax, cfg.max_ax))
    az = float(np.clip(az_cmd + wind_az - cfg.drag * state.vz, -cfg.max_az, cfg.max_az))

    vx = state.vx + ax * cfg.dt
    vz = state.vz + az * cfg.dt
    x = state.x + vx * cfg.dt
    z = state.z + vz * cfg.dt

    return State(x=x, z=max(z, 0.0), vx=vx, vz=vz)
