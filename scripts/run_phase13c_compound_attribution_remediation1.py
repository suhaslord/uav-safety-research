from __future__ import annotations

"""Execution-only remediation for Phase 13C before any evidence exposure.

Run 34009501311 stopped in pre-evidence tests because pandas returned read-only
NumPy views for two sliced estimate columns used by the noise component. No
candidate was recovered and seed 1313135 was never generated or scored.

This module changes only array mutability: the two sliced estimate arrays are
copied before in-place noise addition. The preregistered contrasts, component
magnitudes, random streams, candidate, seed, gates, and evidence partitions are
unchanged.
"""

import numpy as np
import pandas as pd

try:
    from scripts import run_phase13c_compound_attribution as p13c
except ModuleNotFoundError:
    import run_phase13c_compound_attribution as p13c


PRE_EVIDENCE_FAILED_RUN_ID = 34009501311
UNCHANGED_DEV_SEED = 1313135


def _execution_safe_apply_component_subset(
    df: pd.DataFrame,
    contrast_name: str,
    components: frozenset[str],
    seed: int,
) -> pd.DataFrame:
    if components == frozenset(p13c.COMPONENTS):
        out = p13c.p13.apply_shift(df, p13c.ORIGINAL_COMPOUND_NAME, seed)
        out["phase13c_contrast"] = contrast_name
        out["phase13c_components"] = "+".join(p13c.COMPONENTS)
        return out

    unknown = set(components).difference(p13c.COMPONENTS)
    if unknown:
        raise RuntimeError(f"unknown Phase 13C component(s): {sorted(unknown)}")

    out = df.copy(deep=True)
    out["phase13c_contrast"] = contrast_name
    out["phase13c_components"] = "+".join(sorted(components))
    out["phase13_domain"] = p13c.ORIGINAL_COMPOUND_NAME
    out["phase13_domain_category"] = "compound"
    out["phase13_base_domain"] = p13c.BASE_DOMAIN
    out["phase13_shift_applied"] = bool(components)
    out["sequence_id"] = out["sequence_id"].astype(str) + f"|phase13c:{contrast_name}"

    original_lat = out["p14_estimate_lateral_x_m"].to_numpy(float).copy()
    original_alt = out["p14_estimate_altitude_m"].to_numpy(float).copy()

    for _, idx_obj in out.groupby("sequence_id", sort=False).groups.items():
        idx = list(idx_obj)
        frames = out.loc[idx, "frame_index"].to_numpy(int)

        # Execution-only fix: pandas may expose these sliced arrays as read-only.
        # Explicit copies preserve values exactly while permitting the already-
        # preregistered in-place deterministic noise addition below.
        lat = out.loc[idx, "p14_estimate_lateral_x_m"].to_numpy(float).copy()
        alt = out.loc[idx, "p14_estimate_altitude_m"].to_numpy(float).copy()

        if "A" in components:
            lag = np.full(len(idx), 2, dtype=int)
            lat = p13c.p13._lagged(lat, lag)
            alt = p13c.p13._lagged(alt, lag)

        if "B" in components:
            lat = lat + 0.04
            alt = alt + 0.08

        if "C" in components:
            t = frames / max(1.0, float(np.max(frames) or 1))
            lat = lat + 0.07 * (2.0 * t - 1.0)

        if "D" in components:
            seq_for_stream = str(out.loc[idx[0], "sequence_id"])
            seq_for_stream = seq_for_stream.split("|phase13c:", 1)[0]
            for j, frame in enumerate(frames):
                rng = p13c._noise_rng(seed, seq_for_stream, int(frame))
                lat[j] += float(rng.normal(0.0, 0.02))
                alt[j] += float(rng.normal(0.0, 0.04))

        out.loc[idx, "p14_estimate_lateral_x_m"] = lat
        out.loc[idx, "p14_estimate_altitude_m"] = alt

    available = out["p14_available"].astype(bool) & out["truth_visible"].astype(bool)
    out.loc[~available, "p14_estimate_lateral_x_m"] = np.nan
    out.loc[~available, "p14_estimate_altitude_m"] = np.nan

    out["p14_lateral_abs_error_m"] = np.abs(
        out["p14_estimate_lateral_x_m"].to_numpy(float)
        - out["truth_lateral_x_m"].to_numpy(float)
    )
    out["p14_altitude_abs_error_m"] = np.abs(
        out["p14_estimate_altitude_m"].to_numpy(float)
        - out["truth_altitude_m"].to_numpy(float)
    )

    lat_delta = np.abs(out["p14_estimate_lateral_x_m"].to_numpy(float) - original_lat)
    alt_delta = np.abs(out["p14_estimate_altitude_m"].to_numpy(float) - original_alt)

    if "E" in components:
        innovation = out["p9_anchor_innovation_lateral_abs"].to_numpy(float)
        if not np.all(np.isfinite(innovation)) or np.any(innovation < 0.0):
            raise RuntimeError("Phase 13C requires finite nonnegative anchor innovation")
        out["p9_anchor_innovation_lateral_abs"] = np.maximum(
            0.0,
            innovation * 1.35 + 0.45 * np.nan_to_num(lat_delta, nan=0.0),
        )

    if "F" in components:
        severity = out["severity"].to_numpy(float)
        if not np.all(np.isfinite(severity)):
            raise RuntimeError("Phase 13C requires finite severity")
        response = np.clip(
            (
                np.nan_to_num(lat_delta, nan=0.0)
                + 0.5 * np.nan_to_num(alt_delta, nan=0.0)
            )
            / 0.30,
            0.0,
            1.0,
        )
        out["severity"] = np.clip(severity + 0.12 + 0.18 * response, 0.0, 1.0)

    return out


def install_execution_remediation() -> None:
    if int(p13c.STAGE_SEEDS["dev"]) != UNCHANGED_DEV_SEED:
        raise RuntimeError("unexpected Phase 13C development seed")
    p13c._apply_component_subset = _execution_safe_apply_component_subset


if __name__ == "__main__":
    install_execution_remediation()
    p13c.main()
