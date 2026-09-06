from __future__ import annotations

import inspect

import numpy as np
import pandas as pd
import pytest

from scripts import run_phase12_adaptive_normalized_conformal as v1
from scripts import run_phase12_adaptive_normalized_conformal_v2 as v2
from scripts import run_phase12_adaptive_normalized_conformal_v3 as v3


def _scale_models() -> dict[str, object]:
    models: dict[str, object] = {}
    for group in v1.GROUPS:
        models[group] = {}
        for axis in ("lateral", "altitude"):
            models[group][axis] = {
                "severity_10": 0.0,
                "severity_90": 1.0,
                "scale_low_m": 1.0,
                "scale_high_m": 4.0,
                "scale_floor_m": 1.0e-5,
                "rows": 1000,
            }
    return models


def _reliability_models() -> dict[str, object]:
    return {
        group: {
            "coordinate": "test",
            "u10": 0.0,
            "u90": 2.0,
            "residual_low": 0.5,
            "residual_high": 2.0,
            "residual_high_raw": 2.0,
            "geometric_center": 1.0,
            "rows": 100,
            "low_tail_rows": 34,
            "high_tail_rows": 34,
        }
        for group in v3.RELIABILITY_GROUPS
    }


def _rows(group: str, n: int = 3) -> pd.DataFrame:
    horizon_by_group = {
        v1.p11.GROUP_H3: 3,
        v1.p11.GROUP_H45: 4,
        v1.p11.GROUP_H67: 6,
    }
    if group == v1.p11.GROUP_RESCUE:
        source = v1.p11.GROUP_RESCUE
        horizon = 0
    elif group in horizon_by_group:
        source = "soft_innovation_continuity"
        horizon = horizon_by_group[group]
    else:
        source = "direct_primary"
        horizon = 0
    return pd.DataFrame(
        {
            "p14_source": [source] * n,
            "p9_continuity_horizon": [horizon] * n,
            "severity": np.linspace(0.25, 0.75, n),
            "p9_anchor_innovation_lateral_abs": np.linspace(0.0, 4.0, n),
        }
    )


def test_v3_fixture_reaches_every_intended_group():
    frames = []
    expected = []
    for group in v1.GROUPS:
        frames.append(_rows(group, 1))
        expected.append(group)
    df = pd.concat(frames, ignore_index=True)
    assert list(v1.p11._groups(df).astype(str)) == expected


def test_v3_base_and_rescue_lateral_scales_are_exactly_v2():
    for group in (v1.p11.GROUP_BASE, v1.p11.GROUP_RESCUE):
        df = _rows(group)
        old = v2._scale_values(df, _scale_models(), "lateral")
        new = v3._scale_values(df, _scale_models(), _reliability_models(), 1.0, "lateral")
        assert np.array_equal(new, old)


def test_v3_altitude_scale_is_exactly_v2_for_continuity():
    for group in v3.RELIABILITY_GROUPS:
        df = _rows(group)
        old = v2._scale_values(df, _scale_models(), "altitude")
        new = v3._scale_values(df, _scale_models(), _reliability_models(), 1.0, "altitude")
        assert np.array_equal(new, old)


def test_v3_lateral_reliability_scale_is_positive_finite_and_monotone_in_innovation():
    df = _rows(v1.p11.GROUP_H45, 7)
    df["severity"] = 0.5
    df["p9_anchor_innovation_lateral_abs"] = np.linspace(0.0, 12.0, len(df))
    values = v3._scale_values(df, _scale_models(), _reliability_models(), 1.0, "lateral")
    assert np.all(np.isfinite(values))
    assert np.all(values > 0.0)
    assert np.all(np.diff(values) >= 0.0)


