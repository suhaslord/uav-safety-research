from __future__ import annotations

import pandas as pd

from scripts import run_phase11_p14_independent_coarse_fallback as p14


def test_p14_fresh_seed_boundary():
    seeds = (p14.FIT_SEED, p14.BASE_CALIBRATION_SEED, p14.TRANSFER_CALIBRATION_SEED, p14.CHALLENGE_SEED, p14.VALIDATION_SEED)
    assert seeds == (638638, 649649, 660660, 671671, 682682)
    assert len(set(seeds)) == 5


def test_auxiliary_model_is_fixed_independent_fallback_only():
    assert p14.AUX_AVAILABILITY == 0.96
    assert p14.AUX_LATERAL_SIGMA_M == 0.075
    assert p14.AUX_ALTITUDE_SIGMA_M == 0.160
    assert p14.AUX_TAIL_PROBABILITY == 0.025
    assert p14.AUX_TAIL_SCALE_LOW == 2.5
    assert p14.AUX_TAIL_SCALE_HIGH == 4.0


def test_p14_grouping_has_four_fixed_sources():
    df = pd.DataFrame({
        "p14_source": ["known_aruco_refined", "soft_innovation_continuity", "soft_innovation_continuity", "auxiliary_coarse_fallback"],
        "p9_continuity_horizon": [0, 3, 6, 0],
    })
    assert p14._group_series(df).tolist() == [
        "base_output", "primary_continuity_h3", "primary_continuity_h47", "auxiliary_fallback"
    ]


def test_p14_family_sets_are_disjoint():
    sets = [set(p14.FIT_FAMILIES), set(p14.BASE_CALIBRATION_FAMILIES), set(p14.TRANSFER_CALIBRATION_FAMILIES), set(p14.CHALLENGE_FAMILIES), set(p14.VALIDATION_FAMILIES)]
    for i, a in enumerate(sets):
        for b in sets[i + 1:]:
            assert a.isdisjoint(b)


def test_auxiliary_rng_is_deterministic_and_independent_of_primary_availability_flag():
    row = pd.Series({"seed": 1, "family": 2, "frame_index": 3, "candidate_available": True})
    a = p14._aux_rng(row).random(4)
    row2 = row.copy(); row2["candidate_available"] = False
    b = p14._aux_rng(row2).random(4)
    assert (a == b).all()
