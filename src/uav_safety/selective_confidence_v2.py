from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .image_perception import IMAGE_CONDITIONS
from .image_temporal import (
    FrameMeasurement,
    Phase6LandingPadRenderer,
    Phase6PadEstimator,
)


@dataclass
class SharpFrameMeasurement(FrameMeasurement):
    """Phase 6B measurement with an observable edge-sharpness statistic."""

    sharpness_score: float = 0.0


class SharpnessAwarePadEstimator(Phase6PadEstimator):
    """Preserve the Phase 6 geometric estimate and add a blur-sensitive feature.

    Sharpness is used only by confidence calibration. It never directly edits
    the x/z measurement.
    """

    def estimate(self, image: np.ndarray) -> SharpFrameMeasurement:
        base = super().estimate(image)
        sharpness = _sharpness_score(image) if base.valid else 0.0
        return SharpFrameMeasurement(
            x_m=base.x_m,
            z_m=base.z_m,
            raw_confidence=base.raw_confidence,
            valid=base.valid,
            selected_pixels=base.selected_pixels,
            bbox_width_px=base.bbox_width_px,
            contrast=base.contrast,
            geometry_score=base.geometry_score,
            sharpness_score=sharpness,
        )


@dataclass(frozen=True)
class ComponentCalibrationConfig:
    train_fraction: float = 0.70
    l2: float = 0.025
    fit_steps: int = 1700
    fit_learning_rate: float = 0.045
    platt_steps: int = 800
    platt_learning_rate: float = 0.030
    min_scale: float = 1e-6


@dataclass
class _BinaryCalibrator:
    feature_mean: np.ndarray
    feature_scale: np.ndarray
    weights: np.ndarray
    intercept: float
    platt_scale: float
    platt_bias: float

    @classmethod
    def fit(
        cls,
        X: np.ndarray,
        y: np.ndarray,
        *,
        train_idx: np.ndarray,
        cal_idx: np.ndarray,
        cfg: ComponentCalibrationConfig,
    ) -> "_BinaryCalibrator":
        mean = X[train_idx].mean(axis=0)
        scale = X[train_idx].std(axis=0)
        scale = np.where(scale < cfg.min_scale, 1.0, scale)
        Xs = (X - mean) / scale

        w = np.zeros(X.shape[1], dtype=float)
        prevalence = float(np.clip(y[train_idx].mean(), 0.02, 0.98))
        b = float(np.log(prevalence / (1.0 - prevalence)))

        for _ in range(cfg.fit_steps):
            p = _sigmoid(Xs[train_idx] @ w + b)
            err = p - y[train_idx]
            grad_w = (Xs[train_idx].T @ err) / len(train_idx) + cfg.l2 * w
            grad_b = float(err.mean())
            w -= cfg.fit_learning_rate * grad_w
            b -= cfg.fit_learning_rate * grad_b

        held_logits = Xs[cal_idx] @ w + b
        alpha = 1.0
        beta = 0.0
        for _ in range(cfg.platt_steps):
            p = _sigmoid(alpha * held_logits + beta)
            err = p - y[cal_idx]
            alpha = float(max(
                0.05,
                alpha - cfg.platt_learning_rate * float(np.mean(err * held_logits)),
            ))
            beta -= cfg.platt_learning_rate * float(err.mean())

        return cls(
            feature_mean=mean,
            feature_scale=scale,
            weights=w,
            intercept=b,
            platt_scale=alpha,
            platt_bias=beta,
        )

    def probability(self, features: np.ndarray) -> float:
        x = (features - self.feature_mean) / self.feature_scale
        raw = float(x @ self.weights + self.intercept)
        return float(_sigmoid(np.asarray([self.platt_scale * raw + self.platt_bias]))[0])

    def to_dict(self) -> dict:
        return {
            "feature_mean": self.feature_mean.tolist(),
            "feature_scale": self.feature_scale.tolist(),
            "weights": self.weights.tolist(),
            "intercept": self.intercept,
            "platt_scale": self.platt_scale,
            "platt_bias": self.platt_bias,
        }


