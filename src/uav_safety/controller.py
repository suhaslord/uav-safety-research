from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from .config import ControllerConfig, SimConfig
from .perception import Observation


@dataclass
class ControlCommand:
    ax: float
    az: float


class LandingController:
    """Simple PD controller operating on perceived state."""

    def __init__(self, ctrl_cfg: ControllerConfig, sim_cfg: SimConfig):
        self.ctrl_cfg = ctrl_cfg
        self.sim_cfg = sim_cfg

    def command(self, obs: Observation, descent_rate: float) -> ControlCommand:
        c = self.ctrl_cfg
        s = self.sim_cfg

        ax = -c.kp_x * obs.x - c.kd_x * obs.vx
        az = c.kp_z * (descent_rate - obs.vz) - c.kd_z * obs.vz

        return ControlCommand(
            ax=float(np.clip(ax, -s.max_ax, s.max_ax)),
            az=float(np.clip(az, -s.max_az, s.max_az)),
        )
