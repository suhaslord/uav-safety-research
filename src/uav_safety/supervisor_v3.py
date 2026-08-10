from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from math import exp, sqrt
import numpy as np

from .perception import Observation
from .reference_estimator import ReferenceObservation


class DecisionV3(str, Enum):
    PROCEED = "proceed"
    HOLD = "hold"
    ABORT = "abort"


@dataclass(frozen=True)
class SupervisorV3Config:
    dt: float = 0.05
    bias_window: int = 24
    bias_min_samples: int = 6
    bias_activation_m: float = 0.10
    max_bias_correction_m: float = 1.10
    correction_gain: float = 0.95
    reference_base_weight: float = 0.32
    reference_max_age_steps: int = 15
    risk_alpha: float = 0.20
    hold_risk: float = 0.68
    release_risk: float = 0.52
    abort_risk: float = 0.90
    hold_persistence: int = 5
    release_persistence: int = 6
    abort_persistence: int = 14
    disagreement_hold: float = 1.8
    disagreement_abort: float = 3.2
    disagreement_abort_persistence: int = 10
    near_ground_z: float = 0.75
    max_hold_steps: int = 180


@dataclass
class FusionResult:
    control_obs: Observation
    lateral_disagreement_m: float
    normalized_disagreement: float
    unexplained_disagreement: float
    bias_estimate_x: float
    bias_confidence: float
    applied_bias_correction: float
    reference_weight: float
    reference_usable: bool


@dataclass
class SafetyDecisionV3:
    decision: DecisionV3
    risk: float
    instantaneous_risk: float
    reason: str


class RedundantStateFusion:
    """Fuse vision with an independent lower-rate estimate.

    The fusion layer estimates persistent visual lateral bias from fresh,
    independent reference updates. It only applies strong bias correction when
    the offset is both persistent and statistically distinguishable from random
    disagreement. This prevents ordinary clean-condition noise from being
    "corrected" into a new bias.
    """

    def __init__(self, cfg: SupervisorV3Config | None = None):
        self.cfg = cfg or SupervisorV3Config()
        self._bias_samples: deque[float] = deque(maxlen=self.cfg.bias_window)

    def update(
        self,
        raw_vision: Observation,
        filtered_vision: Observation,
        reference: ReferenceObservation,
    ) -> FusionResult:
        c = self.cfg
        reference_usable = bool(
            reference.available and reference.age_steps <= c.reference_max_age_steps
        )

        if reference.fresh and not raw_vision.dropped:
            sample = float(np.clip(raw_vision.x - reference.x, -2.5, 2.5))
            self._bias_samples.append(sample)

        bias_estimate, bias_confidence = self._bias_statistics()
        correction = float(np.clip(
            bias_estimate * bias_confidence * c.correction_gain,
            -c.max_bias_correction_m,
            c.max_bias_correction_m,
        ))

        if reference_usable:
            combined_sigma = max(
                0.08,
                sqrt(filtered_vision.sigma_pos ** 2 + reference.sigma_pos ** 2),
            )
            lateral_disagreement = float(filtered_vision.x - reference.x)
            normalized = abs(lateral_disagreement) / combined_sigma
            unexplained = normalized * (1.0 - 0.85 * bias_confidence)

            freshness = exp(-reference.age_steps / 7.0)
            quality = float(np.clip(1.0 - reference.sigma_pos / 1.8, 0.10, 1.0))
            reference_weight = float(np.clip(
                c.reference_base_weight * freshness * quality,
                0.0,
                c.reference_base_weight,
            ))
        else:
            lateral_disagreement = 0.0
            normalized = 0.0
            unexplained = 0.0
            reference_weight = 0.0

        corrected_x = filtered_vision.x - correction

        if reference_usable:
            # Lateral position receives the strongest redundant-estimator weight
            # because persistent x-bias is the V2 failure mode. Altitude and
            # velocity retain mostly the vision estimate.
            w = reference_weight
            control_x = (1.0 - w) * corrected_x + w * reference.x
            weak_w = 0.35 * w
            control_z = (1.0 - weak_w) * filtered_vision.z + weak_w * reference.z
            control_vx = (1.0 - weak_w) * filtered_vision.vx + weak_w * reference.vx
            control_vz = (1.0 - weak_w) * filtered_vision.vz + weak_w * reference.vz

            ref_conf = float(np.clip(
                exp(-reference.sigma_pos / 0.9) * exp(-reference.age_steps / 10.0),
                0.0,
                0.95,
            ))
            confidence = float(np.clip(
                filtered_vision.confidence + 0.30 * ref_conf * (1.0 - filtered_vision.confidence),
                0.02,
                0.99,
            ))
            sigma_pos = float(max(
                0.04,
                (1.0 - w) * filtered_vision.sigma_pos + w * reference.sigma_pos,
            ))
            dropped = bool(raw_vision.dropped and not reference.fresh)
        else:
            control_x = corrected_x
            control_z = filtered_vision.z
            control_vx = filtered_vision.vx
            control_vz = filtered_vision.vz
            confidence = filtered_vision.confidence
            sigma_pos = filtered_vision.sigma_pos
            dropped = filtered_vision.dropped

        control_obs = Observation(
            x=float(control_x),
            z=float(max(0.0, control_z)),
            vx=float(control_vx),
            vz=float(control_vz),
            confidence=float(confidence),
            sigma_pos=float(sigma_pos),
            dropped=bool(dropped),
        )

        return FusionResult(
            control_obs=control_obs,
            lateral_disagreement_m=float(lateral_disagreement),
            normalized_disagreement=float(normalized),
            unexplained_disagreement=float(unexplained),
            bias_estimate_x=float(bias_estimate),
            bias_confidence=float(bias_confidence),
            applied_bias_correction=float(correction),
            reference_weight=float(reference_weight),
            reference_usable=reference_usable,
        )

    def _bias_statistics(self) -> tuple[float, float]:
        c = self.cfg
        n = len(self._bias_samples)
        if n == 0:
            return 0.0, 0.0

        values = np.asarray(self._bias_samples, dtype=float)
        mean = float(values.mean())
        if n < c.bias_min_samples:
            return mean, 0.0

        std = float(values.std(ddof=1)) if n > 1 else 1.0
        standard_error = std / sqrt(n) + 0.05
        signal = abs(mean) / standard_error

        maturity = float(np.clip((n - c.bias_min_samples + 1) / 8.0, 0.0, 1.0))
        signal_conf = float(np.clip((signal - 0.8) / 1.8, 0.0, 1.0))
        magnitude_conf = float(np.clip(
            (abs(mean) - c.bias_activation_m) / 0.35,
            0.0,
            1.0,
        ))
        confidence = maturity * signal_conf * magnitude_conf
        return mean, float(np.clip(confidence, 0.0, 1.0))


