from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np


class FaultScenario(str, Enum):
    """Simulation-only fault families for external-validity stress tests."""

    INDEPENDENT = "independent"
    REFERENCE_DRIFT = "reference_drift"
    SHARED_LATERAL_BIAS = "shared_lateral_bias"
    SHARED_DROPOUT = "shared_dropout"
    LATENCY_BURST = "latency_burst"


@dataclass(frozen=True)
class Phase7FaultConfig:
    """Episode-level fault configuration.

    Values are intentionally generic stress-model parameters rather than claims
    about a particular physical sensor or aircraft. Phase 7 uses them to test
    whether conclusions survive violations of the independent-noise assumption.
    """

    onset_fraction_low: float = 0.30
    onset_fraction_high: float = 0.55
    duration_fraction_low: float = 0.20
    duration_fraction_high: float = 0.45
    reference_drift_rate_m_per_s: float = 0.035
    shared_lateral_bias_m: float = 0.50
    shared_dropout_probability: float = 0.55
    latency_burst_extra_steps: int = 6
    drift_random_walk_sigma_m: float = 0.004


@dataclass(frozen=True)
class FaultState:
    active: bool
    scenario: FaultScenario
    vision_x_bias_m: float = 0.0
    reference_x_bias_m: float = 0.0
    reference_z_bias_m: float = 0.0
    reference_dropout_boost: float = 0.0
    vision_dropout_boost: float = 0.0
    reference_latency_extra_steps: int = 0


class Phase7FaultInjector:
    """Deterministic per-episode fault scheduler with explicit common-mode cases."""

    def __init__(
        self,
        rng: np.random.Generator,
        *,
        scenario: FaultScenario | str = FaultScenario.INDEPENDENT,
        total_steps: int,
        dt: float,
        cfg: Phase7FaultConfig | None = None,
    ):
        self.rng = rng
        self.scenario = FaultScenario(scenario)
        self.total_steps = int(total_steps)
        self.dt = float(dt)
        self.cfg = cfg or Phase7FaultConfig()

        c = self.cfg
        onset_fraction = float(rng.uniform(c.onset_fraction_low, c.onset_fraction_high))
        duration_fraction = float(rng.uniform(c.duration_fraction_low, c.duration_fraction_high))
        self.onset_step = int(np.clip(round(onset_fraction * self.total_steps), 0, self.total_steps - 1))
        duration_steps = max(1, int(round(duration_fraction * self.total_steps)))
        self.end_step = min(self.total_steps, self.onset_step + duration_steps)
        self._drift_bias = 0.0

    def state(self, step: int) -> FaultState:
        active = bool(self.onset_step <= step < self.end_step)
        if not active or self.scenario == FaultScenario.INDEPENDENT:
            return FaultState(active=False, scenario=self.scenario)

        c = self.cfg
        elapsed_s = max(0.0, (step - self.onset_step) * self.dt)

        if self.scenario == FaultScenario.REFERENCE_DRIFT:
            walk = float(self.rng.normal(0.0, c.drift_random_walk_sigma_m))
            self._drift_bias += c.reference_drift_rate_m_per_s * self.dt + walk
            return FaultState(
                active=True,
                scenario=self.scenario,
                reference_x_bias_m=float(self._drift_bias),
            )

        if self.scenario == FaultScenario.SHARED_LATERAL_BIAS:
            # A measurement-space proxy for a shared frame/map/geometry error:
            # both streams can agree while being wrong in the same direction.
            ramp = float(np.clip(elapsed_s / 1.5, 0.0, 1.0))
            bias = c.shared_lateral_bias_m * ramp
            return FaultState(
                active=True,
                scenario=self.scenario,
                vision_x_bias_m=float(bias),
                reference_x_bias_m=float(bias),
            )

        if self.scenario == FaultScenario.SHARED_DROPOUT:
            return FaultState(
                active=True,
                scenario=self.scenario,
                reference_dropout_boost=c.shared_dropout_probability,
                vision_dropout_boost=c.shared_dropout_probability,
            )

        if self.scenario == FaultScenario.LATENCY_BURST:
            return FaultState(
                active=True,
                scenario=self.scenario,
                reference_latency_extra_steps=c.latency_burst_extra_steps,
            )

        raise RuntimeError(f"Unhandled fault scenario: {self.scenario}")
