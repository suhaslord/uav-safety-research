from __future__ import annotations

from scripts import run_phase11_p14r_robust_group_envelope as p14r


def test_p14r_evidence_units_are_disjoint():
    sets = [
        set(p14r.FIT_FAMILIES),
        set(p14r.CAL_A_FAMILIES),
        set(p14r.CAL_B_FAMILIES),
        set(p14r.TRANSFER_FAMILIES),
        set(p14r.VALIDATION_FAMILIES),
        set(p14r.FINAL_FAMILIES),
    ]
    for i, left in enumerate(sets):
        for right in sets[i + 1 :]:
            assert left.isdisjoint(right)
    assert len({p14r.FIT_SEED, p14r.CAL_A_SEED, p14r.CAL_B_SEED, p14r.TRANSFER_SEED, p14r.VALIDATION_SEED, p14r.FINAL_SEED}) == 6


def test_final_domains_are_not_used_for_p14r_development_or_validation():
    final = set(p14r.FINAL_DOMAINS)
    assert final.isdisjoint(p14r.CAL_A_DOMAINS)
    assert final.isdisjoint(p14r.CAL_B_DOMAINS)
    assert final.isdisjoint(p14r.TRANSFER_DOMAINS)
    assert final.isdisjoint(p14r.VALIDATION_DOMAINS)


def test_robust_envelope_is_pointwise_maximum():
    a = {}
    b = {}
    for gi, group in enumerate(p14r.GROUPS):
        a[group] = {}
        b[group] = {}
        for ai, axis in enumerate(("lateral", "altitude")):
            a[group][axis] = {}
            b[group][axis] = {}
            for qi, q in enumerate(p14r.TARGETS):
                key = f"{q:.2f}"
                a[group][axis][key] = float(gi + ai + qi + 1)
                b[group][axis][key] = float(gi + ai + qi + (2 if qi % 2 else 0.5))
    out = p14r._max_envelope(a, b)
    for group in p14r.GROUPS:
        for axis in ("lateral", "altitude"):
            for q in p14r.TARGETS:
                key = f"{q:.2f}"
                assert out[group][axis][key] == max(a[group][axis][key], b[group][axis][key])


def test_rescue_model_is_unchanged_from_frozen_p14():
    p14 = p14r.p14
    assert p14.RESCUE_AVAILABILITY == 0.95
    assert p14.RESCUE_LATERAL_SIGMA_M == 0.10
    assert p14.RESCUE_ALTITUDE_SIGMA_M == 0.20
    assert p14.RESCUE_TAIL_PROBABILITY == 0.02
    assert p14.RESCUE_TAIL_SCALE == 3.0


def test_final_power_requirements_are_stricter_than_transfer_validation():
    for group in p14r.GROUPS:
        assert p14r.FINAL_MINIMUMS[group] >= p14r.EVAL_MINIMUMS[group]
