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


def validate_external_trace(frame: pd.DataFrame) -> tuple[pd.DataFrame, ExternalTraceValidation]:
    """Validate and normalize an offline simulator trace.

    The schema is intentionally simulator-agnostic. It stores ground truth only
    for evaluation; downstream Aegis logic must not consume the truth columns as
    controller inputs.
    """

    missing = [column for column in REQUIRED_EXTERNAL_TRACE_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"external trace is missing required columns: {missing}")
    if len(frame) < 2:
        raise ValueError("external trace must contain at least two rows")

    normalized = frame.loc[:, REQUIRED_EXTERNAL_TRACE_COLUMNS].copy()
    for column in NUMERIC_COLUMNS:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
        if normalized[column].isna().any():
            raise ValueError(f"{column} contains missing or non-numeric values")
        values = normalized[column].to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError(f"{column} contains non-finite values")

    for column in BOOLEAN_COLUMNS:
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
    )
    return normalized, report


def load_external_trace(path: str | Path) -> tuple[pd.DataFrame, ExternalTraceValidation]:
    path = Path(path)
    if path.suffix.lower() != ".csv":
        raise ValueError("Phase 7 external trace loader currently accepts CSV only")
    return validate_external_trace(pd.read_csv(path))
