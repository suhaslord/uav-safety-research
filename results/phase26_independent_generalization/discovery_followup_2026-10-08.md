# Phase 26 public-source discovery follow-up — 8 October 2026

This addendum records public-source discoveries after the frozen 30 September candidate audit. It does not amend the preregistered admission criteria or admit a dataset.

## IMAV 2025 platform dataset

The Black Bee Drones [IMAV 2025 platform dataset](https://huggingface.co/datasets/blackbeedrones/imav-2025-platform-dataset) is publicly available on Hugging Face. The API identifies revision `0fe4cbf737c229defbe339bd86d5b63ce19964db`, created 12 April 2026, under Apache-2.0. The card reports 1,043 rows in one `train` split. Its exposed schema has image, `image_id`, width, height, and object annotations; it has no capture-session or source-video fields. The card describes a moving 1 m square landing platform with circular markings and an H marking, labeled `platform`.

The team's [competition repository](https://github.com/Black-Bee-Drones/imav-2025) documents an IMX219 down-facing camera in its platform mission and says Mission 4 was completed. This supports a physical-UAV context, but does not establish that every dataset image is a direct, unmodified sensor frame or provide row-level video lineage.

**Disposition: not admitted.** The circular markings make the dataset worth a blinded geometry review. The target-box extent and `platform` label must be compared with the frozen KIOS landing-pad annotation convention. The public schema has no session or source-video identifiers and no sealed test partition. Some viewer examples have zero annotations, but the complete negative-frame inventory and session membership are unverified. No image has been checked against the 422 KIOS real frames for byte, name, or perceptual overlap.

Under the frozen protocol, this dataset is not eligible for a test partition on current evidence. If blinded geometry and physical-image lineage pass, it may be considered as development-only evidence while a separate independent test campaign is sourced. No images were downloaded and no detector inference was run for this follow-up.

## Other public sources checked

- The University of Sheffield [Swarm of UAVs Future Flights dataset](https://orda.shef.ac.uk/articles/dataset/Data_Repository_from_the_Swarm_of_UAVs_Innovate_UK_Project_Future_Flights_Strand_3_UAV_Flights_Dataset/25712577) is shared under CC BY 4.0 and contains real and simulated landing-approach videos with runway side-line labels. It is out of scope for the frozen detector's landing-pad target ontology.
- The [Air2Land repository](https://github.com/micros-uav/micros_air2land) describes 115,684 frames for fixed-wing landing guidance and says its sequential stereo imagery and sensor data are simulated. It fails the real-camera gate and does not provide the frozen landing-pad target class.

This focused search did not find a second public dataset that clears the initial target-geometry and physical-capture screens. The IMAV dataset is the only newly surfaced candidate worth a geometry/provenance follow-up; it remains unadmitted.
