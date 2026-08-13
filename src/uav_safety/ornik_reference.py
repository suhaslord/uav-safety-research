from __future__ import annotations

from dataclasses import dataclass, replace
import numpy as np

from .ornik_fdi import healthy_label, single_fault_label


@dataclass(frozen=True)
class ReferencePlant:
    dt: float = 0.01
    mass_kg: float = 0.027
    arm_m: float = 0.046
    inertia_x: float = 1.4e-5
    inertia_y: float = 1.4e-5
    inertia_z: float = 2.2e-5
    yaw_moment_per_thrust: float = 0.006
    gravity: float = 9.81
    linear_damping: float = 0.20
    angular_damping: float = 0.08

    def mismatched(self, scale: float) -> "ReferencePlant":
        return replace(self, mass_kg=self.mass_kg * scale, inertia_x=self.inertia_x * scale,
                       inertia_y=self.inertia_y * scale, inertia_z=self.inertia_z * scale)


def _controller(state: np.ndarray, plant: ReferencePlant, target: np.ndarray) -> np.ndarray:
    px, py, pz, vx, vy, vz, roll, pitch, yaw, p, q, r = state
    ex, ey, ez = target - state[:3]
    desired_pitch = np.clip(0.16 * ex - 0.11 * vx, -0.28, 0.28)
    desired_roll = np.clip(-0.16 * ey + 0.11 * vy, -0.28, 0.28)
    total = plant.mass_kg * (plant.gravity + 3.2 * ez - 1.8 * vz)
    tau_roll = 8.0e-5 * (desired_roll - roll) - 2.5e-5 * p
    tau_pitch = 8.0e-5 * (desired_pitch - pitch) - 2.5e-5 * q
    tau_yaw = -3.0e-5 * yaw - 1.2e-5 * r
    a, c = plant.arm_m, plant.yaw_moment_per_thrust
    mix = np.array([
        [1, -1/a, -1/a,  1/c], [1, -1/a,  1/a, -1/c],
        [1,  1/a,  1/a,  1/c], [1,  1/a, -1/a, -1/c],
    ], dtype=float) * 0.25
    return np.clip(mix @ np.array([total, tau_roll, tau_pitch, tau_yaw]), 0.0, 0.24)


def _step(state: np.ndarray, commanded: np.ndarray, effectiveness: np.ndarray, plant: ReferencePlant) -> np.ndarray:
    actual = commanded * effectiveness
    total = float(actual.sum()); a = plant.arm_m; c = plant.yaw_moment_per_thrust
    tau_roll = a * (-actual[0] - actual[1] + actual[2] + actual[3])
    tau_pitch = a * (-actual[0] + actual[1] + actual[2] - actual[3])
    tau_yaw = c * (actual[0] - actual[1] + actual[2] - actual[3])
    s = state.copy(); roll, pitch = s[6], s[7]
    ax = plant.gravity * np.sin(pitch) - plant.linear_damping * s[3]
    ay = -plant.gravity * np.sin(roll) - plant.linear_damping * s[4]
    az = total / plant.mass_kg * np.cos(roll) * np.cos(pitch) - plant.gravity - plant.linear_damping * s[5]
    p_dot = tau_roll / plant.inertia_x - plant.angular_damping * s[9]
    q_dot = tau_pitch / plant.inertia_y - plant.angular_damping * s[10]
    r_dot = tau_yaw / plant.inertia_z - plant.angular_damping * s[11]
    dt = plant.dt
    s[3:6] += dt * np.array([ax, ay, az]); s[:3] += dt * s[3:6]
    s[9:12] += dt * np.array([p_dot, q_dot, r_dot]); s[6:9] += dt * s[9:12]
    s[2] = max(0.0, s[2])
    return s


def simulate_sequence(*, seed: int, samples: int, fault_motor: int | None, fault_start: int | None,
                      plant: ReferencePlant | None = None) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(int(seed)); plant = plant or ReferencePlant(); state = np.zeros(12, dtype=float)
    state[:3] = [rng.uniform(-0.8, 0.8), rng.uniform(-0.8, 0.8), rng.uniform(3.2, 4.8)]
    state[3:6] = rng.normal(0.0, 0.08, 3); state[6:9] = rng.normal(0.0, 0.025, 3)
    target = np.array([0.0, 0.0, 4.0]); y = np.zeros((samples, 6), np.float32); u = np.zeros((samples, 4), np.float32)
    for k in range(samples):
        commanded = _controller(state, plant, target)
        y[k] = [state[0], state[1], state[2], state[9], state[10], state[11]]; u[k] = commanded
        eff = np.ones(4)
        if fault_motor is not None and fault_start is not None and k >= fault_start:
            eff[int(fault_motor)] = 0.0
        state = _step(state, commanded, eff, plant)
    return y, u


def make_training_set(*, seed: int, windows: int, window_samples: int = 100) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(int(seed)); x = np.empty((windows, window_samples, 10), np.float32); labels = np.empty((windows, 4), np.float32)
    for i in range(windows):
        cls = i % 5
        fault_motor = None if cls == 0 else cls - 1
        fault_start = None if fault_motor is None else (i // 5) % window_samples
        y, u = simulate_sequence(seed=int(rng.integers(0, 2**31 - 1)), samples=window_samples, fault_motor=fault_motor, fault_start=fault_start)
        x[i] = np.concatenate([y, u], axis=1)
        labels[i] = healthy_label() if fault_motor is None else single_fault_label(fault_motor)
    return x, labels


def make_paper_style_test(*, seed: int, trajectories_per_class: int = 200, mismatch_scale: float = 1.0) -> list[dict]:
    rng = np.random.default_rng(int(seed)); plant = ReferencePlant() if mismatch_scale == 1.0 else ReferencePlant().mismatched(mismatch_scale); rows=[]
    for fault_motor in [None, 0, 1, 2, 3]:
        for j in range(int(trajectories_per_class)):
            y,u=simulate_sequence(seed=int(rng.integers(0,2**31-1)),samples=200,fault_motor=fault_motor,fault_start=None if fault_motor is None else 100,plant=plant)
            rows.append({"fault_motor":fault_motor,"y":y,"u":u,"trajectory":j})
    return rows