def test_v3_scale_does_not_require_or_read_truth_columns():
    df = _rows(v1.p11.GROUP_H3, 4)
    without_truth = v3._scale_values(df, _scale_models(), _reliability_models(), 1.0, "lateral")

    with_truth = df.copy()
    with_truth["truth_lateral_x_m"] = [1e9, -1e9, 5e8, -5e8]
    with_truth["truth_altitude_m"] = [-7e8, 7e8, -3e8, 3e8]
    with_truth["p14_lateral_abs_error_m"] = [0.0, 1e9, 2e9, 3e9]
    with_truth["p14_altitude_abs_error_m"] = [9e9, 8e9, 7e9, 6e9]
    changed_truth = v3._scale_values(with_truth, _scale_models(), _reliability_models(), 1.0, "lateral")

    assert np.array_equal(without_truth, changed_truth)
    source = inspect.getsource(v3._scale_values)
    assert "truth_" not in source
    assert "abs_error" not in source


def test_v3_reliability_coordinate_rejects_invalid_inference_state():
    df = _rows(v1.p11.GROUP_H3, 2)
    df.loc[1, "p9_anchor_innovation_lateral_abs"] = -1.0
    with pytest.raises(RuntimeError):
        v3._reliability_coordinate(df, 1.0)
    with pytest.raises(RuntimeError):
        v3._reliability_coordinate(_rows(v1.p11.GROUP_H3, 2), 0.0)


def _fit_frame() -> pd.DataFrame:
    frames = []
    for group, horizon in (
        (v1.p11.GROUP_H3, 3),
        (v1.p11.GROUP_H45, 4),
        (v1.p11.GROUP_H67, 6),
    ):
        n =  ninety = 90
        innovation = np.linspace(0.05, 12.0, n)
        # Deterministic scale-fit truth is allowed only inside model fitting. Error
        # deliberately rises with the inference-visible innovation coordinate.
        error = 0.2 + 0.08 * innovation
        frames.append(
            pd.DataFrame(
                {
                    "p14_available": [True] * n,
                    "truth_visible": [True] * n,
                    "p14_source": ["soft_innovation_continuity"] * n,
                    "p9_continuity_horizon": [horizon] * n,
                    "severity": np.linspace(0.2, 0.8, n),
                    "p9_anchor_innovation_lateral_abs": innovation,
                    "p14_lateral_abs_error_m": error,
                }
            )
        )
    return pd.concat(frames, ignore_index=True)


def test_v3_reliability_fit_is_deterministic_monotone_and_scale_fit_only():
    df = _fit_frame()
    a = v3._fit_reliability_models(df, _scale_models(), 1.0)
    b = v3._fit_reliability_models(df.copy(), _scale_models(), 1.0)
    assert a == b
    for group in v3.RELIABILITY_GROUPS:
        assert a[group]["residual_high"] >= a[group]["residual_low"] > 0.0
        assert a[group]["u90"] > a[group]["u10"]
        assert a[group]["low_tail_rows"] >= v3.RELIABILITY_MIN_TAIL_ROWS
        assert a[group]["high_tail_rows"] >= v3.RELIABILITY_MIN_TAIL_ROWS
    source = inspect.getsource(v3._fit_reliability_models)
    assert "DEV_SEED" not in source
    assert "TRANSFER_SEED" not in source
    assert "VALIDATION_SEED" not in source
    assert "FINAL_SEED" not in source


def test_v3_candidate_identity_and_locked_predecessor_constants_remain_distinct():
    assert v3.CANDIDATE_SCHEMA not in {
        "aegisland.phase12.adaptive-normalized-conformal.candidate.v1",
        v2.CANDIDATE_SCHEMA,
    }
    assert v2.CONTINUITY_SCALE_SHRINKAGE == 0.5
    assert v1.DEV_SEED == 907907
    assert v1.TRANSFER_SEED == 913913
    assert v1.VALIDATION_SEED == 924924
    assert v1.FINAL_SEED == 935935


def test_development_workflow_never_mentions_downstream_seed_literals():
    workflow = open(".github/workflows/phase12-development.yml", encoding="utf-8").read()
    for forbidden in ("858858", "869869", "913913", "924924", "935935"):
        assert forbidden not in workflow
