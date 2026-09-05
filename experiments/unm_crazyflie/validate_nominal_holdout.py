#!/usr/bin/env python3
"""Evaluate frozen baseline fault-indicator thresholds on an unseen no-fault trajectory."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from analyze_extended import rolling_median, run_filter_diagnostics
from analyze_faults import load_baseline
from fault_indicator_metrics import alert_mask, event_window_false_alarm_rate

HOLDOUT_TURN_TIMES_S = np.array([6.0, 10.0, 14.5, 19.0, 24.0, 28.0])


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("baseline_csv", type=Path)
    ap.add_argument("holdout_csv", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--turn-window-s", type=float, default=0.5)
    args = ap.parse_args()

    baseline = load_baseline(args.baseline_csv)
    holdout = load_baseline(args.holdout_csv)

    if sha256(args.baseline_csv) == sha256(args.holdout_csv):
        raise SystemExit("holdout trajectory is identical to the calibration baseline")

    base_dt = float(np.median(np.diff(baseline.t)))
    hold_dt = float(np.median(np.diff(holdout.t)))
    base_window = max(3, int(round(0.5 / base_dt)))
    hold_window = max(3, int(round(0.5 / hold_dt)))
    persistence = max(1, int(round(0.1 / hold_dt)))

    # Freeze thresholds from the original nominal baseline only.
    _, _, baseline_nis, baseline_sigma = run_filter_diagnostics(baseline.t, baseline.xy.copy())
    baseline_roll = rolling_median(baseline_nis, base_window)
    baseline_armed = (baseline.t >= 5.0) & np.isfinite(baseline_roll)
    nis_threshold = float(np.max(baseline_roll[baseline_armed]) * 1.20)
    sigma_threshold = float(np.max(baseline_sigma[baseline.t >= 5.0]) * 1.50)

    # Evaluate the second trajectory without recalibrating either threshold.
    _, _, holdout_nis, holdout_sigma = run_filter_diagnostics(holdout.t, holdout.xy.copy())
    holdout_roll = rolling_median(holdout_nis, hold_window)
    armed = holdout.t >= 5.0

    residual_alerts = alert_mask(holdout_roll, nis_threshold, persistence) & armed
    sigma_alerts = alert_mask(holdout_sigma, sigma_threshold, persistence) & armed
    residual_eligible = armed & np.isfinite(holdout_roll)
    sigma_eligible = armed & np.isfinite(holdout_sigma)

    residual_count = int(np.count_nonzero(residual_alerts))
    sigma_count = int(np.count_nonzero(sigma_alerts))
    residual_samples = int(np.count_nonzero(residual_eligible))
    sigma_samples = int(np.count_nonzero(sigma_eligible))

    residual_turn_rate = event_window_false_alarm_rate(
        holdout.t,
        holdout_roll,
        nis_threshold,
        HOLDOUT_TURN_TIMES_S,
        args.turn_window_s,
        min_consecutive=persistence,
    )
    sigma_turn_rate = event_window_false_alarm_rate(
        holdout.t,
        holdout_sigma,
        sigma_threshold,
        HOLDOUT_TURN_TIMES_S,
        args.turn_window_s,
        min_consecutive=persistence,
    )

    def first_alert_s(mask: np.ndarray) -> float | None:
        idx = np.flatnonzero(mask)
        return float(holdout.t[idx[0]]) if len(idx) else None

    result = {
        "calibration_baseline_sha256": sha256(args.baseline_csv),
        "holdout_sha256": sha256(args.holdout_csv),
        "holdout_samples": int(len(holdout.t)),
        "holdout_duration_s": float(holdout.t[-1] - holdout.t[0]),
        "holdout_path_extent_m": float(np.linalg.norm(np.ptp(holdout.xy, axis=0))),
        "holdout_turn_times_s": HOLDOUT_TURN_TIMES_S.tolist(),
        "turn_window_s": args.turn_window_s,
        "persistence_samples": persistence,
        "nis_threshold_frozen": nis_threshold,
        "sigma_threshold_m_frozen": sigma_threshold,
        "residual_alert_samples": residual_count,
        "residual_eligible_samples": residual_samples,
        "residual_false_alarm_rate": residual_count / residual_samples if residual_samples else None,
        "residual_turn_window_false_alarm_rate": residual_turn_rate,
        "residual_first_alert_s": first_alert_s(residual_alerts),
        "holdout_max_rolling_median_nis": float(np.nanmax(holdout_roll[armed])),
        "sigma_alert_samples": sigma_count,
        "sigma_eligible_samples": sigma_samples,
        "sigma_false_alarm_rate": sigma_count / sigma_samples if sigma_samples else None,
        "sigma_turn_window_false_alarm_rate": sigma_turn_rate,
        "sigma_first_alert_s": first_alert_s(sigma_alerts),
        "holdout_max_radial_sigma_m": float(np.nanmax(holdout_sigma[armed])),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