@dataclass
class ComponentConfidenceCalibrator:
    """Calibrate lateral and altitude reliability separately.

    `p_x_good` estimates P(|x_hat-x| <= tolerance_x_m).
    `p_z_good` estimates P(|z_hat-z| <= tolerance_z_m).

    Altitude confidence additionally receives a simulation-specific analytic
    observability cap. The Phase 6 renderer quantizes apparent marker half-size
    to integer pixels before drawing. At small apparent sizes, one adjacent
    scale bin can represent more than the 0.85 m altitude tolerance. A learned
    image-quality score alone cannot infer that hidden sub-pixel position, so the
    cap prevents the model from claiming more confidence than the synthetic
    camera geometry can resolve.
    """

    x_model: _BinaryCalibrator
    z_model: _BinaryCalibrator
    tolerance_x_m: float = 0.30
    tolerance_z_m: float = 0.85

    FEATURE_NAMES = (
        "raw_confidence",
        "geometry_score",
        "measured_z_normalized",
        "bbox_width_normalized",
        "component_support_log_normalized",
        "contrast_normalized",
        "sharpness_score",
        "scale_quantization_bin_width_normalized",
        "raw_x_measured_z",
        "geometry_x_measured_z",
        "sharpness_x_measured_z",
        "sharpness_x_bbox_width",
        "contrast_x_sharpness",
    )

    @classmethod
    def fit(
        cls,
        measurements: list[SharpFrameMeasurement],
        abs_x_error_m: list[float],
        abs_z_error_m: list[float],
        *,
        seed: int,
        cfg: ComponentCalibrationConfig | None = None,
        tolerance_x_m: float = 0.30,
        tolerance_z_m: float = 0.85,
    ) -> "ComponentConfidenceCalibrator":
        cfg = cfg or ComponentCalibrationConfig()
        if len(measurements) < 80:
            raise ValueError("component calibration requires at least 80 measurements")
        if len(measurements) != len(abs_x_error_m) or len(measurements) != len(abs_z_error_m):
            raise ValueError("calibration arrays must have equal length")

        X = np.vstack([cls.feature_vector(m) for m in measurements])
        xerr = np.asarray(abs_x_error_m, dtype=float)
        zerr = np.asarray(abs_z_error_m, dtype=float)
        y_x = (xerr <= tolerance_x_m).astype(float)
        y_z = (zerr <= tolerance_z_m).astype(float)

        rng = np.random.default_rng(seed)
        order = rng.permutation(len(measurements))
        split = int(round(cfg.train_fraction * len(order)))
        split = int(np.clip(split, 40, len(order) - 40))
        train_idx = order[:split]
        cal_idx = order[split:]

        return cls(
            x_model=_BinaryCalibrator.fit(X, y_x, train_idx=train_idx, cal_idx=cal_idx, cfg=cfg),
            z_model=_BinaryCalibrator.fit(X, y_z, train_idx=train_idx, cal_idx=cal_idx, cfg=cfg),
            tolerance_x_m=tolerance_x_m,
            tolerance_z_m=tolerance_z_m,
        )

    @staticmethod
    def feature_vector(m: SharpFrameMeasurement) -> np.ndarray:
        if not m.valid:
            return np.zeros(13, dtype=float)

        raw = float(np.clip(m.raw_confidence, 0.0, 1.0))
        geometry = float(np.clip(m.geometry_score, 0.0, 1.0))
        z_norm = float(np.clip(m.z_m / 8.0, 0.0, 1.05))
        width_norm = float(np.clip(m.bbox_width_px / 96.0, 0.0, 1.0))
        support_norm = float(np.clip(np.log1p(m.selected_pixels) / np.log(2500.0), 0.0, 1.2))
        contrast_norm = float(np.clip(m.contrast / 0.70, 0.0, 1.4))
        sharp = float(np.clip(m.sharpness_score, 0.0, 1.5))
        scale_bin_norm = float(np.clip(altitude_scale_bin_width_m(m) / 1.75, 0.0, 1.5))

        return np.asarray([
            raw,
            geometry,
            z_norm,
            width_norm,
            support_norm,
            contrast_norm,
            sharp,
            scale_bin_norm,
            raw * z_norm,
            geometry * z_norm,
            sharp * z_norm,
            sharp * width_norm,
            contrast_norm * sharp,
        ], dtype=float)

    def learned_probabilities(self, m: SharpFrameMeasurement) -> tuple[float, float]:
        if not m.valid:
            return 0.0, 0.0
        f = self.feature_vector(m)
        return self.x_model.probability(f), self.z_model.probability(f)

    def probabilities(self, m: SharpFrameMeasurement) -> tuple[float, float]:
        if not m.valid:
            return 0.0, 0.0
        p_x, p_z_learned = self.learned_probabilities(m)
        p_z_cap = altitude_observability_cap(m, self.tolerance_z_m)
        return float(p_x), float(min(p_z_learned, p_z_cap))

    def joint_probability_lower_bound(self, m: SharpFrameMeasurement) -> float:
        px, pz = self.probabilities(m)
        return float(max(0.0, px + pz - 1.0))

    def to_dict(self) -> dict:
        return {
            "model": "sharpness_scale_observability_component_logistic_plus_heldout_platt",
            "feature_names": list(self.FEATURE_NAMES),
            "tolerance_x_m": self.tolerance_x_m,
            "tolerance_z_m": self.tolerance_z_m,
            "altitude_observability_cap": "min(1, tolerance_z_m / adjacent_renderer_scale_bin_width_m)",
            "x_model": self.x_model.to_dict(),
            "z_model": self.z_model.to_dict(),
        }


