from __future__ import annotations

import numpy as np

from scripts.run_phase11_domain_shift_benchmark import (
    CHALLENGE_DOMAINS,
    FIT_DOMAINS,
    SPLITS,
    _simulate_row,
    conformal_radius,
    reliability_score,
)


def test_phase11_domains_are_compositionally_disjoint() -> None:
    assert set(FIT_DOMAINS).isdisjoint(set(CHALLENGE_DOMAINS))
    assert all("+" not in d for d in FIT_DOMAINS)
    assert all("+" in d for d in CHALLENGE_DOMAINS)


def test_phase11_trajectory_families_are_disjoint() -> None:
    fit = set(SPLITS["fit"][1])
    cal = set(SPLITS["calibration"][1])
    challenge = set(SPLITS["challenge"][1])
    assert fit.isdisjoint(cal)
    assert fit.isdisjoint(challenge)
    assert cal.isdisjoint(challenge)


def test_phase11_generator_is_deterministic() -> None:
    a = _simulate_row("challenge", 33033, 9, CHALLENGE_DOMAINS[0], 17, 60)
    b = _simulate_row("challenge", 33033, 9, CHALLENGE_DOMAINS[0], 17, 60)
    assert a == b


def test_phase11_risk_score_is_bounded_and_orders_clear_shift() -> None:
    nominal = {
        "edge_margin_ratio": 1.0,
        "visible_fraction_proxy": 0.98,
        "projected_scale_px": 78.0,
        "obliquity_proxy": 0.05,
        "brightness_mean": 190.0,
        "contrast_std": 50.0,
        "laplacian_var": 180.0,
        "temporal_innovation": 0.05,
        "track_stability": 0.95,
        "reacquisition": False,
    }
    shifted = {
        "edge_margin_ratio": 0.05,
        "visible_fraction_proxy": 0.35,
        "projected_scale_px": 18.0,
        "obliquity_proxy": 0.90,
        "brightness_mean": 70.0,
        "contrast_std": 12.0,
        "laplacian_var": 18.0,
        "temporal_innovation": 0.90,
        "track_stability": 0.20,
        "reacquisition": True,
    }
    n = reliability_score(nominal)
    s = reliability_score(shifted)
    assert 0.0 <= n <= 1.0
    assert 0.0 <= s <= 1.0
    assert s > n


def test_finite_sample_conformal_rule_uses_upper_order_statistic() -> None:
    values = np.arange(1.0, 101.0)
    # ceil((100+1)*0.95)=96 -> 96th sorted observation
    assert conformal_radius(values, 0.95) == 96.0