class RedundantSafetySupervisorV3:
    """Persistence-aware supervisor that distinguishes correctable bias from risk."""

    def __init__(self, cfg: SupervisorV3Config | None = None):
        self.cfg = cfg or SupervisorV3Config()
        self.filtered_risk: float | None = None
        self.high_streak = 0
        self.severe_streak = 0
        self.clear_streak = 0
        self.disagreement_streak = 0
        self.hold_steps = 0
        self.state = DecisionV3.PROCEED

    def assess(
        self,
        raw_vision: Observation,
        fusion: FusionResult,
        reference: ReferenceObservation,
    ) -> SafetyDecisionV3:
        c = self.cfg
        obs = fusion.control_obs

        confidence_risk = 1.0 - obs.confidence
        uncertainty_risk = float(np.clip(obs.sigma_pos / 0.9, 0.0, 1.0))
        lateral_risk = float(np.clip(abs(obs.x) / 2.8, 0.0, 1.0))
        descent_risk = float(np.clip(max(0.0, -obs.vz - 0.80) / 1.1, 0.0, 1.0))
        disagreement_risk = float(np.clip(
            (fusion.unexplained_disagreement - 1.0) / 2.5,
            0.0,
            1.0,
        ))

        if raw_vision.dropped and not fusion.reference_usable:
            redundancy_risk = 0.20
        elif raw_vision.dropped:
            redundancy_risk = 0.05
        elif not fusion.reference_usable:
            redundancy_risk = 0.04
        else:
            redundancy_risk = 0.0

        inst = float(np.clip(
            0.24 * confidence_risk
            + 0.18 * uncertainty_risk
            + 0.14 * lateral_risk
            + 0.08 * descent_risk
            + 0.24 * disagreement_risk
            + redundancy_risk,
            0.0,
            1.0,
        ))

        if self.filtered_risk is None:
            self.filtered_risk = inst
        else:
            self.filtered_risk = c.risk_alpha * inst + (1.0 - c.risk_alpha) * self.filtered_risk
        r = float(self.filtered_risk)

        self.high_streak = self.high_streak + 1 if r >= c.hold_risk else max(0, self.high_streak - 1)
        self.severe_streak = self.severe_streak + 1 if r >= c.abort_risk else max(0, self.severe_streak - 1)
        self.clear_streak = self.clear_streak + 1 if r <= c.release_risk else 0
        self.disagreement_streak = (
            self.disagreement_streak + 1
            if fusion.unexplained_disagreement >= c.disagreement_hold
            else max(0, self.disagreement_streak - 1)
        )

        near_ground = obs.z <= c.near_ground_z
        unexplained_severe = fusion.unexplained_disagreement >= c.disagreement_abort

        if near_ground and self.severe_streak >= c.abort_persistence:
            return SafetyDecisionV3(DecisionV3.ABORT, r, inst, "persistent severe fused-state risk near ground")

        if (
            near_ground
            and unexplained_severe
            and self.disagreement_streak >= c.disagreement_abort_persistence
            and fusion.bias_confidence < 0.45
        ):
            return SafetyDecisionV3(DecisionV3.ABORT, r, inst, "persistent unexplained estimator disagreement near ground")

        if self.state == DecisionV3.HOLD:
            self.hold_steps += 1
            if self.clear_streak >= c.release_persistence:
                self.state = DecisionV3.PROCEED
                self.hold_steps = 0
                return SafetyDecisionV3(DecisionV3.PROCEED, r, inst, "fused risk recovered")

            if near_ground and self.hold_steps >= c.max_hold_steps:
                return SafetyDecisionV3(DecisionV3.ABORT, r, inst, "unresolved risk exceeded near-ground hold budget")

            return SafetyDecisionV3(DecisionV3.HOLD, r, inst, "waiting for redundant evidence to stabilize")

        if self.high_streak >= c.hold_persistence or self.disagreement_streak >= c.hold_persistence:
            self.state = DecisionV3.HOLD
            self.hold_steps = 1
            return SafetyDecisionV3(DecisionV3.HOLD, r, inst, "persistent fused-state uncertainty")

        return SafetyDecisionV3(DecisionV3.PROCEED, r, inst, "redundant evidence supports continued landing")
