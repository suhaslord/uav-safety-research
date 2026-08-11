# Phase 8 — higher-fidelity trace validation

## Purpose

Phase 8 asks whether the **audited Phase 7 surrogate assumptions resemble an independently generated simulator trace**. It is a model-validation phase, not a controller-tuning phase.

The Phase 7 audited development baseline is fixed for this comparison at:

`7354eeda8b975f45b659ce4f3f86c82501e6321d`

Frozen Phase 6B remains tied to:

`b4e9838555e935a5ec42690495315473629b58f6`

No Phase 8 trace result authorizes retuning the frozen Phase 6B gates or relabeling Phase 7 development evidence as a real-world safety result.

## Research question

For sensor and timing properties that can be represented in the shared offline trace schema, how different are the empirical distributions and temporal dependencies produced by the Phase 7 surrogate from those observed in an independently generated simulator trace?

A large discrepancy is a finding about **external validity of the surrogate model**. It is not a reason to edit thresholds until the same trace looks closer.

## Evidence roles

Every comparison must record exactly one external evidence status:

- `fixture_non_authoritative` — deterministic synthetic data used only to test the pipeline, reports, dashboard, hashing, and CI. It is not external-simulator evidence.
- `external_simulator_seen` — a real independent simulator trace that has already been inspected during development. Useful for diagnosis, not a held-out claim.
- `external_simulator_unseen` — an independently generated simulator trace that was not inspected while building/tuning the Phase 8 comparison machinery. This label must only be selected deliberately.

The CLI defaults to `fixture_non_authoritative` so a local test file cannot accidentally become external-validity evidence.

## Shared trace schema

Required columns remain the simulator-agnostic Phase 7 schema:

- `t_s`
- truth: `truth_x_m`, `truth_z_m`, `truth_vx_mps`, `truth_vz_mps`
- image estimate: `image_x_m`, `image_z_m`, `image_vx_mps`, `image_vz_mps`
- image diagnostics: `image_confidence`, `image_sigma_pos_m`, `image_dropped`
- reference estimate: `reference_x_m`, `reference_z_m`, `reference_vx_mps`, `reference_vz_mps`
- reference diagnostics: `reference_sigma_pos_m`, `reference_available`, `reference_fresh`

Phase 8 additionally retains these optional fields when a simulator exposes them:

- `image_transport_latency_s`
- `reference_transport_latency_s`
- `reference_state_age_s`
- `reference_delivery`

Optional fields are never filled with zeros when absent. Their comparisons become `insufficient`.

Ground-truth fields exist only to measure estimator error. They are not valid controller inputs.

## Predeclared resemblance diagnostics

The default thresholds are committed before authoritative external traces are evaluated. They are **descriptive model-resemblance thresholds**, not flight-safety thresholds.

Distribution metrics use:

- minimum samples: `20`
- KS close: `<= 0.15`
- KS mismatch: `>= 0.30`
- normalized Wasserstein-1 close: `<= 0.25`
- normalized Wasserstein-1 mismatch: `>= 0.50`

A distribution is:

- `close` only when both KS and normalized Wasserstein-1 are in the close region;
- `mismatch` when either metric reaches the mismatch region;
- `watch` otherwise;
- `insufficient` when sample support is too small or the metric is unavailable.

Wasserstein-1 is normalized by an empirical external-trace scale: the maximum of external IQR, external standard deviation, and a fixed physical floor appropriate to that feature. The floor prevents a nearly constant external signal from creating an arbitrarily large normalized value from numerical-scale differences.

Rate diagnostics use absolute-difference thresholds:

- close: `<= 0.05`
- mismatch: `>= 0.15`

Correlation/lag-1 diagnostics use absolute-difference thresholds:

- close: `<= 0.10`
- mismatch: `>= 0.30`

Thresholds are intentionally not exposed as command-line tuning flags.

## Compared properties

### Continuous/error distributions

When supported by both traces, Phase 8 compares:

- sample interval `dt`
- image lateral and vertical position error
- image lateral and vertical velocity error
- reference lateral and vertical position error
- reference lateral and vertical velocity error
- image confidence
- image reported position uncertainty
- reference reported position uncertainty
- reference-fresh inter-arrival interval
- image-drop run length
- reference-unavailability run length
- image transport latency
- reference transport latency
- reference state age

For each distribution the bundle records sample count, mean, standard deviation, 5/50/95 percentiles, KS distance, Wasserstein-1 distance, external scale, normalized Wasserstein-1, and status.

### Temporal/common-mode structure

Phase 8 also compares:

- image drop rate
- reference availability rate
- reference fresh-update rate
- simultaneous image/reference lateral error correlation
- simultaneous image/reference vertical error correlation
- lag-1 autocorrelation of image lateral error
- lag-1 autocorrelation of reference lateral error
- lag-1 autocorrelation of image vertical error
- lag-1 autocorrelation of reference vertical error

