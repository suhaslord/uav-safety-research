from __future__ import annotations

import argparse
import os
from pathlib import Path

import scripts.run_phase10r_generalization as phase10r


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--no-raw", action="store_true")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    development = phase10r.run_split("development", phase10r.DEV_SEED, args.out, not args.no_raw)
    candidate_calibration = phase10r.calibrate(development, "candidate")
    baseline_calibration = phase10r.calibrate(development, "baseline")
    phase10r.dump(args.out / "candidate_uncertainty_calibration.json", candidate_calibration)
    phase10r.dump(args.out / "baseline_uncertainty_calibration.json", baseline_calibration)

    freeze = {
        "schema": "aegisland.phase10r.candidate-freeze.v1",
        "git_sha": os.getenv("GITHUB_SHA", "local-smoke"),
        "development_seed_seen": phase10r.DEV_SEED,
        "validation_seed_unseen_at_candidate_selection": phase10r.VAL_SEED,
        "partial_min_visible_fraction": phase10r.MIN_VISIBLE,
        "historical_phase10_holdout_used_for_selection": False,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
    }
    phase10r.dump(args.out / "candidate_freeze.json", freeze)

    validation = phase10r.run_split("validation", phase10r.VAL_SEED, args.out, not args.no_raw)
    result = phase10r.summarize(development, validation, candidate_calibration, baseline_calibration)
    result["candidate_freeze"] = freeze
    phase10r.dump(args.out / "validation_result.json", result)

    h1, h2, h3 = result["h1"], result["h2"], result["h3"]
    summary = (
        "# Phase 10R trajectory-held-out validation\n\n"
        f"- all preregistered validation gates passed: **{result['all_preregistered_validation_gates_pass']}**\n"
        f"- difficult miss rate: Phase 9 `{100*h1['baseline_miss_rate']:.2f}%` → Phase 10R `{100*h1['candidate_miss_rate']:.2f}%`\n"
        f"- relative miss reduction: **{100*h1['relative_miss_reduction']:.1f}%**\n"
        f"- lateral / altitude MAE improvement: **{100*h2['lateral_mae_relative_improvement']:.1f}% / {100*h2['altitude_mae_relative_improvement']:.1f}%**\n"
        f"- lateral / altitude p95 improvement: **{100*h2['lateral_p95_relative_improvement']:.1f}% / {100*h2['altitude_p95_relative_improvement']:.1f}%**\n"
        f"- mean absolute coverage error: **{100*h3['mean_absolute_coverage_error']:.2f} pp**\n"
        f"- 95% coverage: **{100*h3['coverage']['lateral']['0.95']:.1f}% lateral / {100*h3['coverage']['altitude']['0.95']:.1f}% altitude**\n\n"
        "Simulation-only development/validation evidence. This is not the new frozen holdout and is not a physical-flight safety acceptance.\n"
    )
    (args.out / "summary.md").write_text(summary, encoding="utf-8")

    names = [
        "development_frames.csv",
        "validation_frames.csv",
        "candidate_uncertainty_calibration.json",
        "baseline_uncertainty_calibration.json",
        "candidate_freeze.json",
        "validation_result.json",
        "summary.md",
    ]
    phase10r.dump(
        args.out / "result_manifest.json",
        {
            "schema": "aegisland.phase10r.generalization.v1",
            "files": {
                name: {"sha256": phase10r.fh(args.out / name), "bytes": (args.out / name).stat().st_size}
                for name in names
            },
        },
    )
    print(summary)


if __name__ == "__main__":
    main()
