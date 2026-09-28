from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import run_phase13c_compound_attribution as p13c


def test_noise_only_accepts_pandas_slices_under_current_numpy_stack():
    n = 8
    df = pd.DataFrame(
        {
            "sequence_id": ["maintenance-seq"] * n,
            "frame_index": np.arange(n),
            "p14_estimate_lateral_x_m": np.linspace(-0.1, 0.1, n),
            "p14_estimate_altitude_m": np.linspace(0.0, 0.2, n),
            "p14_available": [True] * n,
            "truth_visible": [True] * n,
            "truth_lateral_x_m": np.zeros(n),
            "truth_altitude_m": np.zeros(n),
            "p9_anchor_innovation_lateral_abs": np.linspace(0.1, 0.8, n),
            "severity": np.linspace(0.1, 0.8, n),
        }
    )

    out = p13c._apply_component_subset(
        df,
        "noise_only",
        p13c.CONTRAST_COMPONENTS["noise_only"],
        p13c.STAGE_SEEDS["dev"],
    )

    assert len(out) == n
    assert np.array_equal(out["truth_visible"].to_numpy(bool), df["truth_visible"].to_numpy(bool))
    assert np.array_equal(out["p14_available"].to_numpy(bool), df["p14_available"].to_numpy(bool))
    assert np.all(np.isfinite(out["p14_estimate_lateral_x_m"].to_numpy(float)))
    assert np.all(np.isfinite(out["p14_estimate_altitude_m"].to_numpy(float)))
