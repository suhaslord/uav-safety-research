from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable
import math

import numpy as np


@dataclass(frozen=True)
class Phase10MetricConfig:
    """Frozen-candidate configuration for the deterministic AegisT10 estimator.

    The model is intentionally small and interpretable. ArUco measurements remain
    the high-confidence geometric update. Ambiguous quad-fallback measurements are
    accepted only when they agree with the causal temporal prediction; otherwise
    the filter predicts through the frame and marks the output as prediction-only.
    """

    alpha_lateral: float = 1.0
    alpha_altitude: float = 1.0
    beta_lateral: float = 0.65
    beta_altitude: float = 0.15

    quad_alpha: float = 0.20
    quad_beta: float = 0.05
    quad_max_lateral_innovation_m: float = 0.75
    quad_max_altitude_innovation_m: float = 1.00
    quad_min_area_px2: float = 1000.0

    max_abs_lateral_velocity_mps: float = 5.0
    max_abs_vertical_velocity_mps: float = 4.0
    min_altitude_m: float = 0.01
    max_dt_s: float = 2.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class MetricFrame:
    t_s: float
    frame_index: int
    observation_available: bool
    observed_lateral_x_m: float | None
    observed_altitude_m: float | None
    detector_kind: str | None
    reprojection_rms_px: float | None = None
    detected_area_px2: float | None = None


@dataclass(frozen=True)
class MetricEstimate:
    frame_index: int
    t_s: float
    front_end_observation_available: bool
    metric_estimate_available: bool
    fresh_geometry_update: bool
    source: str
    lateral_x_m: float | None
    altitude_m: float | None
    lateral_velocity_mps: float | None
    vertical_velocity_mps: float | None
    innovation_lateral_m: float | None
    innovation_altitude_m: float | None
    detector_kind: str | None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class _State:
    lateral_x_m: float
    altitude_m: float
    lateral_velocity_mps: float = 0.0
    vertical_velocity_mps: float = 0.0


