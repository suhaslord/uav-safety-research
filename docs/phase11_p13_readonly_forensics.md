# Phase 11 P13 read-only availability forensics

## Status

**DESCRIPTIVE ONLY — P13 IS FROZEN — NO P13 RETUNING AUTHORIZED**

These diagnostics use only already-exposed P13 seen-transfer artifacts. They do not authorize changing P13 or reusing seed `671671` as unseen evidence.

Protected validation seed `682682` remains unexposed and retired.

## Event-stratified versus natural availability

P13 event-stratified transfer availability:

- `81.79%`.

On the same fresh transfer trajectories with the forced-outage intervention removed, natural-stream availability was still only:

- `86.69%`.

Therefore the H1 failure is not primarily an artifact of the event-stratified outage schedule.

## Natural-stream unavailable reasons

Across `8,640` truth-visible natural-stream transfer frames:

- available: `7,490`;
- unavailable: `1,150`.

Unavailable causal reasons:

- `insufficient_anchors`: `611` frames;
- `gap_beyond_horizon`: `539` frames.

## Event-stratified unavailable reasons

Across the event-stratified transfer:

- unavailable: `1,573` frames;
- `insufficient_anchors`: `749`;
- `gap_beyond_horizon`: `824`.

Assigned-gap-stratum contribution to event unavailable rows:

- gap-3 strata: `452`;
- gap-5 strata: `470`;
- gap-7 strata: `651`.

## Composition concentration

Natural-stream unavailable rows were overwhelmingly concentrated in the two hardest P13 transfer compositions:

- `small_scale+oblique+dim+blur_noise+low_contrast+temporal_dropout`: `663` unavailable frames;
- `edge+oblique+dim+low_contrast+temporal_dropout`: `366` unavailable frames.

Together these account for `1,029 / 1,150 = 89.48%` of natural-stream unavailable frames.

The next largest natural-stream composition had only `60` unavailable frames.

This indicates a **compound-shift anchor-acquisition/continuity failure mode**, not a uniform availability loss across the benchmark.

## Natural-stream interval diagnostic

The natural-stream uncertainty result showed the same general P13 pattern:

- coverage/calibration were substantially improved by severity-conditioned Mondrian conformal;
- availability remained below H1;
- lateral p95 interval-tail efficiency remained above the H4 threshold.

Natural-stream H1 availability: `86.69%`.

Natural-stream lateral p95 half-width / p95 error: `2.656x`.

Natural-stream altitude p95 half-width / p95 error: `1.735x`.

Thus the remaining P13 failures are not created solely by the forced-gap cohort.

## Interpretation

P13 moved the research bottleneck.

The uncertainty-calibration problem that dominated P12 is largely solved on fresh P13 transfer evidence: overall, continuity, base-output, and high-severity coverage all passed.

The next problem is causal estimate availability under severe compound visual degradation:

1. many sequences fail to obtain enough genuine anchors early enough;
2. many later gaps exceed the frozen seven-frame nonrecursive continuation horizon;
3. these failures are highly concentrated in a small number of hardest composition regimes.

A P14 revision should therefore target **anchor acquisition and bounded continuity under compound shift**, not relax coverage gates or simply inflate uncertainty.

Any P14 method must use new seeds/families and preregister before data generation.

## Claim boundaries

- descriptive post-exposure analysis only;
- `simulation_only = true`;
- `safety_acceptance = false`;
- `controller_tuning_allowed = false`;
- no physical-flight validation claim;
- no controller-performance claim;
- no new raw-camera accuracy claim.
