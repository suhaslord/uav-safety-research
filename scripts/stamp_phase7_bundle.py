from __future__ import annotations

from pathlib import Path
import argparse
import json

from uav_safety.provenance import PHASE7_RESULT_MANIFEST_SCHEMA, write_result_manifest


BUNDLE_FILES = (
    "episodes.csv",
    "summary.csv",
    "paired_plant_effects.csv",
    "git_sha.txt",
    "run_metadata.json",
    "summary.md",
    "dashboard_bundle.json",
)

AUDITED_SEMANTICS = {
    "image_rng_model": "frame_indexed_v1",
    "sensor_transport_model": "scheduled_delivery_queue_v1",
    "sensor_rng_model": "channel_isolated_time_indexed_v1",
    "reference_lateral_freshness_model": "gnss_delivery_only_v1",
    "component_reference_freshness_model": "per_component_delivered_v1",
    "shared_dropout_model": "single_common_event_blackout_v1",
    "phase7_architecture_status": "current_development_architecture",
}


def stamp_bundle(out: Path, expected_git_sha: str) -> None:
    metadata_path = out / "run_metadata.json"
    dashboard_path = out / "dashboard_bundle.json"
    git_sha_path = out / "git_sha.txt"

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
    recorded_sha = git_sha_path.read_text(encoding="utf-8").strip()

    if recorded_sha != expected_git_sha:
        raise ValueError(f"git_sha.txt mismatch: {recorded_sha} != {expected_git_sha}")
    if metadata.get("git_sha") != expected_git_sha:
        raise ValueError("run_metadata.json Git SHA mismatch")
    if dashboard.get("metadata", {}).get("git_sha") != expected_git_sha:
        raise ValueError("dashboard bundle Git SHA mismatch")

    metadata.update(AUDITED_SEMANTICS)
    dashboard["metadata"] = dict(metadata)

    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    dashboard_path.write_text(json.dumps(dashboard, indent=2) + "\n", encoding="utf-8")

    summary_path = out / "summary.md"
    summary_text = summary_path.read_text(encoding="utf-8")
    marker = "Architecture semantics: current audited Phase 7 development architecture."
    if marker not in summary_text:
        summary_text = summary_text.replace(
            "# Phase 7 external-validity development benchmark\n",
            "# Phase 7 external-validity development benchmark\n\n"
            f"{marker}\n",
            1,
        )
        summary_path.write_text(summary_text, encoding="utf-8")

    write_result_manifest(
        out,
        BUNDLE_FILES,
        schema=PHASE7_RESULT_MANIFEST_SCHEMA,
        extra={
            "git_sha": expected_git_sha,
            "episode_seed": metadata.get("episode_seed"),
            "calibration_seed": metadata.get("calibration_seed"),
            "run_role": metadata.get("run_role"),
            **AUDITED_SEMANTICS,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Stamp audited Phase 7 architecture semantics into a result bundle.")
    parser.add_argument("out", type=Path)
    parser.add_argument("--git-sha", required=True)
    args = parser.parse_args()
    stamp_bundle(args.out, args.git_sha)
    print(f"Stamped audited Phase 7 bundle at {args.out}")


if __name__ == "__main__":
    main()
