from __future__ import annotations

from dataclasses import dataclass
from math import exp, sqrt

import numpy as np

from .perception import Observation
from .phase6_fusion import Phase6FusionConfig, Phase6RedundantFusionAdapter
from .phase6b_fusion import Phase6BComponentGateConfig
from .reference_estimator import ReferenceObservation
from .supervisor_v3 import FusionResult, SupervisorV3Config


@dataclass(frozen=True)
class Phase6DConsistencyConfig:
    """Simulation-only estimator-consistency policy.

    A 3-sigma threshold is used as a conventional statistical consistency test,
    not selected from landing outcomes.
    """

    altitude_disagreement_sigma_threshold: float = 3.0
    min_combined_altitude_sigma_m: float = 0.20


@dataclass
class Phase6DDiagnostics:
    p_x_good: float
    p_z_good: float
    lateral_abstained: bool
    altitude_abstained: bool
    lateral_reference_takeover: bool
    altitude_reference_takeover: bool
    lateral_reference_weight: float
    altitude_reference_weight: float
    altitude_disagreement_sigma: float
    hard_altitude_alias: bool


class Phase6DComponentFusionAdapter:
    """Separate soft altitude uncertainty from hard estimator contradiction.

    Soft low p_z uses the Phase 6C policy: position-only altitude fallback.
    A >3-sigma image/reference altitude contradiction is classified as a hard
    alias; only then does the existing Phase 6B fallback also blend vertical
    rate. Lateral fallback and frozen V3 evidence remain unchanged.
    """

    def __init__(
        self,
        supervisor_cfg: SupervisorV3Config | None = None,
        base_fusion_cfg: Phase6FusionConfig | None = None,
        gate_cfg: Phase6BComponentGateConfig | None = None,
        consistency_cfg: Phase6DConsistencyConfig | None = None,
    ):
        self.supervisor_cfg = supervisor_cfg or SupervisorV3Config()
        self.gate_cfg = gate_cfg or Phase6BComponentGateConfig()
        self.consistency_cfg = consistency_cfg or Phase6DConsistencyConfig()
        self.base = Phase6RedundantFusionAdapter(self.supervisor_cfg, base_fusion_cfg)

    def update(
        self,
        image_obs: Observation,
        reference: ReferenceObservation,
        *,
        p_x_good: float,
        p_z_good: float,
    ) -> tuple[FusionResult, Phase6DDiagnostics]:
        base = self.base.update(image_obs, reference)
        c = self.gate_cfg
        k = self.consistency_cfg

        reference_usable = bool(
            base.reference_usable
            and reference.available
            and reference.age_steps <= c.max_stale_reference_age_steps
        )
        combined_sigma = max(
            k.min_combined_altitude_sigma_m,
            sqrt(max(0.05, image_obs.sigma_pos) ** 2 + max(0.05, reference.sigma_pos) ** 2),
        )
        altitude_disagreement_sigma = (
            abs(image_obs.z - reference.z) / combined_sigma if reference_usable else 0.0
        )
        hard_altitude_alias = bool(
            reference_usable
            and altitude_disagreement_sigma > k.altitude_disagreement_sigma_threshold
        )

        lateral_abstained = bool(p_x_good < c.lateral_confidence_threshold)
        altitude_abstained = bool(
            p_z_good < c.altitude_confidence_threshold or hard_altitude_alias
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
            if hard_altitude_alias:
                # A hard contradiction invalidates the derivative of the visual
                # altitude track as well as its position. Reuse the existing
                # Phase 6B weight rather than introducing a new outcome-tuned gain.
                vz = (1.0 - altitude_w) * control.vz + altitude_w * reference.vz
            else:
                # Soft scale uncertainty alone does not imply bad vertical rate.
                vz = control.vz

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
            sigma = float(np.clip(max(control.sigma_pos, 0.55 * reference.sigma_pos), 0.05, 2.2))
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
        diag = Phase6DDiagnostics(
            p_x_good=float(p_x_good),
            p_z_good=float(p_z_good),
            lateral_abstained=lateral_abstained,
            altitude_abstained=altitude_abstained,
            lateral_reference_takeover=bool(lateral_abstained and reference_usable),
            altitude_reference_takeover=bool(altitude_abstained and reference_usable),
            lateral_reference_weight=lateral_w,
            altitude_reference_weight=altitude_w,
            altitude_disagreement_sigma=float(altitude_disagreement_sigma),
            hard_altitude_alias=hard_altitude_alias,
        )
        return fused, diag
