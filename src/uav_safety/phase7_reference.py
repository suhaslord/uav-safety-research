from __future__ import annotations

from dataclasses import dataclass
from math import hypot

import numpy as np

from .dynamics import State
from .phase7_faults import FaultScenario, FaultState
from .reference_estimator import ReferenceObservation


@dataclass(frozen=True)
class Phase7SensorStackConfig:
    """Generic multi-sensor surrogate used only for simulation research.

    The model separates lateral and vertical sensing, adds update-rate mismatch,
    latency, bias random walk, and dropout, and deliberately avoids pretending
    that one direct noisy copy of simulator state is a physical sensor stack.
    Parameter values are stress-model choices, not calibrated hardware specs.
    """

    gnss_update_every_steps: int = 4
    baro_update_every_steps: int = 2
    range_update_every_steps: int = 1
    base_latency_steps: int = 2
    max_latency_history_steps: int = 32

    gnss_sigma_x_m: float = 0.24
    gnss_sigma_vx_mps: float = 0.16
    gnss_dropout_prob: float = 0.06
    gnss_bias_walk_sigma_m: float = 0.006

    baro_sigma_z_m: float = 0.16
    baro_dropout_prob: float = 0.04
    baro_bias_walk_sigma_m: float = 0.005

    range_sigma_z_m: float = 0.07
    range_dropout_prob: float = 0.05
    range_max_altitude_m: float = 2.8

    vertical_velocity_alpha: float = 0.35
    stale_sigma_growth_per_step: float = 0.025
    max_sigma_pos_m: float = 2.2
    max_channel_age_steps: int = 24


@dataclass(frozen=True)
class Phase7ReferenceDiagnostics:
    gnss_fresh: bool
    baro_fresh: bool
    range_fresh: bool
    gnss_age_steps: int
    vertical_age_steps: int
    applied_latency_steps: int
    gnss_bias_m: float
    baro_bias_m: float
    delivered_transport_latency_steps: int = 0
    delivered_age_steps: int = 10**6
    new_delivery: bool = False


@dataclass(frozen=True)
class _ReferenceSnapshot:
    acquisition_step: int
    scheduled_latency_steps: int
    observation: ReferenceObservation
    diagnostics: Phase7ReferenceDiagnostics


