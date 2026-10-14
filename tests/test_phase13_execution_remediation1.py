from __future__ import annotations

import numpy as np

from scripts import run_phase13_external_validity_gauntlet as p13
from scripts import run_phase13_external_validity_gauntlet_remediation1 as remediation


def test_remediation_retires_only_the_failed_development_seed():
    assert remediation.RETIRED_TECHNICAL_DEV_SEED == 946946
    assert remediation.REPLACEMENT_DEV_SEED == 947947
    assert p13.TRANSFER_SEED == 957957
    assert p13.VALIDATION_SEED == 968968
    assert p13.FINAL_SEED == 979979


def test_two_argument_sign_seed_is_reduced_to_parity_only():
    raw = remediation._original_stable_seed(
        "actual-like-phase13-sequence-with-large-hash",
        "reacquisition_shock",
    )
    safe = remediation._execution_safe_stable_seed(
        "actual-like-phase13-sequence-with-large-hash",
        "reacquisition_shock",
    )
    assert safe in (0, 1)
    assert safe == (raw & 1)
    frames = np.arange(60, dtype=np.int64)
    parity = (frames + safe) % 2
    assert set(np.unique(parity)).issubset({0, 1})


def test_non_sign_stable_seed_streams_are_unchanged():
    cases = [
        ("phase13-phase", "seq", "domain"),
        (947947, "domain", "seq", 17, "lag"),
        (947947, "domain", "seq", 17, "noise"),
    ]
    for parts in cases:
        assert remediation._execution_safe_stable_seed(*parts) == remediation._original_stable_seed(*parts)


def test_install_changes_only_development_seed_and_sign_seed(monkeypatch):
    monkeypatch.setattr(p13, "DEV_SEED", 946946)
    monkeypatch.setitem(p13.STAGE_SEEDS, "dev", 946946)
    monkeypatch.setattr(p13, "_stable_seed", remediation._original_stable_seed)

    remediation.install_execution_remediation()

    assert p13.DEV_SEED == 947947
    assert p13.STAGE_SEEDS["dev"] == 947947
    assert p13.STAGE_SEEDS["transfer"] == 957957
    assert p13.STAGE_SEEDS["validation"] == 968968
    assert p13.STAGE_SEEDS["final"] == 979979
    assert p13._stable_seed("seq", "reacquisition_shock") in (0, 1)
