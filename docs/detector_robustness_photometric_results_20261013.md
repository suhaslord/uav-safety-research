# AegisLand detector — conservative photometric training results

**Research date:** 2026-10-13 PT (workflow executed 2026-10-14 UTC)  
**Scope:** Existing detector robustness work. **No new numbered phase.**  
**Decision:** **Development screen passed; candidate kept for research only. Published/frozen detector is NOT replaced.**

The complete 12-epoch, matched-update baseline-versus-candidate run
[38513371676](https://github.com/suhaslord/uav-safety-research/actions/runs/38513371676)
finished **success**. Artifact **11871186257**
(`detector-conservative-photometric-dev-pilot`) contains the exact
`comparison.json`, data-build receipt, training CSVs, and both weight files.

All code CI checks on the experimental PR passed:
[38513371674](https://github.com/suhaslord/uav-safety-research/actions/runs/38513371674)
and [38513355985](https://github.com/suhaslord/uav-safety-research/actions/runs/38513355985).
[PR #206](https://github.com/suhaslord/uav-safety-research/pull/206)
merged the code and reproducibility tests.

## Controlled experiment

- Dataset: historical SHA-locked KIOS 2024 **real-video development split** only (same two source videos); 252 original train frames and 64 untouched development-validation frames. The separate **86 protected test frames were not used**.
- Architecture/initialization: independently initialized YOLO11n from the same pretrained weights; image size 320; SGD; fixed seed 20261013; batch 16; **12 epochs**, with equal training-image count and equal optimizer-step budget.
- Candidate training: 214 byte-preserved originals and 38 *in-place* photometric-only replacements (13 blur, 13 low light, 12 noise). The baseline uses all 252 originals. No extra examples or mask-based/occlusion training; labels and source filenames preserved.
- Evaluation: six correlated development conditions, clean plus independently generated blur, low light, noise, partial occlusion and mixed views. **Same 64 development frames in every condition**, not 384 independent scenes; there are no certified absent-pad examples.

## Actual development-validation results

Precision/recall/mAP are Ultralytics object-detection validation aggregates.
**mAP50 is not a safe-landing probability.**

| Condition | Baseline mAP50 | Candidate mAP50 | Delta | Baseline recall | Candidate recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| Clean | 0.50881 | 0.51815 | **+0.00934** | 0.45313 | 0.40625 |
| Blur | 0.44614 | 0.42636 | **−0.01977** | 0.42188 | 0.30068 |
| Low light | 0.43823 | 0.47701 | **+0.03877** | 0.37500 | 0.32813 |
| Noise | 0.44131 | 0.37599 | **−0.06533** | 0.37500 | 0.29688 |
| Partial occlusion | 0.51604 | 0.48998 | **−0.02607** | 0.43750 | 0.40549 |
| Mixed | 0.16829 | 0.29526 | **+0.12697** | 0.18750 | 0.28125 |

Clean precision improved from **0.65555** to **0.69896**, and clean
mAP50–95 improved from **0.25482** to **0.26338**, but clean recall declined
by **0.04688**. The candidate is substantially better in mixed mAP50
(0.16829 → 0.29526), while noise and occlusion mAP50 get worse.

The equal-condition (descriptive, correlated) mAP50 delta is **+0.01065**.
The five pre-recorded development-screen gates all **passed**, including
clean mAP50 drop ≤0.005, clean precision drop ≤0.05, blur/mixed declines
≤0.02 and mean condition mAP50 gain ≥0.01.

## Authenticity and reproducibility

- Source split manifest SHA-256: `32623634069c4f3082b79a6a42bca408c636f4b626e5f7691276257999544905`
- Candidate augmentation receipt SHA-256: `7b05f9b190f8ed42fb96b99195d75d8aeba4008dd436163adf08bb075a16b826`
- Twelve-epoch baseline checkpoint `best.pt`: `aac1dd16dcef57ea39b2bb69252cbc690f33b32ab3a476afab331748ebc99661`
- Twelve-epoch photometric candidate checkpoint `best.pt`: `9dd08804d61809d6ab1e8c973d64a50ccde2a4ea9a91e5b8cb9d96e570d87050`
- The two weight hashes above were independently rechecked against the downloaded artifact bytes.

**Hard evidence limit:** `protected_test_evaluated: false`,
`independent_validation: false`, `automatic_model_promotion: false`,
`model_improvement_established: false`. The run did not train/test on
independent camera sessions or negative-target frames, and the historical
86 protected KIOS test frames cannot be used to select this new variant.

## Interpretation and next actions

This is a real, reproducible **development-domain improvement under the
stated aggregate screen**, not a universal detector or independent-safety
demonstration. The single seed, temporally related validation images,
partially correlated stress transformations and model checkpoint selection
on the development validation data constrain interpretation.

Noise, blur and partial occlusion regressions still matter despite the
mean-screen pass. Keep the published original/frozen detector unchanged.
Preserve both candidate/baseline checkpoints for **additional-seed stability
checks**, offline error analysis and evaluation on genuinely independent,
properly labeled and licensed real-camera capture sessions after the
existing admission gate passes. Do not repurpose this experiment for live
aircraft control or claim tested physical flight safety.