class AegisT10:
    """Causal temporal metric estimator for the Phase 9 camera front-end.

    Key semantics:
    - no simulator truth is accepted as an input;
    - no future frame is used;
    - prediction is explicit and is never labelled as a fresh geometry update;
    - a rejected quad can still yield a metric estimate from the causal state,
      but the output source records that it is prediction-only;
    - a missing camera observation remains missing at the front-end.
    """

    def __init__(self, config: Phase10MetricConfig | None = None):
        self.config = config or Phase10MetricConfig()
        self._state: _State | None = None
        self._last_t_s: float | None = None

    @property
    def initialized(self) -> bool:
        return self._state is not None

    def reset(self) -> None:
        self._state = None
        self._last_t_s = None

    def update(self, frame: MetricFrame) -> MetricEstimate:
        t_s = float(frame.t_s)
        if not math.isfinite(t_s):
            raise ValueError("frame timestamp must be finite")

        dt = self._advance_prediction(t_s)
        obs_available = bool(frame.observation_available)
        detector_kind = frame.detector_kind if obs_available else None

        if not obs_available or not self._finite_measurement(frame):
            self._last_t_s = t_s
            return self._output(
                frame,
                metric_available=False,
                fresh=False,
                source="no_front_end_observation",
                innovation_x=None,
                innovation_z=None,
            )

        mx = float(frame.observed_lateral_x_m)
        mz = float(frame.observed_altitude_m)

        if detector_kind == "aruco":
            innovation_x, innovation_z = self._apply_aruco(mx, mz, dt)
            source = "aruco_update"
            fresh = True
        elif detector_kind == "quad_fallback":
            innovation_x, innovation_z, source, fresh = self._apply_quad(
                mx,
                mz,
                dt,
                frame.detected_area_px2,
            )
        else:
            # Unknown observation types fail closed as metric updates.
            self._last_t_s = t_s
            return self._output(
                frame,
                metric_available=False,
                fresh=False,
                source="unsupported_observation_kind",
                innovation_x=None,
                innovation_z=None,
            )

        self._last_t_s = t_s
        return self._output(
            frame,
            metric_available=self._state is not None,
            fresh=fresh,
            source=source,
            innovation_x=innovation_x,
            innovation_z=innovation_z,
        )

    def _advance_prediction(self, t_s: float) -> float:
        if self._last_t_s is None:
            return 0.0
        dt = float(np.clip(t_s - self._last_t_s, 0.0, self.config.max_dt_s))
        if self._state is not None and dt > 0.0:
            self._state.lateral_x_m += self._state.lateral_velocity_mps * dt
            self._state.altitude_m = max(
                self.config.min_altitude_m,
                self._state.altitude_m + self._state.vertical_velocity_mps * dt,
            )
        return dt

    @staticmethod
    def _finite_measurement(frame: MetricFrame) -> bool:
        if frame.observed_lateral_x_m is None or frame.observed_altitude_m is None:
            return False
        return bool(
            np.isfinite(float(frame.observed_lateral_x_m))
            and np.isfinite(float(frame.observed_altitude_m))
            and float(frame.observed_altitude_m) > 0.0
        )

    def _apply_aruco(self, mx: float, mz: float, dt: float) -> tuple[float | None, float | None]:
        if self._state is None:
            self._state = _State(mx, max(self.config.min_altitude_m, mz))
            return None, None

        innovation_x = mx - self._state.lateral_x_m
        innovation_z = mz - self._state.altitude_m
        safe_dt = max(dt, 1e-6)

        self._state.lateral_velocity_mps = float(
            np.clip(
                self._state.lateral_velocity_mps
                + self.config.beta_lateral * innovation_x / safe_dt,
                -self.config.max_abs_lateral_velocity_mps,
                self.config.max_abs_lateral_velocity_mps,
            )
        )
        self._state.vertical_velocity_mps = float(
            np.clip(
                self._state.vertical_velocity_mps
                + self.config.beta_altitude * innovation_z / safe_dt,
                -self.config.max_abs_vertical_velocity_mps,
                self.config.max_abs_vertical_velocity_mps,
            )
        )
        self._state.lateral_x_m += self.config.alpha_lateral * innovation_x
        self._state.altitude_m = max(
            self.config.min_altitude_m,
            self._state.altitude_m + self.config.alpha_altitude * innovation_z,
        )
        return float(innovation_x), float(innovation_z)

    def _apply_quad(
        self,
        mx: float,
        mz: float,
        dt: float,
        area_px2: float | None,
    ) -> tuple[float | None, float | None, str, bool]:
        # The first visible Phase 9 frame can be a severely clipped quad. We keep
        # a bootstrap estimate so availability is not silently reduced, but label
        # it untrusted and let its calibrated uncertainty remain broad.
        if self._state is None:
            self._state = _State(mx, max(self.config.min_altitude_m, mz))
            return None, None, "quad_bootstrap_untrusted", False

        innovation_x = mx - self._state.lateral_x_m
        innovation_z = mz - self._state.altitude_m
        area = float(area_px2) if area_px2 is not None and np.isfinite(area_px2) else 0.0

        within_gate = bool(
            abs(innovation_x) <= self.config.quad_max_lateral_innovation_m
            and abs(innovation_z) <= self.config.quad_max_altitude_innovation_m
            and area >= self.config.quad_min_area_px2
        )
        if not within_gate:
            return (
                float(innovation_x),
                float(innovation_z),
                "quad_rejected_temporal_prediction",
                False,
            )

        safe_dt = max(dt, 1e-6)
        self._state.lateral_velocity_mps = float(
            np.clip(
                self._state.lateral_velocity_mps
                + self.config.quad_beta * innovation_x / safe_dt,
                -self.config.max_abs_lateral_velocity_mps,
                self.config.max_abs_lateral_velocity_mps,
            )
        )
        self._state.vertical_velocity_mps = float(
            np.clip(
                self._state.vertical_velocity_mps
                + self.config.quad_beta * innovation_z / safe_dt,
                -self.config.max_abs_vertical_velocity_mps,
                self.config.max_abs_vertical_velocity_mps,
            )
        )
        self._state.lateral_x_m += self.config.quad_alpha * innovation_x
        self._state.altitude_m = max(
            self.config.min_altitude_m,
            self._state.altitude_m + self.config.quad_alpha * innovation_z,
        )
        return float(innovation_x), float(innovation_z), "quad_gated_update", True

    def _output(
        self,
        frame: MetricFrame,
        *,
        metric_available: bool,
        fresh: bool,
        source: str,
        innovation_x: float | None,
        innovation_z: float | None,
    ) -> MetricEstimate:
        state = self._state if metric_available else None
        return MetricEstimate(
            frame_index=int(frame.frame_index),
            t_s=float(frame.t_s),
            front_end_observation_available=bool(frame.observation_available),
            metric_estimate_available=bool(metric_available),
            fresh_geometry_update=bool(fresh),
            source=source,
            lateral_x_m=None if state is None else float(state.lateral_x_m),
            altitude_m=None if state is None else float(state.altitude_m),
            lateral_velocity_mps=None if state is None else float(state.lateral_velocity_mps),
            vertical_velocity_mps=None if state is None else float(state.vertical_velocity_mps),
            innovation_lateral_m=innovation_x,
            innovation_altitude_m=innovation_z,
            detector_kind=frame.detector_kind if frame.observation_available else None,
        )


def run_sequence(
    frames: Iterable[MetricFrame],
    config: Phase10MetricConfig | None = None,
) -> list[MetricEstimate]:
    model = AegisT10(config)
    return [model.update(frame) for frame in frames]
