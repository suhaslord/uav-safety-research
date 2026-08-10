from __future__ import annotations

from dataclasses import dataclass
from math import exp

import numpy as np

from .perception import Observation


@dataclass(frozen=True)
class RobustVelocityConfig:
    """Configuration for robust velocity extraction from accepted image positions."""

    dt: float = 0.05
    history_window: int = 13
    min_pair_dt_s: float = 0.10
    min_samples: int = 4
    spread_scale_mps: float = 0.75
    min_update_gain: float = 0.10
    max_update_gain: float = 0.42
    max_abs_vx: float = 2.2
    dropout_decay: float = 0.985
    confidence_floor_factor: float = 0.78
    sigma_inflation_max: float = 1.25


@dataclass(frozen=True)
class VelocityDiagnostics:
    robust_vx: float
    stabilized_vx: float
    slope_mad: float
    quality: float
    samples: int
    updated: bool


class RobustImageVelocityFilter:
    """Estimate lateral velocity robustly from a short image-position history.

    A single occluded-frame centroid can shift position by a few tenths of a
    metre. Differentiating that shift over 50 ms can create a large false
    velocity. This filter instead takes the median of all sufficiently separated
    pairwise slopes in a short accepted-position window, then uses the slope MAD
    to decide how aggressively the estimate should update.
    """

    def __init__(self, cfg: RobustVelocityConfig | None = None):
        self.cfg = cfg or RobustVelocityConfig()
        self._time_s = 0.0
        self._history: list[tuple[float, float]] = []
        self._vx = 0.0

    def update(self, obs: Observation) -> tuple[Observation, VelocityDiagnostics]:
        self._time_s += self.cfg.dt

        if obs.dropped:
            self._vx *= self.cfg.dropout_decay
            stabilized = Observation(
                x=obs.x,
                z=obs.z,
                vx=float(self._vx),
                vz=obs.vz,
                confidence=obs.confidence,
                sigma_pos=obs.sigma_pos,
                dropped=True,
            )
            return stabilized, VelocityDiagnostics(
                robust_vx=float(self._vx),
                stabilized_vx=float(self._vx),
                slope_mad=float("nan"),
                quality=0.0,
                samples=len(self._history),
                updated=False,
            )

        self._history.append((self._time_s, float(obs.x)))
        self._history = self._history[-self.cfg.history_window:]
        target_vx, mad, quality = self._robust_slope()

        if len(self._history) < self.cfg.min_samples:
            # Early in track acquisition there is not enough history for a robust
            # derivative. Keep velocity conservative rather than amplifying a
            # two-frame pixel shift.
            target_vx = float(np.clip(obs.vx, -1.2, 1.2))
            quality *= 0.5

        target_vx = float(np.clip(target_vx, -self.cfg.max_abs_vx, self.cfg.max_abs_vx))
        gain = self.cfg.min_update_gain + (
            self.cfg.max_update_gain - self.cfg.min_update_gain
        ) * quality
        self._vx = float((1.0 - gain) * self._vx + gain * target_vx)

        confidence_factor = self.cfg.confidence_floor_factor + (
            1.0 - self.cfg.confidence_floor_factor
        ) * quality
        sigma_factor = 1.0 + (self.cfg.sigma_inflation_max - 1.0) * (1.0 - quality)
        stabilized = Observation(
            x=obs.x,
            z=obs.z,
            vx=float(self._vx),
            vz=obs.vz,
            confidence=float(np.clip(obs.confidence * confidence_factor, 0.02, 0.99)),
            sigma_pos=float(np.clip(obs.sigma_pos * sigma_factor, 0.05, 2.5)),
            dropped=False,
        )
        return stabilized, VelocityDiagnostics(
            robust_vx=float(target_vx),
            stabilized_vx=float(self._vx),
            slope_mad=float(mad),
            quality=float(quality),
            samples=len(self._history),
            updated=True,
        )

    def _robust_slope(self) -> tuple[float, float, float]:
        if len(self._history) < 2:
            return 0.0, float("inf"), 0.0

        slopes: list[float] = []
        for i in range(len(self._history) - 1):
            ti, xi = self._history[i]
            for j in range(i + 1, len(self._history)):
                tj, xj = self._history[j]
                dt = tj - ti
                if dt >= self.cfg.min_pair_dt_s:
                    slopes.append((xj - xi) / dt)

        if not slopes:
            return self._vx, float("inf"), 0.0

        arr = np.asarray(slopes, dtype=float)
        median = float(np.median(arr))
        mad = float(np.median(np.abs(arr - median)))
        quality = float(np.clip(exp(-mad / self.cfg.spread_scale_mps), 0.0, 1.0))
        return median, mad, quality
