# AegisLand Phase 26 public-data search sweep — 10 October 2026

## Decision

No newly found public dataset meets the frozen Phase 26 admission gate. Keep the result at **`NO_DATASET_ADMITTED`**. No dataset images were downloaded, the KIOS overlap audit was not run on these leads, and no detector inference was run.

The gate still requires at least 30 real-camera images from at least two independent sessions; source-video and session IDs; a whole-session development/test split; a physical KIOS-compatible concentric target; reviewed labels and verified empty-target frames; research-use permission; and zero byte, decoded-pixel, filename, or dHash overlap against the 422 authenticated KIOS real frames (`--near-distance 9`).

## Search and screening

I used Exa for 118 requested results across 13 targeted queries, then read the primary dataset/repository or paper pages for the plausible leads below. Search-result counts include duplicates. A lead was excluded when its public evidence already failed a hard gate; no image payloads were retrieved.

| Lead | Evidence from its public record | Disposition |
| --- | --- | --- |
| [AGH `drone_landing_static`](https://github.com/vision-agh/drone_landing_static) and [paper](https://arxiv.org/pdf/2004.11612v1.pdf) | 75 HD test images in three sets (32, 18, 25); physical UAV-camera sequences. The paper describes a marker with one large black circle, a square, a rectangle, and a small circle. The public record does not map images to source videos or independent session IDs and states no dataset license. The three sets are organized by measurement source, not documented as separate capture sessions. | Not eligible: target geometry differs from the frozen KIOS target; video/session lineage, rights, and a sealed whole-session split are not established. |
| [COMMTR real-video validation card](https://huggingface.co/datasets/ChenglinLiuChris/commtr-real-video-validation) | Ten real landing flights plus two calibration flights, 12 source videos, synchronized telemetry/checksums, 137 manually annotated frames, and 84 frames labeled `board_not_visible`. It uses a blue rectangular board. The card says the license and contact are still to be confirmed. | Strong flight-level provenance lead, but not eligible: rectangular target does not match the frozen pad and reuse rights are unconfirmed. |
| [Kaggle Landing Pad](https://www.kaggle.com/datasets/nuidelirina/landing-pad) | H-pad and rotation-invariant `pattern_circle` images; the card describes a random 60/20/20 image split. It does not document source videos, capture sessions, or session-held-out evaluation. The page's database-content license statement does not establish rights for the images themselves. | Not eligible: capture lineage, rights, target equivalence, and independent split are unverified. |
| [DatasetUAVlanding repository](https://github.com/Matildevieira00/DatasetUAVlanding) and [thesis record](https://comum.rcaap.pt/entities/publication/d94b2f20-bd4e-468b-8fae-7ae5de344e3f) | Roughly 107,000 images across three acquisition scenarios, with about 20,000 bounding-box annotations. The thesis describes two-camera UAV localization during landing, including a ship scenario; it does not describe landing-pad detections as the labeled target. | Not eligible: annotation ontology is UAV localization rather than KIOS-compatible pad detection; dataset-specific rights and image-to-session mapping are also absent from the repository page. |
| [UDWA repository](https://github.com/Aprus-system/UDWA) | 179 real videos and 46,028 extracted images across 39 places and six altitudes. Its released annotations cover people and cars. | Not eligible: the released labels and target do not cover landing pads. |
| [TEKNOFEST landing dataset mirror](https://www.kaggle.com/datasets/esracum/autonomous-drone-landing-dataset-teknofest) | A third-party mirror describes UAP text and crescent-marked circular pads, plus people/vehicles, with train/validation folders and a CC BY-NC 4.0 label. No whole-session split or source-video/session mapping is documented. | Not eligible: marker ontology differs, and independent sessions, a sealed test split, lineage, and owner-level rights are not established by the mirror. |

The previously screened KIOS Zenodo collection remains ineligible as an independent test source: the frozen audit found exact-byte overlap with all 422 authenticated KIOS real frames. The later mixed real/Unreal KIOS record includes those same real frames and synthetic scenes.

## What would close the data gate

The best-supported route is a new, independently captured campaign using a physical KIOS-compatible target. Before capture, freeze two or more separate session IDs and the session-level split. Record the source video, camera/platform settings, target dimensions, frame timestamps, empty-target intervals, permissions, and annotation convention. Then review the target and labels, build the hash-bound input lock, and run the locked overlap audit against all 422 KIOS frames. Do not run detector inference until those checks and the development-only decision rule are locked.

The AGH and COMMTR owners could be asked for missing files/rights, but their documented targets already fail the KIOS geometry check; pursuing them would not by itself close this gate.
