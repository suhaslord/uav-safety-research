from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .image_temporal import (
    CalibratedTemporalImagePipeline,
    EmpiricalConfidenceCalibrator,
    FrameMeasurement,
    Phase6LandingPadRenderer,
    Phase6PadEstimator,
    TemporalImageConfig,
)
from .image_perception import IMAGE_CONDITIONS


@dataclass(frozen=True)
class ContextualCalibrationConfig:
    """Offline-only configuration for the Phase 6 contextual confidence model."""

    train_fraction: float = 0.70
    l2: float = 0.035
    fit_steps: int = 1400
    fit_learning_rate: float = 0.055
    calibration_steps: int = 650
    calibration_learning_rate: float = 0.035
    min_scale: float = 1e-6


@dataclass
class ContextualConfidenceCalibrator:
    """Interpretable multifeature confidence model with held-out Platt calibration.

    The ranking model is a small logistic regression over measurement features that
    exist at runtime. A deterministic held-out split then fits a monotone one-
    dimensional logistic calibration map. Synthetic ground truth is used only
    during offline fitting.
    """

    feature_mean: np.ndarray
    feature_scale: np.ndarray
    weights: np.ndarray
    intercept: float
    platt_scale: float
    platt_bias: float
    scalar_error_model: EmpiricalConfidenceCalibrator
    tolerance_x_m: float = 0.30
    tolerance_z_m: float = 0.85

    @staticmethod
    def feature_vector(m: FrameMeasurement) -> np.ndarray:
        if not m.valid:
            return np.zeros(9, dtype=float)

        z_norm = float(np.clip(m.z_m / 6.5, 0.0, 1.25))
        width_norm = float(np.clip(m.bbox_width_px / 96.0, 0.0, 1.0))
        support_norm = float(np.clip(np.log1p(m.selected_pixels) / np.log(2500.0), 0.0, 1.2))
        contrast_norm = float(np.clip(m.contrast / 0.70, 0.0, 1.4))
        raw = float(np.clip(m.raw_confidence, 0.0, 1.0))
        geometry = float(np.clip(m.geometry_score, 0.0, 1.0))

        # Scale/geometry interactions let the model recognize measurements that
        # look locally clean but whose apparent pad scale is less trustworthy.
        return np.asarray([
            raw,
            geometry,
            z_norm,
            width_norm,
            support_norm,
            contrast_norm,
            raw * z_norm,
            geometry * z_norm,
            contrast_norm * z_norm,
        ], dtype=float)

    @classmethod
    def fit(
        cls,
        measurements: list[FrameMeasurement],
        abs_x_error_m: list[float],
        abs_z_error_m: list[float],
        *,
        seed: int,
        cfg: ContextualCalibrationConfig | None = None,
        tolerance_x_m: float = 0.30,
        tolerance_z_m: float = 0.85,
    ) -> "ContextualConfidenceCalibrator":
        cfg = cfg or ContextualCalibrationConfig()
        if len(measurements) < 40:
            raise ValueError("contextual calibration requires at least 40 measurements")
        if len(measurements) != len(abs_x_error_m) or len(measurements) != len(abs_z_error_m):
            raise ValueError("calibration arrays must have equal length")
        if not 0.5 <= cfg.train_fraction < 0.9:
            raise ValueError("train_fraction must be in [0.5, 0.9)")

        X = np.vstack([cls.feature_vector(m) for m in measurements])
        xerr = np.asarray(abs_x_error_m, dtype=float)
        zerr = np.asarray(abs_z_error_m, dtype=float)
        y = ((xerr <= tolerance_x_m) & (zerr <= tolerance_z_m)).astype(float)

        rng = np.random.default_rng(seed)
        order = rng.permutation(len(y))
        split = int(round(cfg.train_fraction * len(y)))
        split = int(np.clip(split, 20, len(y) - 20))
        train_idx = order[:split]
        cal_idx = order[split:]

        mean = X[train_idx].mean(axis=0)
        scale = X[train_idx].std(axis=0)
        scale = np.where(scale < cfg.min_scale, 1.0, scale)
        Xs = (X - mean) / scale

        w = np.zeros(X.shape[1], dtype=float)
        prevalence = float(np.clip(y[train_idx].mean(), 0.02, 0.98))
        b = float(np.log(prevalence / (1.0 - prevalence)))

        for _ in range(cfg.fit_steps):
            logits = Xs[train_idx] @ w + b
            p = _sigmoid(logits)
            err = p - y[train_idx]
            grad_w = (Xs[train_idx].T @ err) / len(train_idx) + cfg.l2 * w
            grad_b = float(err.mean())
            w -= cfg.fit_learning_rate * grad_w
            b -= cfg.fit_learning_rate * grad_b

        held_logits = Xs[cal_idx] @ w + b
        alpha = 1.0
        beta = 0.0
        for _ in range(cfg.calibration_steps):
            p = _sigmoid(alpha * held_logits + beta)
            err = p - y[cal_idx]
            grad_alpha = float(np.mean(err * held_logits))
            grad_beta = float(err.mean())
            alpha = float(max(0.05, alpha - cfg.calibration_learning_rate * grad_alpha))
            beta -= cfg.calibration_learning_rate * grad_beta

        raw_conf = [m.raw_confidence if m.valid else 0.0 for m in measurements]
        scalar_error_model = _fit_scalar_error_model(
            raw_conf,
            xerr,
            zerr,
            tolerance_x_m=tolerance_x_m,
            tolerance_z_m=tolerance_z_m,
        )

        return cls(
            feature_mean=mean,
            feature_scale=scale,
            weights=w,
            intercept=float(b),
            platt_scale=float(alpha),
            platt_bias=float(beta),
            scalar_error_model=scalar_error_model,
            tolerance_x_m=tolerance_x_m,
            tolerance_z_m=tolerance_z_m,
        )

    def raw_logit(self, m: FrameMeasurement) -> float:
        if not m.valid:
            return -20.0
        x = (self.feature_vector(m) - self.feature_mean) / self.feature_scale
        return float(x @ self.weights + self.intercept)

    def calibrate_measurement(self, m: FrameMeasurement) -> float:
        if not m.valid:
            return 0.0
        return float(_sigmoid(np.asarray([self.platt_scale * self.raw_logit(m) + self.platt_bias]))[0])

    # Compatibility methods used by the inherited temporal accept path. The
    # actual acceptance probability uses calibrate_measurement above.
    def calibrate(self, raw_confidence: float) -> float:
        return float(self.scalar_error_model.calibrate(raw_confidence))

    def expected_error(self, raw_confidence: float) -> tuple[float, float]:
        return self.scalar_error_model.expected_error(raw_confidence)

    def to_dict(self) -> dict:
        return {
            "model": "contextual_logistic_plus_heldout_platt",
            "feature_names": [
                "raw_confidence",
                "geometry_score",
                "measured_z_normalized",
                "bbox_width_normalized",
                "component_support_log_normalized",
                "contrast_normalized",
                "raw_confidence_x_measured_z",
                "geometry_x_measured_z",
                "contrast_x_measured_z",
            ],
            "feature_mean": self.feature_mean.tolist(),
            "feature_scale": self.feature_scale.tolist(),
            "weights": self.weights.tolist(),
            "intercept": self.intercept,
            "platt_scale": self.platt_scale,
            "platt_bias": self.platt_bias,
            "tolerance_x_m": self.tolerance_x_m,
            "tolerance_z_m": self.tolerance_z_m,
            "scalar_error_model": self.scalar_error_model.to_dict(),
        }


