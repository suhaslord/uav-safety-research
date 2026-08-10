from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .image_perception import IMAGE_CONDITIONS, SyntheticLandingPadRenderer
from .perception import Observation


class Phase6LandingPadRenderer(SyntheticLandingPadRenderer):
    """Phase-6-only renderer with usable apparent scale closer to touchdown.

    The Phase 5 renderer intentionally clipped marker half-size at 18 px, which
    makes altitude increasingly unobservable below roughly one metre. Phase 6
    keeps the historical renderer untouched and uses a separate perspective
    mapping whose apparent scale remains informative much closer to the ground.
    """

    def render(
        self,
        x_offset_m: float,
        altitude_m: float,
        rng: np.random.Generator,
        condition: str = "clean",
        severity: float = 1.0,
    ) -> np.ndarray:
        if condition not in IMAGE_CONDITIONS:
            raise ValueError(f"Unknown image condition: {condition}")
        if severity <= 0:
            raise ValueError("severity must be > 0")

        c = self.cfg
        n = c.image_size
        yy, _ = np.mgrid[0:n, 0:n]
        image = np.full((n, n), c.background_level, dtype=float)
        image += 0.025 * (yy / max(1, n - 1))
        image += rng.normal(0.0, c.sensor_noise * severity, size=(n, n))

        center_x = (n - 1) / 2 - (x_offset_m / c.horizontal_span_m) * n
        center_y = (n - 1) / 2
        max_half = max(18, int(0.46 * n))
        half = int(np.clip(35.0 / (max(0.05, altitude_m) + 0.60), 4, max_half))

        x0 = max(0, int(round(center_x - half)))
        x1 = min(n, int(round(center_x + half + 1)))
        y0 = max(0, int(round(center_y - half)))
        y1 = min(n, int(round(center_y + half + 1)))

        if x0 < x1 and y0 < y1:
            border = max(1, half // 4)
            image[y0:y1, x0:x1] += 0.35
            image[y0:y0 + border, x0:x1] += 0.45
            image[y1 - border:y1, x0:x1] += 0.45
            image[y0:y1, x0:x0 + border] += 0.45
            image[y0:y1, x1 - border:x1] += 0.45

            cx = int(np.clip(round(center_x), 0, n - 1))
            cy = int(np.clip(round(center_y), 0, n - 1))
            arm = max(1, border)
            image[max(0, cy - arm):min(n, cy + arm + 1), x0:x1] += 0.28
            image[y0:y1, max(0, cx - arm):min(n, cx + arm + 1)] += 0.28

        image = np.clip(image, 0.0, 1.0)
        return self._degrade(image, rng, condition, severity, center_x, center_y, half)


@dataclass
class FrameMeasurement:
    x_m: float
    z_m: float
    raw_confidence: float
    valid: bool
    selected_pixels: int
    bbox_width_px: int
    contrast: float
    geometry_score: float


@dataclass
class TemporalImageDiagnostics:
    accepted: bool
    abstained: bool
    reason: str
    raw_confidence: float
    calibrated_confidence: float
    innovation_score: float
    selected_pixels: int
    bbox_width_px: int
    geometry_score: float


@dataclass(frozen=True)
class TemporalImageConfig:
    dt: float = 0.05
    min_calibrated_confidence: float = 0.52
    min_raw_confidence: float = 0.16
    min_geometry_score: float = 0.40
    max_innovation_score: float = 2.2
    x_innovation_scale_m: float = 0.65
    z_innovation_scale_m: float = 0.85
    min_component_pixels: int = 10
    min_bbox_width_px: int = 4
    max_sigma_pos: float = 2.2


class Phase6PadEstimator:
    """Structured, interpretable estimator for the Phase 6 synthetic frame."""

    def __init__(self, min_component_pixels: int = 10, min_bbox_width_px: int = 4):
        self.min_component_pixels = min_component_pixels
        self.min_bbox_width_px = min_bbox_width_px

    def estimate(self, image: np.ndarray) -> FrameMeasurement:
        if image.ndim != 2:
            raise ValueError("image must be a 2D grayscale array")

        median = float(np.median(image))
        std = float(np.std(image))
        p90 = float(np.percentile(image, 90))
        if std < 1e-4 or (p90 - median) < 0.008:
            return FrameMeasurement(0.0, 0.0, 0.0, False, 0, 0, 0.0, 0.0)

        threshold = max(median + 1.30 * std, 0.72 * p90 + 0.28 * median)
        mask = image > threshold
        component = _largest_component(mask)
        if len(component) < self.min_component_pixels:
            return FrameMeasurement(0.0, 0.0, 0.0, False, len(component), 0, 0.0, 0.0)

        yy = np.asarray([p[0] for p in component], dtype=int)
        xx = np.asarray([p[1] for p in component], dtype=int)
        weights = np.maximum(image[yy, xx] - threshold + 1e-4, 1e-4)
        centroid_x = float(np.average(xx, weights=weights))

        width = int(xx.max() - xx.min() + 1)
        height = int(yy.max() - yy.min() + 1)
        if width < self.min_bbox_width_px or height < self.min_bbox_width_px:
            return FrameMeasurement(0.0, 0.0, 0.0, False, len(component), width, 0.0, 0.0)

        n = image.shape[1]
        center = (n - 1) / 2
        x_m = -(centroid_x - center) / n * 6.0

        # Invert the Phase 6 renderer's perspective scale:
        # half ~= 35 / (z + 0.60).
        apparent_half = max(2.0, 0.5 * np.sqrt(max(1.0, width * height)))
        z_m = float(np.clip(35.0 / apparent_half - 0.60, 0.08, 8.0))

        contrast = max(0.0, float(image[yy, xx].mean()) - median)
        if contrast < 0.01:
            return FrameMeasurement(0.0, 0.0, 0.0, False, len(component), width, contrast, 0.0)

        contrast_score = contrast / (contrast + 0.10)
        support_score = float(np.clip(len(component) / 120.0, 0.0, 1.0))
        aspect = min(width, height) / max(width, height)
        area_fill = float(np.clip(len(component) / max(1.0, width * height), 0.0, 1.0))
        geometry_score = float(np.clip(0.60 * aspect + 0.40 * area_fill, 0.0, 1.0))
        raw_confidence = float(np.clip(
            contrast_score * (0.25 + 0.40 * support_score + 0.35 * geometry_score),
            0.0,
            0.995,
        ))

        return FrameMeasurement(
            x_m=float(x_m),
            z_m=z_m,
            raw_confidence=raw_confidence,
            valid=True,
            selected_pixels=len(component),
            bbox_width_px=width,
            contrast=float(contrast),
            geometry_score=geometry_score,
        )


@dataclass
class EmpiricalConfidenceCalibrator:
    bin_edges: np.ndarray
    probability_good: np.ndarray
    expected_x_error_m: np.ndarray
    expected_z_error_m: np.ndarray
    tolerance_x_m: float = 0.30
    tolerance_z_m: float = 0.85

    @classmethod
    def fit(
        cls,
        raw_confidence: Iterable[float],
        abs_x_error_m: Iterable[float],
        abs_z_error_m: Iterable[float],
        bins: int = 10,
        tolerance_x_m: float = 0.30,
        tolerance_z_m: float = 0.85,
    ) -> "EmpiricalConfidenceCalibrator":
        conf = np.asarray(list(raw_confidence), dtype=float)
        xerr = np.asarray(list(abs_x_error_m), dtype=float)
        zerr = np.asarray(list(abs_z_error_m), dtype=float)
        if len(conf) == 0 or len(conf) != len(xerr) or len(conf) != len(zerr):
            raise ValueError("calibration arrays must be non-empty and have equal length")

        edges = np.linspace(0.0, 1.0, bins + 1)
        probs = np.zeros(bins, dtype=float)
        mean_x = np.zeros(bins, dtype=float)
        mean_z = np.zeros(bins, dtype=float)
        global_good = float(np.mean((xerr <= tolerance_x_m) & (zerr <= tolerance_z_m)))
        global_x = float(np.mean(xerr))
        global_z = float(np.mean(zerr))

        for i in range(bins):
            if i == bins - 1:
                idx = (conf >= edges[i]) & (conf <= edges[i + 1])
            else:
                idx = (conf >= edges[i]) & (conf < edges[i + 1])
            n = int(idx.sum())
            if n == 0:
                probs[i] = global_good
                mean_x[i] = global_x
                mean_z[i] = global_z
                continue
            good = int(((xerr[idx] <= tolerance_x_m) & (zerr[idx] <= tolerance_z_m)).sum())
            probs[i] = (good + 2.0) / (n + 4.0)
            mean_x[i] = float(np.mean(xerr[idx]))
            mean_z[i] = float(np.mean(zerr[idx]))

        probs = np.maximum.accumulate(probs)
        mean_x = np.maximum.accumulate(mean_x[::-1])[::-1]
        mean_z = np.maximum.accumulate(mean_z[::-1])[::-1]

        return cls(
            bin_edges=edges,
            probability_good=np.clip(probs, 0.01, 0.99),
            expected_x_error_m=np.maximum(mean_x, 0.01),
            expected_z_error_m=np.maximum(mean_z, 0.02),
            tolerance_x_m=tolerance_x_m,
            tolerance_z_m=tolerance_z_m,
        )

    def _index(self, raw_confidence: float) -> int:
        i = int(np.searchsorted(self.bin_edges, np.clip(raw_confidence, 0.0, 1.0), side="right") - 1)
        return int(np.clip(i, 0, len(self.probability_good) - 1))

    def calibrate(self, raw_confidence: float) -> float:
        return float(self.probability_good[self._index(raw_confidence)])

    def expected_error(self, raw_confidence: float) -> tuple[float, float]:
        i = self._index(raw_confidence)
        return float(self.expected_x_error_m[i]), float(self.expected_z_error_m[i])

    def to_dict(self) -> dict:
        return {
            "bin_edges": self.bin_edges.tolist(),
            "probability_good": self.probability_good.tolist(),
            "expected_x_error_m": self.expected_x_error_m.tolist(),
            "expected_z_error_m": self.expected_z_error_m.tolist(),
            "tolerance_x_m": self.tolerance_x_m,
            "tolerance_z_m": self.tolerance_z_m,
        }


class CalibratedTemporalImagePipeline:
    """Convert a synthetic image sequence into calibrated Aegis observations."""

    def __init__(
        self,
        calibrator: EmpiricalConfidenceCalibrator,
        cfg: TemporalImageConfig | None = None,
        estimator: Phase6PadEstimator | None = None,
    ):
        self.cfg = cfg or TemporalImageConfig()
        self.calibrator = calibrator
        self.estimator = estimator or Phase6PadEstimator(
            self.cfg.min_component_pixels,
            self.cfg.min_bbox_width_px,
        )
        self._state: Observation | None = None
        self._accepted_frames = 0

    def update(self, image: np.ndarray) -> tuple[Observation, TemporalImageDiagnostics]:
        m = self.estimator.estimate(image)
        calibrated = self.calibrator.calibrate(m.raw_confidence) if m.valid else 0.0

        if not m.valid:
            return self._abstain(m, calibrated, 0.0, "no reliable landing-pad component")

        innovation = self._innovation(m)
        if m.raw_confidence < self.cfg.min_raw_confidence:
            return self._abstain(m, calibrated, innovation, "raw image quality below threshold")
        if m.geometry_score < self.cfg.min_geometry_score:
            return self._abstain(m, calibrated, innovation, "landing-pad geometry inconsistent")
        if calibrated < self.cfg.min_calibrated_confidence:
            return self._abstain(m, calibrated, innovation, "calibrated confidence below threshold")
        if self._state is not None and innovation > self.cfg.max_innovation_score:
            return self._abstain(m, calibrated, innovation, "temporal innovation inconsistent with track")

        prev = self._state
        expected_x, expected_z = self.calibrator.expected_error(m.raw_confidence)
        sigma = float(np.clip(np.hypot(expected_x, expected_z), 0.05, self.cfg.max_sigma_pos))

        if prev is None:
            obs = Observation(
                x=m.x_m,
                z=m.z_m,
                vx=0.0,
                vz=0.0,
                confidence=float(np.clip(calibrated * 0.80, 0.02, 0.99)),
                sigma_pos=sigma,
                dropped=False,
            )
        else:
            gain = float(np.clip(0.24 + 0.56 * calibrated, 0.28, 0.78))
            x_pred = prev.x + prev.vx * self.cfg.dt
            z_pred = max(0.0, prev.z + prev.vz * self.cfg.dt)
            x = (1.0 - gain) * x_pred + gain * m.x_m
            z = max(0.0, (1.0 - gain) * z_pred + gain * m.z_m)

            measured_vx = float(np.clip((x - prev.x) / self.cfg.dt, -4.0, 4.0))
            measured_vz = float(np.clip((z - prev.z) / self.cfg.dt, -3.0, 3.0))
            velocity_gain = float(np.clip(0.12 + 0.30 * calibrated, 0.14, 0.42))
            vx = (1.0 - velocity_gain) * prev.vx + velocity_gain * measured_vx
            vz = (1.0 - velocity_gain) * prev.vz + velocity_gain * measured_vz

            maturity = float(np.clip((self._accepted_frames + 1) / 5.0, 0.35, 1.0))
            obs = Observation(
                x=float(x),
                z=float(z),
                vx=float(vx),
                vz=float(vz),
                confidence=float(np.clip(calibrated * maturity, 0.02, 0.99)),
                sigma_pos=float(np.clip(0.55 * prev.sigma_pos + 0.45 * sigma, 0.05, self.cfg.max_sigma_pos)),
                dropped=False,
            )

        self._accepted_frames += 1
        self._state = obs
        return obs, TemporalImageDiagnostics(
            accepted=True,
            abstained=False,
            reason="frame accepted",
            raw_confidence=m.raw_confidence,
            calibrated_confidence=calibrated,
            innovation_score=innovation,
            selected_pixels=m.selected_pixels,
            bbox_width_px=m.bbox_width_px,
            geometry_score=m.geometry_score,
        )

    def _innovation(self, m: FrameMeasurement) -> float:
        if self._state is None:
            return 0.0
        pred_x = self._state.x + self._state.vx * self.cfg.dt
        pred_z = max(0.0, self._state.z + self._state.vz * self.cfg.dt)
        return float(np.hypot(
            (m.x_m - pred_x) / self.cfg.x_innovation_scale_m,
            (m.z_m - pred_z) / self.cfg.z_innovation_scale_m,
        ))

    def _abstain(
        self,
        m: FrameMeasurement,
        calibrated: float,
        innovation: float,
        reason: str,
    ) -> tuple[Observation, TemporalImageDiagnostics]:
        if self._state is None:
            obs = Observation(
                x=0.0,
                z=5.0,
                vx=0.0,
                vz=0.0,
                confidence=0.02,
                sigma_pos=self.cfg.max_sigma_pos,
                dropped=True,
            )
        else:
            prev = self._state
            obs = Observation(
                x=float(prev.x + prev.vx * self.cfg.dt),
                z=float(max(0.0, prev.z + prev.vz * self.cfg.dt)),
                vx=float(prev.vx),
                vz=float(prev.vz),
                confidence=float(max(0.02, prev.confidence * 0.72)),
                sigma_pos=float(min(self.cfg.max_sigma_pos, prev.sigma_pos * 1.22 + 0.03)),
                dropped=True,
            )
        self._state = obs
        return obs, TemporalImageDiagnostics(
            accepted=False,
            abstained=True,
            reason=reason,
            raw_confidence=m.raw_confidence,
            calibrated_confidence=calibrated,
            innovation_score=innovation,
            selected_pixels=m.selected_pixels,
            bbox_width_px=m.bbox_width_px,
            geometry_score=m.geometry_score,
        )


def fit_synthetic_calibrator(
    *,
    seed: int = 616161,
    samples_per_condition: int = 180,
) -> EmpiricalConfidenceCalibrator:
    if samples_per_condition < 10:
        raise ValueError("samples_per_condition must be >= 10")

    rng = np.random.default_rng(seed)
    renderer = Phase6LandingPadRenderer()
    estimator = Phase6PadEstimator()
    conf: list[float] = []
    xerr: list[float] = []
    zerr: list[float] = []

    for condition in IMAGE_CONDITIONS:
        for _ in range(samples_per_condition):
            x_true = float(rng.uniform(-2.1, 2.1))
            z_true = float(rng.uniform(0.25, 5.3))
            severity = float(rng.uniform(0.75, 1.35))
            frame_seed = int(rng.integers(0, 2**31 - 1))
            frame = renderer.render(
                x_offset_m=x_true,
                altitude_m=z_true,
                rng=np.random.default_rng(frame_seed),
                condition=condition,
                severity=severity,
            )
            m = estimator.estimate(frame)
            if not m.valid:
                conf.append(0.0)
                xerr.append(3.0)
                zerr.append(4.0)
            else:
                conf.append(m.raw_confidence)
                xerr.append(abs(m.x_m - x_true))
                zerr.append(abs(m.z_m - z_true))

    return EmpiricalConfidenceCalibrator.fit(conf, xerr, zerr)


def _largest_component(mask: np.ndarray) -> list[tuple[int, int]]:
    h, w = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    best: list[tuple[int, int]] = []

    for y in range(h):
        for x in range(w):
            if not mask[y, x] or visited[y, x]:
                continue
            stack = [(y, x)]
            visited[y, x] = True
            component: list[tuple[int, int]] = []
            while stack:
                cy, cx = stack.pop()
                component.append((cy, cx))
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        stack.append((ny, nx))
            if len(component) > len(best):
                best = component
    return best
