from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import run_phase12_adaptive_normalized_conformal as v1
from scripts import run_phase12_adaptive_normalized_conformal_v2 as v2


def _models() -> dict[str, object]:
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


def _df(group: str) -> pd.DataFrame:
    horizon_by_group = {
        v1.p11.GROUP_H3: 3,
        v1.p11.GROUP_H45: 4,
        v1.p11.GROUP_H67: 6,
    }
    is_continuity = group in horizon_by_group
    source = "soft_innovation_continuity" if is_continuity else group
    horizon = horizon_by_group.get(group, 0)
    return pd.DataFrame(
        {
            "p14_source": [source, source, source],
            "p9_continuity_horizon": [horizon, horizon, horizon],
            "severity": [0.0, 0.5, 1.0],
        }
    )


def test_v2_keeps_base_scale_exactly_v1():
    df = _df(v1.p11.GROUP_BASE)
    assert np.allclose(
        v2._scale_values(df, _models(), "lateral"),
        v1._scale_values(df, _models(), "lateral"),
    )


def test_fixture_reaches_the_intended_continuity_group():
    df = _df(v1.p11.GROUP_H3)
    assert set(v1.p11._groups(df).astype(str)) == {v1.p11.GROUP_H3}


def test_v2_continuity_scale_is_positive_monotone_and_lower_contrast():
    df = _df(v1.p11.GROUP_H3)
    old = v1._scale_values(df, _models(), "lateral")
    new = v2._scale_values(df, _models(), "lateral")
    assert np.all(new > 0.0)
    assert np.all(np.diff(new) >= 0.0)
    assert new[-1] / new[0] < old[-1] / old[0]
    assert np.isclose(new[-1] / new[0], np.sqrt(old[-1] / old[0]))


def test_v2_shrinkage_is_center_preserving():
    df = _df(v1.p11.GROUP_H3)
    new = v2._scale_values(df, _models(), "lateral")
    center = 2.0
    expected_low = center * (1.0 / center) ** v2.CONTINUITY_SCALE_SHRINKAGE
    expected_high = center * (4.0 / center) ** v2.CONTINUITY_SCALE_SHRINKAGE
    assert np.isclose(new[0], expected_low)
    assert np.isclose(new[-1], expected_high)


def test_v2_candidate_schema_is_distinct_from_iteration_one():
    assert v2.CANDIDATE_SCHEMA != "aegisland.phase12.adaptive-normalized-conformal.candidate.v1"
    assert v2.CONTINUITY_SCALE_SHRINKAGE == 0.5
