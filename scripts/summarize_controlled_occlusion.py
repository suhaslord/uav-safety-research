#!/usr/bin/env python3
"""Descriptive research answers from authenticated saved controlled-occlusion cases.

This is a new retrospective summary, not a new detector run, preregistered
change-point test, physical occlusion measure, or deployment threshold.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from phase25_lib import sha256_file
from verify_phase22_occlusion_v2 import verify
from verify_phase23_research_replay import authenticate_recovery, boolean, read_rows, RECOVERY_COMMIT


def summarize(output: Path) -> tuple[dict, list[dict], list[dict]]:
    replay = verify(output)
    authenticate_recovery()
    frames = read_rows(output / "frame_condition_metrics.csv")
    doses = read_rows(output / "dose_response.csv")
    lookup = {(r["frame_id"], int(r["dose_index"])): r for r in frames}
    ids = sorted({r["frame_id"] for r in frames})
    if len(ids) != 86 or len(lookup) != 516 or len(doses) != 6:
        raise ValueError("Incomplete controlled-occlusion population")
    onset = []
    for frame in ids:
        curve = [lookup[frame, i] for i in range(6)]
        success = [boolean(r["frame_success"]) for r in curve]
        first = next((i for i in range(1, 6) if success[0] and not success[i]), None)
        row = curve[first] if first is not None else None
        onset.append({"frame_id": frame, "sequence": curve[0]["sequence"], "clean_success": success[0],
                      "first_observed_new_loss_dose_index": first,
                      "requested_dose_at_first_loss": float(row["requested_dose"]) if row else None,
                      "achieved_box_occlusion_at_first_loss": float(row["achieved_annotation_box_mask_fraction"]) if row else None,
                      "later_recovery_after_first_loss": any(success[first + 1:]) if first is not None else False,
                      "success_at_maximum_dose": success[-1]})
    grouped = []
    for sequence in sorted({r["sequence"] for r in frames}):
        subset = [r for r in onset if r["sequence"] == sequence]
        for i in range(6):
            cases = [lookup[r["frame_id"], i] for r in subset]
            grouped.append({"sequence": sequence, "dose_index": i, "source_frames": len(cases),
                            "successful_frames": sum(boolean(r["frame_success"]) for r in cases),
                            "frame_success_fraction": sum(boolean(r["frame_success"]) for r in cases) / len(cases),
                            "mean_achieved_box_occlusion": sum(float(r["achieved_annotation_box_mask_fraction"]) for r in cases) / len(cases)})
    measured = [{"dose_index": int(r["dose_index"]), "requested_dose": float(r["requested_dose"]),
                 "mean_achieved_box_occlusion": 1 - float(r["achieved_visible_annotation_box_fraction_mean"]),
                 "successful_frames": int(r["frame_success_count"]), "frame_success_fraction": float(r["frame_success_fraction"]),
                 "mean_best_overlap_confidence": float(r["best_overlap_confidence_mean"]),
                 "mean_best_iou": float(r["target_best_iou_mean"]), "false_positives_per_frame": float(r["false_positives_per_frame"])} for r in doses]
    counts = Counter(r["first_observed_new_loss_dose_index"] for r in onset if r["clean_success"])
    return {"schema": "aegisland.controlled-occlusion-descriptive-summary.v1", "status": "PASS",
            "recovery_source_commit": RECOVERY_COMMIT, "inference_freeze_commit": replay["freeze_commit"],
            "artifact_replay": replay, "detector_inference_run": False, "source_frames": 86, "capture_sequences": 2,
            "object_classes": ["landing_pad"], "baseline_failures_before_added_occlusion": sum(not r["clean_success"] for r in onset),
            "clean_successes": sum(r["clean_success"] for r in onset),
            "first_observed_loss_counts_among_clean_successes": {str(k): v for k, v in counts.items()},
            "frames_with_later_recovery": sum(r["later_recovery_after_first_loss"] for r in onset),
            "dose_response": measured, "by_sequence": grouped,
            "shape_interpretation": "Confidence and localization degrade across measured dose; frame recall declines modestly and nonmonotonically. These six points do not establish an abrupt universal failure threshold.",
            "onset_definition": "First sampled added-occlusion case that fails among frames successful at dose zero; an exploratory observation, not a preregistered breakpoint or deployment threshold.",
            "limitations": ["Annotation-box pixel occlusion is not physical pad-surface occlusion.",
                            "One target class and two temporally dependent sequences; no independent-dataset inference.",
                            "The original raw-source attempt failed its clean gate and produced no treatment predictions.",
                            "This summary uses the separately frozen Q95-representation v2 follow-up, not a retrospective relabeling of the failed original attempt.",
                            "Confidence floor 0.001 retains hundreds of false positives per frame; frame success is not precision or flight safety.",
                            "No threshold criterion was preregistered in the recovered original protocol; none is invented here."],
            "source_sha256": {name: sha256_file(output / name) for name in ["run_outcome.json", "protocol.json", "dose_response.csv", "frame_condition_metrics.csv", "target_mask_manifest.csv"]}}, onset, grouped


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, default=ROOT / "results/phase22_occlusion_v2")
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    if args.out_dir.exists():
        p.error("Use a new output directory; historical summaries are not overwritten")
    report, onset, groups = summarize(args.source)
    args.out_dir.mkdir(parents=True)
    for name, rows in [("first_observed_losses.csv", onset), ("sequence_dose_response.csv", groups)]:
        with (args.out_dir / name).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    d = report["dose_response"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    x = [r["mean_achieved_box_occlusion"] for r in d]
    axes[0].plot(x, [r["frame_success_fraction"] for r in d], "o-")
    axes[0].set(ylabel="Frame success fraction (IoU ≥ 0.50)", ylim=(0, 1))
    axes[1].plot(x, [r["mean_best_overlap_confidence"] for r in d], "o-")
    axes[1].set(ylabel="Mean best-overlap confidence (all targets)", ylim=(0, 1))
    for ax in axes:
        ax.set(xlabel="Mean measured annotation-box occlusion", xlim=(0, 0.8))
        ax.grid(alpha=0.2)
    fig.suptitle("Frozen controlled-occlusion v2 · 86 KIOS frames · descriptive, not independent validation")
    fig.tight_layout(); fig.savefig(args.out_dir / "controlled_occlusion.png", dpi=180); plt.close(fig)
    report["output_sha256"] = {name: sha256_file(args.out_dir / name) for name in ["first_observed_losses.csv", "sequence_dose_response.csv", "controlled_occlusion.png"]}
    report["summary_script_sha256"] = sha256_file(Path(__file__))
    (args.out_dir / "analysis.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ["status", "baseline_failures_before_added_occlusion", "clean_successes", "first_observed_loss_counts_among_clean_successes", "frames_with_later_recovery"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
