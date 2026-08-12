from __future__ import annotations

import pytest
from uav_safety.phase10_calibration import Phase10UncertaintyCalibrator


def test_source_calibration_is_broader_for_prediction_errors():
    samples=[{"source":"aruco_update","abs_lateral_error_m":.02,"abs_altitude_error_m":.03},{"source":"aruco_update","abs_lateral_error_m":.03,"abs_altitude_error_m":.02},{"source":"aruco_update","abs_lateral_error_m":.04,"abs_altitude_error_m":.04},{"source":"quad_rejected_temporal_prediction","abs_lateral_error_m":.3,"abs_altitude_error_m":.12},{"source":"quad_rejected_temporal_prediction","abs_lateral_error_m":.5,"abs_altitude_error_m":.18},{"source":"quad_rejected_temporal_prediction","abs_lateral_error_m":.7,"abs_altitude_error_m":.2}]; cal=Phase10UncertaintyCalibrator.fit(samples); aruco=cal.sigma("aruco_update"); prediction=cal.sigma("quad_rejected_temporal_prediction"); assert prediction[0]>aruco[0]; assert prediction[1]>aruco[1]


def test_calibration_roundtrip_dict():
    cal=Phase10UncertaintyCalibrator.fit([{"source":"a","abs_lateral_error_m":.1,"abs_altitude_error_m":.2},{"source":"a","abs_lateral_error_m":.2,"abs_altitude_error_m":.3},{"source":"a","abs_lateral_error_m":.3,"abs_altitude_error_m":.4}]); restored=Phase10UncertaintyCalibrator.from_dict(cal.to_dict()); assert restored.sigma("a")==cal.sigma("a")


def test_empty_calibration_rejected():
    with pytest.raises(ValueError): Phase10UncertaintyCalibrator.fit([])
