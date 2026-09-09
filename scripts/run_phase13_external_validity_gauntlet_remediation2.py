from __future__ import annotations

"""Final Phase 13 pre-result execution remediation.

This composes amendment 01's parity-only overflow fix and retires the second
technical development seed after the missing-SciPy pre-result failure. The
scientific domain manifest, gates, model, and downstream evidence remain
unchanged.
"""

try:
    from scripts import run_phase13_external_validity_gauntlet as p13
    from scripts import run_phase13_external_validity_gauntlet_remediation1 as remediation1
except ModuleNotFoundError:
    import run_phase13_external_validity_gauntlet as p13
    import run_phase13_external_validity_gauntlet_remediation1 as remediation1

RETIRED_TECHNICAL_DEV_SEEDS = (946946, 947947)
FINAL_REPLACEMENT_DEV_SEED = 948948


def install_execution_remediation() -> None:
    remediation1.install_execution_remediation()
    if int(p13.DEV_SEED) != 947947 or int(p13.STAGE_SEEDS["dev"]) != 947947:
        raise RuntimeError("unexpected Phase 13 development seed after remediation 01")
    p13.DEV_SEED = FINAL_REPLACEMENT_DEV_SEED
    p13.STAGE_SEEDS["dev"] = FINAL_REPLACEMENT_DEV_SEED


if __name__ == "__main__":
    install_execution_remediation()
    p13.main()
