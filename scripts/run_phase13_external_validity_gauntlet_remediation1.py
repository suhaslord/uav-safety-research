from __future__ import annotations

"""Phase 13 execution-only remediation for the pre-result uint64 parity overflow.

Scientific domain definitions, stress magnitudes, gates, candidate identity, and
all downstream evidence partitions remain owned by
run_phase13_external_validity_gauntlet.py and the frozen Phase 13 manifest.
"""

try:
    from scripts import run_phase13_external_validity_gauntlet as p13
except ModuleNotFoundError:
    import run_phase13_external_validity_gauntlet as p13

RETIRED_TECHNICAL_DEV_SEED = 946946
REPLACEMENT_DEV_SEED = 947947


_original_stable_seed = p13._stable_seed


def _execution_safe_stable_seed(*parts: object) -> int:
    """Preserve every original stream except the 2-argument sign-parity use.

    The failed run only needed one parity bit for reacquisition-shock sign.
    Reducing that specific two-argument value before NumPy integer arithmetic
    prevents platform C-long overflow without altering any RNG/lag/phase stream.
    """

    value = int(_original_stable_seed(*parts))
    if len(parts) == 2:
        return value & 1
    return value


def install_execution_remediation() -> None:
    if int(p13.DEV_SEED) != RETIRED_TECHNICAL_DEV_SEED:
        raise RuntimeError("unexpected Phase 13 development seed before remediation")
    if int(p13.STAGE_SEEDS["dev"]) != RETIRED_TECHNICAL_DEV_SEED:
        raise RuntimeError("unexpected Phase 13 stage seed before remediation")

    p13._stable_seed = _execution_safe_stable_seed
    p13.DEV_SEED = REPLACEMENT_DEV_SEED
    p13.STAGE_SEEDS["dev"] = REPLACEMENT_DEV_SEED


if __name__ == "__main__":
    install_execution_remediation()
    p13.main()
