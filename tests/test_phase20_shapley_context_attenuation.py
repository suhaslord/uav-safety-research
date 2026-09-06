from __future__ import annotations

import math

from scripts import run_phase20_shapley_context_attenuation as p20


def test_fresh_partitions_are_disjoint_and_fixed():
    roles = [set(v) for v in p20.STAGE_FAMILIES.values()]
    for i, a in enumerate(roles):
        for b in roles[i + 1 :]:
            assert a.isdisjoint(b)
    assert p20.STAGE_SEEDS == {
        "dev": 2020201,
        "transfer": 2020202,
        "validation": 2020203,
        "final": 2020204,
    }


def test_complete_power_set_and_endpoint_domains():
    subsets = p20._all_subsets()
    assert len(subsets) == 32
    assert len(set(subsets)) == 32
    assert frozenset() in subsets
    assert frozenset(p20.FACTORS) in subsets
    assert p20._domain_from_subset(frozenset()) == p20.SIMPLE_DOMAIN
    assert p20._domain_from_subset(frozenset(p20.FACTORS)) == p20.HARD_DOMAIN


def test_domain_order_is_canonical():
    subset = frozenset({"low_contrast", "edge", "dim"})
    assert p20._domain_from_subset(subset) == "edge+small_scale+dim+low_contrast+temporal_dropout"


def test_exact_shapley_recovers_additive_attenuation():
    weights = {
        "edge": 0.01,
        "oblique": 0.02,
        "dim": 0.03,
        "blur_noise": 0.04,
        "low_contrast": 0.05,
    }
    advantages = {
        subset: 0.20 - sum(weights[f] for f in subset)
        for subset in p20._all_subsets()
    }
    result = p20._shapley_attenuation(advantages)
    assert math.isclose(result["endpoint_attenuation"], sum(weights.values()), abs_tol=1e-12)
    assert result["efficiency_abs_error"] <= 1e-12
    for factor, expected in weights.items():
        assert math.isclose(result["contributions"][factor], expected, abs_tol=1e-12)


def test_frozen_predecessor_identities_are_exact():
    assert p20.FROZEN_PHASE17_FIT_CANDIDATE_SHA256 == "2ca52a418f5616e0e83ef84d0c9238ee429260cd4de7a553356b0c1bba44d8e0"
    assert p20.FROZEN_PHASE19_FINAL_RESULT_SHA256 == "8c23b9b9c8c9fb2f9146bf739e52074f8709d2fe9a81c794e64fb43f360acebf"
