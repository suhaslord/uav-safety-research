from __future__ import annotations

import argparse
import csv
from pathlib import Path
import numpy as np

from analyze_extended import rolling_median, run_filter_diagnostics
from analyze_faults import BASE_SEED, load_baseline
from fault_indicator_metrics import evaluate_indicator, summarize


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("baseline_csv", type=Path)
    ap.add_argument("--out", type=Path, default=Path("fault_indicator_validation.csv"))
    ap.add_argument("--seeds", type=int, default=30)
    args = ap.parse_args()

    baseline = load_baseline(args.baseline_csv)
    t, truth = baseline.t, baseline.xy
    dt = float(np.median(np.diff(t)))
    window = max(3, int(round(0.5 / dt)))

    _, _, nominal_nis, nominal_sigma = run_filter_diagnostics(t, truth.copy())
    nominal_roll = rolling_median(nominal_nis, window)
    steady = (t >= 5.0) & np.isfinite(nominal_roll)
    nis_threshold = float(np.max(nominal_roll[steady]) * 1.20)
    sigma_threshold = float(np.max(nominal_sigma[t >= 5.0]) * 1.50)

    cases = [
        ("noise", 0.08), ("noise", 0.16), ("noise", 0.32),
        ("bias", 0.10), ("bias", 0.20), ("bias", 0.40),
        ("dropout", 0.5), ("dropout", 1.0), ("dropout", 2.0), ("dropout", 4.0),
    ]

    rows = []
    for fault_type, severity in cases:
        trial_metrics = []
        for seed in range(args.seeds):
            rng = np.random.default_rng(BASE_SEED + seed)
            measurements = truth.copy()
            if fault_type == "noise":
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
                    min_consecutive=max(1, int(round(0.1 / dt))),
                )
            )

        summary = summarize(trial_metrics)
        rows.append({
            "fault_type": fault_type,
            "severity": severity,
            "indicator": "radial_sigma" if fault_type == "dropout" else "rolling_median_nis",
            "threshold": sigma_threshold if fault_type == "dropout" else nis_threshold,
            **summary,
        })

    with args.out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    for row in rows:
        print(row)


if __name__ == "__main__":
    main()
