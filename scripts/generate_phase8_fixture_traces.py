from __future__ import annotations

from pathlib import Path
import argparse

import numpy as np
import pandas as pd


def _fixture(*, external: bool, rows: int) -> pd.DataFrame:
    data: list[dict] = []
    scale = 1.22 if external else 1.0
    bias = 0.035 if external else 0.0
    for i in range(rows):
        t = 0.05 * i
        truth_x = 0.9 * np.exp(-0.012 * i) * np.cos(0.06 * i)
        truth_z = max(0.0, 5.0 - 0.028 * i)
        truth_vx = -0.055 * np.sin(0.06 * i)
        truth_vz = -0.56 if truth_z > 0.25 else -0.08

        image_error_x = scale * (0.045 * np.sin(0.20 * i) + 0.012 * np.cos(0.05 * i)) + bias
        reference_error_x = scale * (0.028 * np.sin(0.17 * i + 0.4)) + 0.25 * bias
        image_error_z = scale * 0.038 * np.cos(0.13 * i)
        reference_error_z = scale * 0.022 * np.sin(0.11 * i + 0.2)

        image_dropped = i % (29 if external else 31) == 9
        reference_available = i % (23 if external else 25) != 13
        reference_fresh = reference_available and i % (3 if external else 2) == 0

        data.append({
            "t_s": t,
            "truth_x_m": truth_x,
            "truth_z_m": truth_z,
            "truth_vx_mps": truth_vx,
            "truth_vz_mps": truth_vz,
            "image_x_m": truth_x + image_error_x,
            "image_z_m": truth_z + image_error_z,
            "image_vx_mps": truth_vx + scale * 0.018 * np.sin(0.14 * i),
            "image_vz_mps": truth_vz + scale * 0.025 * np.cos(0.10 * i),
            "image_confidence": max(0.05, min(0.99, 0.88 - 1.7 * abs(image_error_x))),
            "image_sigma_pos_m": 0.10 + 0.30 * abs(image_error_x),
            "image_dropped": image_dropped,
            "reference_x_m": truth_x + reference_error_x,
            "reference_z_m": truth_z + reference_error_z,
            "reference_vx_mps": truth_vx + scale * 0.010 * np.cos(0.08 * i),
            "reference_vz_mps": truth_vz + scale * 0.016 * np.sin(0.09 * i),
            "reference_sigma_pos_m": 0.12 + 0.22 * abs(reference_error_x),
            "reference_available": reference_available,
            "reference_fresh": reference_fresh,
            "image_transport_latency_s": (0.018 if external else 0.015) + 0.002 * (i % 3),
            "reference_transport_latency_s": (0.060 if external else 0.048) + 0.01 * (i % 4),
            "reference_state_age_s": 0.05 * (i % (4 if external else 3)),
            "reference_delivery": reference_fresh,
        })
    return pd.DataFrame(data)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate deterministic non-authoritative traces used only to exercise the Phase 8 pipeline."
    )
    parser.add_argument("--out", type=Path, default=Path("results/phase8_fixture_inputs"))
    parser.add_argument("--rows", type=int, default=160)
    args = parser.parse_args()
    if args.rows < 40:
        raise SystemExit("Use at least 40 rows so distribution diagnostics have meaningful fixture coverage.")

    args.out.mkdir(parents=True, exist_ok=True)
    surrogate = args.out / "phase7_surrogate_fixture.csv"
    external = args.out / "external_simulator_fixture.csv"
    _fixture(external=False, rows=args.rows).to_csv(surrogate, index=False)
    _fixture(external=True, rows=args.rows).to_csv(external, index=False)
    print(f"Wrote non-authoritative fixture traces to {args.out.resolve()}")


if __name__ == "__main__":
    main()
