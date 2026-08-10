from __future__ import annotations

from dataclasses import dataclass
from math import exp

import numpy as np

from .perception import Observation
from .reference_estimator import ReferenceObservation
from .supervisor_v3 import FusionResult, RedundantStateFusion, SupervisorV3Config


@dataclass(frozen=True)
class Phase6FusionConfig:
    """Adapter policy for pixel-derived observations feeding frozen V3 safety logic."""

    bias_confidence_gate: float = 0.50
    bias_correction_ramp_end: float = 0.78
    max_reference_weight_when_tracked: float = 0.10
    dropped_reference_weight: float = 0.70
    stale_reference_weight: float = 0.48
    reference_vertical_weight_when_dropped: float = 0.55
    reference_velocity_weight_when_dropped: float = 0.45

    # Near touchdown, a visually plausible sequence can still be smoothly wrong.
    # If independent evidence strongly conflicts with the accepted image track,
    # temporarily treat redundancy as an integrity fallback rather than merely a
    # small bias-correction aid.
    integrity_gate_altitude_m: float = 1.00
    integrity_position_disagreement_m: float = 0.65
    integrity_velocity_disagreement_mps: float = 0.80
    integrity_max_reference_age_steps: int = 5
    integrity_reference_weight_fresh: float = 0.78
    integrity_reference_weight_stale: float = 0.62
    integrity_velocity_weight: float = 0.85


