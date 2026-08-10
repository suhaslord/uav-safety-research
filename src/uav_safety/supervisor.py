from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import numpy as np

from .config import SupervisorConfig
from .perception import Observation


class Decision(str, Enum):
    PROCEED = "proceed"
    HOLD = "hold"
    ABORT = "abort"


@dataclass
class SafetyDecision:
    decision: Decision
    risk: float
    reason: str


class SafetySupervisor:
    """
    Confidence-aware supervisory layer.

    It does not replace the flight controller. It decides whether the downstream
    controller should continue descending, temporarily hold, or terminate the
    simulated landing attempt when perception risk is too high.
    """

    def __init__(self, cfg: SupervisorConfig):
        self.cfg = cfg
        self.hold_steps = 0

    def assess(self, obs: Observation) -> SafetyDecision:
        c = self.cfg

        confidence_risk = 1.0 - obs.confidence
        uncertainty_risk = float(np.clip(obs.sigma_pos / 0.8, 0.0, 1.0))
        lateral_risk = float(np.clip(abs(obs.x) / 2.5, 0.0, 1.0))
        descent_risk = float(np.clip(max(0.0, -obs.vz - 0.75) / 1.0, 0.0, 1.0))
        dropout_risk = 0.12 if obs.dropped else 0.0

        # Risk deliberately uses interpretable components instead of an opaque model.
        risk = float(np.clip(
            0.43 * confidence_risk
            + 0.27 * uncertainty_risk
            + 0.16 * lateral_risk
            + 0.09 * descent_risk
            + dropout_risk,
            0.0,
            1.0,
        ))

        if obs.z <= c.near_ground_z and (
            risk >= c.abort_risk or obs.confidence < c.min_confidence
        ):
            return SafetyDecision(Decision.ABORT, risk, "high perception risk near ground")

        if risk >= c.hold_risk:
            self.hold_steps += 1
            if self.hold_steps > c.max_hold_steps:
                return SafetyDecision(Decision.ABORT, risk, "risk persisted beyond hold budget")
            return SafetyDecision(Decision.HOLD, risk, "uncertainty above hold threshold")

        self.hold_steps = max(0, self.hold_steps - 1)
        return SafetyDecision(Decision.PROCEED, risk, "risk acceptable")
