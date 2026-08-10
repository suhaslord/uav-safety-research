from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from .dynamics import State


@dataclass(frozen=True)
class ReferenceEstimatorConfig:
    """Configuration for the independent V3 reference estimator.

    This is a deliberately imperfect, lower-rate simulated state estimate. It is
    not meant to represent a specific physical sensor. Its only purpose is to
    test whether independent error structure adds useful information when vision
    develops a persistent bias.
    """

    update_every_steps: int = 5
    sigma_x: float = 0.28
    sigma_z: float = 0.20
    sigma_vx: float = 0.18
    sigma_vz: float = 0.14
    dropout_prob: float = 0.12
    uncertainty_growth: float = 1.06
    max_sigma_pos: float = 1.8


@dataclass
class ReferenceObservation:
    x: float
    z: float
    vx: float
    vz: float
    sigma_pos: float
    fresh: bool
    available: bool
    age_steps: int


class IndependentReferenceEstimator:
    """Lower-bandwidth state estimator with independent zero-mean errors.

    Fresh measurements are sampled from the simulated state with independent
    noise. Between updates, the last estimate is propagated with a constant-
    velocity model and its uncertainty grows. The estimator uses its own RNG so
    adding V3 cannot alter the vision or disturbance random sequence.
    """

    def __init__(
        self,
        rng: np.random.Generator,
        dt: float,
        cfg: ReferenceEstimatorConfig | None = None,
    ):
        self.rng = rng
        self.dt = dt
        self.cfg = cfg or ReferenceEstimatorConfig()
        self._step = 0
        self._last: ReferenceObservation | None = None

    def observe(self, state: State) -> ReferenceObservation:
        c = self.cfg
        scheduled = (self._step % c.update_every_steps) == 0
        self._step += 1

        if scheduled and self.rng.random() >= c.dropout_prob:
            sigma_pos = float(np.hypot(c.sigma_x, c.sigma_z))
            obs = ReferenceObservation(
                x=float(state.x + self.rng.normal(0.0, c.sigma_x)),
                z=float(max(0.0, state.z + self.rng.normal(0.0, c.sigma_z))),
                vx=float(state.vx + self.rng.normal(0.0, c.sigma_vx)),
                vz=float(state.vz + self.rng.normal(0.0, c.sigma_vz)),
                sigma_pos=sigma_pos,
                fresh=True,
                available=True,
                age_steps=0,
            )
            self._last = obs
            return obs

        if self._last is None:
            return ReferenceObservation(
                x=0.0,
                z=0.0,
                vx=0.0,
                vz=0.0,
                sigma_pos=c.max_sigma_pos,
                fresh=False,
                available=False,
                age_steps=10**6,
            )

        prev = self._last
        age = prev.age_steps + 1
        predicted = ReferenceObservation(
            x=float(prev.x + prev.vx * self.dt),
            z=float(max(0.0, prev.z + prev.vz * self.dt)),
            vx=float(prev.vx),
            vz=float(prev.vz),
            sigma_pos=float(min(c.max_sigma_pos, prev.sigma_pos * c.uncertainty_growth)),
            fresh=False,
            available=True,
            age_steps=age,
        )
        self._last = predicted
        return predicted
