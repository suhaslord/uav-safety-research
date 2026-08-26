#!/usr/bin/env python3
import numpy as np

from analyze_mitigation import run_filter


def main():
    t = np.linspace(0.0, 10.0, 501)
    truth = np.column_stack((0.2 * t, np.zeros_like(t)))
    nominal = truth.copy()
    large_bias = truth.copy()
    large_bias[(t >= 4.0) & (t < 7.0), 0] += 0.8

    baseline = run_filter(t, large_bias, "baseline")
    reject = run_filter(t, large_bias, "reject")
    downweight = run_filter(t, large_bias, "downweight")

    assert reject.alerts > 0 and reject.rejected > 0
    assert downweight.alerts > 0 and downweight.downweighted > 0
    for result in (baseline, reject, downweight):
        assert np.isfinite(result.estimate).all()

    for strategy in ("baseline", "reject", "downweight"):
        result = run_filter(t, nominal, strategy)
        assert np.isfinite(result.estimate).all()

    print("mitigation logic tests: PASS")


if __name__ == "__main__":
    main()
