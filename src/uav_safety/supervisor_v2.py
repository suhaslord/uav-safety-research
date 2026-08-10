from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import numpy as np

from .perception import Observation


class DecisionV2(str, Enum):
    PROCEED = "proceed"
    HOLD = "hold"
    ABORT = "abort"


@dataclass(frozen=True)
class SupervisorV2Config:
    """Configuration for the temporal Aegis V2 supervisor.

    V2 deliberately separates instantaneous risk from persistent risk. A single
    bad frame can trigger caution, but abort requires sustained evidence.
    """

    dt: float = 0.05
    risk_alpha: float = 0.22
    hold_risk: float = 0.70
    release_risk: float = 0.56
    abort_risk: float = 0.88
    hold_persistence: int = 5
    release_persistence: int = 7
    abort_persistence: int = 12
    dropout_hold_streak: int = 3
    dropout_abort_streak: int = 12
    near_ground_z: float = 0.85
    max_hold_steps: int = 220


@dataclass
class SafetyDecisionV2:
    decision: DecisionV2
    risk: float
    instantaneous_risk: float
    reason: str


class TemporalObservationFilter:
    """Small temporal filter for control-side observations.

    Non-dropped observations are smoothed with confidence-dependent gains.
    During a dropout, the last filtered state is propagated using its velocity
    rather than repeatedly feeding a stale camera frame to the controller.

    This is intentionally simple and interpretable; it is not a Kalman filter.
    """

    def __init__(self, dt: float = 0.05):
        self.dt = dt
        self._state: Observation | None = None

    def update(self, obs: Observation) -> Observation:
        if self._state is None:
            self._state = obs
            return obs

        prev = self._state

        if obs.dropped:
            predicted = Observation(
                x=prev.x + prev.vx * self.dt,
                z=max(0.0, prev.z + prev.vz * self.dt),
                vx=prev.vx,
                vz=prev.vz,
                confidence=max(0.04, prev.confidence * 0.82),
                sigma_pos=min(2.0, prev.sigma_pos * 1.12),
                dropped=True,
            )
            self._state = predicted
            return predicted

        # Trust clean/high-confidence measurements faster; smooth uncertain ones.
        gain = float(np.clip(0.28 + 0.42 * obs.confidence, 0.30, 0.68))
        filtered = Observation(
            x=(1.0 - gain) * prev.x + gain * obs.x,
            z=max(0.0, (1.0 - gain) * prev.z + gain * obs.z),
            vx=(1.0 - gain) * prev.vx + gain * obs.vx,
            vz=(1.0 - gain) * prev.vz + gain * obs.vz,
            confidence=float(np.clip(0.65 * obs.confidence + 0.35 * prev.confidence, 0.02, 0.99)),
            sigma_pos=float((1.0 - gain) * prev.sigma_pos + gain * obs.sigma_pos),
            dropped=False,
        )
        self._state = filtered
        return filtered


class TemporalSafetySupervisorV2:
    """Aegis V2: persistence-aware supervisor with hysteresis.

    Key changes from V1:
    - risk is smoothed across time;
    - HOLD/ABORT require persistent evidence;
    - release uses a separate lower threshold (hysteresis);
    - dropouts are tracked as streaks rather than treated as isolated events;
    - temporal inconsistency contributes to risk;
    - abort is intentionally difficult away from the ground.
    """

    def __init__(self, cfg: SupervisorV2Config | None = None):
        self.cfg = cfg or SupervisorV2Config()
        self.filtered_risk: float | None = None
        self.prev_obs: Observation | None = None
        self.high_streak = 0
        self.severe_streak = 0
        self.clear_streak = 0
        self.dropout_streak = 0
        self.hold_steps = 0
        self.state = DecisionV2.PROCEED

    def _instantaneous_risk(self, obs: Observation) -> float:
        confidence_risk = 1.0 - obs.confidence
        uncertainty_risk = float(np.clip(obs.sigma_pos / 0.9, 0.0, 1.0))
        lateral_risk = float(np.clip(abs(obs.x) / 2.8, 0.0, 1.0))
        descent_risk = float(np.clip(max(0.0, -obs.vz - 0.80) / 1.1, 0.0, 1.0))

        temporal_risk = 0.0
        if self.prev_obs is not None and not obs.dropped and not self.prev_obs.dropped:
            measured_dx_dt = (obs.x - self.prev_obs.x) / self.cfg.dt
            velocity_disagreement = abs(measured_dx_dt - obs.vx)
            temporal_risk = float(np.clip(velocity_disagreement / 4.0, 0.0, 1.0))

        dropout_risk = 0.16 if obs.dropped else 0.0

        # Lower weight on raw confidence than V1: a consistently conservative
        # confidence score should not by itself force an abort.
        return float(np.clip(
            0.28 * confidence_risk
            + 0.22 * uncertainty_risk
            + 0.16 * lateral_risk
            + 0.08 * descent_risk
            + 0.10 * temporal_risk
            + dropout_risk,
            0.0,
            1.0,
        ))

    def assess(self, obs: Observation) -> SafetyDecisionV2:
        c = self.cfg
        inst = self._instantaneous_risk(obs)
        self.prev_obs = obs

        if self.filtered_risk is None:
            self.filtered_risk = inst
        else:
            self.filtered_risk = c.risk_alpha * inst + (1.0 - c.risk_alpha) * self.filtered_risk

        r = self.filtered_risk

        self.dropout_streak = self.dropout_streak + 1 if obs.dropped else 0
        self.high_streak = self.high_streak + 1 if r >= c.hold_risk else max(0, self.high_streak - 1)
        self.severe_streak = self.severe_streak + 1 if r >= c.abort_risk else max(0, self.severe_streak - 1)
        self.clear_streak = self.clear_streak + 1 if r <= c.release_risk else 0

        # Abort requires sustained severe evidence near the ground, a very long
        # dropout streak, or a hold that cannot recover within its time budget.
        if obs.z <= c.near_ground_z and self.severe_streak >= c.abort_persistence:
            return SafetyDecisionV2(DecisionV2.ABORT, r, inst, "persistent severe risk near ground")

        if obs.z <= c.near_ground_z and self.dropout_streak >= c.dropout_abort_streak:
            return SafetyDecisionV2(DecisionV2.ABORT, r, inst, "persistent perception dropout near ground")

        if self.state == DecisionV2.HOLD:
            self.hold_steps += 1

            if self.clear_streak >= c.release_persistence:
                self.state = DecisionV2.PROCEED
                self.hold_steps = 0
                return SafetyDecisionV2(DecisionV2.PROCEED, r, inst, "risk recovered below release threshold")

            if self.hold_steps >= c.max_hold_steps and r >= c.hold_risk:
                return SafetyDecisionV2(DecisionV2.ABORT, r, inst, "risk failed to recover within hold budget")

            return SafetyDecisionV2(DecisionV2.HOLD, r, inst, "waiting for persistent risk to clear")

        should_hold = (
            self.high_streak >= c.hold_persistence
            or self.dropout_streak >= c.dropout_hold_streak
        )
        if should_hold:
            self.state = DecisionV2.HOLD
            self.hold_steps = 1
            return SafetyDecisionV2(DecisionV2.HOLD, r, inst, "persistent uncertainty detected")

        return SafetyDecisionV2(DecisionV2.PROCEED, r, inst, "risk not persistent enough to intervene")