These are intended to expose independence and white-noise assumptions that marginal histograms alone can hide.

## Overall diagnostic

The bundle reports one of:

- `diagnostic_close`
- `diagnostic_watch`
- `diagnostic_mismatch`

This is **not** a safety acceptance result. The bundle always records:

- `safety_acceptance = false`
- `controller_tuning_allowed = false`

If any metric is a mismatch, the overall diagnostic is a mismatch. If there are no mismatches but at least one watch/insufficient metric, the overall diagnostic is watch. Only all-close supported metrics produce diagnostic close.

## Input and output provenance

The Phase 8 writer records for each input trace:

- source label
- evidence status
- filename
- byte size
- SHA-256
- schema validation summary

Outputs include:

- `trace_comparison.json` — complete machine-readable comparison bundle
- `metric_comparison.csv` — flat metric table
- `summary.md` — human-readable interpretation boundary and counts
- `phase8_report.html` — standalone offline report
- `run_metadata.json` — executable SHA, frozen baselines, input hashes, evidence role, and thresholds
- `result_manifest.json` — SHA-256 and byte size for every output file above

The manifest uses schema `aegisland.phase8.result-bundle.v1`.

## Running a comparison

Validate each trace independently first if desired:

```bash
python scripts/validate_external_trace.py path/to/trace.csv
```

Then run Phase 8:

```bash
python scripts/run_phase8_trace_validation.py \
  path/to/phase7_surrogate.csv \
  path/to/external_simulator.csv \
  --out results/phase8_trace_validation \
  --external-evidence-status external_simulator_seen \
  --external-source "PX4 SITL + simulator configuration identifier"
```

For a genuinely uninspected external trace, use `external_simulator_unseen` only if that provenance statement is true.

Validate the output manifest:

```bash
python scripts/validate_result_manifest.py \
  results/phase8_trace_validation/result_manifest.json \
  --schema aegisland.phase8.result-bundle.v1
```

Open `phase8_dashboard/index.html` and load `trace_comparison.json` for the interactive Trace Lab, or open `phase8_report.html` directly for a standalone report.

## Adapting a higher-fidelity simulator log

Phase 8 intentionally does not bind the repository to one simulator or binary log format. A simulator-specific adapter should:

1. export timestamps and landing-frame ground truth;
2. export the image-derived estimate actually available to the autonomy stack;
3. export the independent reference estimate actually available to the autonomy stack;
4. preserve observed dropout/availability/freshness events;
5. preserve measured transport latency/state age when available;
6. convert units to seconds, meters, and meters/second;
7. write the shared CSV schema without interpolation that fabricates sensor deliveries.

If streams run at different rates, use a time-indexed analysis export that preserves availability/freshness flags. Do not forward-fill a measurement and then mark the repeated value fresh.

The adapter itself should be versioned and its simulator configuration/source identifier recorded in `--external-source`.

## CI fixture policy

`scripts/generate_phase8_fixture_traces.py` creates deterministic synthetic traces used only to exercise the complete Phase 8 pipeline in GitHub Actions. The workflow must assert:

- evidence status is `fixture_non_authoritative`;
- claim level is `pipeline_validation_only`;
- safety acceptance is false;
- controller tuning is false;
- Phase 7 and Phase 6B baseline SHAs are exact;
- input hashes are present;
- the Phase 8 manifest validates;
- dashboard JavaScript syntax validates;
- the full pytest suite passes.

A successful fixture audit proves software correctness of the comparison path. It does **not** prove that Phase 7 resembles a higher-fidelity simulator.

## Interpretation policy

1. Preserve discrepancies, including embarrassing ones.
2. Do not tune Phase 6B or the audited Phase 7 baseline against observed Phase 8 trace results.
3. If the surrogate is later revised, version that as a new model and compare both old and new models against clearly labeled development traces.
4. Do not call an inspected trace held out.
5. Do not infer real-world safety rates from simulator resemblance.
6. Physical flight remains outside this phase.

## Completion criterion for Phase 8 software

Phase 8 implementation is complete when one exact branch head passes:

1. Python compilation;
2. Phase 7 and Phase 8 JavaScript syntax checks;
3. full pytest suite;
4. all existing CI smoke/regression benchmarks;
5. deterministic Phase 8 fixture generation;
6. end-to-end comparison CLI;
7. input provenance assertions;
8. Phase 8 result-manifest validation;
9. explicit no-tuning/no-safety-acceptance assertions;
10. Phase 7 regression factorial on the inherited code path;
11. artifact upload only after all checks above pass.

A separate scientific completion claim requires a real independently generated higher-fidelity trace. The software completion gate must not invent that evidence when no such trace has been supplied.
