from __future__ import annotations

import pandas as pd
import pytest

from uav_safety.external_trace import REQUIRED_EXTERNAL_TRACE_COLUMNS, validate_external_trace


def valid_trace() -> pd.DataFrame:
    rows = []
    for i in range(4):
        rows.append({
            "t_s": 0.05 * i,
            "truth_x_m": 0.2 - 0.02 * i,
            "truth_z_m": 2.0 - 0.1 * i,
            "truth_vx_mps": -0.1,
            "truth_vz_mps": -0.4,
            "image_x_m": 0.22 - 0.02 * i,
            "image_z_m": 2.05 - 0.1 * i,
            "image_vx_mps": -0.1,
            "image_vz_mps": -0.4,
            "image_confidence": 0.8,
            "image_sigma_pos_m": 0.2,
            "image_dropped": False,
            "reference_x_m": 0.19 - 0.02 * i,
            "reference_z_m": 1.98 - 0.1 * i,
            "reference_vx_mps": -0.09,
            "reference_vz_mps": -0.39,
            "reference_sigma_pos_m": 0.25,
            "reference_available": True,
            "reference_fresh": i % 2 == 0,
        })
    return pd.DataFrame(rows)


def test_external_trace_schema_accepts_valid_simulator_log():
    normalized, report = validate_external_trace(valid_trace())
    assert tuple(normalized.columns) == REQUIRED_EXTERNAL_TRACE_COLUMNS
    assert report.rows == 4
    assert report.duration_s == pytest.approx(0.15)
    assert report.reference_available_rate == pytest.approx(1.0)


def test_external_trace_rejects_nonmonotonic_time():
    frame = valid_trace()
    frame.loc[2, "t_s"] = frame.loc[1, "t_s"]
    with pytest.raises(ValueError, match="strictly increasing"):
        validate_external_trace(frame)


def test_external_trace_rejects_out_of_range_confidence():
    frame = valid_trace()
    frame.loc[1, "image_confidence"] = 1.2
    with pytest.raises(ValueError, match="\[0,1\]"):
        validate_external_trace(frame)
