# Phase 26 — IMAV 2025 candidate admission and rule specification

**Status: candidate only.** No IMAV images, annotations, capture sessions, or
detector outcomes have been audited in this repository. This document fixes
the initial question and admission criteria before evaluation. An input lock
with original file hashes and independently documented capture sessions is
still required. It must be committed before the prospective test is opened.

## Admission before inference

IMAV's `platform` can map to `landing_target` only if a blinded annotation
review finds that its boxes enclose the physical platform with extents
comparable to KIOS pad boxes. Record the license, dataset revision, annotation
version, every image SHA-256, original image ID, source capture/video/session,
and the reviewer decision. No session may occur in both development and test.
Compare every image against **all 422** KIOS real images using bytes, decoded
pixel hashes, normalized source names, and perceptual near-match screening;
review every flagged pair manually. Verify that the annotation inventory
includes images with zero targets. Complete this work without detector output.

Run `scripts/audit_phase26_manifest.py` on a local candidate directory and
an image manifest. Supply the original checksum-verified KIOS archive too:
the screen compares all 422 extracted reference JPEGs against a fresh archive
extraction. Without it, the report is blocked even when names and counts look
right. Its report is a screen, not automatic independence
certification: human provenance, license, annotation, and near-match decisions
remain required. The test partition is accepted only after those reviews and
an input lock with file hashes and immutable session IDs are committed.

The local UTF-8 CSV requires columns
`path,partition,session_id,source_video_id,target_count,sha256`. `path` is
relative to the candidate image directory; `partition` is `dev` or `test`;
the IDs must come from independent capture records. `target_count` comes from
annotations and may be zero. The audit rejects missing files, changed hashes,
unlisted images, shared sessions/videos, known KIOS matches, and unreviewed
perceptual near matches. Example invocation after sourcing the images and
their capture records:

```bash
python scripts/audit_phase26_manifest.py \
  --reference-archive data/external/kios_landing_pad/airisim_dataset2.7z \
  --reference-root data/external/kios_landing_pad/extracted/airisim_dataset2/Real_images_tight_labels \
  --candidate-root data/external/imav2025/images \
  --manifest data/external/imav2025/capture_manifest.csv \
  --out data/external/imav2025/admission_screen.json
```

- If the source sessions and class geometry are verified, use disjoint whole
  sessions for development and a sealed test.
- If geometry is valid but sessions cannot be verified, use IMAV as
  development-only evidence and acquire a different, separately captured test.
- If geometry or target semantics fail review, treat IMAV as auxiliary only.
- Never random-split frames or infer sessions solely from visual similarity.

## Development-only rule lock

When development predictions and reviewed correctness labels exist, export a
CSV with one row per development image and columns `path,score,correct`.
`correct` is 1 only when the top prediction matches a target at the frozen
IoU threshold; it is 0 for negative frames and misses. Then run:

```bash
python scripts/freeze_phase26_development_rule.py \
  --manifest data/external/imav2025/capture_manifest.csv \
  --screen data/external/imav2025/admission_screen.json \
  --dev-outcomes data/external/imav2025/dev_outcomes.csv \
  --out data/external/imav2025/development_rule_lock.json
```

This rejects every test outcome row and records input and rule hashes. It
does not certify annotation correctness, dataset admission, or test
performance. Keep the test data sealed while making this choice.

## Frozen first question

Evaluate the **available frozen Phase 22 baseline detector**. The original
Phase 23 detector joins only after its exact checkpoint and runtime recover
and reproduce the six published aggregates. Its absence never changes the
identity of the Phase 22 model or licenses a substitute.

Use the detector's frozen confidence floor, preprocessing, NMS, and class map.
For an image, let `R_conf` be the greatest score among post-NMS predictions
of the mapped landing-target class, or **0** when none is predicted. This
function can read predictions and their scores only, never annotations. The
decision is `ACCEPT` when `R_conf >= threshold` and `ABSTAIN` otherwise;
the threshold must be strictly greater than zero.

Primary outcome, assessed only after the decision: the very prediction that
supplied the greatest score matches an eligible annotated target at IoU >=
0.50. Match ties deterministically by original prediction order. On an
empty-target frame, any accepted target prediction is an incorrect accept.
No prediction on an empty-target frame yields `R_conf=0` and abstention;
report it separately as a correct no-target observation, without counting it
as a correctly localized accepted target. A missed target also has score zero.

Secondary descriptive endpoints: all targets localized by one-to-one matching,
FP/FN counts under frozen inference, empty-target false detections, accepted
error count, abstention count, coverage, and per-session counts. A score is
not a probability that landing is safe. With too few independent sessions,
report counts without frame-level significance tests.

## Development choice and test lock

Before viewing development outcomes, record the fixed threshold grid
`0.05, 0.10, ..., 0.95`, objective (maximize acceptance on development
while accepted-error rate is at most 5%), and tie-break (prefer the larger
threshold). If no candidate meets the bound, freeze a rule that abstains on
every image and report that the development gate failed. Treat the 5% target
as a research selection criterion, not a guarantee on new data. Store every
grid point and the chosen rule in a hash-locked JSON file. The rule and test
manifest are committed before any detector inference on the test sessions.

An eligible negative frame contributes to the accepted-error denominator if
the rule accepts it. There is no evaluation-set tuning, test-frame removal,
or second attempt after results are viewed. Record any protocol amendment as
a separate dated document with its reason and affected evidence.