class Phase7SensorStackReferenceEstimator:
    """Lower-rate GNSS-like + barometric/range-like simulated reference stack.

    Ground-truth state is read only inside this sensor simulator to synthesize
    imperfect measurements. Downstream fusion receives only ReferenceObservation.

    Transport latency is represented with a scheduled-delivery queue. Packets are
    tagged with an acquisition step and delivered no earlier than their scheduled
    time. If a later, lower-latency packet overtakes an older one, the older packet
    is discarded once it is obsolete; no acquisition is re-delivered as fresh.
    """

    def __init__(
        self,
        rng: np.random.Generator,
        dt: float,
        cfg: Phase7SensorStackConfig | None = None,
    ):
        self.rng = rng
        self.dt = float(dt)
        self.cfg = cfg or Phase7SensorStackConfig()
        self._step = 0
        self._gnss_bias = 0.0
        self._baro_bias = 0.0

        self._x: float | None = None
        self._vx: float | None = None
        self._z: float | None = None
        self._vz = 0.0
        self._x_age = 10**6
        self._z_age = 10**6
        self._last_vertical_measurement: float | None = None
        self._last_vertical_step: int | None = None

        self._pending: list[tuple[int, _ReferenceSnapshot]] = []
        self._last_delivered: _ReferenceSnapshot | None = None
        self._last_delivered_acquisition_step = -1

    def observe(
        self,
        state: State,
        fault: FaultState | None = None,
    ) -> tuple[ReferenceObservation, Phase7ReferenceDiagnostics]:
        f = fault or FaultState(active=False, scenario=FaultScenario.INDEPENDENT)
        c = self.cfg
        step = self._step
        self._step += 1

        gnss_fresh = False
        baro_fresh = False
        range_fresh = False
        self._x_age += 1
        self._z_age += 1

        if step % c.gnss_update_every_steps == 0:
            p_drop = float(np.clip(c.gnss_dropout_prob + f.reference_dropout_boost, 0.0, 0.98))
            if self.rng.random() >= p_drop:
                self._gnss_bias += float(self.rng.normal(0.0, c.gnss_bias_walk_sigma_m))
                self._x = float(
                    state.x
                    + self._gnss_bias
                    + f.reference_x_bias_m
                    + self.rng.normal(0.0, c.gnss_sigma_x_m)
                )
                self._vx = float(state.vx + self.rng.normal(0.0, c.gnss_sigma_vx_mps))
                self._x_age = 0
                gnss_fresh = True

        vertical_candidates: list[tuple[float, float]] = []
        if step % c.baro_update_every_steps == 0:
            p_drop = float(np.clip(c.baro_dropout_prob + f.reference_dropout_boost, 0.0, 0.98))
            if self.rng.random() >= p_drop:
                self._baro_bias += float(self.rng.normal(0.0, c.baro_bias_walk_sigma_m))
                z_baro = float(
                    max(
                        0.0,
                        state.z
                        + self._baro_bias
                        + f.reference_z_bias_m
                        + self.rng.normal(0.0, c.baro_sigma_z_m),
                    )
                )
                vertical_candidates.append((z_baro, c.baro_sigma_z_m))
                baro_fresh = True

        if state.z <= c.range_max_altitude_m and step % c.range_update_every_steps == 0:
            p_drop = float(np.clip(c.range_dropout_prob + f.reference_dropout_boost, 0.0, 0.98))
            if self.rng.random() >= p_drop:
                z_range = float(max(0.0, state.z + self.rng.normal(0.0, c.range_sigma_z_m)))
                vertical_candidates.append((z_range, c.range_sigma_z_m))
                range_fresh = True

        vertical_sigma = c.baro_sigma_z_m
        if vertical_candidates:
            weights = np.asarray([1.0 / max(1e-6, sigma**2) for _, sigma in vertical_candidates])
            values = np.asarray([value for value, _ in vertical_candidates])
            z_new = float(np.sum(weights * values) / np.sum(weights))
            vertical_sigma = float(np.sqrt(1.0 / np.sum(weights)))

            if self._last_vertical_measurement is not None and self._last_vertical_step is not None:
                elapsed = max(self.dt, (step - self._last_vertical_step) * self.dt)
                raw_vz = (z_new - self._last_vertical_measurement) / elapsed
                self._vz = float(
                    c.vertical_velocity_alpha * raw_vz
                    + (1.0 - c.vertical_velocity_alpha) * self._vz
                )
            self._last_vertical_measurement = z_new
            self._last_vertical_step = step
            self._z = z_new
            self._z_age = 0

        x_available = self._x is not None and self._vx is not None and self._x_age <= c.max_channel_age_steps
        z_available = self._z is not None and self._z_age <= c.max_channel_age_steps
        available = bool(x_available and z_available)

        if available:
            sigma_x = c.gnss_sigma_x_m + c.stale_sigma_growth_per_step * self._x_age
            sigma_z = vertical_sigma + c.stale_sigma_growth_per_step * self._z_age
            sigma_pos = float(min(c.max_sigma_pos_m, hypot(sigma_x, sigma_z)))
            acquired_obs = ReferenceObservation(
                x=float(self._x),
                z=float(self._z),
                vx=float(self._vx),
                vz=float(self._vz),
                sigma_pos=sigma_pos,
                fresh=bool(gnss_fresh or baro_fresh or range_fresh),
                available=True,
                age_steps=int(max(self._x_age, self._z_age)),
            )
        else:
            acquired_obs = self._unavailable()

        latency = int(np.clip(
            c.base_latency_steps + f.reference_latency_extra_steps,
            0,
            c.max_latency_history_steps - 1,
        ))
        acquisition_diag = Phase7ReferenceDiagnostics(
            gnss_fresh=gnss_fresh,
            baro_fresh=baro_fresh,
            range_fresh=range_fresh,
            gnss_age_steps=int(self._x_age),
            vertical_age_steps=int(self._z_age),
            applied_latency_steps=latency,
            gnss_bias_m=float(self._gnss_bias + f.reference_x_bias_m),
            baro_bias_m=float(self._baro_bias + f.reference_z_bias_m),
            delivered_transport_latency_steps=latency,
            delivered_age_steps=int(acquired_obs.age_steps),
            new_delivery=False,
        )
        snapshot = _ReferenceSnapshot(
            acquisition_step=step,
            scheduled_latency_steps=latency,
            observation=acquired_obs,
            diagnostics=acquisition_diag,
        )
        self._pending.append((step + latency, snapshot))

        due: list[_ReferenceSnapshot] = []
        still_pending: list[tuple[int, _ReferenceSnapshot]] = []
        for delivery_step, pending_snapshot in self._pending:
            if delivery_step <= step:
                due.append(pending_snapshot)
            else:
                still_pending.append((delivery_step, pending_snapshot))
        self._pending = still_pending

        new_delivery = False
        candidates = [
            item for item in due
            if item.acquisition_step > self._last_delivered_acquisition_step
        ]
        if candidates:
            newest = max(candidates, key=lambda item: item.acquisition_step)
            self._last_delivered = newest
            self._last_delivered_acquisition_step = newest.acquisition_step
            new_delivery = True

        if self._last_delivered is None:
            diag = Phase7ReferenceDiagnostics(
                gnss_fresh=False,
                baro_fresh=False,
                range_fresh=False,
                gnss_age_steps=10**6,
                vertical_age_steps=10**6,
                applied_latency_steps=latency,
                gnss_bias_m=0.0,
                baro_bias_m=0.0,
                delivered_transport_latency_steps=0,
                delivered_age_steps=10**6,
                new_delivery=False,
            )
            return self._unavailable(), diag

        delivered = self._last_delivered
        transport_age = max(0, step - delivered.acquisition_step)
        base = delivered.observation
        delivered_age = int(base.age_steps + transport_age) if base.available else 10**6
        delivered_available = bool(base.available and delivered_age <= c.max_channel_age_steps)

        if delivered_available:
            delivered_obs = ReferenceObservation(
                x=base.x,
                z=base.z,
                vx=base.vx,
                vz=base.vz,
                sigma_pos=float(min(
                    c.max_sigma_pos_m,
                    base.sigma_pos + transport_age * c.stale_sigma_growth_per_step,
                )),
                fresh=bool(new_delivery and base.fresh),
                available=True,
                age_steps=delivered_age,
            )
        else:
            delivered_obs = self._unavailable()

        source_diag = delivered.diagnostics
        delivery_diag = Phase7ReferenceDiagnostics(
            gnss_fresh=bool(new_delivery and source_diag.gnss_fresh),
            baro_fresh=bool(new_delivery and source_diag.baro_fresh),
            range_fresh=bool(new_delivery and source_diag.range_fresh),
            gnss_age_steps=int(source_diag.gnss_age_steps + transport_age),
            vertical_age_steps=int(source_diag.vertical_age_steps + transport_age),
            applied_latency_steps=latency,
            gnss_bias_m=source_diag.gnss_bias_m,
            baro_bias_m=source_diag.baro_bias_m,
            delivered_transport_latency_steps=int(delivered.scheduled_latency_steps),
            delivered_age_steps=delivered_age,
            new_delivery=new_delivery,
        )
        return delivered_obs, delivery_diag

    def _unavailable(self) -> ReferenceObservation:
        return ReferenceObservation(
            x=0.0,
            z=0.0,
            vx=0.0,
            vz=0.0,
            sigma_pos=self.cfg.max_sigma_pos_m,
            fresh=False,
            available=False,
            age_steps=10**6,
        )
