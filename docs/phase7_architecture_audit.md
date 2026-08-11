# Phase 7 architecture audit trail

## Purpose

This document records correctness issues found while building the Phase 7 external-validity stress program and how each was resolved **before accepting a current-architecture development result**.

The audit is intentionally separate from outcome reporting. A modeling bug is not a scientific result, and a development result produced by a superseded architecture is not silently mixed with a later corrected architecture.

Frozen Phase 6B remains tied to `b4e9838555e935a5ec42690495315473629b58f6` and is not modified by this work.

## Superseded Phase 7 attempts

Early Phase 7 attempts remain part of the GitHub/Actions history but are superseded for interpretation for the reasons below.

### Delayed-new reference updates marked non-fresh

The first latency interface treated any transported update as non-fresh. That prevented the existing lateral-bias estimator from learning from newly arrived delayed GNSS-like evidence.

**Resolution:** freshness is defined at delivery, not as zero transport delay.

### History-index latency model

The initial latency shortcut selected an older history element by index. Under changing latency it could re-expose an old sample as fresh, move backward in acquisition time, or create artificial reference unavailability.

**Resolution:** latency now uses a scheduled packet-delivery queue with acquisition timestamps, monotonically advancing delivered acquisitions, stale-state aging, and obsolete-packet suppression.

### Transport diagnostic reported scheduled instead of actual stale age

During a latency transition, a held packet could have been acquired with one scheduled delay but be several steps old when actually used.

**Resolution:** the benchmark separates the currently configured latency from the actual transport age of the estimate being used and also records reference-state age.

### Shared dropout was not truly common-mode

The first shared-dropout model gave the two streams similar dropout probabilities but allowed independent random outcomes.

**Resolution:** one Bernoulli event is sampled for each active fault frame and the same event blacks out both the image observation and reference observation on that frame. The realized common-outage rate is recorded.

### Dropped image retained component confidence

An image could be marked dropped while `p_x_good` and `p_z_good` still came from the rendered frame, allowing unavailable imagery to retain trustworthy-looking component scores.

**Resolution:** a dropped Phase 7 image forces both component confidence values to zero for that frame.

### Vertical-only updates counted as fresh lateral evidence

A scalar reference `fresh` bit initially represented GNSS, barometer, or range updates. The historical V3 bias estimator uses that bit to add lateral disagreement samples, so a vertical-only update could duplicate stale lateral evidence.

**Resolution:** `ReferenceObservation.fresh` means newly delivered GNSS-like lateral evidence in Phase 7. Per-sensor freshness remains available in diagnostics.

### One freshness bit controlled both lateral and altitude takeover strength

The Phase 6B component adapter historically used one reference-freshness flag for both components. That is appropriate for the historical single reference stream but not for asynchronous Phase 7 sensors.

**Resolution:** the adapter now accepts optional lateral and altitude reference-freshness flags. Phase 7 supplies delivered GNSS freshness for lateral takeover and delivered barometer/range freshness for altitude takeover. When those optional flags are omitted, the historical scalar behavior is preserved, protecting Phase 6B compatibility.

### Reference sensor RNG coupling

GNSS-like, barometric-like, and range-like measurements initially shared one random-number stream. Plant-dependent range activation could therefore change the later GNSS/barometer noise sequence and contaminate a paired plant comparison.

**Resolution:** the three sensor channels use isolated deterministic child RNG streams with fixed scheduled draw patterns. The range stream consumes its scheduled draws even while out of range.

### Camera RNG coupling across frames

Synthetic occlusion can consume a geometry-dependent number of random pixel draws. A persistent camera RNG could therefore drift apart after the legacy and stronger plant trajectories diverged.

**Resolution:** camera randomness is derived from `(episode seed, frame index)`. Different geometry within frame *n* cannot shift the random sequence used for frame *n+1*.

## Current audited semantics

A current Phase 7 development bundle is expected to record:

- `image_rng_model = frame_indexed_v1`
- `sensor_transport_model = scheduled_delivery_queue_v1`
- `sensor_rng_model = channel_isolated_time_indexed_v1`
- `reference_lateral_freshness_model = gnss_delivery_only_v1`
- `component_reference_freshness_model = per_component_delivered_v1`
- `shared_dropout_model = single_common_event_blackout_v1`
- `phase7_architecture_status = current_development_architecture`

The acceptance workflow verifies those fields together with the exact Git commit, development-seed status, expected result-cell count, paired-effect count, and result-manifest hashes before uploading the artifact.

## Pairing interpretation

The legacy-vs-stronger-plant comparison is intended to isolate **plant-model sensitivity**, not to claim that the two trajectories see identical measurements. Once the plant states diverge, sensor values and rendered geometry should differ because they are functions of different states.

What is held paired is the exogenous randomness structure:

- same episode initialization/environment seed;
- same fault schedule seed;
- same frame-indexed camera random stream for each frame number;
- same time-indexed GNSS/barometer/range random streams;
- same calibration models and frozen component gates;
- same controller/fusion/supervisor configuration.

This is stronger than merely reusing one top-level seed and makes paired outcome transitions easier to interpret.

## Evidence policy

1. Superseded attempts remain visible in Actions history and are not relabeled as accepted evidence.
2. The first corrected-architecture factorial remains **development evidence** because seed `979797` is already seen and each cell is intentionally small.
3. No Phase 7 held-out seed is declared until the architecture and evaluation protocol are explicitly frozen in a later commit.
4. A bad common-mode result is not a reason to retune frozen Phase 6B thresholds.
5. A zero observed unsafe-touchdown rate in a small cell is not evidence of zero real risk.
6. Physical flight remains outside the scope of this repository.
