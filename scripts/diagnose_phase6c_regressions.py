from __future__ import annotations

from pathlib import Path
import argparse

import pandas as pd

from uav_safety.image_temporal import fit_synthetic_calibrator
from uav_safety.phase6b_fusion import Phase6BComponentGateConfig
from uav_safety.selective_confidence_v2 import fit_component_calibrator
from uav_safety.simulator_image_phase6b import run_phase6b_episode
from uav_safety.simulator_image_phase6c import run_phase6c_episode
from uav_safety.simulator_image_v3 import run_image_episode


CASES = (
    ("low_light", 327915747, "Phase 6B timeout regression"),
    ("mixed", 404641207, "Phase 6B vertical-speed regression"),
    ("occlusion", 1488232361, "Shared Phase 6/6B horizontal-speed failure"),
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay already-seen Phase 6B regression episodes against Phase 6C.")
    parser.add_argument("--calibration-seed", type=int, default=616161)
    parser.add_argument("--temporal-calibration-samples", type=int, default=180)
    parser.add_argument("--component-calibration-samples", type=int, default=280)
    parser.add_argument("--out", type=Path, default=Path("results/phase6c_regression_diagnostic"))
    args = parser.parse_args()

    temporal = fit_synthetic_calibrator(
        seed=args.calibration_seed,
        samples_per_condition=args.temporal_calibration_samples,
    )
    component = fit_component_calibrator(
        seed=args.calibration_seed,
        samples_per_condition=args.component_calibration_samples,
    )
    gate = Phase6BComponentGateConfig(
        lateral_confidence_threshold=0.80,
        altitude_confidence_threshold=0.80,
    )

    rows: list[dict] = []
    for condition, seed, note in CASES:
        phase6 = run_image_episode(
            seed,
            condition,
            temporal,
            architecture="image_aegis_v3",
        )
        phase6b = run_phase6b_episode(
            seed,
            condition,
            temporal,
            component,
            component_gate_cfg=gate,
        )
        phase6c = run_phase6c_episode(
            seed,
            condition,
            temporal,
            component,
            component_gate_cfg=gate,
        )

        for revision, result in (
            ("phase6", phase6),
            ("phase6b", phase6b),
            ("phase6c", phase6c),
        ):
            row = {
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
            }
            for name in (
                "lateral_component_abstentions",
                "altitude_component_abstentions",
                "lateral_reference_takeovers",
                "altitude_reference_takeovers",
                "unresolved_component_frames",
                "mean_p_x_good",
                "mean_p_z_good",
            ):
                row[name] = getattr(result, name, None)
            rows.append(row)

    df = pd.DataFrame(rows)
    args.out.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out / "diagnostic.csv", index=False)
    (args.out / "diagnostic.md").write_text(
        "# Phase 6C targeted regression diagnostic\n\n"
        "These are already-seen development episode seeds. This diagnostic is not a held-out evaluation. "
        "Phase 6C differs from Phase 6B only by preserving the established Phase 6 vertical-rate estimate during altitude-only fallback.\n\n"
        + df.to_markdown(index=False)
        + "\n",
        encoding="utf-8",
    )

    print(df.to_string(index=False))
    print(f"\nSaved diagnostic to {args.out.resolve()}")


if __name__ == "__main__":
    main()