class ContextualTemporalImagePipeline(CalibratedTemporalImagePipeline):
    """Temporal perception using contextual calibrated confidence for abstention."""

    calibrator: ContextualConfidenceCalibrator

    def __init__(
        self,
        calibrator: ContextualConfidenceCalibrator,
        cfg: TemporalImageConfig | None = None,
        estimator: Phase6PadEstimator | None = None,
    ):
        super().__init__(calibrator, cfg, estimator)
        self.calibrator = calibrator

    def update(self, image: np.ndarray):
        self._time_s += self.cfg.dt
        m = self.estimator.estimate(image)
        calibrated = self.calibrator.calibrate_measurement(m) if m.valid else 0.0

        if not m.valid:
            self._clear_reacquisition()
            return self._abstain(m, calibrated, 0.0, "no reliable landing-pad component")

        innovation = self._innovation(m)
        if m.raw_confidence < self.cfg.min_raw_confidence:
            self._clear_reacquisition()
            return self._abstain(m, calibrated, innovation, "raw image quality below threshold")
        if calibrated < self.cfg.min_calibrated_confidence:
            self._clear_reacquisition()
            return self._abstain(m, calibrated, innovation, "contextual calibrated confidence below threshold")
        if self._accepted_frames >= 2 and m.geometry_score < self.cfg.min_geometry_score:
            self._clear_reacquisition()
            return self._abstain(m, calibrated, innovation, "landing-pad geometry inconsistent")

        if self._state is not None and innovation > self.cfg.max_innovation_score:
            if self._update_reacquisition_candidate(m, calibrated):
                return self._accept(m, calibrated, innovation, reacquired=True)
            return self._abstain(m, calibrated, innovation, "temporal innovation inconsistent with track")

        self._clear_reacquisition()
        return self._accept(m, calibrated, innovation, reacquired=False)


