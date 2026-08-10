from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ScaleCensorDiagnostics:
    threshold: float
    total_foreground_pixels: int
    border_foreground_pixels: int
    border_foreground_fraction: float
    touched_sides: int
    scale_censored: bool


def analyze_scale_censor(image: np.ndarray, *, min_border_pixels: int = 10) -> ScaleCensorDiagnostics:
    """Detect when apparent marker scale is censored by the image boundary.

    Phase 6 renders a finite-field-of-view synthetic frame. If a meaningful
    amount of thresholded foreground reaches the image boundary, the full marker
    extent is not observable and a bounding-box-derived altitude should not be
    treated as an ordinary scale measurement.

    ``min_border_pixels`` defaults to the existing Phase 6 minimum component
    support of 10 pixels rather than a landing-outcome-tuned value.
    """

    if image.ndim != 2:
        raise ValueError("image must be a 2D grayscale array")
    if min_border_pixels < 1:
        raise ValueError("min_border_pixels must be >= 1")

    median = float(np.median(image))
    std = float(np.std(image))
    p90 = float(np.percentile(image, 90))
    if std < 1e-4 or (p90 - median) < 0.008:
        return ScaleCensorDiagnostics(
            threshold=float("inf"),
            total_foreground_pixels=0,
            border_foreground_pixels=0,
            border_foreground_fraction=0.0,
            touched_sides=0,
            scale_censored=False,
        )

    threshold = max(median + 1.05 * std, 0.58 * p90 + 0.42 * median)
    mask = image > threshold
    total = int(mask.sum())

    top = mask[0, :]
    bottom = mask[-1, :]
    left = mask[:, 0]
    right = mask[:, -1]
    border_pixels = int(top.sum() + bottom.sum() + left.sum() + right.sum())
    # Corner pixels are counted twice above. That is harmless for the censor
    # decision but correct the reported fraction to a unique-pixel count.
    unique_border = np.zeros_like(mask, dtype=bool)
    unique_border[0, :] = True
    unique_border[-1, :] = True
    unique_border[:, 0] = True
    unique_border[:, -1] = True
    unique_border_count = int((mask & unique_border).sum())

    touched_sides = int(top.any()) + int(bottom.any()) + int(left.any()) + int(right.any())
    fraction = float(unique_border_count / max(1, 2 * image.shape[0] + 2 * image.shape[1] - 4))
    censored = bool(unique_border_count >= min_border_pixels)

    return ScaleCensorDiagnostics(
        threshold=float(threshold),
        total_foreground_pixels=total,
        border_foreground_pixels=unique_border_count,
        border_foreground_fraction=fraction,
        touched_sides=touched_sides,
        scale_censored=censored,
    )