class Phase6RedundantFusionAdapter:
    """Use frozen V3 evidence while adapting fusion to calibrated image tracks.

    Healthy accepted image tracks stay primary. Persistent bias evidence may
    gradually correct lateral position. During image abstention, or during a
    strong near-ground cross-estimator integrity conflict, the independent
    reference is allowed to carry substantially more temporary control weight.
    """

    def __init__(
        self,
        supervisor_cfg: SupervisorV3Config | None = None,
        cfg: Phase6FusionConfig | None = None,
    ):
        self.supervisor_cfg = supervisor_cfg or SupervisorV3Config()
        self.cfg = cfg or Phase6FusionConfig()
        self._core = RedundantStateFusion(self.supervisor_cfg)

    def update(
        self,
        image_obs: Observation,
        reference: ReferenceObservation,
    ) -> FusionResult:
        # Preserve frozen V3's evidence model: bias window, confidence logic, and
        # explained/unexplained disagreement are computed unchanged.
        base = self._core.update(image_obs, image_obs, reference)
        c = self.cfg

        if not image_obs.dropped:
            ramp = float(np.clip(
                (base.bias_confidence - c.bias_confidence_gate)
                / max(1e-6, c.bias_correction_ramp_end - c.bias_confidence_gate),
                0.0,
                1.0,
            ))
            correction = float(base.applied_bias_correction * ramp)
            corrected_x = float(image_obs.x - correction)

            if self._integrity_conflict(image_obs, reference, base):
                ref_weight = float(
                    c.integrity_reference_weight_fresh
                    if reference.fresh
                    else c.integrity_reference_weight_stale
                )
                velocity_weight = float(c.integrity_velocity_weight)
                control_x = (1.0 - ref_weight) * corrected_x + ref_weight * reference.x
                control_vx = (1.0 - velocity_weight) * image_obs.vx + velocity_weight * reference.vx

                # Accepted image geometry/altitude can remain useful even when its
                # lateral solution is corrupted. Keep z/vz image-derived, but
                # reduce confidence and expose higher uncertainty to frozen V3.
                confidence = float(np.clip(image_obs.confidence * 0.72, 0.05, 0.90))
                sigma = float(np.clip(max(image_obs.sigma_pos, reference.sigma_pos) * 1.15, 0.08, 2.2))
                control_obs = Observation(
                    x=float(control_x),
                    z=float(image_obs.z),
                    vx=float(control_vx),
                    vz=float(image_obs.vz),
                    confidence=confidence,
                    sigma_pos=sigma,
                    dropped=False,
                )
                return FusionResult(
                    control_obs=control_obs,
                    lateral_disagreement_m=base.lateral_disagreement_m,
                    normalized_disagreement=base.normalized_disagreement,
                    unexplained_disagreement=base.unexplained_disagreement,
                    bias_estimate_x=base.bias_estimate_x,
                    bias_confidence=base.bias_confidence,
                    applied_bias_correction=correction,
                    reference_weight=ref_weight,
                    reference_usable=base.reference_usable,
                )

            # Normal tracked mode: a single noisy reference sample must not
            # perturb an already-good accepted image trajectory.
            if base.reference_usable and ramp > 0.0:
                ref_weight = float(min(
                    c.max_reference_weight_when_tracked,
                    base.reference_weight * ramp,
                ))
                control_x = (1.0 - ref_weight) * corrected_x + ref_weight * reference.x
            else:
                ref_weight = 0.0
                control_x = corrected_x

            control_obs = Observation(
                x=float(control_x),
                z=float(image_obs.z),
                vx=float(image_obs.vx),
                vz=float(image_obs.vz),
                confidence=float(image_obs.confidence),
                sigma_pos=float(image_obs.sigma_pos),
                dropped=False,
            )

            return FusionResult(
                control_obs=control_obs,
                lateral_disagreement_m=base.lateral_disagreement_m,
                normalized_disagreement=base.normalized_disagreement,
                unexplained_disagreement=base.unexplained_disagreement,
                bias_estimate_x=base.bias_estimate_x,
                bias_confidence=base.bias_confidence,
                applied_bias_correction=correction,
                reference_weight=ref_weight,
                reference_usable=base.reference_usable,
            )

        # Image abstention: visual state is propagated rather than fresh. If
        # independent evidence is usable, allow it to carry more of the estimate
        # until image tracking reacquires.
        if base.reference_usable:
            freshness = exp(-reference.age_steps / 7.0)
            target_w = (
                c.dropped_reference_weight if reference.fresh
                else c.stale_reference_weight
            )
            ref_weight = float(np.clip(target_w * (0.55 + 0.45 * freshness), 0.0, 0.85))
            vertical_w = float(c.reference_vertical_weight_when_dropped * ref_weight)
            velocity_w = float(c.reference_velocity_weight_when_dropped * ref_weight)

            control_x = (1.0 - ref_weight) * image_obs.x + ref_weight * reference.x
            control_z = (1.0 - vertical_w) * image_obs.z + vertical_w * reference.z
            control_vx = (1.0 - velocity_w) * image_obs.vx + velocity_w * reference.vx
            control_vz = (1.0 - velocity_w) * image_obs.vz + velocity_w * reference.vz

            ref_conf = float(np.clip(
                exp(-reference.sigma_pos / 0.9) * exp(-reference.age_steps / 10.0),
                0.0,
                0.95,
            ))
            confidence = float(np.clip(max(image_obs.confidence, 0.72 * ref_conf), 0.02, 0.95))
            sigma = float(np.clip(
                (1.0 - ref_weight) * image_obs.sigma_pos + ref_weight * reference.sigma_pos,
                0.05,
                2.2,
            ))
            dropped = bool(not reference.fresh)
        else:
            ref_weight = 0.0
            control_x = image_obs.x
            control_z = image_obs.z
            control_vx = image_obs.vx
            control_vz = image_obs.vz
            confidence = image_obs.confidence
            sigma = image_obs.sigma_pos
            dropped = True

        control_obs = Observation(
            x=float(control_x),
            z=float(max(0.0, control_z)),
            vx=float(control_vx),
            vz=float(control_vz),
            confidence=float(confidence),
            sigma_pos=float(sigma),
            dropped=bool(dropped),
        )
        return FusionResult(
            control_obs=control_obs,
            lateral_disagreement_m=base.lateral_disagreement_m,
            normalized_disagreement=base.normalized_disagreement,
            unexplained_disagreement=base.unexplained_disagreement,
            bias_estimate_x=base.bias_estimate_x,
            bias_confidence=base.bias_confidence,
            applied_bias_correction=0.0,
            reference_weight=ref_weight,
            reference_usable=base.reference_usable,
        )

    def _integrity_conflict(
        self,
        image_obs: Observation,
        reference: ReferenceObservation,
        base: FusionResult,
    ) -> bool:
        c = self.cfg
        if not base.reference_usable:
            return False
        if reference.age_steps > c.integrity_max_reference_age_steps:
            return False
        if reference.z > c.integrity_gate_altitude_m:
            return False

        # Use independent disagreement, never simulator ground truth. Either a
        # large unexplained lateral offset or a large velocity disagreement is
        # enough to indicate that a smooth image track may be confidently wrong.
        position_conflict = base.unexplained_disagreement >= c.integrity_position_disagreement_m
        velocity_conflict = abs(image_obs.vx - reference.vx) >= c.integrity_velocity_disagreement_mps
        return bool(position_conflict or velocity_conflict)