def fit_component_calibrator(
    *,
    seed: int = 616161,
    samples_per_condition: int = 260,
    cfg: ComponentCalibrationConfig | None = None,
) -> ComponentConfidenceCalibrator:
    if samples_per_condition < 30:
        raise ValueError("samples_per_condition must be >= 30")

    rng = np.random.default_rng(seed)
    renderer = Phase6LandingPadRenderer()
    estimator = SharpnessAwarePadEstimator()
    measurements: list[SharpFrameMeasurement] = []
    xerr: list[float] = []
    zerr: list[float] = []

    # Condition-balanced and altitude-stratified across the full simulated
    # landing envelope. Runtime never receives a condition or altitude-band
    # label; those variables only construct the offline calibration dataset.
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
            m = estimator.estimate(frame)
            measurements.append(m)
            if m.valid:
                xerr.append(abs(m.x_m - x_true))
                zerr.append(abs(m.z_m - z_true))
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


def altitude_scale_bin_width_m(m: SharpFrameMeasurement) -> float:
    """Approximate altitude span represented by one renderer half-size bin.

    The renderer uses ``int(35 / (z + 0.60))`` for apparent half-size. If the
    observed estimate implies half-size h, adjacent true altitudes that map into
    that integer bin span approximately 35/h - 35/(h+1). This is a synthetic
    camera-resolution diagnostic, not a real-camera uncertainty formula.
    """

    if not m.valid:
        return float("inf")
    implied_half = float(np.clip(35.0 / max(0.61, m.z_m + 0.60), 2.0, 70.0))
    width = 35.0 / implied_half - 35.0 / (implied_half + 1.0)
    return float(max(0.0, width))


def altitude_observability_cap(m: SharpFrameMeasurement, tolerance_z_m: float = 0.85) -> float:
    """Conservative confidence ceiling imposed by synthetic scale quantization."""

    if not m.valid:
        return 0.0
    bin_width = altitude_scale_bin_width_m(m)
    if not np.isfinite(bin_width) or bin_width <= 1e-9:
        return 0.0
    return float(np.clip(tolerance_z_m / bin_width, 0.0, 1.0))


def _sharpness_score(image: np.ndarray) -> float:
    """Robust normalized high-frequency energy; higher means crisper edges."""

    if image.ndim != 2 or image.size < 16:
        return 0.0
    dynamic = float(np.percentile(image, 99) - np.percentile(image, 5))
    if dynamic < 0.01:
        return 0.0

    gx = np.abs(np.diff(image, axis=1)).ravel()
    gy = np.abs(np.diff(image, axis=0)).ravel()
    gradients = np.concatenate([gx, gy])
    q99 = float(np.percentile(gradients, 99))
    q90 = float(np.percentile(gradients, 90))
    concentration = max(0.0, q99 - 0.35 * q90) / dynamic
    return float(np.clip(1.8 * concentration, 0.0, 1.5))


def _sigmoid(x: np.ndarray) -> np.ndarray:
    x = np.clip(np.asarray(x, dtype=float), -35.0, 35.0)
    return 1.0 / (1.0 + np.exp(-x))
