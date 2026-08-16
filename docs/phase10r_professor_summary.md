# Phase 10R — compact research summary

AegisLand Phase 10R tested whether causal edge/partial-view recovery could improve visual landing-target geometry without sacrificing clean observations or calibrated uncertainty. The candidate was selected using new development/validation evidence, frozen at commit `e1d566f8baa47bf10f9bdf39dd5988724208be80`, and then evaluated once on a protected simulation holdout with 12 new geometry trajectories, three appearance conditions, 36 sequences, and 1,440 truth-visible frames.

The final result was mixed / failed overall under the preregistered all-gates rule. Average ambiguous-view error improved substantially: lateral MAE improved **79.2%** and altitude MAE improved **73.7%** versus the unchanged Phase 9 baseline. Clean-observation MAE also improved rather than regressing, and false positives remained **0%**. However, difficult-tail performance did not transfer: lateral p95 changed by **−1.1%** and altitude p95 by only **7.3%**, below the preregistered ≥25% target. The candidate also missed **20.0%** of truth-visible frames.

The most important finding was uncertainty transfer. The same development-frozen calibration that produced about **94.1% / 94.1%** 95% coverage on the earlier validation domain achieved only **84.3% lateral / 79.7% altitude** coverage on the harder protected holdout. This provides a concrete example where average point-estimate accuracy can improve while the system becomes overconfident under distribution shift.

The result is frozen without post-holdout retuning. It motivates Phase 11: testing domain-shift-aware reliability, context-conditioned/conformal uncertainty, and principled abstention while preserving useful perception availability.

Scope: simulation only; `safety_acceptance = false`; no physical-flight or certification claim.
