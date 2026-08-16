from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import run_phase11_p14_bounded_independent_rescue as p14


def _caps_and_scales():
    fit = p14._raw("p14_test_fit", p14.FIT_SEED, p14.FIT_FAMILIES, p14.FIT_DOMAINS)
    caps = p14.p9._fit_velocity_caps(fit)
    scales = p14.p9._fit_innovation_scales(fit, caps)
    return caps, scales


def test_p14_seeds_are_fresh_and_disjoint_from_current_p13():
    p14_seeds = {p14.FIT_SEED, p14.PARTITION_SEED, p14.CALIBRATION_SEED, p14.TRANSFER_SEED, p14.VALIDATION_SEED}
    current_p13_seen_or_retired = {638638, 649649, 660660, 671671, 682682}
    assert len(p14_seeds) == 5
    assert p14_seeds.isdisjoint(current_p13_seen_or_retired)


def test_primary_continuity_remains_bounded_and_unchanged():
    assert p14.p9.MAX_CONTINUITY_GAP == 7
    assert p14.p9.DAMPING == 0.85
    assert p14.p9.SOFT_SCALE_MULTIPLIER == 3.0
    assert p14.p9.BLEND_PREVIOUS_SLOPE == 0.5
    assert p14.p9.BLEND_SOFT_UPDATED_SLOPE == 0.5


def test_event_mask_is_outcome_independent():
    families = tuple(p14.PARTITION_FAMILIES[:4])
    raw = p14._raw("p14_mask_test", p14.PARTITION_SEED, families, p14.PARTITION_CALIBRATION_DOMAINS[:1])
    # Use the exact strata entries relevant to the selected families.
    selected = {name: tuple(f for f in fams if f in families) for name, fams in p14.PARTITION_STRATA.items()}
    selected = {name: fams for name, fams in selected.items() if fams}
    m1 = p14.forced_dropout_mask(raw, selected)
    changed = raw.copy()
    changed["truth_lateral_x_m"] = np.linspace(-999.0, 999.0, len(changed))
    changed["truth_altitude_m"] = 12345.0
    changed["candidate_available"] = ~changed["candidate_available"].astype(bool)
    if "lateral_abs_error_m" in changed:
        changed["lateral_abs_error_m"] = 9999.0
    m2 = p14.forced_dropout_mask(changed, selected)
    pd.testing.assert_series_equal(m1, m2)


def test_rescue_never_changes_primary_state_or_anchor_history():
    caps, scales = _caps_and_scales()
    families = p14.PARTITION_STRATA["bootstrap5"][:1]
    raw = p14._raw("p14_anchor_test", p14.PARTITION_SEED, families, p14.PARTITION_CALIBRATION_DOMAINS[:1])
    raw = p14.apply_intervention(raw, "partition", {"bootstrap5": families})
    primary = p14.p9.add_p9_continuity(raw, caps, scales)
    rescued = p14.add_p14_rescue(raw, p14.PARTITION_SEED, caps, scales)
    p9_columns = [c for c in primary.columns if c.startswith("p9_")]
    pd.testing.assert_frame_equal(primary[p9_columns], rescued[p9_columns], check_dtype=False)


def test_rescue_is_used_only_when_primary_is_unavailable():
    caps, scales = _caps_and_scales()
    families = p14.PARTITION_STRATA["gap12"][:1]
    raw = p14._raw("p14_use_rule_test", p14.PARTITION_SEED, families, p14.PARTITION_CALIBRATION_DOMAINS[:1])
    raw = p14.apply_intervention(raw, "partition", {"gap12": families})
    out = p14.add_p14_rescue(raw, p14.PARTITION_SEED, caps, scales)
    rescue = out["p14_source"].astype(str) == p14.GROUP_RESCUE
    assert not bool((rescue & out["p14_primary_available"].astype(bool)).any())
    assert bool((rescue & (~out["p14_primary_available"].astype(bool))).any())


def test_p14_runner_has_no_final_holdout_stage():
    source = open(p14.__file__, "r", encoding="utf-8").read()
    assert 'choices=("partition", "freeze", "transfer", "validation")' in source
    assert "759759" not in source
