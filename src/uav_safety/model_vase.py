from __future__ import annotations

from dataclasses import dataclass

from .perception import Observation
from .reference_estimator import ReferenceObservation
from .supervisor_v3 import (
    FusionResult,
    RedundantSafetySupervisorV3,
    RedundantStateFusion,
    SafetyDecisionV3,
    SupervisorV3Config,
)


MODEL_VASE_NAME = "Model VASE"
MODEL_VASE_EXPANSION = "Vision, Auxiliary evidence, State reliability, Escalation"
MODEL_VASE_SCHEMA = "aegisland.model-vase.research-stack.v1"


@dataclass(frozen=True)
class ModelVaseStep:
    """One state-fusion and supervision result from Model VASE."""

    fusion: FusionResult
    decision: SafetyDecisionV3


class ModelVase:
    """Versioned orchestration of the frozen V3 safety-decision path.

    The project has several evidence tracks: image perception, uncertainty
    calibration, redundant state estimation, and external trace checks. Their
    results do not share one compatible learned checkpoint. This runtime joins
    the validated state-estimate handoff to the frozen V3 fusion and supervisor
    without changing their equations, parameters, or random-number streams.

    A caller supplies both the raw and temporally filtered vision estimates,
    plus the independent reference estimate. The wrapper returns the fused
    control observation and the existing PROCEED/HOLD/ABORT decision. Image
    detector scores and Phase 12 interval widths remain evidence inputs for
    future preregistered integration work; they are not silently converted to
    safety probabilities here.
    """

    name = MODEL_VASE_NAME
    expansion = MODEL_VASE_EXPANSION
    schema = MODEL_VASE_SCHEMA

    def __init__(self, cfg: SupervisorV3Config | None = None):
        self.fusion = RedundantStateFusion(cfg)
        self.supervisor = RedundantSafetySupervisorV3(cfg)

    def step(
        self,
        raw_vision: Observation,
        filtered_vision: Observation,
        reference: ReferenceObservation,
    ) -> ModelVaseStep:
        """Fuse available state evidence, then apply the unchanged V3 policy."""

        fused = self.fusion.update(raw_vision, filtered_vision, reference)
        decision = self.supervisor.assess(raw_vision, fused, reference)
        return ModelVaseStep(fusion=fused, decision=decision)
