# Phase 10R development + trajectory-held-out validation implementation note

This note records the concrete implementation choices used to execute the already-approved Phase 10R preregistration. It does not change the hypotheses or the final frozen-holdout gate.

## Evidence split

- `phase10r_development`: top-level seed `12345`
- `phase10r_validation`: top-level seed `271828`
- separation unit: complete trajectory/sequence; no random frame split
- 5 trajectory families × 2 obliquity bands × 3 appearance conditions per split
- 30 sequences per split, 60 total
- 48 frames per sequence; target present/truth-visible on 40 frames per sequence
- 1,200 truth-visible frames per split; 2,400 total

The validation seed is not used for candidate selection. The workflow writes `candidate_freeze.json` after development calibration and before validation generation/evaluation.

## Camera / rendering configuration

- grayscale: `160 × 120`
- `fx = fy = 145 px`
- principal point: image center
- marker: `DICT_4X4_50`, ID `0`, physical size `0.60 m`
- appearances: nominal, low exposure/reduced contrast, blur + noise
- obliquity: nominal and a deterministic difficult trapezoidal projection band
- edge stress is produced causally by trajectory motion; the target center stays truth-visible while part of the projected footprint may leave the image.

Raw frame bytes and SHA-256 hashes are preserved in the Actions artifact. Dataset acceptance is determined by generator/truth metadata, not detector outcomes.

## Candidate frozen before validation

The selected deterministic candidate retains the unchanged Phase 9 detector as the paired baseline and adds:

1. known-marker (`DICT_4X4_50`, ID 0) subpixel corner refinement when available;
2. a causal component representation that learns only from earlier successfully decoded frames in the same sequence;
3. explicit left/right partial-edge pose hypotheses using previously observed marker span and current vertical scale;
4. temporal innovation rejection for implausible single-frame geometry;
5. selective abstention when the inferred visible marker fraction is below `0.66`;
6. source-conditional empirical conformal radii fit only on `phase10r_development` residuals.

No learned residual model is used.

## Operational analysis strata

- `difficult_truth_visible`: truth-visible and at least one of difficult obliquity, non-nominal appearance, or partial edge footprint.
- `ambiguous_pose_truth`: truth-visible and either difficult obliquity or partial edge footprint.
- `clean_aruco_truth`: truth-visible, nominal obliquity, nominal appearance, fully in-frame footprint.

H3 source-conditioning uses only inference-visible source labels (`known_aruco_refined`, `phase9_center_regeometry`, `partial_edge`). The interval-width comparison is paired on rows where both unchanged Phase 9 and Phase 10R produce observations, at the same nominal coverage target.

## Claim boundary

This is controlled simulation development/validation evidence, not physical-flight validation and not the new protected `phase10r_frozen_holdout`.

`safety_acceptance = false`  
`controller_tuning_allowed = false`
