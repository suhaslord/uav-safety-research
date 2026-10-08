# Phase 26 public-source discovery follow-up — 8 October 2026

This addendum records public-source discoveries after the frozen 30 September candidate audit. It does not amend the preregistered admission criteria or admit a dataset.

## IMAV 2025 platform dataset

The Black Bee Drones [IMAV 2025 platform dataset](https://huggingface.co/datasets/blackbeedrones/imav-2025-platform-dataset) is publicly available on Hugging Face. The API identifies revision `0fe4cbf737c229defbe339bd86d5b63ce19964db`, created 12 April 2026, under Apache-2.0. The card reports 1,043 rows in one `train` split. Its exposed schema has image, `image_id`, width, height, and object annotations; it has no capture-session or source-video fields. The card describes a moving 1 m square landing platform with circular markings and an H marking, labeled `platform`.

The team's [competition repository](https://github.com/Black-Bee-Drones/imav-2025) documents an IMX219 down-facing camera in its platform mission and says Mission 4 was completed. This supports a physical-UAV context, but does not establish that every dataset image is a direct, unmodified sensor frame or provide row-level video lineage.

**Disposition: not admitted.** The circular markings make the dataset worth a blinded geometry review. The target-box extent and `platform` label must be compared with the frozen KIOS landing-pad annotation convention. The public schema has no session or source-video identifiers and no sealed test partition. Some viewer examples have zero annotations, but the complete negative-frame inventory and session membership are unverified. No image has been checked against the 422 KIOS real frames for byte, name, or perceptual overlap.

Under the frozen protocol, this dataset is not eligible for a test partition on current evidence. If blinded geometry and physical-image lineage pass, it may be considered as development-only evidence while a separate independent test campaign is sourced. No images were downloaded and no detector inference was run for this follow-up.

## GWU / OLSAS Hoodman pad dataset

A George Washington University study describes a public Roboflow project containing 600 manually boxed landing-pad JPEGs selected from 3,392 frames sampled from flight-test videos. The 600 images were selected as 200 per altitude range. The paper says the exported set was split randomly 90/10 into training and validation, with no session-held-out test partition. It documents a physical DJI Mini 3 camera and a five-foot Hoodman pad with a black H marking: [AIAA Aviation 2025 study PDF](https://bpb-us-w2.wpmucdn.com/web.seas.gwu.edu/dist/9/15/files/2025/06/AIAA-Aviation25-Jadon.pdf).

**Disposition: out of scope for the frozen Phase 26 test.** The target is a commercial H-marked pad rather than the frozen concentric-circle KIOS target, and the random frame split does not establish independent capture sessions. The article does not identify the Roboflow project URL or a data license in the evidence found, so rights and exact artifact lineage remain unverified. No images were downloaded and no detector inference was run.

## Other public sources checked

- The University of Sheffield [Swarm of UAVs Future Flights dataset](https://orda.shef.ac.uk/articles/dataset/Data_Repository_from_the_Swarm_of_UAVs_Innovate_UK_Project_Future_Flights_Strand_3_UAV_Flights_Dataset/25712577) is shared under CC BY 4.0 and contains real and simulated landing-approach videos with runway side-line labels. It is out of scope for the frozen detector's landing-pad target ontology.
- The [Air2Land repository](https://github.com/micros-uav/micros_air2land) describes 115,684 frames for fixed-wing landing guidance and says its sequential stereo imagery and sensor data are simulated. It fails the real-camera gate and does not provide the frozen landing-pad target class.

This focused search found one additional real-camera landing-pad lead, but its H-marked target and random frame split fail the frozen test gate. The IMAV dataset remains the only newly surfaced candidate with circular target markings worth a geometry/provenance follow-up; it remains unadmitted.
