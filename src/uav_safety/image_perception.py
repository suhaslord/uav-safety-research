from __future__ import annotations

from dataclasses import dataclass
import numpy as np


IMAGE_CONDITIONS = ("clean", "blur", "low_light", "occlusion", "mixed")


@dataclass(frozen=True)
class SyntheticImageConfig:
    image_size: int = 96
    horizontal_span_m: float = 6.0
    background_level: float = 0.08
    sensor_noise: float = 0.018


@dataclass
class ImageEstimate:
    x_m: float
    confidence: float
    valid: bool
    centroid_x_px: float
    selected_pixels: int


class SyntheticLandingPadRenderer:
    """Render a tiny simulation-only landing-pad perception benchmark.

    This is not a camera simulator and is not calibrated to real optics. It is a
    controlled bridge between the abstract state-corruption model and a future
    pixel-based perception experiment.
    """

    def __init__(self, cfg: SyntheticImageConfig | None = None):
        self.cfg = cfg or SyntheticImageConfig()

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
        yy, xx = np.mgrid[0:n, 0:n]

        # Mild background gradient plus independent sensor-like noise.
        image = np.full((n, n), c.background_level, dtype=float)
        image += 0.025 * (yy / max(1, n - 1))
        image += rng.normal(0.0, c.sensor_noise * severity, size=(n, n))

        center_x = (n - 1) / 2 - (x_offset_m / c.horizontal_span_m) * n
        center_y = (n - 1) / 2
        half = int(np.clip(30.0 / (max(0.4, altitude_m) + 0.8), 4, 18))

        x0 = max(0, int(round(center_x - half)))
        x1 = min(n, int(round(center_x + half + 1)))
        y0 = max(0, int(round(center_y - half)))
        y1 = min(n, int(round(center_y + half + 1)))

        if x0 < x1 and y0 < y1:
            # Bright square marker with a cross. This is intentionally simple so
            # the first image experiment tests degradation and confidence rather
            # than deep-network capacity.
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

    def _degrade(
        self,
        image: np.ndarray,
        rng: np.random.Generator,
        condition: str,
        severity: float,
        center_x: float,
        center_y: float,
        half: int,
    ) -> np.ndarray:
        out = image.copy()

        if condition in {"blur", "mixed"}:
            passes = max(1, int(round(1 + 2 * severity)))
            for _ in range(passes):
                out = _box_blur3(out)

        if condition in {"low_light", "mixed"}:
            brightness = max(0.16, 0.48 / max(1.0, severity))
            out *= brightness
            out += rng.normal(0.0, 0.035 * severity, size=out.shape)

        if condition in {"occlusion", "mixed"}:
            n = out.shape[0]
            width = int(np.clip((1.1 + 0.7 * severity) * max(3, half), 5, n // 2))
            height = int(np.clip((0.8 + 0.5 * severity) * max(3, half), 5, n // 2))
            # Bias the occluder toward the marker but randomize its exact location.
            ox = int(np.clip(center_x + rng.normal(0, max(2, half * 0.45)), 0, n - 1))
            oy = int(np.clip(center_y + rng.normal(0, max(2, half * 0.35)), 0, n - 1))
            x0 = max(0, ox - width // 2)
            x1 = min(n, x0 + width)
            y0 = max(0, oy - height // 2)
            y1 = min(n, y0 + height)
            fill = float(np.median(out))
            out[y0:y1, x0:x1] = fill + rng.normal(0.0, 0.01 * severity, size=(y1 - y0, x1 - x0))

        if condition == "mixed":
            out += rng.normal(0.0, 0.025 * severity, size=out.shape)

        return np.clip(out, 0.0, 1.0)


class ThresholdPadEstimator:
    """Interpretable centroid estimator for the synthetic landing-pad frames."""

    def __init__(self, cfg: SyntheticImageConfig | None = None):
        self.cfg = cfg or SyntheticImageConfig()

    def estimate(self, image: np.ndarray) -> ImageEstimate:
        if image.ndim != 2:
            raise ValueError("image must be a 2D grayscale array")

        median = float(np.median(image))
        std = float(np.std(image))
        p90 = float(np.percentile(image, 90))
        threshold = max(median + 1.35 * std, 0.70 * p90 + 0.30 * median)
        mask = image >= threshold
        count = int(mask.sum())

        if count < 8:
            return ImageEstimate(0.0, 0.0, False, float("nan"), count)

        yy, xx = np.nonzero(mask)
        weights = np.maximum(image[mask] - threshold + 1e-4, 1e-4)
        centroid_x = float(np.average(xx, weights=weights))

        n = image.shape[1]
        center = (n - 1) / 2
        x_m = -(centroid_x - center) / n * self.cfg.horizontal_span_m

        contrast = max(0.0, float(image[mask].mean()) - median)
        contrast_score = contrast / (contrast + 0.12)
        support_score = float(np.clip(count / 90.0, 0.0, 1.0))
        confidence = float(np.clip(contrast_score * (0.35 + 0.65 * support_score), 0.0, 0.99))

        return ImageEstimate(
            x_m=float(x_m),
            confidence=confidence,
            valid=True,
            centroid_x_px=centroid_x,
            selected_pixels=count,
        )


def _box_blur3(image: np.ndarray) -> np.ndarray:
    padded = np.pad(image, 1, mode="edge")
    total = np.zeros_like(image, dtype=float)
    for dy in range(3):
        for dx in range(3):
            total += padded[dy:dy + image.shape[0], dx:dx + image.shape[1]]
    return total / 9.0
