# Phase 26 independent capture campaign guide

**Preparation only:** no campaign has been captured or admitted. This guide
turns the frozen admission rules into field steps; it does not amend
[`phase26_protocol.md`](phase26_protocol.md),
[`phase26_independent_generalization_protocol.json`](phase26_independent_generalization_protocol.json),
or [`phase26_admission_execution_lock.json`](phase26_admission_execution_lock.json).
If this guide conflicts with those frozen documents, follow the frozen
documents.

## Before capture

1. Confirm permission to capture, retain, annotate, and publish or research-share
   the images. Record the actual terms; do not assume the repository license
   covers captured data.
2. Use a new, independent capture campaign outside the KIOS collection and
   lineage. Record the site, platform, camera, operators, and why the footage is
   independent. Do not reuse, crop, transform, or relabel KIOS frames.
3. Define development and sealed test collections before viewing detector
   outputs. Assign each complete capture session and source video to exactly
   one partition. Never split frames from a continuous session or video across
   development and test.
4. Plan for at least 30 images overall and at least two independent capture
   sessions, with nonempty development and test partitions. Capture and record
   verified empty-target frames from the same campaign, including counts by
   partition. Aim for at least five independent evaluation sessions if
   session-clustered uncertainty is needed; with fewer, the frozen plan calls
   for descriptive counts only.
5. Fix a deterministic frame-extraction and annotation procedure before
   reviewing candidate images. Keep original videos and metadata unchanged.

## For every session and source video

Create one session record and retain the original video. Record:

- campaign ID, session ID, source-video ID, partition, operator, date/time,
  location, and the operational reason this is an independent session;
- UAV/platform and camera make/model, camera serial if appropriate, lens,
  resolution, pixel format, exposure, gain, trigger mode, frame rate, and
  camera orientation;
- physical target make/material, measured dimensions, placement, and a photo
  of the target setup; record lighting and relevant approach conditions;
- original video filename, byte size, SHA-256, time span, and any interrupted
  segments;
- frame-extraction method/version, timestamps, resulting image filenames,
  and SHA-256 hashes;
- annotation class and box convention, annotator, independent reviewer, and
  verified empty-target intervals/counts.

Use IDs taken from the capture log. Never infer session or video IDs from
visual similarity. Do not edit, resize, crop, or color-transform the images
used for the admission screen. Store annotations separately from image files.

## Partition and seal

- Development and test must use different sessions **and** different source
  videos. Record the partition assignment before inference.
- Keep the test images and annotations sealed while selecting the development
  rule. Record who holds the test copy and when it was sealed.
- Include negative frames in the inventory and report their counts by
  partition and session. The audit checks that the total manifest includes
  empty-target frames; human review must verify their labels.
- Do not run the detector on test images until the candidate input lock,
  human admission reviews, and development-rule lock have been committed.

## Build and screen the candidate

1. Put unchanged candidate images under one candidate directory. Fill
   [`phase26_capture_manifest_template.csv`](phase26_capture_manifest_template.csv)
   with one row for every image. `path` is relative to the candidate directory;
   `partition` is `dev` or `test`; `target_count` comes from reviewed
   annotations.
2. Run the full KIOS comparison using the checksum-verified official archive
   and the frozen near-match setting:

   ```bash
   python scripts/audit_phase26_manifest.py \
     --reference-archive data/external/kios_landing_pad/airisim_dataset2.7z \
     --reference-root data/external/kios_landing_pad/extracted/airisim_dataset2/Real_images_tight_labels \
     --candidate-root data/external/phase26_new_campaign/images \
     --manifest data/external/phase26_new_campaign/capture_manifest.csv \
     --near-distance 9 \
     --out data/external/phase26_new_campaign/admission_screen.json
   ```

   The audit refuses to overwrite an existing output. Keep each screen in a
   new path. A passing screen is still pending human review; it is not an
   admission decision.
3. Complete the documented reviews: capture provenance and independent
   lineage; physical target/box compatibility, blinded to detector output;
   annotation quality and negative-frame inventory; research-use permission;
   all exact and near-match flags; and session-level development/test
   assignments.
4. Commit a candidate input lock binding the dataset revision, every image
   hash, capture records, partition assignments, permissions, annotations,
   audit output, and reviewer decisions. Keep raw imagery out of Git unless
   its rights and the project's data-handling rules explicitly allow it.
5. Only after the candidate is admitted, evaluate development data and freeze
   the single permitted rule. Keep the test partition sealed, open it once,
   and report session-grouped counts and the frozen descriptive limits.

## Admission is still blocked until

- the images come from a distinct physical camera campaign and a new location;
- the physical target matches the frozen landing-pad ontology and reviewed
  annotation convention;
- permissions, source provenance, and complete image/video/session inventories
  are documented;
- the full archive-backed overlap screen and every flagged-pair review are
  complete; and
- development/test collections, the input lock, and later the development-rule
  lock are committed before test inference.

The process establishes research evidence only. A detection score does not
measure probability of a safe landing and does not authorize autonomous
flight.
