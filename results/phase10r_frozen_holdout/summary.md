# Phase 10R frozen holdout

- all preregistered gates passed: **False**
- truth-visible frames: **1,440**
- geometry trajectories: **12** (`36` sequence IDs across three appearances)
- candidate miss rate: **20.00%**
- false-positive rate: **0.00%**
- ambiguous lateral MAE / p95 improvement: **79.2% / -1.1%**
- ambiguous altitude MAE / p95 improvement: **73.7% / 7.3%**
- clean lateral / altitude MAE ratio vs Phase 9: **0.704× / 0.417×**
- 95% coverage: **84.3% lateral / 79.7% altitude**

The result is **mixed / failed overall** under the preregistered all-gates rule. Average ambiguous-view error improved strongly and clean geometry did not regress, but the candidate missed the availability, tail-error, and uncertainty-coverage gates under the harder domain shift.

No post-holdout retuning is part of this Phase 10R result.

Simulation-only frozen evidence. `safety_acceptance = false`; no physical-flight validation claim.
