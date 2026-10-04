# Original-detector replay and controlled-occlusion evidence

## Question and scope

This report asks how landing-pad detector performance changes under measured image occlusion and other reconstructed stresses, where observed losses begin, and which of the two available KIOS sequences is vulnerable. It is separate from AegisLand's frozen simulation landing-outcome studies. Detector boxes do not measure aircraft behavior or safe landing.

## Original model and reproducibility

The original Phase 23 YOLO11n checkpoint was recovered, not replaced. A checksum-authenticated replay under the recovered Python/Ultralytics/Torch/NumPy/Pillow lock regenerated all six published condition evaluations. All 24 aggregate metric cells matched exactly, with maximum absolute delta zero. The subsequent raw prediction, target, frame-metric and aggregate tables matched their frozen counterparts byte-for-byte.

The source population comprises 86 protected KIOS frames from two temporally related video sequences. Six reconstructions give 516 frame-condition views, not 516 independent samples. The replay used verified source/archive/image/checkpoint identities, no training, no test threshold selection and no removed frames.

## Two distinct paired comparisons

At the frozen confidence floor, the same-view cross-model comparison records 49 recovered, 65 regressed, 223 both-pass and 179 both-fail outcomes. Those counts describe baseline-versus-Phase-23 outcomes within a condition.

The new clean-versus-stressed table instead pairs each detector with itself: 860 rows across two detectors, 86 frames and five nonclean conditions. It isolates each model's observed change from its own clean view; it must not be reported as another 860 independent trials. Both comparisons are retrospective.

Frame success requires matching the annotated target at IoU at least 0.50, but does not exclude false positives. At the 0.001 confidence floor, 136,359 baseline and 71,420 Phase 23 predictions were scored. Official evaluator precision/recall uses a different operating point. A matched frame cannot be interpreted as a reliable deployment decision.

## Controlled measured occlusion

Only commit `f090da03d20b2425c5addccb4d19117c8991bcc1` authenticates the recovered ten research files. The recovered raw-source attempt failed its clean gate and produced no treatment inference; it remains inconclusive. The usable curve comes from the separately versioned Q95-representation v2 study frozen at `6a8623cbeb54951f43b8ca65293598e7c41a474e`. Its saved 145,169 detections and all frame/target statistics were replay-verified, without claiming a new detector rerun in its different Linux/CPU runtime.

Across six doses, mean annotation-box occlusion increases from zero to about 74.6%. Matched-frame count decreases from 53 to 48 out of 86. Mean best-overlap confidence decreases from 0.312 to 0.065; mean best IoU decreases from 0.609 to 0.554. The recall curve is nonmonotonic: a small increase occurs at the 0.45 requested dose. This is more consistent with graded degradation and frame-specific transitions than an established universal cliff; six points cannot identify a deployment breakpoint.

Thirty-three frames already fail without added occlusion. Among the 53 clean successes, first sampled new losses occur in two frames at requested dose 0.15, three at 0.30 and two at 0.75; one subsequently recovers. These are observations, not preregistered threshold findings.

The `land_pad` sequence changes from 33/66 to 28/66 matched frames, while `land_pad2` retains 20/20 at all sampled doses. Only the landing-pad class is represented. Sequence differences cannot by themselves establish a causal target-size, texture or training-resolution mechanism, nor generalize to other classes or scenes.

## Independent validation and limits

Phase 26 has a frozen admission protocol but **no admitted independent dataset**. All KIOS real imagery and derived views are excluded from independent validation. The next candidate needs documented independent capture sessions, ontology/annotation and negative-frame review, rights, a zero-overlap screen against all 422 KIOS real frames, a committed input lock and a development-only rule before sealed-test inference.

The next-candidate execution lock makes the archived dHash separation rule executable: reject distances at most 9 so accepted separation is at least 10. A clear automated screen is not admission. No physical-flight certification, detector-to-controller composition result, independent reliability result or causal training mechanism follows from this report.

## Figures, tables and provenance

- Real-data controlled-occlusion figure: [`controlled_occlusion.png`](../results/research_revalidation_2026_10_03/controlled_occlusion/controlled_occlusion.png).
- New within-model pairs: [`paired_clean_vs_stressed.csv`](../results/research_revalidation_2026_10_03/paired_clean_vs_stressed.csv).
- First observed losses and scene-specific curves: [`controlled_occlusion/`](../results/research_revalidation_2026_10_03/controlled_occlusion/).
- Original-model authentication and exact-match receipt: [`replay_receipt.json`](../results/research_revalidation_2026_10_03/replay_receipt.json).
- Original 516-view paired tables and publication figures: [`results/phase25_failure_atlas/`](../results/phase25_failure_atlas/).
- Runtime/data/method details and qualifications: [`research revalidation`](../docs/research_revalidation_2026_10_03.md).
- Dataset source: [KIOS 2024 Zenodo record](https://zenodo.org/records/13682584). Cite its creators and dataset record separately from the repository software; no new rights to the source imagery are asserted.

The historical simulation paper and original numerical archives remain unchanged. This report is a scoped retrospective research supplement, not a new independent-validation paper.
