# Phase 25 audit corrections — 2026-10-03

The current interpretation is the [corrected descriptive report](../results/phase25_corrected_analysis_v1/report.md) and [machine-readable summary](../results/phase25_corrected_analysis_v1/summary.json). Rebuild and check them, including the public summaries, with:

```powershell
python scripts/phase25_descriptive_analysis.py
python scripts/phase25_descriptive_analysis.py --check
```

This is an explicitly post hoc correction. It uses the retained observations from commit `db7aca05382f608cbe021cabb5c32862123c7633`, with LF-normalized text hashes pinned in `phase25_descriptive_analysis_v1.json`. No new training or detector inference was performed. The historical raw tables, reports, figures, frozen protocols and October 3 release manifest remain intact as historical evidence. The inferential prose in `results/phase25_failure_atlas/{summary.md,paired_study_report.md,statistical_associations.*}` and `results/phase25_occlusion_topology/{study_report.md,statistics.json,topology_comparisons.json,ed50_estimates.json,change_point_results.json}` is superseded by this correction; those files and their figures must not be cited as current confirmatory conclusions. Original source implementations remain available at the historical commit.

## Corrections

- Report values now come from saved observations. The original topology report hardcoded crossings and change points that disagreed with its machine output, and incorrectly said OUTER_RING never fell below 50%. The paired report's printed McNemar statistic also disagreed with its saved statistic. The correction reports counts and interpolated first downward crossings, without these invalid inferential summaries.
- The original Phase 25 protocol requires descriptive results because the 86 reused frames come from only two video sequences. Treating frames, doses or conditions as independent does not resolve temporal dependence. The archived frame-bootstrap intervals and significance tests cannot establish confirmatory population findings. Training resolution, ring features and masking mechanisms were not separately tested.
- Topology contrasts compare per-frame rates at shared achieved-dose bins, average shared bins equally within each frame, then average frames equally. This replaces the pooled requested-dose contrast. Bins remain approximate matching, not identical achieved doses: the summary exposes dose distributions, shared denominators and sequence strata. Achieved doses outside `[0, 0.75)` are explicitly excluded rather than clamped. These are exploratory contrasts.
- The original zero-dose gate evaluated source clean JPEGs, while the generated controls were JPEG-reencoded. All 344 controls have different file hashes; 268 have different false-positive counts from canonical Phase 23 clean predictions. Binary frame success agrees for all controls. The corrected historical analysis cannot undo this representation difference.

## Lossless v2.1 execution

`docs/phase25_topology_lossless_v2_1.json` defines the current execution version. The prior v2 protocol and its implementation remain available at commit `b04100f24c7f504ac8813c0bb37745f9151d9061`; neither method has produced new detector inference. The current method retains the authenticated Phase 23 checkpoint, deterministic mask geometry, seed and inference settings, but generates PNG treatments. Every saved image must preserve the intended decoded RGB pixels, including exact zero-dose pixel identity. The aggregate baseline gate runs on **all actual generated zero-dose controls**, before any treatment predictions. Failure aborts treatment inference.

The runner verifies the original archive, protected source images and labels, exact source and six-condition inventories, frozen reconstruction hashes, model bundle and checkpoint, runtime versions, and committed method hashes. It rejects historical or nonempty output paths and stale treatment files, including new child directories under any frozen release result directory. Zero and positive doses use the same rasterized target area, with achieved dose saved as the unrounded ratio of masked pixels to box pixels. Dataset paths are quoted for YAML so spaces, backslashes and comment characters remain literal. A completed run records input, method, protocol, runtime and output provenance. A failure leaves an incomplete new directory for inspection; it cannot be resumed or mistaken for a completed receipt.

Commit methods and protocol before executing. Use actual authenticated paths and a new output directory:

```powershell
python scripts/execute_phase23_occlusion_topology.py --archive <verified-kios-archive> --source-root <protected-source-root> --stress-root <frozen-stress-root> --bundle <authenticated-phase23-bundle> --out-dir <new-lossless-v2-directory>
```

Lossless v2.1 inference has **not** been run as part of this correction. Its outcomes must be published separately and must not replace historical JPEG observations. The descriptive correction command is intentionally pinned to historical inputs; it must not silently analyze lossless output as the original study.

`analyze_occlusion_topology.py` forwards to the corrected descriptive analyzer. `run_occlusion_topology_experiment.py --execute` forwards to the v2.1 runner instead of its obsolete authorization placeholder. `run_phase23_paired_study.py` forwards to `run_phase25_frame_audit.py`, which requires both authenticated checkpoints and the canonical input/runtime gates; use its `--help` for current arguments. The frozen `analyze_phase25_failures.py` belongs to historical release reproduction; use the corrected descriptive analyzer for current reporting.

## Validation

The focused Phase 25 and site regression suite passes 181 tests, including the new correction and execution-gate cases. The scoped release validator authenticates all 184 frozen files and the retained detector replay. Python compilation, both existing site-data checks, corrected report/site reproducibility and the installed locked runtime check also pass. No lossless v2 detector inference or new physical validation is claimed.

The follow-up audit also checked the first branch CI run. Its full suite exposed missing recovery-commit history in a shallow checkout and a site test coupled to retired wording. CI now fetches full history as well as LFS evidence, and the site test expects the corrected descriptive status. The follow-up regression cases cover the common rasterized denominator, literal YAML paths and frozen child-directory protection. Reconstructing exact achieved doses from retained mask/box counts changes no historical bin memberships or corrected numerical conclusions.

The follow-up full local test suite, corrected report/site checks, Python compilation and the 184-file frozen-release validation pass. Four optional tests are skipped. Neither lossless execution version has been evaluated with fresh detector inference.
