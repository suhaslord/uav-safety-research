# Phase 25B — controlled occlusion sweep

**Status:** frozen exploratory protocol. Do not change the rules after generating
any occluded view or viewing any predictions.

## Question

With one fixed detector and fixed inference settings, does increasing a
centered opaque occlusion inside the landing-pad annotation box reduce target
recall and localization quality? Does confidence decline with correctness, or
remain high as overlap gets worse?

This tests sensitivity to one controlled synthetic intervention. It cannot
identify every cause of real-world occlusion failures.

## Evidence boundary and inputs

- Use the same 86 protected KIOS real-video frames and their original labels,
  verified against `docs/phase25_reconstruction_lock.json` and the
  checksum-verified Zenodo archive.
- All frames were used by the earlier Phase 23/24 aggregate evaluation and the
  Phase 25 baseline diagnostic. This is **exploratory retrospective evidence**,
  not independent confirmation.
- Test only the exact Phase 22 *detector baseline* checkpoint with SHA-256
  `3a1801b192d624f8dcdda4bc5d9a9157309000df67a4c30d62368c37901feddd`.
  This is not the Phase 22 simulation model. Phase 23 remains aggregate-only
  while its original checkpoint and runtime are missing; this experiment does
  not replace or compare against it.
- Use the frozen inference settings in `docs/phase25_input_lock.json`:
  320px, confidence floor 0.001, NMS IoU 0.7, 300 maximum detections, batch 16,
  2 workers, CPU. Match the Phase 25 baseline runtime:
  Python 3.12.14, PyTorch 2.9.1, Ultralytics 8.4.152, NumPy 2.5.3, Pillow
  12.3.0. Record OpenCV and other installed runtime versions in the run
  manifest as well. Do not train, tune, or change a threshold.

## Fixed intervention

For each original image, decode its pixel array once and create six copies.
The zero-dose copy is unchanged. For every annotated landing pad, draw a
centered solid neutral-gray rectangle (RGB 127, 127, 127) over its box at these
nominal occluded fractions of the rasterized ground-truth box area:

| Dose | Occluded box area | Nominal visible box area |
| --- | ---: | ---: |
| 0 | 0% | 100% |
| 1 | 15% | 85% |
| 2 | 30% | 70% |
| 3 | 45% | 55% |
| 4 | 60% | 40% |
| 5 | 75% | 25% |

Rasterize normalized label coordinates with floor for the top-left and ceil
for the exclusive bottom-right, clipped to the image. For a requested dose
`q`, scale both box dimensions by `sqrt(q)`, round mask dimensions to the nearest
pixel using round-half-up with a minimum of one pixel for nonzero doses, and
center the mask using floor for the top-left offset. Fill only the resulting rectangle.
Record the actual mask pixel count and achieved fraction for every target;
pixel rounding means the achieved fraction may differ slightly from the
nominal dose. Do not add blur, noise, brightness changes, translation, or any
other image treatment. Save derived views as lossless PNGs and hash every one.

The dataset supplies bounding boxes, not segmentation masks. Therefore the
measured visibility coordinate is the fraction of annotated **box pixels** not
covered by the mask. It is a visibility proxy, not a measurement of the true
visible physical surface area of the pad. Name and label it accordingly.

## Inference and scoring

Run the frozen detector on all 86 frames at all six doses: 516 frame-dose
cases, with no exclusions. Keep each frame paired across doses. Preserve every
predicted box and its confidence score.

- Match same-class boxes one-to-one, in descending confidence order, at IoU
  ≥ 0.50. Count unmatched predictions as false positives and unmatched labels
  as false negatives.
- Primary outcome: object recall at the frozen IoU rule by achieved visible
  box fraction.
- Secondary outcomes: all-target frame success; false positives per frame;
  best IoU for each target over any same-class prediction (zero if none); and
  confidence of that best-overlap prediction (null if none). Break equal-IoU
  ties by higher confidence, then stable prediction index. Also report IoU and
  confidence for matched true positives, clearly labeled as a survivor-only
  subset.
- Detector confidence is a model score, not a probability of a safe landing.

Before interpreting nonzero doses, the zero-dose control must reproduce the
published clean Phase 22 baseline recall and mAP50 within 0.001 under the
frozen runtime. If that gate fails, stop and report the run as blocked; do not
inspect or summarize the occluded-dose outputs.

## Analysis and reporting

Report per-dose counts, recall, frame success, false positives per frame,
target best-IoU, and confidence summaries against the **achieved** visible-box
fraction. Include paired per-frame changes from dose 0 and adjacent-dose
transitions. Show the full frame-level table and a dose-response figure.

There are only two recorded source sequences, and adjacent frames may be
correlated. Treat this as descriptive exploratory evidence: no significance
tests, population-level confidence intervals, causal claims beyond the
specified synthetic intervention, or independent-confirmation language.
Publish the protocol hash, source/checkpoint/runtime hashes, achieved mask
fractions, all predictions, and all outcomes. Report null or adverse results
with the same prominence as favorable ones.

## Fail-closed checks

Before inference, verify all 86 source image and label hashes, the archive
checksum, the exact checkpoint hash, the runtime, and the protocol freeze
hash. Check that each dose has exactly one derived image per source frame and
that no image was omitted. Verify the zero-dose aggregate gate first. Any
failure blocks result publication; do not patch inputs, settings, exclusions,
or scoring after seeing treatment outcomes.
