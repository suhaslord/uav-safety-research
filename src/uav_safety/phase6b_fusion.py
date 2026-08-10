from __future__ import annotations

from dataclasses import dataclass
from math import exp

import numpy as np

from .perception import Observation
from .phase6_fusion import Phase6FusionConfig, Phase6RedundantFusionAdapter
from .reference_estimator import ReferenceObservation
from .supervisor_v3 import FusionResult, SupervisorV3Config


@dataclass(frozen=True)
class Phase6BComponentGateConfig:
    """Development-selected component abstention policy.

    The 0.80 thresholds were selected from a predeclared risk/coverage grid on
    the Phase 6B calibration-development benchmark, before any Phase 6B landing
    outcomes were run.
    """

    lateral_confidence_threshold: float = 0.80
    altitude_confidence_threshold: float = 0.80
    fresh_reference_weight: float = 0.86
    stale_reference_weight: float = 0.66
    max_stale_reference_age_steps: int = 14
    unresolved_confidence_scale: float = 0.45
    unresolved_sigma_floor: float = 1.10


@dataclass
class ComponentFusionDiagnostics:
    p_x_good: float
    p_z_good: float
    lateral_abstained: bool
    altitude_abstained: bool
    lateral_reference_takeover: bool
    altitude_reference_takeover: bool
    lateral_reference_weight: float
    altitude_reference_weight: float


class Phase6BComponentFusionAdapter:
    """Add component-wise abstention around the established Phase 6 adapter.

    The base Phase 6 fusion and frozen V3 disagreement/bias evidence are retained.
    Phase 6B only changes the control observation when a calibrated image
    component is below its preselected confidence threshold.
    """

    def __init__(
        self,
        supervisor_cfg: SupervisorV3Config | None = None,
        base_fusion_cfg: Phase6FusionConfig | None = None,
        gate_cfg: Phase6BComponentGateConfig | None = None,
    ):
        self.supervisor_cfg = supervisor_cfg or SupervisorV3Config()
        self.gate_cfg = gate_cfg or Phase6BComponentGateConfig()
        self.base = Phase6RedundantFusionAdapter(self.supervisor_cfg, base_fusion_cfg)

    def update(
        self,
        image_obs: Observation,
        reference: ReferenceObservation,
        *,
        p_x_good: float,
        p_z_good: float,
    ) -> tuple[FusionResult, ComponentFusionDiagnostics]:
        base = self.base.update(image_obs, reference)
        c = self.gate_cfg

        lateral_abstained = bool(p_x_good < c.lateral_confidence_threshold)
        altitude_abstained = bool(p_z_good < c.altitude_confidence_threshold)
        reference_usable = bool(
            base.reference_usable
            and reference.available
            and reference.age_steps <= c.max_stale_reference_age_steps
        )

        if reference_usable:
            freshness = exp(-reference.age_steps / 7.0)
            target = c.fresh_reference_weight if reference.fresh else c.stale_reference_weight
            fallback_weight = float(np.clip(target * (0.60 + 0.40 * freshness), 0.0, 0.92))
        else:
            fallback_weight = 0.0

        control = base.control_obs
        x, z, vx, vz = control.x, control.z, control.vx, control.vz
        lateral_w = 0.0
        altitude_w = 0.0

        if lateral_abstained and reference_usable:
            lateral_w = fallback_weight
            x = (1.0 - lateral_w) * control.x + lateral_w * reference.x
            vx = (1.0 - lateral_w) * control.vx + lateral_w * reference.vx

        if altitude_abstained and reference_usable:
            altitude_w = fallback_weight
            z = (1.0 - altitude_w) * control.z + altitude_w * reference.z
            vz = (1.0 - altitude_w) * control.vz + altitude_w * reference.vz

        unresolved = bool(
            (lateral_abstained or altitude_abstained)
            and not reference_usable
        )
        ref_conf = float(np.clip(
            exp(-reference.sigma_pos / 0.9) * exp(-reference.age_steps / 10.0)
            if reference_usable else 0.0,
            0.0,
            0.95,
        ))

        component_conf_x = ref_conf if lateral_abstained and reference_usable else float(p_x_good)
        component_conf_z = ref_conf if altitude_abstained and reference_usable else float(p_z_good)
        confidence = float(np.clip(
            min(
                max(0.02, control.confidence),
                max(0.02, component_conf_x),
                max(0.02, component_conf_z),
            ),
            0.02,
            0.99,
        ))
        sigma = float(control.sigma_pos)
        dropped = bool(control.dropped)
        if unresolved:
            confidence = float(max(0.02, confidence * c.unresolved_confidence_scale))
            sigma = float(max(sigma, c.unresolved_sigma_floor))
            dropped = True
        elif reference_usable and (lateral_abstained or altitude_abstained):
            # A resolved component abstention is not a fabricated visual update:
            # the control state explicitly records uncertainty from two sources.
            sigma = float(np.clip(
                max(control.sigma_pos, 0.55 * reference.sigma_pos),
                0.05,
                2.2,
            ))
            dropped = False

        control_obs = Observation(
            x=float(x),
            z=float(max(0.0, z)),
            vx=float(vx),
            vz=float(vz),
            confidence=confidence,
            sigma_pos=sigma,
            dropped=dropped,
        )

        fused = FusionResult(
            control_obs=control_obs,
            lateral_disagreement_m=base.lateral_disagreement_m,
            normalized_disagreement=base.normalized_disagreement,
            unexplained_disagreement=base.unexplained_disagreement,
            bias_estimate_x=base.bias_estimate_x,
            bias_confidence=base.bias_confidence,
            applied_bias_correction=base.applied_bias_correction,
            reference_weight=float(max(base.reference_weight, lateral_w, altitude_w)),
            reference_usable=base.reference_usable,
        )
        diag = ComponentFusionDiagnostics(
            p_x_good=float(p_x_good),
            p_z_good=float(p_z_good),
            lateral_abstained=lateral_abstained,
            altitude_abstained=altitude_abstained,
            lateral_reference_takeover=bool(lateral_abstained and reference_usable),
            altitude_reference_takeover=bool(altitude_abstained and reference_usable),
            lateral_reference_weight=lateral_w,
            altitude_reference_weight=altitude_w,
        )
        return fused, diag
