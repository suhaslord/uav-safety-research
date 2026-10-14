# Conservative detector replication — second random seed

**Existing detector work; no numbered research phase. Pre-specified before inference.**

The initial, equal-optimizer-budget photometric training comparison (seed
20261013; 12 epochs, 15% replacements, blur/low-light/noise only) passed an
exploratory development screen, but also showed nontrivial noise/occlusion
regressions. See
[`detector_robustness_photometric_results_20261013.md`](detector_robustness_photometric_results_20261013.md).

## Single planned intervention

Repeat the **same paired experiment** with random seed **20261014** for
training and generation. Keep the same SHA-verified 252-image development
train and original 64-image validation splits; the same pretrained YOLO11n
initialization, optimizer, 12 epochs, 320-pixel resolution, batch 16,
photometric-only set, **15% in-place replacements**, five development stress
conditions, and pre-recorded five-part development screen.

No model architecture change, test-data access, post-hoc threshold tuning,
camera/control instructions, or weight promotion.

The second seed may change the subset and noise/blur magnitude of augmented
training views and change stochastic SGD trajectories. It **does not create
new independent source videos or an independent generalization result**.
This is an exploratory reproducibility check on the existing two KIOS videos.

Report both outcomes **even if the second run fails the screen**. Do not
select a favorite seed as evidence of external validity. If either seed
shows a clean/stress regression, maintain the original frozen model and
prioritize genuinely independent, labeled, provenance-documented capture
sessions through the existing admission gate. New experimental results are
informational only and not a deployment/safety claim.
