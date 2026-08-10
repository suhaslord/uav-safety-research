from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SimConfig:
    dt: float = 0.05
    max_time: float = 45.0
    initial_x_range: tuple[float, float] = (-3.0, 3.0)
    initial_z_range: tuple[float, float] = (5.0, 8.0)
    max_ax: float = 2.5
    max_az: float = 2.0
    drag: float = 0.12
    touchdown_x_tolerance: float = 0.45
    touchdown_vz_limit: float = 0.80
    touchdown_vx_limit: float = 0.80
    target_descent_rate: float = -0.70
    hold_descent_rate: float = -0.10
    near_ground_z: float = 1.2


@dataclass(frozen=True)
class ControllerConfig:
    kp_x: float = 0.85
    kd_x: float = 1.15
    kp_z: float = 0.65
    kd_z: float = 0.95


@dataclass(frozen=True)
class SupervisorConfig:
    hold_risk: float = 0.68
    abort_risk: float = 0.90
    min_confidence: float = 0.12
    near_ground_z: float = 1.2
    max_hold_steps: int = 120
