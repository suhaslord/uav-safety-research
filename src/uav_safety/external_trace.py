from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED_EXTERNAL_TRACE_COLUMNS = (
    "t_s",
    "truth_x_m",
    "truth_z_m",
    "truth_vx_mps",
    "truth_vz_mps",
    "image_x_m",
    "image_z_m",
    "image_vx_mps",
    "image_vz_mps",
    "image_confidence",
    "image_sigma_pos_m",
    "image_dropped",
    "reference_x_m",
    "reference_z_m",
    "reference_vx_mps",
    "reference_vz_mps",
    "reference_sigma_pos_m",
    "reference_available",
    "reference_fresh",
)

# Phase 8 can consume richer timing diagnostics when a simulator exposes them,
# but these columns remain optional so the Phase 7 simulator-agnostic schema is
# backward compatible.
OPTIONAL_EXTERNAL_TRACE_NUMERIC_COLUMNS = (
    "image_transport_latency_s",
    "reference_transport_latency_s",
    "reference_state_age_s",
)
OPTIONAL_EXTERNAL_TRACE_BOOLEAN_COLUMNS = (
    "reference_delivery",
)
OPTIONAL_EXTERNAL_TRACE_COLUMNS = (
    *OPTIONAL_EXTERNAL_TRACE_NUMERIC_COLUMNS,
    *OPTIONAL_EXTERNAL_TRACE_BOOLEAN_COLUMNS,
)

NUMERIC_COLUMNS = tuple(
    column
    for column in REQUIRED_EXTERNAL_TRACE_COLUMNS
    if column not in {"image_dropped", "reference_available", "reference_fresh"}
)
BOOLEAN_COLUMNS = ("image_dropped", "reference_available", "reference_fresh")


