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

1. Use the recovered, frozen Phase 22 detector as the minimum Phase 26 model.
   If the original Phase 23 weights and inference environment are recovered,
   reconcile all six published aggregates before admitting that detector or
   interpreting paired Phase 25 results. If recovery fails, record a
   baseline-only amendment; never replace Phase 23 with a retrained model.
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
   missing-detection and empty-target handling, and the final evaluation
   summaries. A detector
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

## Candidate-specific amendment, before external predictions

The [IMAV 2025 admission plan](phase26_imav2025_preregistration.md) specifies
the ontology, empty-target policy, prediction-only score, and fallback when
capture sessions cannot be verified. These rules are provisional until the
candidate input hashes, session provenance, and annotation audit are recorded.
No IMAV model outcomes have been inspected or declared independent here.

The [DDroneC-DB2 candidate screen](phase26_candidate_screen_dronedb2_2026-10-08.md)
rejects its published random image-level folds as an independent test set;
dataset rights and source-video/session mapping also remain unverified.

The [UAVLandData candidate screen](phase26_candidate_screen_uavlanddata_2026-10-10.md)
records its real-landing source as a possible development lead, but rejects
the published random image split as an independent test and requires
image-to-session provenance, rights verification, and a blinded target review
before further use.

The [secondary public-source screen](phase26_secondary_leads_screen_2026-10-10.md)
records other rejected landing-data leads and the specific ontology, release,
or provenance gap for each.

The [TiHAN Marker Based Landing candidate screen](phase26_candidate_screen_tihan_mbl_2026-10-10.md)
records a newly surfaced 7,517-image lead. Its published 70/15/15 split is not
documented as capture-session-separated; access terms, session provenance,
and target geometry remain unverified, so it is not admitted.

The first reliability score is the maximum score of the frozen detector's
post-NMS landing-target predictions; use zero when no prediction exists. It
must never take ground-truth boxes or labels as inputs. For the primary
endpoint, assess *afterward* whether the highest-scoring prediction localizes
an annotated target at IoU >= 0.50. A predicted target on an empty-target
frame is incorrect. An empty-target frame with no prediction has no correct
localization to accept: the score is zero and the rule abstains for any positive
threshold. Report empty-target counts and false predictions separately.

On development data only, choose one strictly positive threshold from the
prespecified grid in the candidate-specific protocol. Save the entire choice
trace, selected threshold, code commit, and hashes before opening test data.
Do not use Phase 25 outcomes to choose that threshold. If session provenance,
label geometry, near-duplicate adjudication, or rights are unresolved, the
candidate remains pending or development-only, never an admitted sealed test.
