from __future__ import annotations

import math

from scripts import run_phase21_orthogonal_context_spectrum as p21


def _surface(first_order: dict[str, float], pair: tuple[str, str] | None = None, pair_beta: float = 0.0):
    out = {}
    for subset in p21.p20._all_subsets():
        value = 0.2
        for factor, beta in first_order.items():
            value += beta * (1.0 if factor in subset else -1.0)
        if pair is not None:
            value += pair_beta * math.prod(1.0 if f in subset else -1.0 for f in pair)
        out[subset] = value
    return out


def test_fresh_partitions_are_disjoint_and_after_phase20():
    roles = [set(v) for v in p21.STAGE_FAMILIES.values()]
    for i, a in enumerate(roles):
        for b in roles[i + 1 :]:
            assert a.isdisjoint(b)
    assert p21.STAGE_SEEDS == {
        "dev": 2121211,
        "transfer": 2121212,
        "validation": 2121213,
        "final": 2121214,
    }
    assert p21.STAGE_FAMILIES["dev"] == tuple(range(2217, 2241))
    assert p21.STAGE_FAMILIES["final"] == tuple(range(2289, 2313))


def test_exact_phase20_final_identity_is_frozen():
    assert p21.FROZEN_PHASE20_FINAL_RESULT_SHA256 == "f2a0cf4e1cf0765c3194025eb29072f9663f27e3cdd13b0594cde4643f33934e"
    assert p21.FACTORS == ("edge", "oblique", "dim", "blur_noise", "low_contrast")


def test_walsh_recovers_pure_first_order_surface_exactly():
    first = {
        "edge": -0.02,
        "oblique": -0.015,
        "dim": -0.01,
        "blur_noise": -0.012,
        "low_contrast": -0.009,
    }
    spectrum = p21._walsh_spectrum(_surface(first))
    assert spectrum["parseval_abs_error"] <= 1.0e-15
    assert abs(spectrum["first_order_variance_share"] - 1.0) <= 1.0e-12
    assert abs(spectrum["interaction_variance_share"]) <= 1.0e-12
    for factor, expected in first.items():
        assert abs(spectrum["first_order_coefficients"][factor] - expected) <= 1.0e-12


def test_walsh_detects_pair_interaction_without_calling_it_first_order():
    pair = ("edge", "oblique")
    spectrum = p21._walsh_spectrum(_surface({}, pair=pair, pair_beta=0.03))
    assert spectrum["parseval_abs_error"] <= 1.0e-15
    assert spectrum["first_order_variance_share"] <= 1.0e-12
    assert abs(spectrum["interaction_variance_share"] - 1.0) <= 1.0e-12
    assert abs(spectrum["coefficients"]["edge+oblique"] - 0.03) <= 1.0e-12


def test_preregistered_first_order_threshold_is_not_majority_only():
    assert p21.THRESHOLDS["first_order_variance_share_min"] == 0.70
    assert p21.THRESHOLDS["orthogonal_abs_tolerance"] == 1.0e-12
