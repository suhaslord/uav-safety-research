#!/usr/bin/env python3
import csv
import tempfile
from pathlib import Path
import numpy as np
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_faults as a


def make_baseline(path: Path):
    t = np.arange(0.0, 32.0, 0.05)
    x = np.zeros_like(t)
    y = np.zeros_like(t)
    x += np.where((t >= 5) & (t < 10), (t - 5) * 0.25, 0.0)
    x += np.where(t >= 10, 1.25, 0.0)
    y += np.where((t >= 10) & (t < 15), (t - 10) * 0.25, 0.0)
    y += np.where(t >= 15, 1.25, 0.0)
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["time_s", "x_m", "y_m"])
        for ti, xi, yi in zip(t, x, y):
            w.writerow([ti, xi, yi])


def main():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "baseline.csv"
        make_baseline(p)
        b = a.load_baseline(p)
        assert len(b.t) > 100
        assert b.source_sha256

        nominal = a.run_filter(b.t, b.xy.copy())
        assert np.isfinite(nominal).all()

        noised = a.inject_noise(b.xy, 0.08, a.BASE_SEED)
        noised2 = a.inject_noise(b.xy, 0.08, a.BASE_SEED)
        assert np.allclose(noised, noised2)

        biased, end = a.inject_bias(b.t, b.xy, 0.2)
        assert np.isclose(np.max(np.abs(biased[:, 0] - b.xy[:, 0])), 0.2)
        assert end == a.FAULT_START_S + 4.0

        dropped, end = a.inject_dropout(b.t, b.xy, 2.0)
        mask = (b.t >= a.FAULT_START_S) & (b.t < a.FAULT_START_S + 2.0)
        assert np.isnan(dropped[mask]).all()

    print("UNM_TESTS_PASSED")


if __name__ == "__main__":
    main()
