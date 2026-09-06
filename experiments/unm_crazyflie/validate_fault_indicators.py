from __future__ import annotations

import argparse
import csv
from pathlib import Path
import numpy as np

from analyze_extended import TURN_TIMES_S, rolling_median, run_filter_diagnostics
from analyze_faults import BASE_SEED, load_baseline
from fault_indicator_metrics import (
    evaluate_indicator,
    event_window_false_alarm_rate,
    summarize,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("baseline_csv", type=Path)
    ap.add_argument("--out", type=Path, default=Path("fault_indicator_validation.csv"))
    ap.add_argument(
        "--seeds",
        type=int,
        default=30,
        help="number of randomized trials for Gaussian-noise cases",
    )
    ap.add_argument("--turn-window-s", type=float, default=0.5)
    args = ap.parse_args()
    if args.seeds < 1:
        ap.error("--seeds must be at least 1")

    baseline = load_baseline(args.baseline_csv)
    t, truth = baseline.t, baseline.xy
    dt = float(np.median(np.diff(t)))
    window = max(3, int(round(0.5 / dt)))
    persistence = max(1, int(round(0.1 / dt)))
    armed = t >= 5.0

    _, _, nominal_nis, nominal_sigma = run_filter_diagnostics(t, truth.copy())
    nominal_roll = rolling_median(nominal_nis, window)
    steady = armed & np.isfinite(nominal_roll)
    nis_threshold = float(np.max(nominal_roll[steady]) * 1.20)
    sigma_threshold = float(np.max(nominal_sigma[armed]) * 1.50)

    cases = [
        ("noise", 0.04), ("noise", 0.08), ("noise", 0.16), ("noise", 0.32),
        ("bias", 0.05), ("bias", 0.10), ("bias", 0.20), ("bias", 0.40),
        ("dropout", 0.5), ("dropout", 1.0), ("dropout", 2.0), ("dropout", 4.0),
    ]

    rows = []
    for fault_type, severity in cases:
        trial_metrics = []
        turn_false_alarm_rates = []
        # Bias and dropout injections are deterministic in this experiment.
        # Repeating them with different seed labels would duplicate identical
        # evidence, so only the stochastic noise cases use the seed sweep.
        n_trials = args.seeds if fault_type == "noise" else 1
        for seed in range(n_trials):
            measurements = truth.copy()
            if fault_type == "noise":
                rng = np.random.default_rng(BASE_SEED + seed)
                fault_mask = (t >= 12.0) & (t < 16.0)
                measurements[fault_mask] += rng.normal(0.0, severity, size=(fault_mask.sum(), 2))
            elif fault_type == "bias":
                fault_mask = (t >= 12.0) & (t < 16.0)
                measurements[fault_mask, 0] += severity
            else:
                fault_mask = (t >= 12.0) & (t < 12.0 + severity)
                measurements[fault_mask] = np.nan

            _, _, nis, sigma = run_filter_diagnostics(t, measurements)
            if fault_type == "dropout":
                indicator, threshold = sigma, sigma_threshold
            else:
                indicator, threshold = rolling_median(nis, window), nis_threshold

            trial_metrics.append(
                evaluate_indicator(
                    t,
                    indicator,
                    fault_mask,
                    threshold,
                    min_consecutive=persistence,
                    evaluation_mask=armed,
                )
            )
            turn_false_alarm_rates.append(
                event_window_false_alarm_rate(
                    t,
                    indicator,
                    threshold,
                    TURN_TIMES_S,
                    args.turn_window_s,
                    exclude_mask=fault_mask,
                    min_consecutive=persistence,
                )
            )

        summary = summarize(trial_metrics)
        finite_turn_rates = np.asarray(turn_false_alarm_rates, dtype=float)
        finite_turn_rates = finite_turn_rates[np.isfinite(finite_turn_rates)]
        rows.append({
            "fault_type": fault_type,
            "severity": severity,
            "indicator": "radial_sigma" if fault_type == "dropout" else "rolling_median_nis",
            "threshold": sigma_threshold if fault_type == "dropout" else nis_threshold,
            **summary,
            "mean_turn_window_false_alarm_rate": (
                float(np.mean(finite_turn_rates)) if len(finite_turn_rates) else float("nan")
            ),
        })

    with args.out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    for row in rows:
        print(row)


if __name__ == "__main__":
    main()
