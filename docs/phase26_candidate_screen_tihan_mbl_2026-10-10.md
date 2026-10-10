# Phase 26 candidate screen — TiHAN Marker Based Landing

Screened 10 October 2026 from the official [TiHAN IIT Hyderabad TiAND
dataset page](https://tihan.iith.ac.in/TiAND.html) and the [IEEE paper
record](https://ieeexplore.ieee.org/document/10990283/) for “TDMBPLD: A Dataset
Focusing on Marker Scene for UAV Landing” (DOI
[10.1109/LGRS.2025.3567863](https://doi.org/10.1109/LGRS.2025.3567863)). No images
were downloaded and no detector inference was run.

## Evidence found

- TiHAN's official page lists a Marker Based Landing (MBL) navigation dataset
  with 7,517 high-resolution images captured across various altitudes and
  weather conditions, 2D annotations for a custom marker class, and a
  70/15/15 train/validation/test split.
- The same MBL entry lists sensor details as “Available Soon.” The site gives a
  general request-and-approval download process and says datasets are subject
  to a data usage agreement, but the MBL entry itself has no dataset-specific
  request or download link and no explicit reuse license.
- The IEEE abstract describes a TiHAN marker-based precision-landing dataset
  with high- and low-resolution data and an ArUco marker detection task. The
  accessible paper record does not disclose split grouping, capture-session
  identifiers, a negative-frame inventory, or dataset reuse terms.

## Gate disposition

**Promising lead; not admitted.** A 70/15/15 image split does not establish
independent evaluation when the page does not say whether related frames from
the same flight or session cross the split. The frozen Phase 26 target is the
KIOS circular landing pad; the available description says “custom marker” and
the paper abstract says ArUco, without enough geometry detail to establish an
ontology match. Do not download, use for development, evaluate, or treat the
reported split as an independent holdout until the dataset owner provides the
data-use terms and the following evidence:

1. Exact annotation class definition, representative target geometries, and
   box quality criteria.
2. The 70/15/15 membership manifest, file hashes, and flight/video/session IDs
   showing whether the test partition is separated by collection session.
3. Empty-target or negative-frame counts and labels for every partition.
4. Dataset-specific permission, citation requirements, and a lawful access
   path.
5. Enough metadata to screen exact and near-duplicate images and source video
   against all 422 KIOS real frames and any development collection.

This screen does not change the frozen `NO_DATASET_ADMITTED` status or permit
inference. If access is granted, first perform rights, ontology, annotation,
manifest, and overlap review; only then decide whether the collection is
eligible for development or a genuinely session-held-out evaluation.
