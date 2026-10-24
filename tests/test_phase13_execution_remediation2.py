from __future__ import annotations

from scripts import run_phase13_external_validity_gauntlet as p13
from scripts import run_phase13_external_validity_gauntlet_remediation1 as remediation1
from scripts import run_phase13_external_validity_gauntlet_remediation2 as remediation2


def test_final_remediation_retires_both_invalid_technical_seeds():
    assert remediation2.RETIRED_TECHNICAL_DEV_SEEDS == (946946, 947947)
    assert remediation2.FINAL_REPLACEMENT_DEV_SEED == 948948


def test_final_remediation_preserves_downstream_evidence(monkeypatch):
    monkeypatch.setattr(p13, "DEV_SEED", 946946)
    monkeypatch.setitem(p13.STAGE_SEEDS, "dev", 946946)
    monkeypatch.setattr(p13, "_stable_seed", remediation1._original_stable_seed)

    remediation2.install_execution_remediation()

    assert p13.DEV_SEED == 948948
    assert p13.STAGE_SEEDS["dev"] == 948948
    assert p13.STAGE_SEEDS["transfer"] == 957957
    assert p13.STAGE_SEEDS["validation"] == 968968
    assert p13.STAGE_SEEDS["final"] == 979979
    assert p13._stable_seed("seq", "reacquisition_shock") in (0, 1)
