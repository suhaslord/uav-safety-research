from __future__ import annotations

import numpy as np

from .image_temporal import PHASE6_HORIZONTAL_SPAN_M, _largest_component
from .selective_confidence_v2 import (
    ComponentCalibrationConfig,
    ComponentConfidenceCalibrator,
    SharpFrameMeasurement,
    _sharpness_score,
)
from .image_temporal import Phase6LandingPadRenderer
from .image_perception import IMAGE_CONDITIONS


class Phase6ERobustPadEstimator:
    """Phase 6E image estimator with occupancy-robust background estimation.

    Historical Phase 6 estimates background intensity with the image median.
    When a large nearby marker occupies much of the frame, that median can become
    foreground-dominated and drive the segmentation threshold close to saturation,
    causing the largest-component logic to lock onto a small inner marker piece.

    Phase 6E keeps the same marker geometry, threshold formula, connected-component
    estimator, x/z inversion, confidence formula, and sharpness statistic. It only
    changes the background statistic used by the threshold:

    - ordinary frame: historical median;
    - foreground-majority signature (median > 0.5 * p90): 30th percentile.

    The 0.5 switch is the natural majority boundary. The 30th percentile is fixed
    before the Phase 6E validation benchmark and is not selected from landing
    outcomes.
    """

    def __init__(self, min_component_pixels: int = 10, min_bbox_width_px: int = 4):
        self.min_component_pixels = min_component_pixels
        self.min_bbox_width_px = min_bbox_width_px

    def estimate(self, image: np.ndarray) -> SharpFrameMeasurement:
        if image.ndim != 2:
            raise ValueError("image must be a 2D grayscale array")

        median = float(np.median(image))
        p30 = float(np.percentile(image, 30))
        std = float(np.std(image))
        p90 = float(np.percentile(image, 90))
        if std < 1e-4 or (p90 - min(median, p30)) < 0.008:
            return SharpFrameMeasurement(0.0, 0.0, 0.0, False, 0, 0, 0.0, 0.0, 0.0)

        background = p30 if median > 0.5 * p90 else median
        threshold = max(
            background + 1.05 * std,
            0.58 * p90 + 0.42 * background,
        )
        mask = image > threshold
        component = _largest_component(mask)
        if len(component) < self.min_component_pixels:
            return SharpFrameMeasurement(
                0.0, 0.0, 0.0, False, len(component), 0, 0.0, 0.0, 0.0
            )

        yy = np.asarray([p[0] for p in component], dtype=int)
        xx = np.asarray([p[1] for p in component], dtype=int)
        weights = np.maximum(image[yy, xx] - threshold + 1e-4, 1e-4)
        centroid_x = float(np.average(xx, weights=weights))

        width = int(xx.max() - xx.min() + 1)
        height = int(yy.max() - yy.min() + 1)
        if width < self.min_bbox_width_px or height < self.min_bbox_width_px:
            return SharpFrameMeasurement(
                0.0, 0.0, 0.0, False, len(component), width, 0.0, 0.0, 0.0
            )

        n = image.shape[1]
        center = (n - 1) / 2
        x_m = -(centroid_x - center) / n * PHASE6_HORIZONTAL_SPAN_M

        apparent_half = max(2.0, 0.5 * np.sqrt(max(1.0, width * height)))
        z_m = float(np.clip(35.0 / apparent_half - 0.60, 0.08, 8.0))

        contrast = max(0.0, float(image[yy, xx].mean()) - background)
        if contrast < 0.01:
            return SharpFrameMeasurement(
                0.0, 0.0, 0.0, False, len(component), width, contrast, 0.0, 0.0
            )

        contrast_score = contrast / (contrast + 0.10)
        support_score = float(np.clip(len(component) / 120.0, 0.0, 1.0))
        aspect = min(width, height) / max(width, height)
        area_fill = float(np.clip(len(component) / max(1.0, width * height), 0.0, 1.0))
        geometry_score = float(np.clip(0.72 * aspect + 0.28 * area_fill, 0.0, 1.0))
        raw_confidence = float(np.clip(
            contrast_score * (0.25 + 0.40 * support_score + 0.35 * geometry_score),
            0.0,
            0.995,
        ))
        sharpness = _sharpness_score(image)

        return SharpFrameMeasurement(
            x_m=float(x_m),
            z_m=z_m,
            raw_confidence=raw_confidence,
            valid=True,
            selected_pixels=len(component),
            bbox_width_px=width,
            contrast=float(contrast),
            geometry_score=geometry_score,
            sharpness_score=sharpness,
        )


def fit_phase6e_component_calibrator(
    *,
    seed: int = 616161,
    samples_per_condition: int = 280,
    cfg: ComponentCalibrationConfig | None = None,
) -> ComponentConfidenceCalibrator:
    """Fit the existing component-confidence model on Phase 6E measurements."""

    if samples_per_condition < 30:
        raise ValueError("samples_per_condition must be >= 30")

    rng = np.random.default_rng(seed)
    renderer = Phase6LandingPadRenderer()
    estimator = Phase6ERobustPadEstimator()
    measurements: list[SharpFrameMeasurement] = []
    xerr: list[float] = []
    zerr: list[float] = []
    altitude_bands = (
        (0.25, 2.0),
        (2.0, 4.0),
        (4.0, 6.0),
        (6.0, 8.0),
    )

    for condition in IMAGE_CONDITIONS:
        for sample_index in range(samples_per_condition):
            z_low, z_high = altitude_bands[sample_index % len(altitude_bands)]
            x_true = float(rng.uniform(-3.0, 3.0))
            z_true = float(rng.uniform(z_low, z_high))
            severity = float(rng.uniform(0.70, 1.40))
            frame_seed = int(rng.integers(0, 2**31 - 1))
            frame = renderer.render(
                x_offset_m=x_true,
                altitude_m=z_true,
                rng=np.random.default_rng(frame_seed),
                condition=condition,
                severity=severity,
            )
            measurement = estimator.estimate(frame)
            measurements.append(measurement)
            if measurement.valid:
                xerr.append(abs(measurement.x_m - x_true))
                zerr.append(abs(measurement.z_m - z_true))
            else:
                xerr.append(4.0)
                zerr.append(4.0)

    return ComponentConfidenceCalibrator.fit(
        measurements,
        xerr,
        zerr,
        seed=seed + 2843,
        cfg=cfg,
    )
