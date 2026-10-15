# External real-image lead: Black Bee Drones IMAV 2025 platform dataset

**Status: public metadata reviewed, candidate NOT admitted. No model inference, training
or generalization evaluation on this source has occurred in AegisLand.**
Continuation of the existing AegisLand detector; no new numbered research phase.

Source: https://huggingface.co/datasets/blackbeedrones/imav-2025-platform-dataset
Dataset card revision reviewed 2026-10-14, current repo root commit 0fe4cbf.
This public collection was not present among the six datasets evaluated in
the older 2026-09-28 audit report and should be reconsidered under the
**unchanged existing external-admission rules**, not silently marked admitted.

## Observable public facts

- The card lists an **Apache-2.0 license** and **1,043 image rows** in a
  **single `train` split** (Parquet, total repository ~391 MB).
- Class: `platform`, object detection with COCO-style pixel bounding boxes.
- Target geometry: a square platform with two concentric rings and a central
  **H** marking. This is *not obviously the same visual/label ontology* as
  the KIOS landing-pad sticker; blinded target and box-extent review is mandatory.
- Dataset viewer includes rows with **empty `objects.id` and `objects.bbox`
  lists** (e.g. IDs 4, 9, 10). These are **possible** negative examples,
  not proof of human-reviewed absent-pad frames.
- The card does not provide verified camera-session IDs, original capture-video
  partition provenance, or an independent holdout split. Its single `train`
  partition must **not** be arbitrarily re-split by individual frame.

## Strict admission blockers (none waived)

1. Download/archive/hash the exact released bytes and list **all** images and
   annotations (not only the displayed preview). Authenticate license and
   research use from primary records.
2. Acquire camera/video/session provenance from the publisher; verify video
   independence from each other and from the SHA-verified 422 KIOS real frames.
   Run the frozen full-archive exact, decoded-pixel and perceptual near-match
   checks; manually review near-match flags.
3. Blinded review of physical target geometry/label ontology and compatible
   bounding-box extents. The H marking and possible motion/smoke differences
   may invalidate direct comparison.
4. Independently confirm the empty-target examples and determine counts by
   *capture session*, not just rows with an empty array.
5. Preserve entire original video sessions in any dev/test assignment; do not
   infer independent sessions from image IDs or shuffled order.
6. Freeze the eligible input and research rule *before* any externally
   prospective inference, and open a sealed test only once after admission.

**Decision:** Public data availability is promising, and potential negatives
are especially valuable. The collection currently remains an **unverified
training/development candidate**; no claim of external model accuracy,
generalization, independent-camera reliability, or safe aircraft landing.

The existing frozen admission rules and protected KIOS holdout remain
unchanged. Do not treat this as a new phase.
