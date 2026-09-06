from __future__ import annotations

import inspect

import numpy as np

from scripts import run_phase13_external_validity_gauntlet as p13
from scripts import run_phase13c_compound_attribution as p13c
from scripts import run_phase13c_compound_attribution_remediation1 as remediation


def test_remediation_keeps_development_seed_unchanged():
    assert remediation.UNCHANGED_DEV_SEED == 1313135
    assert p13c.STAGE_SEEDS["dev"] == 1313135


def test_remediation_is_only_explicit_writable_array_copy_for_subset_path():
    source = inspect.getsource(remediation._execution_safe_apply_component_subset)
    assert 'to_numpy(float).copy()' in source
    assert "0.04" in source
    assert "0.08" in source
    assert "0.07" in source
    assert "0.02" in source
    assert "1.35" in source
    assert "0.12" in source


def test_full_compound_still_delegates_to_frozen_phase13_transform():
    source = inspect.getsource(remediation._execution_safe_apply_component_subset)
    assert "p13c.p13.apply_shift(df, p13c.ORIGINAL_COMPOUND_NAME, seed)" in source


def test_noise_only_executes_after_remediation_without_mutating_truth():
    from tests.test_phase13c_compound_attribution import _fixture

    remediation.install_execution_remediation()
    df = _fixture()
    out = p13c._apply_component_subset(
        df,
        "noise_only",
        p13c.CONTRAST_COMPONENTS["noise_only"],
        p13c.STAGE_SEEDS["dev"],
    )
    assert np.array_equal(df["truth_lateral_x_m"], out["truth_lateral_x_m"])
    assert np.array_equal(df["truth_altitude_m"], out["truth_altitude_m"])
    assert np.array_equal(df["p14_available"], out["p14_available"])
    assert not np.array_equal(
        df["p14_estimate_lateral_x_m"].to_numpy(float),
        out["p14_estimate_lateral_x_m"].to_numpy(float),
    )


def test_install_only_replaces_component_execution_function():
    original_seed = p13c.STAGE_SEEDS["dev"]
    original_contrasts = dict(p13c.CONTRAST_COMPONENTS)
    remediation.install_execution_remediation()
    assert p13c.STAGE_SEEDS["dev"] == original_seed
    assert p13c.CONTRAST_COMPONENTS == original_contrasts
    assert p13c._apply_component_subset is remediation._execution_safe_apply_component_subset
