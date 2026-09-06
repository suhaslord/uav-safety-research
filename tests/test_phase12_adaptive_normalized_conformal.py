from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import run_phase12_adaptive_normalized_conformal as p12


def test_phase12_evidence_units_and_seeds_are_disjoint():
    family_sets = [
        set(p12.SCALE_FIT_FAMILIES),
        set(p12.CAL_A_FAMILIES),
        set(p12.CAL_B_FAMILIES),
        set(p12.DEV_FAMILIES),
        set(p12.TRANSFER_FAMILIES),
        set(p12.VALIDATION_FAMILIES),
        set(p12.FINAL_FAMILIES),
    ]
    for i, left in enumerate(family_sets):
        for right in family_sets[i + 1 :]:
            assert left.isdisjoint(right)

    seeds = {
        p12.SCALE_FIT_SEED,
        p12.CAL_A_SEED,
        p12.CAL_B_SEED,
        p12.DEV_SEED,
        p12.TRANSFER_SEED,
        p12.VALIDATION_SEED,
        p12.FINAL_SEED,
    }
    assert len(seeds) == 7
    assert 858858 not in seeds
    assert 869869 not in seeds


def test_final_domains_are_not_used_before_final():
    final = set(p12.FINAL_DOMAINS)
    for earlier in (
        p12.SCALE_FIT_DOMAINS,
        p12.CAL_A_DOMAINS,
        p12.CAL_B_DOMAINS,
        p12.DEV_DOMAINS,
        p12.TRANSFER_DOMAINS,
        p12.VALIDATION_DOMAINS,
    ):
        assert final.isdisjoint(earlier)


def test_normalized_robust_envelope_is_pointwise_maximum():
    a = {}
    b = {}
    for gi, group in enumerate(p12.GROUPS):
        a[group] = {}
        b[group] = {}
        for ai, axis in enumerate(("lateral", "altitude")):
            a[group][axis] = {}
            b[group][axis] = {}
            for qi, q in enumerate(p12.TARGETS):
                key = f"{q:.2f}"
                a[group][axis][key] = float(1 + gi + ai + qi)
                b[group][axis][key] = float(0.5 + gi + ai + qi + (1 if qi % 2 else 0))

    out = p12._max_envelope(a, b)
    for group in p12.GROUPS:
        for axis in ("lateral", "altitude"):
            for q in p12.TARGETS:
                key = f"{q:.2f}"
                assert out[group][axis][key] == max(a[group][axis][key], b[group][axis][key])


def _toy_models() -> dict[str, object]:
    models: dict[str, object] = {}
    for group in p12.GROUPS:
        models[group] = {}
        for axis in ("lateral", "altitude"):
            models[group][axis] = {
                "severity_10": 0.2,
                "severity_90": 0.8,
                "scale_low_m": 0.10,
                "scale_high_m": 0.30,
                "scale_floor_m": 1.0e-5,
                "rows": 1000,
            }
    return models


def test_scale_is_clipped_monotone_and_inference_visible_only():
    base_group = p12.p11.GROUP_BASE
    df = pd.DataFrame(
        {
            "p14_source": [base_group] * 5,
            "p9_continuity_horizon": [0] * 5,
            "severity": [-1.0, 0.2, 0.5, 0.8, 2.0],
        }
    )
    scale = p12._scale_values(df, _toy_models(), "lateral")
    assert np.all(np.diff(scale) >= 0)
    assert scale[0] == scale[1] == 0.10
    assert scale[-1] == scale[-2] == 0.30
    assert np.isclose(scale[2], 0.20)


def test_halfwidth_equals_scale_times_frozen_multiplier():
    base_group = p12.p11.GROUP_BASE
    df = pd.DataFrame(
        {
            "p14_source": [base_group, base_group],
            "p9_continuity_horizon": [0, 0],
            "severity": [0.2, 0.8],
        }
    )
    radii = {}
    for group in p12.GROUPS:
        radii[group] = {}
        for axis in ("lateral", "altitude"):
            radii[group][axis] = {f"{q:.2f}": 2.0 for q in p12.TARGETS}

    candidate = {
        "scale_models": _toy_models(),
        "robust_normalized_radii": radii,
    }
    width = p12._halfwidths(df, candidate, "lateral", 0.95)
    assert np.allclose(width, [0.20, 0.60])


def test_final_power_requirements_are_at_least_transfer_requirements():
    for group in p12.GROUPS:
        assert p12.FINAL_MINIMUMS[group] >= p12.EVAL_MINIMUMS[group]
