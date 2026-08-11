from __future__ import annotations

from pathlib import Path
import argparse
import json

import pandas as pd

from uav_safety.external_trace import validate_external_trace
from uav_safety.image_temporal import fit_synthetic_calibrator
from uav_safety.selective_confidence_v2 import fit_component_calibrator
import uav_safety.simulator_phase7 as sim7


FROZEN_PHASE8_HEAD = "bd62e3b31431306fd9d897f560be7325d711d21a"


def capture_trace(seed: int, calibration_seed: int, condition: str) -> tuple[pd.DataFrame, dict]:
    temporal = fit_synthetic_calibrator(seed=calibration_seed, samples_per_condition=60)
    component = fit_component_calibrator(seed=calibration_seed, samples_per_condition=120)

    rows: list[dict] = []
    pending: dict = {}
    original_observe = sim7.Phase7SensorStackReferenceEstimator.observe
    original_fusion_update = sim7.Phase6BComponentFusionAdapter.update
    original_step = sim7.step_phase7_dynamics

    def wrapped_observe(self, state, fault=None):
        obs, diag = original_observe(self, state, fault)
        pending["ref_diag"] = diag
        return obs, diag

    def wrapped_fusion_update(self, image_obs, ref_obs, **kwargs):
        pending["image_obs"] = image_obs
        pending["ref_obs"] = ref_obs
        return original_fusion_update(self, image_obs, ref_obs, **kwargs)

    def wrapped_step(state, memory, ax_cmd, az_cmd, wind_ax, wind_az, rng, sim_cfg, dyn_cfg=None):
        image = pending.get("image_obs")
        ref = pending.get("ref_obs")
        diag = pending.get("ref_diag")
        if image is not None and ref is not None and diag is not None:
            rows.append({
                "t_s": len(rows) * float(sim_cfg.dt),
                "truth_x_m": float(state.x),
                "truth_z_m": float(state.z),
                "truth_vx_mps": float(state.vx),
                "truth_vz_mps": float(state.vz),
                "image_x_m": float(image.x),
                "image_z_m": float(image.z),
                "image_vx_mps": float(image.vx),
                "image_vz_mps": float(image.vz),
                "image_confidence": float(image.confidence),
                "image_sigma_pos_m": float(image.sigma_pos),
                "image_dropped": bool(image.dropped),
                "reference_x_m": float(ref.x),
                "reference_z_m": float(ref.z),
                "reference_vx_mps": float(ref.vx),
                "reference_vz_mps": float(ref.vz),
                "reference_sigma_pos_m": float(ref.sigma_pos),
                "reference_available": bool(ref.available),
                "reference_fresh": bool(ref.fresh),
            })
        return original_step(state, memory, ax_cmd, az_cmd, wind_ax, wind_az, rng, sim_cfg, dyn_cfg)

    sim7.Phase7SensorStackReferenceEstimator.observe = wrapped_observe
    sim7.Phase6BComponentFusionAdapter.update = wrapped_fusion_update
    sim7.step_phase7_dynamics = wrapped_step
    try:
        result = sim7.run_phase7_episode(
            seed,
            condition,
            temporal,
            component,
            fault_scenario="independent",
            plant_model="phase7",
        )
    finally:
        sim7.Phase7SensorStackReferenceEstimator.observe = original_observe
        sim7.Phase6BComponentFusionAdapter.update = original_fusion_update
        sim7.step_phase7_dynamics = original_step

    if len(rows) < 2:
        raise RuntimeError("Phase 7 episode did not produce enough trace rows")
    frame, validation = validate_external_trace(pd.DataFrame(rows))
    metadata = {
        "source": "frozen Phase 7 simulator",
        "frozen_phase8_head": FROZEN_PHASE8_HEAD,
        "episode_seed": seed,
        "calibration_seed": calibration_seed,
        "condition": condition,
        "fault_scenario": "independent",
        "plant_model": "phase7",
        "capture_method": "read-only monkeypatch hooks around the frozen run_phase7_episode execution; controller/fusion/supervisor/dynamics code unchanged",
        "episode_result": result.to_dict(),
        "validation": validation.to_dict(),
    }
    return frame, metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Export an actual frozen Phase 7 episode into the Phase 8 shared trace schema without modifying Phase 7 core code.")
    parser.add_argument("--seed", type=int, default=979797)
    parser.add_argument("--calibration-seed", type=int, default=616161)
    parser.add_argument("--condition", default="clean")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--metadata-out", type=Path, required=True)
    args = parser.parse_args()

    frame, metadata = capture_trace(args.seed, args.calibration_seed, args.condition)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.out, index=False)
    args.metadata_out.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(frame), "duration_s": float(frame["t_s"].iloc[-1]), "out": str(args.out)}, indent=2))


if __name__ == "__main__":
    main()
