from __future__ import annotations

import json

import numpy as np

from scripts import run_phase11_p5_perception_continuity as p5
from scripts import run_phase11_p6_source_conditional_calibration as p6


def test_freeze_never_generates_protected_validation(tmp_path, monkeypatch):
    seen = []
    original = p6._raw

    def guarded(name, seed, families, domains):
        seen.append(seed)
        assert seed != p6.VALIDATION_SEED
        return original(name, seed, families, domains)

    monkeypatch.setattr(p6, "_raw", guarded)
    p6.freeze(tmp_path, "p6-freeze-test")

    assert p6.VALIDATION_SEED not in seen
    assert not (tmp_path / "validation_frames.csv").exists()
    assert not (tmp_path / "validation_result.json").exists()


def test_p6_keeps_p5_continuity_constants_exact(tmp_path):
    p6.freeze(tmp_path, "p6-constants-test")
    candidate = json.loads((tmp_path / "candidate_freeze.json").read_text())
    constants = candidate["continuity_constants"]

    assert constants["max_continuity_gap"] == p5.MAX_CONTINUITY_GAP == 5
    assert constants["damping"] == p5.DAMPING == 0.85
    assert constants["velocity_cap_quantile"] == p5.VELOCITY_CAP_QUANTILE == 0.99
    assert candidate["ridge_lambda"] == p5.RIDGE_LAMBDA == 4.0


def test_transfer_groups_are_exact_and_large_enough(tmp_path):
    p6.freeze(tmp_path, "p6-groups-test")
    candidate = json.loads((tmp_path / "candidate_freeze.json").read_text())

    assert candidate["transfer_groups"] == ["base_output", "continuity_extension"]
    counts = candidate["transfer_group_rows"]
    assert counts["continuity_extension"] >= p6.MIN_CONTINUITY_TRANSFER_ROWS
    assert counts["base_output"] >= p6.MIN_BASE_TRANSFER_ROWS
    assert set(candidate["transfer_multipliers"]) == set(p6.GROUPS)

    for group in p6.GROUPS:
        for axis in ("lateral", "altitude"):
            values = candidate["transfer_multipliers"][group][axis]
            assert set(values) == {f"{q:.2f}" for q in p6.TARGETS}
            assert all(np.isfinite(float(v)) and float(v) > 0 for v in values.values())


def test_source_grouping_has_no_third_or_fallback_group():
    fit_raw = p6._raw("fit", p6.FIT_SEED, p6.FIT_FAMILIES, p6.FIT_DOMAINS)
    caps = p5._fit_velocity_caps(fit_raw)
    transfer = p6._prepare(
        p6._raw("transfer", p6.TRANSFER_SEED, p6.TRANSFER_FAMILIES, p6.TRANSFER_DOMAINS),
        caps,
    )
    groups = set(p6._group_series(transfer[p6._available(transfer)]).unique())
    assert groups == {"base_output", "continuity_extension"}
