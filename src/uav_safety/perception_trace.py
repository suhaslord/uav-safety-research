from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath
import re

import numpy as np
import pandas as pd


PHASE9_PERCEPTION_TRACE_SCHEMA = "aegisland.phase9.perception-trace.v1"

REQUIRED_PERCEPTION_TRACE_COLUMNS = (
    "t_s",
    "frame_index",
    "frame_path",
    "frame_sha256",
    "image_width_px",
    "image_height_px",
    "truth_target_visible",
    "truth_center_x_px",
    "truth_center_y_px",
    "truth_target_area_px2",
    "truth_lateral_x_m",
    "truth_altitude_m",
    "observation_available",
    "observed_center_x_px",
    "observed_center_y_px",
    "observed_lateral_x_m",
    "observed_altitude_m",
    "confidence",
    "sigma_lateral_m",
    "sigma_altitude_m",
)

OPTIONAL_PERCEPTION_TRACE_NUMERIC_COLUMNS = (
    "frame_transport_latency_s",
    "camera_exposure_s",
)

BOOLEAN_COLUMNS = ("truth_target_visible", "observation_available")
ALWAYS_NUMERIC_COLUMNS = (
    "t_s",
    "frame_index",
    "image_width_px",
    "image_height_px",
    "truth_lateral_x_m",
    "truth_altitude_m",
)
TRUTH_VISIBLE_NUMERIC_COLUMNS = (
    "truth_center_x_px",
    "truth_center_y_px",
    "truth_target_area_px2",
)
OBSERVATION_NUMERIC_COLUMNS = (
    "observed_center_x_px",
    "observed_center_y_px",
    "observed_lateral_x_m",
    "observed_altitude_m",
    "confidence",
    "sigma_lateral_m",
    "sigma_altitude_m",
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class PerceptionTraceValidation:
    rows: int
    duration_s: float
    median_dt_s: float
    target_visible_rate: float
    observation_available_rate: float
    missed_detection_rate_when_visible: float
    false_positive_rate_when_not_visible: float
    paired_observation_samples: int
    lateral_mae_m: float | None
    altitude_mae_m: float | None
    verified_frame_hashes: int

    def to_dict(self) -> dict:
        return {
            "schema": PHASE9_PERCEPTION_TRACE_SCHEMA,
            "rows": self.rows,
            "duration_s": self.duration_s,
            "median_dt_s": self.median_dt_s,
            "target_visible_rate": self.target_visible_rate,
            "observation_available_rate": self.observation_available_rate,
            "missed_detection_rate_when_visible": self.missed_detection_rate_when_visible,
            "false_positive_rate_when_not_visible": self.false_positive_rate_when_not_visible,
            "paired_observation_samples": self.paired_observation_samples,
            "lateral_mae_m": self.lateral_mae_m,
            "altitude_mae_m": self.altitude_mae_m,
            "verified_frame_hashes": self.verified_frame_hashes,
        }


def _coerce_bool(series: pd.Series, column: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(bool)
    mapping = {
        "true": True,
        "false": False,
        "1": True,
        "0": False,
        "yes": True,
        "no": False,
    }
    normalized = series.astype(str).str.strip().str.lower()
    unknown = normalized[~normalized.isin(mapping)]
    if not unknown.empty:
        raise ValueError(f"{column} contains non-boolean values: {sorted(unknown.unique())[:5]}")
    return normalized.map(mapping).astype(bool)


def _coerce_numeric_allow_missing(series: pd.Series, column: str) -> pd.Series:
    normalized = pd.to_numeric(series, errors="coerce")
    original_missing = series.isna()
    introduced_missing = normalized.isna() & ~original_missing
    if introduced_missing.any():
        raise ValueError(f"{column} contains non-numeric values")
    finite = normalized.dropna().to_numpy(dtype=float)
    if not np.isfinite(finite).all():
        raise ValueError(f"{column} contains non-finite values")
    return normalized


def _validate_relative_frame_path(value: object) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError("frame_path must not be empty")
    path = PurePosixPath(text.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"frame_path must be a safe relative path, got {text!r}")
    return path.as_posix()


def _hash_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_perception_trace(
    frame: pd.DataFrame,
    *,
    frame_root: str | Path | None = None,
    verify_frame_hashes: bool = False,
) -> tuple[pd.DataFrame, PerceptionTraceValidation]:
    """Validate a Phase 9 camera/perception evidence trace.

    Raw-frame identity and estimator observations are kept separate. Missing
    observations must remain missing; zeros are not accepted as implicit
    substitutes. Ground truth is evaluation-only and must never be used as an
    estimator/controller input.
    """

    missing = [column for column in REQUIRED_PERCEPTION_TRACE_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"perception trace is missing required columns: {missing}")
    if len(frame) < 2:
        raise ValueError("perception trace must contain at least two rows")
    if verify_frame_hashes and frame_root is None:
        raise ValueError("frame_root is required when verify_frame_hashes=True")

    optional = tuple(column for column in OPTIONAL_PERCEPTION_TRACE_NUMERIC_COLUMNS if column in frame.columns)
    normalized = frame.loc[:, (*REQUIRED_PERCEPTION_TRACE_COLUMNS, *optional)].copy()

    for column in BOOLEAN_COLUMNS:
        normalized[column] = _coerce_bool(normalized[column], column)

    for column in ALWAYS_NUMERIC_COLUMNS:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
        if normalized[column].isna().any():
            raise ValueError(f"{column} contains missing or non-numeric values")
        values = normalized[column].to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError(f"{column} contains non-finite values")

    for column in (*TRUTH_VISIBLE_NUMERIC_COLUMNS, *OBSERVATION_NUMERIC_COLUMNS, *optional):
        normalized[column] = _coerce_numeric_allow_missing(normalized[column], column)

    frame_index = normalized["frame_index"].to_numpy(dtype=float)
    if not np.all(frame_index == np.floor(frame_index)):
        raise ValueError("frame_index must contain integers")
    if np.any(np.diff(frame_index) <= 0):
        raise ValueError("frame_index must be strictly increasing")
    normalized["frame_index"] = normalized["frame_index"].astype(int)

    for dimension in ("image_width_px", "image_height_px"):
        values = normalized[dimension].to_numpy(dtype=float)
        if not np.all(values == np.floor(values)) or np.any(values <= 0):
            raise ValueError(f"{dimension} must contain positive integers")
        normalized[dimension] = normalized[dimension].astype(int)

    t = normalized["t_s"].to_numpy(dtype=float)
    dt = np.diff(t)
    if t[0] < 0 or np.any(dt <= 0):
        raise ValueError("t_s must start at or after zero and be strictly increasing")
    if (normalized["truth_altitude_m"] < 0).any():
        raise ValueError("truth_altitude_m must be non-negative")

    visible = normalized["truth_target_visible"].to_numpy(dtype=bool)
    observed = normalized["observation_available"].to_numpy(dtype=bool)

    for column in TRUTH_VISIBLE_NUMERIC_COLUMNS:
        values = normalized[column]
        if values[visible].isna().any():
            raise ValueError(f"{column} must be present when truth_target_visible is true")
        if values[~visible].notna().any():
            raise ValueError(f"{column} must be missing when truth_target_visible is false")

    for column in OBSERVATION_NUMERIC_COLUMNS:
        values = normalized[column]
        if values[observed].isna().any():
            raise ValueError(f"{column} must be present when observation_available is true")
        if values[~observed].notna().any():
            raise ValueError(f"{column} must be missing when observation_available is false")

    if (normalized.loc[visible, "truth_target_area_px2"] <= 0).any():
        raise ValueError("truth_target_area_px2 must be positive when the target is visible")
    if (normalized.loc[observed, "confidence"] < 0).any() or (
        normalized.loc[observed, "confidence"] > 1
    ).any():
        raise ValueError("confidence must lie in [0,1] for available observations")
    if (normalized.loc[observed, "sigma_lateral_m"] < 0).any() or (
        normalized.loc[observed, "sigma_altitude_m"] < 0
    ).any():
        raise ValueError("observation uncertainty must be non-negative")

    width = normalized["image_width_px"].to_numpy(dtype=float)
    height = normalized["image_height_px"].to_numpy(dtype=float)
    truth_x = normalized["truth_center_x_px"].to_numpy(dtype=float)
    truth_y = normalized["truth_center_y_px"].to_numpy(dtype=float)
    obs_x = normalized["observed_center_x_px"].to_numpy(dtype=float)
    obs_y = normalized["observed_center_y_px"].to_numpy(dtype=float)
    if np.any((truth_x[visible] < 0) | (truth_x[visible] >= width[visible])) or np.any(
        (truth_y[visible] < 0) | (truth_y[visible] >= height[visible])
    ):
        raise ValueError("visible truth target center must lie inside the image")
    if np.any((obs_x[observed] < 0) | (obs_x[observed] >= width[observed])) or np.any(
        (obs_y[observed] < 0) | (obs_y[observed] >= height[observed])
    ):
        raise ValueError("available observed target center must lie inside the image")

    normalized["frame_path"] = normalized["frame_path"].map(_validate_relative_frame_path)
    hashes = normalized["frame_sha256"].astype(str).str.strip().str.lower()
    bad_hashes = hashes[~hashes.map(lambda value: bool(_SHA256_RE.fullmatch(value)))]
    if not bad_hashes.empty:
        raise ValueError("frame_sha256 must contain lowercase or uppercase SHA-256 hex digests")
    normalized["frame_sha256"] = hashes

    verified = 0
    if verify_frame_hashes:
        root = Path(frame_root).resolve()
        for row in normalized.itertuples(index=False):
            path = (root / row.frame_path).resolve()
            try:
                path.relative_to(root)
            except ValueError as exc:
                raise ValueError(f"frame path escapes frame_root: {row.frame_path}") from exc
            if not path.is_file():
                raise ValueError(f"frame file not found: {row.frame_path}")
            actual = _hash_file(path)
            if actual != row.frame_sha256:
                raise ValueError(f"frame SHA-256 mismatch for {row.frame_path}")
            verified += 1

    for column in optional:
        if normalized[column].notna().any() and (normalized[column].dropna() < 0).any():
            raise ValueError(f"{column} must be non-negative when present")

    visible_count = int(visible.sum())
    invisible_count = int((~visible).sum())
    missed = visible & ~observed
    false_positive = ~visible & observed
    paired = visible & observed
    paired_count = int(paired.sum())

    lateral_error = (
        normalized.loc[paired, "observed_lateral_x_m"]
        - normalized.loc[paired, "truth_lateral_x_m"]
    ).to_numpy(dtype=float)
    altitude_error = (
        normalized.loc[paired, "observed_altitude_m"]
        - normalized.loc[paired, "truth_altitude_m"]
    ).to_numpy(dtype=float)

    report = PerceptionTraceValidation(
        rows=int(len(normalized)),
        duration_s=float(t[-1] - t[0]),
        median_dt_s=float(np.median(dt)),
        target_visible_rate=float(visible.mean()),
        observation_available_rate=float(observed.mean()),
        missed_detection_rate_when_visible=(float(missed.sum() / visible_count) if visible_count else 0.0),
        false_positive_rate_when_not_visible=(
            float(false_positive.sum() / invisible_count) if invisible_count else 0.0
        ),
        paired_observation_samples=paired_count,
        lateral_mae_m=(float(np.mean(np.abs(lateral_error))) if paired_count else None),
        altitude_mae_m=(float(np.mean(np.abs(altitude_error))) if paired_count else None),
        verified_frame_hashes=verified,
    )
    return normalized, report


def load_perception_trace(
    path: str | Path,
    *,
    frame_root: str | Path | None = None,
    verify_frame_hashes: bool = False,
) -> tuple[pd.DataFrame, PerceptionTraceValidation]:
    path = Path(path)
    if path.suffix.lower() != ".csv":
        raise ValueError("Phase 9 perception trace loader currently accepts CSV only")
    return validate_perception_trace(
        pd.read_csv(path),
        frame_root=frame_root,
        verify_frame_hashes=verify_frame_hashes,
    )