def fit_contextual_calibrator(
    *,
    seed: int = 616161,
    samples_per_condition: int = 240,
    cfg: ContextualCalibrationConfig | None = None,
) -> ContextualConfidenceCalibrator:
    if samples_per_condition < 20:
        raise ValueError("samples_per_condition must be >= 20")

    rng = np.random.default_rng(seed)
    renderer = Phase6LandingPadRenderer()
    estimator = Phase6PadEstimator()
    measurements: list[FrameMeasurement] = []
    xerr: list[float] = []
    zerr: list[float] = []

    for condition in IMAGE_CONDITIONS:
        for _ in range(samples_per_condition):
            x_true = float(rng.uniform(-2.8, 2.8))
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
            measurements.append(m)
            if m.valid:
                xerr.append(abs(m.x_m - x_true))
                zerr.append(abs(m.z_m - z_true))
            else:
                xerr.append(4.0)
                zerr.append(4.0)

    return ContextualConfidenceCalibrator.fit(
        measurements,
        xerr,
        zerr,
        seed=seed + 1771,
        cfg=cfg,
    )


def _fit_scalar_error_model(
    raw_confidence,
    xerr,
    zerr,
    *,
    tolerance_x_m: float,
    tolerance_z_m: float,
    bins: int = 10,
) -> EmpiricalConfidenceCalibrator:
    """Fit the legacy-compatible error lookup without the empty-bin inflation bug."""

    conf = np.asarray(raw_confidence, dtype=float)
    xerr = np.asarray(xerr, dtype=float)
    zerr = np.asarray(zerr, dtype=float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    probs = np.full(bins, np.nan, dtype=float)
    mean_x = np.full(bins, np.nan, dtype=float)
    mean_z = np.full(bins, np.nan, dtype=float)

    for i in range(bins):
        idx = (conf >= edges[i]) & (conf <= edges[i + 1] if i == bins - 1 else conf < edges[i + 1])
        n = int(idx.sum())
        if n:
            good = int(((xerr[idx] <= tolerance_x_m) & (zerr[idx] <= tolerance_z_m)).sum())
            probs[i] = (good + 1.0) / (n + 2.0)
            mean_x[i] = float(np.mean(xerr[idx]))
            mean_z[i] = float(np.mean(zerr[idx]))

    occupied = np.flatnonzero(np.isfinite(probs))
    if len(occupied) == 0:
        raise ValueError("no occupied confidence bins")

    for arr in (probs, mean_x, mean_z):
        for i in range(bins):
            if not np.isfinite(arr[i]):
                nearest = occupied[np.argmin(np.abs(occupied - i))]
                arr[i] = arr[nearest]

    # Preserve the intended ordering without letting empty bins inherit the
    # global prevalence and inflate all lower-confidence probabilities.
    probs = np.maximum.accumulate(probs)
    mean_x = np.maximum.accumulate(mean_x[::-1])[::-1]
    mean_z = np.maximum.accumulate(mean_z[::-1])[::-1]

    return EmpiricalConfidenceCalibrator(
        bin_edges=edges,
        probability_good=np.clip(probs, 0.01, 0.99),
        expected_x_error_m=np.maximum(mean_x, 0.01),
        expected_z_error_m=np.maximum(mean_z, 0.02),
        tolerance_x_m=tolerance_x_m,
        tolerance_z_m=tolerance_z_m,
    )


def _sigmoid(x: np.ndarray) -> np.ndarray:
    x = np.clip(np.asarray(x, dtype=float), -35.0, 35.0)
    return 1.0 / (1.0 + np.exp(-x))
