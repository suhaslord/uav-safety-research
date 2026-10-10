# Phase 26 candidate screen — UAVLandData

**Disposition: not eligible as the frozen independent test set.** UAVLandData
is a relevant real-landing data lead, but its published evaluation randomly
splits images and the available sources do not map images to source videos or
capture sessions.

## Public-source evidence

The [AeroLite-MDNet paper](https://arxiv.org/html/2506.21635v1) describes
UAVLandData as 9,142 annotated images drawn from 13 hours of video across 24
landing scenarios. It labels `Nest`, `QRcode`, and `House`; the paper describes
the nest as the landing target and the QR code and house as additional classes.
It reports 7,506 randomly selected training images and the remaining 1,636 for
testing. The table labels the latter partition `Val`, while the text calls it
the test set. No session-held-out alternative is reported. The paper does not
identify the camera or capture sites and does not provide per-image source
video/session IDs or a session-linked negative inventory.

The current [Kaggle dataset card](https://www.kaggle.com/datasets/niufaxin/uav-land-coco)
lists Apache 2.0, version 1 at 1.22 GB, and 9,144 files. Kaggle's public
dataset API reports the current revision was updated on 5 March 2025, confirms
the Apache 2.0 license, and exposes no source fields or itemized file list.
The card exposes no video, session, timestamp, or capture-provenance metadata.
The file count differs from the paper's image count; the repository contents
would need to be inventoried before any input lock. The paper says nests and houses tend to
have aspect ratios near 1:2 or 2:1, while QR codes are square; a blinded review
is still needed to establish whether `Nest` boxes represent a compatible
physical landing-target extent under the frozen KIOS ontology.

## Gate decision and handling

Do not use the published random image test split as an independent Phase 26
test set. If development-only consideration is pursued, first verify the
license against the exact Kaggle revision, obtain an image-to-video/session
manifest and camera/site records, establish the negative-frame inventory,
review target geometry and annotation extents, reconcile image/file counts,
and screen all candidate images against all 422 KIOS real frames for exact and
near duplicates. The protocol's hash-locked manifest is required before any
detector inference.

No dataset files were downloaded; no overlap screen or detector inference was
run. Phase 26 remains `NO_DATASET_ADMITTED`.