@dataclass(frozen=True)
class ExternalTraceValidation:
    rows: int
    duration_s: float
    median_dt_s: float
    max_dt_s: float
    reference_available_rate: float
    image_drop_rate: float
    max_abs_truth_x_m: float
    min_truth_z_m: float
    max_truth_z_m: float
    image_lateral_mae_m: float
    reference_lateral_mae_m: float
    mean_abs_lateral_disagreement_m: float
    paired_lateral_samples: int
    lateral_error_correlation: float | None

    def to_dict(self) -> dict:
        return {
            "rows": self.rows,
            "duration_s": self.duration_s,
            "median_dt_s": self.median_dt_s,
            "max_dt_s": self.max_dt_s,
            "reference_available_rate": self.reference_available_rate,
            "image_drop_rate": self.image_drop_rate,
            "max_abs_truth_x_m": self.max_abs_truth_x_m,
            "min_truth_z_m": self.min_truth_z_m,
            "max_truth_z_m": self.max_truth_z_m,
            "image_lateral_mae_m": self.image_lateral_mae_m,
            "reference_lateral_mae_m": self.reference_lateral_mae_m,
            "mean_abs_lateral_disagreement_m": self.mean_abs_lateral_disagreement_m,
            "paired_lateral_samples": self.paired_lateral_samples,
            "lateral_error_correlation": self.lateral_error_correlation,
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


def _safe_correlation(a: np.ndarray, b: np.ndarray) -> float | None:
    if len(a) < 3:
        return None
    if float(np.std(a)) < 1e-12 or float(np.std(b)) < 1e-12:
        return None
    value = float(np.corrcoef(a, b)[0, 1])
    return value if np.isfinite(value) else None


def validate_external_trace(frame: pd.DataFrame) -> tuple[pd.DataFrame, ExternalTraceValidation]:
    """Validate and normalize an offline simulator trace.

    The required schema is intentionally simulator-agnostic. It stores ground
    truth only for evaluation; downstream Aegis logic must not consume the truth
    columns as controller inputs.

    Phase 8 optionally retains transport-latency/state-age fields when they are
    provided by a higher-fidelity simulator. Their absence is recorded later as
    unavailable evidence rather than silently replaced with zeros.
    """

    missing = [column for column in REQUIRED_EXTERNAL_TRACE_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"external trace is missing required columns: {missing}")
    if len(frame) < 2:
        raise ValueError("external trace must contain at least two rows")

    present_optional = tuple(column for column in OPTIONAL_EXTERNAL_TRACE_COLUMNS if column in frame.columns)
    normalized = frame.loc[:, (*REQUIRED_EXTERNAL_TRACE_COLUMNS, *present_optional)].copy()

    for column in NUMERIC_COLUMNS:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
        if normalized[column].isna().any():
            raise ValueError(f"{column} contains missing or non-numeric values")
        values = normalized[column].to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError(f"{column} contains non-finite values")

    for column in OPTIONAL_EXTERNAL_TRACE_NUMERIC_COLUMNS:
        if column not in normalized.columns:
            continue
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
        if normalized[column].isna().any():
            raise ValueError(f"{column} contains missing or non-numeric values")
        values = normalized[column].to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError(f"{column} contains non-finite values")
        if np.any(values < 0):
            raise ValueError(f"{column} must be non-negative")

    for column in BOOLEAN_COLUMNS:
        normalized[column] = _coerce_bool(normalized[column], column)
    for column in OPTIONAL_EXTERNAL_TRACE_BOOLEAN_COLUMNS:
        if column in normalized.columns:
            normalized[column] = _coerce_bool(normalized[column], column)

    t = normalized["t_s"].to_numpy(dtype=float)
    dt = np.diff(t)
    if t[0] < 0:
        raise ValueError("t_s must start at or after zero")
    if np.any(dt <= 0):
        raise ValueError("t_s must be strictly increasing")

    if ((normalized["image_confidence"] < 0) | (normalized["image_confidence"] > 1)).any():
        raise ValueError("image_confidence must lie in [0,1]")
    if (normalized["image_sigma_pos_m"] < 0).any() or (normalized["reference_sigma_pos_m"] < 0).any():
        raise ValueError("uncertainty values must be non-negative")
    if (normalized["truth_z_m"] < 0).any():
        raise ValueError("truth_z_m must be non-negative in the landing-frame convention")

    image_valid = ~normalized["image_dropped"]
    reference_valid = normalized["reference_available"]
    paired = image_valid & reference_valid

    image_error = (
        normalized.loc[image_valid, "image_x_m"] - normalized.loc[image_valid, "truth_x_m"]
    ).to_numpy(dtype=float)
    reference_error = (
        normalized.loc[reference_valid, "reference_x_m"] - normalized.loc[reference_valid, "truth_x_m"]
    ).to_numpy(dtype=float)
    paired_image_error = (
        normalized.loc[paired, "image_x_m"] - normalized.loc[paired, "truth_x_m"]
    ).to_numpy(dtype=float)
    paired_reference_error = (
        normalized.loc[paired, "reference_x_m"] - normalized.loc[paired, "truth_x_m"]
    ).to_numpy(dtype=float)
    paired_disagreement = (
        normalized.loc[paired, "image_x_m"] - normalized.loc[paired, "reference_x_m"]
    ).to_numpy(dtype=float)

    report = ExternalTraceValidation(
        rows=int(len(normalized)),
        duration_s=float(t[-1] - t[0]),
        median_dt_s=float(np.median(dt)),
        max_dt_s=float(np.max(dt)),
        reference_available_rate=float(normalized["reference_available"].mean()),
        image_drop_rate=float(normalized["image_dropped"].mean()),
        max_abs_truth_x_m=float(normalized["truth_x_m"].abs().max()),
        min_truth_z_m=float(normalized["truth_z_m"].min()),
        max_truth_z_m=float(normalized["truth_z_m"].max()),
        image_lateral_mae_m=float(np.mean(np.abs(image_error))) if len(image_error) else float("nan"),
        reference_lateral_mae_m=float(np.mean(np.abs(reference_error))) if len(reference_error) else float("nan"),
        mean_abs_lateral_disagreement_m=(
            float(np.mean(np.abs(paired_disagreement))) if len(paired_disagreement) else float("nan")
        ),
        paired_lateral_samples=int(len(paired_image_error)),
        lateral_error_correlation=_safe_correlation(paired_image_error, paired_reference_error),
    )
    return normalized, report


def load_external_trace(path: str | Path) -> tuple[pd.DataFrame, ExternalTraceValidation]:
    path = Path(path)
    if path.suffix.lower() != ".csv":
        raise ValueError("external trace loader currently accepts CSV only")
    return validate_external_trace(pd.read_csv(path))
