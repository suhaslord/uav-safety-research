# Phase 25 corrected descriptive analysis v1

86 reused frames from two video sequences; repeated views are dependent. No population inference or internal feature mechanism is established.

This post hoc correction supersedes the numerical prose and inferential claims in the archived reports. Historical raw observations and frozen release files are unchanged. No new detector inference was performed.

## Paired detector outcomes

Across 516 paired views: 49 recovered, 65 regressed, 223 both pass, 179 both fail. Baseline success: 288/516; Phase 23: 272/516 (-3.10 percentage points).

- blur: baseline 45/86, Phase 23 53/86; 13 recovered, 5 regressed.
- clean: baseline 53/86, Phase 23 46/86; 7 recovered, 14 regressed.
- low_light: baseline 49/86, Phase 23 38/86; 6 recovered, 17 regressed.
- mixed: baseline 43/86, Phase 23 44/86; 7 recovered, 6 regressed.
- noise: baseline 45/86, Phase 23 48/86; 10 recovered, 7 regressed.
- occlusion: baseline 53/86, Phase 23 43/86; 6 recovered, 16 regressed.

## Historical topology observations

Mean within-frame difference of success rates at shared achieved-dose bins, averaging shared bins equally within each frame, then frames equally. Matching is by bin, not exact dose; discrete dose distributions remain unequal.

Achieved doses outside [0, 0.75) are excluded rather than clamped into the last bin. summary.json records counts, dose distributions, matched denominators, sequence strata and every bin. Bin rates below pool views; contrasts instead give frames equal weight.

### CENTER

First observed downward 50% crossing: 0.559317. Excluded views: 9.

- [0.00, 0.05): 76/142 (53.52%), 86 frames.
- [0.05, 0.15): 92/155 (59.35%), 86 frames.
- [0.15, 0.25): 92/168 (54.76%), 84 frames.
- [0.25, 0.35): 98/170 (57.65%), 80 frames.
- [0.35, 0.45): 93/185 (50.27%), 79 frames.
- [0.45, 0.55): 84/142 (59.15%), 71 frames.
- [0.55, 0.65): 94/215 (43.72%), 84 frames.
- [0.65, 0.75): 48/104 (46.15%), 74 frames.

### OUTER_RING

First observed downward 50% crossing: 0.072282. Excluded views: 1.

- [0.00, 0.05): 63/115 (54.78%), 86 frames.
- [0.05, 0.15): 101/214 (47.20%), 82 frames.
- [0.15, 0.25): 95/155 (61.29%), 80 frames.
- [0.25, 0.35): 81/145 (55.86%), 76 frames.
- [0.35, 0.45): 112/215 (52.09%), 84 frames.
- [0.45, 0.55): 95/142 (66.90%), 71 frames.
- [0.55, 0.65): 94/185 (50.81%), 79 frames.
- [0.65, 0.75): 70/118 (59.32%), 75 frames.

### STRIPED

First observed downward 50% crossing: 0.337788. Excluded views: 0.

- [0.00, 0.05): 63/125 (50.40%), 86 frames.
- [0.05, 0.15): 100/178 (56.18%), 86 frames.
- [0.15, 0.25): 91/163 (55.83%), 86 frames.
- [0.25, 0.35): 94/180 (52.22%), 86 frames.
- [0.35, 0.45): 76/164 (46.34%), 86 frames.
- [0.45, 0.55): 89/175 (50.86%), 86 frames.
- [0.55, 0.65): 70/165 (42.42%), 86 frames.
- [0.65, 0.75): 60/140 (42.86%), 86 frames.

### RANDOM_PATCH

First observed downward 50% crossing: 0.622854. Excluded views: 3.

- [0.00, 0.05): 48/89 (53.93%), 86 frames.
- [0.05, 0.15): 93/172 (54.07%), 86 frames.
- [0.15, 0.25): 74/141 (52.48%), 85 frames.
- [0.25, 0.35): 111/196 (56.63%), 84 frames.
- [0.35, 0.45): 91/178 (51.12%), 84 frames.
- [0.45, 0.55): 92/179 (51.40%), 84 frames.
- [0.55, 0.65): 103/201 (51.24%), 85 frames.
- [0.65, 0.75): 60/131 (45.80%), 83 frames.

## Matched exploratory contrasts

- CENTER_minus_OUTER_RING: -2.64 percentage points; 86 frames, 604 shared frame/bin pairs.
- CENTER_minus_STRIPED: +3.15 percentage points; 86 frames, 644 shared frame/bin pairs.
- CENTER_minus_RANDOM_PATCH: +0.31 percentage points; 86 frames, 634 shared frame/bin pairs.
- OUTER_RING_minus_STRIPED: +5.60 percentage points; 86 frames, 633 shared frame/bin pairs.
- OUTER_RING_minus_RANDOM_PATCH: +2.91 percentage points; 86 frames, 622 shared frame/bin pairs.
- STRIPED_minus_RANDOM_PATCH: -2.81 percentage points; 86 frames, 677 shared frame/bin pairs.

## Control limitation

344/344 generated zero-dose images differ in bytes from their sources; 268 have different false-positive counts from canonical Phase 23 clean predictions. Frame-success mismatches: 0. Historical controls were JPEG-reencoded. The original aggregate gate evaluated source clean images, not these generated controls. Lossless v2 inference has not been run.

Crossings are interpolation summaries of non-monotonic observations, not robust biological or physical dose thresholds. The corrected contrasts are exploratory and cannot restore confirmatory status to the historical JPEG experiment. Two sequences do not justify the archived frame-bootstrap uncertainty or significance claims. Training-resolution and central-ring explanations remain untested hypotheses.
