# Phase 26 candidate screen — DDroneC-DB2

**Disposition: not eligible as the frozen independent test set.** The published
evaluation uses a random image-level split. The source does not establish a
session-held-out test, and the available lab page does not expose the metadata
needed to reconstruct one.

## Public-source evidence

The [LightDenseYOLO study](https://pmc.ncbi.nlm.nih.gov/articles/PMC6022018/)
describes the Dongguk Drone Camera Database version 2 (DDroneC-DB2) as 10,642
images. It combines images from the earlier DDroneC-DB1 with newly extracted
frames from DJI Phantom 4 videos recorded at 50 m. The study reports downward-
facing color-camera video at 1280 × 720 and 30 fps, and morning, afternoon, and
evening recordings for each sub-dataset. It describes the marker as 1 m × 1 m.
This is enough to establish a real-UAV landing context, but not enough to
certify compatibility with the frozen KIOS annotation ontology.

For its detection evaluation, the study performs two-fold cross-validation.
In each fold, it randomly selects 5,231 of the 10,642 images for training and
uses the remainder for testing. It does not describe a session-held-out or
sealed external test partition, and the paper does not map each image to a
source video or capture session. Those test folds cannot support an
independent-generalization claim under the frozen Phase 26 protocol.

The paper points to the [Dongguk CGCV lab database page](http://dm.dgu.edu/link.html)
and calls DDroneC-DB2 public. The page's accessible text mentions DDroneC-DB2
as an open dataset used to create other datasets, but does not expose a
dataset-specific download or request URL, file/split metadata, or license
terms. The article itself is published under CC BY; this does not establish
the image dataset's license.

## Gate decision and handling

Do not use the published random-fold test images as the Phase 26 test set.
Development use is also not admitted yet: confirm image rights, obtain the
source files and per-image video/session mapping, verify session-linked
negative frames, review target geometry and annotation extents against the
frozen ontology, and screen every image against all 422 KIOS real frames for
exact and near duplicates. Only then can the protocol's manifest and input
lock be built.

No images were downloaded; no hashes or visual-overlap checks were run; and
no detector inference was performed. The frozen state remains
`NO_DATASET_ADMITTED`.
