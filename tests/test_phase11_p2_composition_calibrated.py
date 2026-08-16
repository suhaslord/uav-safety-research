from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import run_phase11_p2_composition_calibrated as p2


def test_p2_seeds_and_families_are_disjoint_from_prior_revisions():
    prior_seeds = {33033, 63333, 44044, 55055, 66066, 77077}
    assert {p2.FIT_SEED, p2.CALIBRATION_SEED, p2.TRANSFER_SEED, p2.VALIDATION_SEED}.isdisjoint(prior_seeds)
    groups = [set(p2.FIT_FAMILIES), set(p2.CALIBRATION_FAMILIES), set(p2.TRANSFER_FAMILIES), set(p2.VALIDATION_FAMILIES)]
    for i, left in enumerate(groups):
        for right in groups[i + 1 :]:
            assert left.isdisjoint(right)


def test_freeze_never_generates_validation_seed(tmp_path, monkeypatch):
    calls: list[int] = []
    original = p2.p1.generate_split

    def guarded(name, seed, families, domains, frames=p2.FRAMES_PER_SEQUENCE):
        calls.append(seed)
        assert seed != p2.VALIDATION_SEED
        return original(name, seed, families, domains, frames=frames)

    monkeypatch.setattr(p2.p1, "generate_split", guarded)
    candidate = p2.freeze(tmp_path, "test-sha")
    assert p2.VALIDATION_SEED not in calls
    assert candidate["validation_seed_unseen_at_freeze"] == p2.VALIDATION_SEED


def test_final_intervals_are_nested():
    fit = p2._prepare("fit", p2.FIT_SEED, p2.FIT_FAMILIES[:1], p2.FIT_DOMAINS[:2])
    cal = p2._prepare("calibration", p2.CALIBRATION_SEED, p2.CALIBRATION_FAMILIES[:1], p2.FIT_DOMAINS[:2])
    transfer = p2._prepare("transfer", p2.TRANSFER_SEED, p2.TRANSFER_FAMILIES[:1], p2.TRANSFER_DOMAINS[:2])
    candidate = p2._build_candidate(fit, cal, transfer, "test-sha")
    subset = transfer[p2._available(transfer)].head(20)
    for axis in ("lateral", "altitude"):
        widths = p2.final_halfwidths(subset, candidate, axis)
        matrix = np.column_stack([widths[f"{q:.2f}"] for q in p2.TARGETS])
        assert np.all(np.diff(matrix, axis=1) >= -1e-12)


def test_budget_acceptance_is_width_based_not_truth_error():
    source = pd.read_csv if False else None  # keep lint/simple import path stable
    fit = p2._prepare("fit", p2.FIT_SEED, p2.FIT_FAMILIES[:1], p2.FIT_DOMAINS[:2])
    cal = p2._prepare("calibration", p2.CALIBRATION_SEED, p2.CALIBRATION_FAMILIES[:1], p2.FIT_DOMAINS[:2])
    transfer = p2._prepare("transfer", p2.TRANSFER_SEED, p2.TRANSFER_FAMILIES[:1], p2.TRANSFER_DOMAINS[:2])
    candidate = p2._build_candidate(fit, cal, transfer, "test-sha")
    accept_before = p2._budget_accept(transfer, candidate)
    modified = transfer.copy()
    modified["p1_lateral_abs_error_m"] = modified["p1_lateral_abs_error_m"] * 1000
    modified["p1_altitude_abs_error_m"] = modified["p1_altitude_abs_error_m"] * 1000
    accept_after = p2._budget_accept(modified, candidate)
    assert accept_before.equals(accept_after)
