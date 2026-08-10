from __future__ import annotations

from pathlib import Path
import argparse

import pandas as pd

from uav_safety.image_temporal import fit_synthetic_calibrator
from uav_safety.phase6b_fusion import Phase6BComponentGateConfig
from uav_safety.phase6c_fusion import Phase6CComponentFusionAdapter
from uav_safety.phase6e_perception import fit_phase6e_component_calibrator
from uav_safety.selective_confidence_v2 import fit_component_calibrator
from uav_safety.simulator_image_phase6c import run_phase6c_episode
from uav_safety.simulator_image_phase6g import run_phase6g_episode
from uav_safety.simulator_image_v3 import run_image_episode


CASES = (
    ("low_light", 327915747, "historical Phase 6B altitude-vz coupling timeout"),
    ("mixed", 404641207, "historical Phase 6B vertical-speed regression"),
    ("occlusion", 1033307971, "historical Phase 6C near-ground altitude-alias regression"),
    ("occlusion", 1488232361, "shared historical horizontal-speed failure"),
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay already-seen development cases against Phase 6G.")
    parser.add_argument("--calibration-seed", type=int, default=616161)
    parser.add_argument("--out", type=Path, default=Path("results/phase6g_known_cases"))
    args = parser.parse_args()

    temporal = fit_synthetic_calibrator(seed=args.calibration_seed, samples_per_condition=180)
    historical_component = fit_component_calibrator(seed=args.calibration_seed, samples_per_condition=280)
    phase6e_component = fit_phase6e_component_calibrator(seed=args.calibration_seed, samples_per_condition=300)
    gate = Phase6BComponentGateConfig(
        lateral_confidence_threshold=0.80,
        altitude_confidence_threshold=0.80,
    )

    rows: list[dict] = []
    for condition, seed, note in CASES:
        phase6 = run_image_episode(seed, condition, temporal, architecture="image_aegis_v3")
        phase6c = run_phase6c_episode(
            seed,
            condition,
            temporal,
            historical_component,
            component_gate_cfg=gate,
        )
        phase6g = run_phase6g_episode(
            seed,
            condition,
            temporal,
            phase6e_component,
            component_gate_cfg=gate,
        )
        for revision, result in (
            ("phase6", phase6),
            ("phase6c", phase6c),
            ("phase6g", phase6g),
        ):
            rows.append({
                "condition": condition,
                "seed": seed,
                "case_note": note,
                "revision": revision,
                "outcome": result.outcome,
                "success": result.success,
                "unsafe_touchdown": result.unsafe_touchdown,
                "aborted": result.aborted,
                "duration_s": result.duration_s,
                "final_x_error": result.final_x_error,
                "final_vx": result.final_vx,
                "final_vz": result.final_vz,
                "interventions": result.interventions,
                "lateral_reference_takeovers": getattr(result, "lateral_reference_takeovers", None),
                "altitude_reference_takeovers": getattr(result, "altitude_reference_takeovers", None),
                "mean_p_x_good": getattr(result, "mean_p_x_good", None),
                "mean_p_z_good": getattr(result, "mean_p_z_good", None),
            })

    df = pd.DataFrame(rows)
    args.out.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out / "diagnostic.csv", index=False)
    (args.out / "diagnostic.md").write_text(
        "# Phase 6G known-case development replay\n\n"
        "All episode seeds are already-seen development cases. This is not held-out validation. "
        "Phase 6G combines frozen Phase 6E perception with Phase 6C z-only altitude fallback.\n\n"
        + df.to_markdown(index=False)
        + "\n",
        encoding="utf-8",
    )
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
