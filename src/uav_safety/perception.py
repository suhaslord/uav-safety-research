from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from .dynamics import State


@dataclass(frozen=True)
class PerceptionProfile:
    sigma_x: float
    sigma_z: float
    sigma_vx: float
    sigma_vz: float
    dropout_prob: float
    bias_x: float
    confidence_scale: float


PROFILES: dict[str, PerceptionProfile] = {
    "clean": PerceptionProfile(0.05, 0.05, 0.03, 0.03, 0.00, 0.00, 1.00),
    "blur": PerceptionProfile(0.20, 0.12, 0.10, 0.08, 0.02, 0.08, 0.90),
    "low_light": PerceptionProfile(0.30, 0.18, 0.14, 0.10, 0.05, 0.22, 0.78),
    "occlusion": PerceptionProfile(0.45, 0.25, 0.22, 0.16, 0.18, 0.42, 0.64),
    "mixed": PerceptionProfile(0.60, 0.32, 0.28, 0.20, 0.22, 0.62, 0.52),
}


@dataclass
class Observation:
    x: float
    z: float
    vx: float
    vz: float
    confidence: float
    sigma_pos: float
    dropped: bool


class PerceptionModel:
    """Synthetic perception-corruption model.

    Named profiles are the fixed historical experiment definitions. Robustness
    experiments may pass an explicit :class:`PerceptionProfile` instead. This
    keeps the frozen V1-V3 profiles unchanged while allowing out-of-distribution
    stress tests to be fully recorded in experiment metadata.

    Profiles are abstract stress-test surrogates, not calibrated camera physics.
    """

    def __init__(
        self,
        profile: str | PerceptionProfile,
        rng: np.random.Generator,
        profile_name: str | None = None,
    ):
        if isinstance(profile, str):
            if profile not in PROFILES:
                raise ValueError(f"Unknown perception profile: {profile}")
            self.profile_name = profile
            self.profile = PROFILES[profile]
        else:
            self.profile_name = profile_name or "custom"
            self.profile = profile

        self.rng = rng
        self._last: Observation | None = None

    def observe(self, state: State) -> Observation:
        p = self.profile
        dropped = bool(self.rng.random() < p.dropout_prob)

        if dropped and self._last is not None:
            # Stale observation with an explicit confidence penalty.
            obs = Observation(
                x=self._last.x,
                z=self._last.z,
                vx=self._last.vx,
                vz=self._last.vz,
                confidence=max(0.05, self._last.confidence * 0.45),
                sigma_pos=self._last.sigma_pos * 1.65,
                dropped=True,
            )
            self._last = obs
            return obs

        nx = self.rng.normal(0.0, p.sigma_x)
        nz = self.rng.normal(0.0, p.sigma_z)
        nvx = self.rng.normal(0.0, p.sigma_vx)
        nvz = self.rng.normal(0.0, p.sigma_vz)

        sigma_pos = float(np.hypot(p.sigma_x, p.sigma_z))
        # Confidence intentionally remains imperfect so calibration can be studied.
        uncertainty_penalty = min(0.85, sigma_pos / 1.1)
        confidence = float(np.clip(
            p.confidence_scale * (1.0 - uncertainty_penalty)
            + self.rng.normal(0.0, 0.035),
            0.02,
            0.99,
        ))

        obs = Observation(
            x=state.x + p.bias_x + nx,
            z=max(0.0, state.z + nz),
            vx=state.vx + nvx,
            vz=state.vz + nvz,
            confidence=confidence,
            sigma_pos=sigma_pos,
            dropped=False,
        )
        self._last = obs
        return obs
