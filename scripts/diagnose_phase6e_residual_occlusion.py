from __future__ import annotations

from pathlib import Path
import argparse
import json

import numpy as np

from uav_safety.image_temporal import Phase6LandingPadRenderer, _largest_component
from uav_safety.phase6e_perception import Phase6ERobustPadEstimator, fit_phase6e_component_calibrator
from uav_safety.selective_confidence_v2 import (
    SharpnessAwarePadEstimator,
    altitude_observability_cap,
    altitude_scale_bin_width_m,
)


TRUE_X = -0.723186
TRUE_Z = 6.0
FRAME_SEED = 944050995
CONDITION = "occlusion"


def segmentation_stats(image: np.ndarray) -> dict:
    median = float(np.median(image))
    p30 = float(np.percentile(image, 30))
    p90 = float(np.percentile(image, 90))
    std = float(np.std(image))
    background = p30 if median > 0.5 * p90 else median
    threshold = max(background + 1.05 * std, 0.58 * p90 + 0.42 * background)
    mask = image > threshold
    component = _largest_component(mask)
    return {
        "median": median,
        "p30": p30,
        "p90": p90,
        "std": std,
        "phase6e_background": background,
        "phase6e_threshold": float(threshold),
        "threshold_foreground_pixels": int(mask.sum()),
        "largest_component_pixels": len(component),
    }


def measurement_payload(name: str, measurement, calibrator) -> dict:
    learned_x, learned_z = calibrator.learned_probabilities(measurement)
    final_x, final_z = calibrator.probabilities(measurement)
    return {
        "revision": name,
        "valid": bool(measurement.valid),
        "measured_x_m": float(measurement.x_m),
        "measured_z_m": float(measurement.z_m),
        "abs_x_error_m": float(abs(measurement.x_m - TRUE_X)),
        "abs_z_error_m": float(abs(measurement.z_m - TRUE_Z)),
        "bbox_width_px": int(measurement.bbox_width_px),
        "selected_pixels": int(measurement.selected_pixels),
        "raw_confidence": float(measurement.raw_confidence),
        "geometry_score": float(measurement.geometry_score),
        "contrast": float(measurement.contrast),
        "sharpness_score": float(measurement.sharpness_score),
        "altitude_scale_bin_width_m": float(altitude_scale_bin_width_m(measurement)),
        "altitude_observability_cap": float(altitude_observability_cap(measurement, 0.85)),
        "learned_p_x_good": float(learned_x),
        "learned_p_z_good": float(learned_z),
        "final_p_x_good": float(final_x),
        "final_p_z_good": float(final_z),
        "selected_at_080": bool(final_z >= 0.80),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Perception-only diagnosis of the one selected-bad Phase 6E occlusion frame.")
    parser.add_argument("--calibration-seed", type=int, default=616161)
    parser.add_argument("--out", type=Path, default=Path("results/phase6e_residual_occlusion"))
    args = parser.parse_args()

    renderer = Phase6LandingPadRenderer()
    frame = renderer.render(
        x_offset_m=TRUE_X,
        altitude_m=TRUE_Z,
        rng=np.random.default_rng(FRAME_SEED),
        condition=CONDITION,
        severity=1.0,
    )
    historical = SharpnessAwarePadEstimator().estimate(frame)
    candidate = Phase6ERobustPadEstimator().estimate(frame)
    calibrator = fit_phase6e_component_calibrator(seed=args.calibration_seed, samples_per_condition=300)

    payload = {
        "scope": "static synthetic image only",
        "source": "single selected-bad frame from Phase 6E perception validation seed 697431",
        "condition": CONDITION,
        "true_x_m": TRUE_X,
        "true_z_m": TRUE_Z,
        "frame_seed": FRAME_SEED,
        "renderer_half_bin_from_truth": int(np.clip(35.0 / (TRUE_Z + 0.60), 4, int(0.46 * frame.shape[1]))),
        "segmentation": segmentation_stats(frame),
        "phase6": measurement_payload("phase6", historical, calibrator),
        "phase6e": measurement_payload("phase6e", candidate, calibrator),
        "replacement_reserved_unseen_seeds_not_used": [918271, 928271],
    }

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "diagnostic.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (args.out / "diagnostic.md").write_text(
        "# Phase 6E residual occlusion confidence diagnostic\n\n"
        "Static development frame only; no landing controller or held-out seed.\n\n"
        "```json\n" + json.dumps(payload, indent=2) + "\n```\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
