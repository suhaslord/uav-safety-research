# Phase 26 — Separate-data reliability study

## Status

Input sourcing and contamination screening started. No threshold has been
selected, no new holdout has been admitted, and no reliability or landing-safety
result has been established. Phase 25's 86 frames and six generated variants
are previously used test material; exclude them from both Phase 26 development
and new evaluation. The remaining KIOS real frames come from the same two
source videos and are also unsuitable as an independent new evaluation set.

## First candidate rejected

The [2022 KIOS record](https://zenodo.org/records/7477560) is not a fresh
real-image holdout relative to the [2024 KIOS
record](https://zenodo.org/records/13682584). A byte-hash and source-name audit
of its `Images.zip` against **all 422** real JPEGs in the 2024 archive found
422/422 exact duplicates, despite the extra numeric prefix on the older ZIP's
member names. The candidate archive contains 1,921 images in total; the other
images have **not** been established as independent labeled real landing-pad
views. See `docs/phase26_candidate_2022_audit.json` and reproduce with:

```bash
python scripts/audit_phase26_candidate.py \
  --reference-root data/external/kios_landing_pad/extracted/airisim_dataset2/Real_images_tight_labels \
  --candidate-zip data/external/kios_2022_candidate/Images.zip
```

The 2022 `Images.zip` downloaded for this check has the Zenodo-published MD5
`e09cbbd0cae32fa7b28a09e7ecc906bc`; the audit report records its SHA-256.

The script exits with status 2 on exact byte or normalized source-name
overlap. Its passing status is only a first screen: near-duplicate images,
shared videos, collection sessions, labels, and use rights still need review.
Never use the rejected archive as an independent test set by relabeling its
known KIOS frames.

## Freeze before looking at new outcomes

1. Recover and freeze the original Phase 23 weights and inference environment
   under `docs/phase25_input_lock.json`. Reconcile both models with published
   Phase 23 aggregate metrics before interpreting Phase 25 results. The same
   frozen detectors must be used for Phase 26.
2. Source a **distinct** labeled real-image development collection and a
   separately collected new evaluation collection. Record origin, permission,
   capture session or video ID, annotation class and quality review, frame
   hashes, and sequence boundaries. Screen both collections against **all**
   KIOS real frames and against one another for exact and near duplicates and
   related video frames. Group splits at capture session level, never at
   individual frame level.
3. Before any evaluation results are viewed, specify the detector output to
   score, a frame-level target outcome, a small prespecified set of candidate
   scores, the choice rule and its acceptable tradeoff on development data,
   missing-detection handling, and the final evaluation summaries. A detector
   confidence is a localization-related score, not a probability of safe
   landing. The rule can flag predictions for review; it cannot certify a
   landing or make an autonomous safety decision.
4. Pick at most one rule and threshold using **development** data only; log
   the full selection trace, versions, and file hashes. Seal the new evaluation
   collection until the choice is frozen. Run once on that collection and
   report grouped counts, false accept/reject tradeoffs, condition breakdowns,
   and uncertainty at capture-session level if enough independent sessions
   exist. If there are too few independent sessions, report descriptive counts
   without misleading precision or p-values.

## Publication gate

Publish a Phase 26 results page only when both independent collection
manifests, overlap/annotation audits, frozen model and rule hashes, and a
reproducible evaluation report exist. Until then, keep the site at the Phase 25
retrospective and describe Phase 26 as a separate-data study in preparation.
