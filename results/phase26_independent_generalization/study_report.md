# Phase 26 — Independent External Dataset Admission & Generalization Benchmark Report

**Project:** AegisLand UAV Safety Benchmark  
**Phase:** Phase 26  
**Status:** `NO_DATASET_ADMITTED` (Admission gate preserved without compromise)  
**Date:** 2026-09-30  
**Protocol:** [`docs/phase26_independent_generalization_protocol.json`](file:///C:/Users/suhas/.gemini/antigravity/scratch/uav-origin-main/docs/phase26_independent_generalization_protocol.json)  
**Protocol SHA-256:** `a12fb965721d0cde7c96969e19f7a00ab6ead1ae62870e563b30f844bd65791c`  
**Base Commit:** `3b4881da19bf3ff2e01ab46a1d1f79ff337bd6db`

---

## 1. Executive Summary

Phase 26 investigates the foundational external generalization question of the AegisLand research program:
> *Do the Phase 22 baseline and Phase 23 robust landing-pad detectors retain useful detection, localization, and reliability performance on real aerial camera imagery genuinely independent of the KIOS benchmark distribution?*

To prevent confirmation bias, data snooping, and circular reasoning, Phase 26 instituted a **strict, pre-registered admission protocol** prior to inspecting any candidate model predictions. This protocol establishes rigorous standards for acquisition independence, zero frame/session contamination, target class ontology compatibility, capture provenance, and negative frame inventories.

Seven public candidate datasets and sources were exhaustively screened against the authenticated KIOS reference archive (422 real frames across two continuous video capture sessions). 

### Final Admission Verdict
**`NO_DATASET_ADMITTED`**

All seven candidate sources failed admission under the preregistered criteria:
- **2 sources (`REJECTED_OVERLAP`):** Sourced from the University of Cyprus KIOS repository. The KIOS 2022 Archive exhibits **100% byte-duplicate overlap** (422/422 exact SHA-256 matches) with the KIOS 2024 real benchmark. The KIOS 2024 residual real frames stem from the exact same two continuous video flights (`land_pad`, `land_pad2`) used to train and test Phase 23, exhibiting severe temporal autocorrelation and cross-split collisions at perceptual Hamming distance 4.
- **1 source (`REJECTED_PROVENANCE_UNKNOWN`):** IMAV 2025 candidate imagery, manifests, session identifiers, and negative frame inventories have not been publicly released or archived.
- **3 sources (`REJECTED_LABEL_INCOMPATIBLE`):** TEKNOFEST, HelipadCat, and Roboflow Universe community collections feature fundamentally incompatible visual targets (competition emblems with 'UAP' lettering, civilian airport/hospital helipads, commercial 'H' folding pads, or ArUco markers). The frozen YOLO11n detectors cannot recognize these patterns without retraining or fine-tuning, which is strictly prohibited.
- **1 source (`REJECTED_NON_REAL_IMAGERY`):** Synthetic simulators (AirSim, Gazebo, Webots) are categorically excluded from real-camera external generalization benchmarks.

Rather than weakening the admission criteria or manufacturing an illusion of external validity, Phase 26 faithfully records that **no existing public dataset satisfies the requirements for independent external evaluation**.

---

## 2. Preregistered Admission Protocol

The Phase 26 protocol (`docs/phase26_independent_generalization_protocol.json`, SHA-256: `a12fb965...`) defines eight strict admission requirements:

| Criterion | Requirement | Verification Method |
|---|---|---|
| **Campaign Independence** | Capture campaign, flight location, and team distinct from KIOS (University of Cyprus). | Provenance records; flight logs, operator identity, geographical coordinates. |
| **Zero Frame Overlap** | Zero duplicate or near-duplicate frames against any KIOS real image. | Exact SHA-256 byte matching, normalized source name matching, and 64-bit difference hash (dhash) with Hamming distance $\ge 10$. |
| **Zero Session Overlap** | Zero shared continuous video sequences or capture sessions with KIOS (`land_pad`, `land_pad2`). | Explicit `session_id` and `source_video_id` metadata from origin capture logs. |
| **Non-Derivative Integrity** | No synthetic crops, neutral-gray occluders, noise transforms, or rescalings of KIOS frames. | Lineage audit tracing frames to raw camera sensor output. |
| **Real Optical Imagery** | Physical optical camera capture from an airborne UAV or terminal descent approach. | Exclusion of rendered synthetic engines (AirSim, Gazebo, Unreal). |
| **Target Ontology Compatibility** | Target must represent a physical visual landing pad matching detector semantics (`landing_pad`). | Geometric extent audit; bounding box encloses pad surface without subjective class remapping. |
| **Negative Frame Inventory** | Dataset must include empty-target frames (`target_count == 0`) from the same flight sessions. | Manifest verification; enables unbiased false alarm and abstention auditing. |
| **Permissive License** | Open research license allowing reproduction and public benchmarking. | Documented license terms (CC-BY, CC0, MIT, Apache 2.0). |

---

## 3. Candidate Screening & Audit Findings

An exhaustive search evaluated seven candidate dataset families:

```
Candidate Datasets Evaluated (N = 7)
├── KIOS 2022 Archive (Zenodo 7477560) ───────────► REJECTED_OVERLAP (422/422 exact bytes)
├── KIOS 2024 Residual Real (Zenodo 13682584) ────► REJECTED_OVERLAP (temporal autocorrelation; d=4)
├── IMAV 2025 Competition Benchmark ──────────────► REJECTED_PROVENANCE_UNKNOWN (unreleased artifacts)
├── TEKNOFEST Drone Landing Dataset ──────────────► REJECTED_LABEL_INCOMPATIBLE ('UAP' text / crescent)
├── HelipadCat Helicopter Benchmark ──────────────► REJECTED_LABEL_INCOMPATIBLE (satellite airport 'H')
├── Roboflow Community Landing Sets ──────────────► REJECTED_LABEL_INCOMPATIBLE (DJI 'H' pads / ArUco)
└── Synthetic AirSim / Gazebo Suites ─────────────► REJECTED_NON_REAL_IMAGERY (rendered graphics)
```

### Detailed Candidate Audits

#### 1. KIOS 2022 Archive (`Zenodo 7477560`)
- **Publisher:** Rafael Makrigiorgis et al., KIOS CoE, University of Cyprus
- **Target Type:** KIOS logo and concentric circular landing pad
- **Image Count:** 1,921 images in `Images.zip` (MD5: `e09cbbd0cae32fa7b28a09e7ecc906bc`)
- **Audit Findings:** An automated byte-hash audit against all 422 real images in the official KIOS 2024 archive (`airisim_dataset2.7z`) revealed **422 / 422 exact byte-level SHA-256 matches**, despite an arbitrary numeric prefix prepended to filenames in the 2022 archive. The real images in this archive are identical to the existing benchmark; the remaining images are unverified mixed/synthetic views.
- **Verdict:** `REJECTED_OVERLAP`

#### 2. KIOS 2024 Residual Real Frames (`Zenodo 13682584`)
- **Publisher:** KIOS CoE, University of Cyprus
- **Target Type:** Concentric circular landing pad
- **Image Count:** 422 frames (252 train, 64 val, 20 embargo, 86 test)
- **Audit Findings:** All 422 frames stem from only two continuous video recordings: `land_pad` (frames 6025–6850) and `land_pad2` (frames 0025–0675). Video frames captured fractions of a second apart exhibit severe temporal autocorrelation. A perceptual hash screen found a direct cross-split collision between embargo frame `land_pad__6475.jpg` and test frame `land_pad__6500.jpg` at perceptual Hamming distance 4. Repartitioning frames from the same two videos cannot constitute an independent external dataset.
- **Verdict:** `REJECTED_OVERLAP`

#### 3. IMAV 2025 Competition Benchmark
- **Publisher:** International Micro Air Vehicle Conference & Competition 2025
- **Target Type:** Autonomous landing deck / target platform
- **Audit Findings:** As documented in `docs/phase26_admission_report.json` and `docs/phase26_imav2025_preregistration.md`, candidate images, capture manifests, session provenance logs (`session_id`), target ontology specifications, and negative frame inventories have not been released publicly. The candidate remains completely blocked at the provenance gate.
- **Verdict:** `REJECTED_PROVENANCE_UNKNOWN`

#### 4. TEKNOFEST Autonomous Drone Landing Dataset
- **Publisher:** TEKNOFEST Competitions / Kaggle Community
- **Target Type:** Competition landing markers (cyan/blue circular target with 'UAP' lettering; red landing surface with white crescent emblem)
- **Audit Findings:** The visual markers are competition-specific symbols fundamentally distinct from the concentric circular target learned by the Phase 22/23 models. Furthermore, annotations are randomly split across individual frames without session or continuous video provenance. The frozen detector cannot detect these targets without retraining.
- **Verdict:** `REJECTED_LABEL_INCOMPATIBLE`

#### 5. HelipadCat / Rowan University Helipad Benchmark
- **Publisher:** Rowan University Computer Vision Lab / FAA 5010 Directory
- **Target Type:** Full-scale civil and military concrete helipads (large 'H' markings)
- **Audit Findings:** Imagery consists of nadir high-altitude satellite and aerial orthophotos of permanent aviation infrastructure (hospitals, airports). The spatial resolution, nadir camera angle, and structural architectural scale diverge completely from terminal low-altitude UAV approach imagery.
- **Verdict:** `REJECTED_LABEL_INCOMPATIBLE`

#### 6. Roboflow Universe Community Landing Datasets
- **Publisher:** Community contributors
- **Target Type:** Commercial DJI foldable fabric landing pads ('H' inside circle/square) and ArUco/AprilTag fiducials
- **Audit Findings:** Targets differ substantially from concentric circular landing pads. Uploads consist of ad-hoc scraped video frames lacking session metadata, flight logs, or negative control frames. Licensing terms are unverified.
- **Verdict:** `REJECTED_LABEL_INCOMPATIBLE`

#### 7. Synthetic AirSim / Gazebo / Webots Suites
- **Publisher:** Microsoft AirSim, PX4 Gazebo, UNM Crazyflie
- **Target Type:** 3D rendered textures of landing pads
- **Audit Findings:** Rendered computer graphics are categorically excluded from real-world external generalization benchmarks. Phase 23 was already trained on synthetic AirSim imagery; evaluating on additional synthetic graphics cannot establish real-world validity.
- **Verdict:** `REJECTED_NON_REAL_IMAGERY`

---

## 4. The Concentric Circle Specialization Paradox

The systematic failure of candidate admission exposes a fundamental architectural and experimental paradox in UAV precision landing research:

1. **Hyper-Specialized Visual Feature Representation:**  
   The frozen Phase 23 detector was trained exclusively on concentric circular landing pad geometry. Its learned convolutional features are tuned to concentric radial transitions and central crosshair markings.
2. **Provenance Monoculture:**  
   In the public computer vision ecosystem, datasets containing physical concentric circular landing pads originate exclusively from a single research team: the KIOS Center of Excellence at the University of Cyprus. Consequently, **every existing public dataset containing the required target exhibits 100% duplicate or temporal session overlap with the training distribution**.
3. **Ontology Incompatibility of Independent Data:**  
   Conversely, every genuinely independent aerial dataset employs different target designs—most commonly civilian 'H' helipads, ArUco fiducial tags, or competition emblems. Because the evaluation protocol strictly forbids fine-tuning, gradient updates, or prompt tuning (to preserve the frozen identity of the detectors), evaluating the models on these targets would measure out-of-ontology semantic absence rather than detector perceptual robustness.

---

## 5. Frozen Detector Model Locks

Both detector checkpoints remain authenticated, frozen, and verified via clean-room reproduction receipts:

| Property | Phase 22 Baseline Detector | Phase 23 Robust Detector |
|---|---|---|
| **Architecture** | Ultralytics YOLO11n | Ultralytics YOLO11n |
| **Input Resolution** | 320 px | 480 px |
| **Checkpoint File** | `best.pt` | `best.pt` |
| **Checkpoint SHA-256** | `3a1801b192d624f8dcdda4bc5d9a9157309000df67a4c30d62368c37901feddd` | `43240be969708c32b3e11340c9846b3a588baf361378398677c794d16a455310` |
| **Release Tag** | `phase22-baseline-recovery` | `phase23-checkpoint-recovery` |
| **Bundle SHA-256** | `8d6eda7f8775ad899be7a8b6fbf9e6dea30678c1e28c0b687a88184ac592288b` | `a55531930988deeadf81853d00b63c7e589c6b7fd2270f57653abdb5cdd3e55d` |
| **Clean Reproduction** | 24 / 24 metric cells matched | 24 / 24 metric cells matched (0.0 delta) |
| **Evaluation Parameters** | `conf=0.001, iou=0.7, max_det=300` | `conf=0.001, iou=0.7, max_det=300` |

Neither model has been tuned, modified, or evaluated on candidate data.

---

## 6. Scientific Boundaries & Epistemic Limits

1. **No Pseudo-Generalization:**  
   Admitting the KIOS 2022 archive or repartitioning KIOS 2024 video frames would create a deceptive appearance of "external generalization" while actually testing on memorized or temporally correlated background pixels.
2. **No Flight-Safety Claims:**  
   A detector's bounding-box accuracy or confidence score on static imagery cannot establish closed-loop flight safety, landing stability, airworthiness, or autonomous operational capability.
3. **Integrity of Negative Findings:**  
   In empirical science, confirming that current public archives lack the necessary artifacts for an independent evaluation is an essential, high-value result. It prevents premature claims of operational reliability.

---

## 7. Roadmap to an Admissible External Benchmark

To unblock Phase 26 external evaluation without violating model locks or compromising scientific rigor, the AegisLand program requires a **new physical capture campaign**:

1. **Physical Target Replication:**  
   Fabricate an exact physical replica of the KIOS landing pad (standardized dimensions, concentric ring radii, and central geometry).
2. **Independent Aerial Campaign:**  
   Deploy a distinct UAV platform (e.g., DJI Matrice 300, Holybro S500, or PX4 custom quadrotor) equipped with an independent optical camera sensor at a distinct geographical site.
3. **Structured Session Logging:**  
   Record continuous video sequences across multiple distinct flight sorties under varied approach trajectories, altitudes, and lighting conditions.
4. **Negative Control Acquisition:**  
   Explicitly record flight sequences over landing-pad-free ground surfaces (grass, pavement, gravel) to establish a rigorous empty-target inventory for false alarm calibration.
5. **Pre-Release Input Lock:**  
   Commit all raw video hashes, frame manifests, and blinded bounding-box annotations before executing detector inference.
