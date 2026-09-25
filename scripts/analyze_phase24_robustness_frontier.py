#!/usr/bin/env python3
"""Reproducible descriptive reanalysis for Phase 24."""
from __future__ import annotations
import argparse, csv, hashlib, json, math
from pathlib import Path
from statistics import mean

EXPECTED = ("clean", "blur", "low_light", "noise", "occlusion", "mixed")
SEVERE = ("occlusion", "mixed")
FIELDS = ("condition", "baseline_recall", "phase23_recall", "recall_gain", "baseline_map50", "phase23_map50", "map50_gain")


def analyze(source_csv: Path) -> dict:
    raw = source_csv.read_bytes()
    rows = list(csv.DictReader(raw.decode("utf-8-sig").splitlines()))
    names = tuple(row.get("condition") for row in rows)
    if names != EXPECTED:
        raise ValueError(f"Expected ordered conditions {EXPECTED}; got {names}")
    for row in rows:
        missing = [field for field in FIELDS if field not in row]
        if missing:
            raise ValueError(f"Missing CSV fields: {missing}")
        for field in FIELDS[1:]:
            row[field] = float(row[field])
            if not math.isfinite(row[field]):
                raise ValueError(f"Non-finite {field} for {row['condition']}")
        if not math.isclose(row["phase23_recall"] - row["baseline_recall"], row["recall_gain"], abs_tol=1e-9):
            raise ValueError(f"Recall delta does not reconcile for {row['condition']}")
        if not math.isclose(row["phase23_map50"] - row["baseline_map50"], row["map50_gain"], abs_tol=1e-9):
            raise ValueError(f"mAP50 delta does not reconcile for {row['condition']}")

    labels = {"clean": "Clean", "blur": "Blur", "low_light": "Low light", "noise": "Noise", "occlusion": "Occlusion", "mixed": "Mixed stress"}
    conditions = [{
        "condition": row["condition"], "label": labels[row["condition"]],
        "baseline": {"recall": row["baseline_recall"], "map50": row["baseline_map50"]},
        "phase23": {"recall": row["phase23_recall"], "map50": row["phase23_map50"]},
        "delta": {"recall": row["recall_gain"], "map50": row["map50_gain"]},
    } for row in rows]

    baseline_map = mean(row["baseline_map50"] for row in rows)
    phase23_map = mean(row["phase23_map50"] for row in rows)
    baseline_recall = mean(row["baseline_recall"] for row in rows)
    phase23_recall = mean(row["phase23_recall"] for row in rows)
    severe_rows = [row for row in rows if row["condition"] in SEVERE]
    severe_baseline_map = mean(row["baseline_map50"] for row in severe_rows)
    severe_phase23_map = mean(row["phase23_map50"] for row in severe_rows)
    severe_baseline_recall = mean(row["baseline_recall"] for row in severe_rows)
    severe_phase23_recall = mean(row["phase23_recall"] for row in severe_rows)
    improved = [row["condition"] for row in rows if row["map50_gain"] > 0]
    regressed = [row["condition"] for row in rows if row["map50_gain"] < 0]

    summary = {
        "condition_count": len(rows),
        "map50_improved_conditions": improved,
        "map50_regressed_conditions": regressed,
        "macro_map50": {"baseline": baseline_map, "phase23": phase23_map, "delta": phase23_map-baseline_map, "relative_percent": (phase23_map/baseline_map-1)*100},
        "macro_recall": {"baseline": baseline_recall, "phase23": phase23_recall, "delta": phase23_recall-baseline_recall, "relative_percent": (phase23_recall/baseline_recall-1)*100},
        "severe_tail": {
            "conditions": list(SEVERE),
            "macro_map50_baseline": severe_baseline_map,
            "macro_map50_phase23": severe_phase23_map,
            "macro_map50_delta": severe_phase23_map-severe_baseline_map,
            "macro_map50_relative_percent": (severe_phase23_map/severe_baseline_map-1)*100,
            "macro_recall_baseline": severe_baseline_recall,
            "macro_recall_phase23": severe_phase23_recall,
            "macro_recall_delta": severe_phase23_recall-severe_baseline_recall,
            "macro_recall_relative_percent": (severe_phase23_recall/severe_baseline_recall-1)*100,
        },
    }
    return {
        "schema_version": "phase24.robustness-audit.v1",
        "phase": "Phase 24",
        "title": "Robustness frontier audit",
        "analysis_type": "descriptive_reanalysis",
        "status": "complete_reanalysis_no_new_training",
        "claim": "The Phase 23 six-condition average improves, while occlusion and mixed stress regress sharply.",
        "new_model_training": False,
        "new_predictions_generated": False,
        "source": {"repository_path": "results/phase23_robust_detector/robustness_comparison.csv", "sha256": hashlib.sha256(raw).hexdigest()},
        "dataset": {
            "name": "KIOS Aerial Landing Pad, Unreal Engine Dataset (2024)",
            "total_labeled_frames": 422, "train_frames": 252, "validation_frames": 64,
            "embargo_frames": 20, "heldout_test_frames": 86,
            "same_temporal_holdout_reused_across_conditions": True,
            "condition_views_are_independent_samples": False,
        },
        "method": {
            "macro": "Unweighted arithmetic mean of the six published condition-level metrics.",
            "severe_tail": "Unweighted mean of occlusion and mixed-stress condition metrics.",
            "confidence_intervals": None, "per_frame_predictions_available": False,
        },
        "limits": {
            "safety_acceptance": False, "controller_tuning_allowed": False, "flight_safety_claim": False,
            "note": "Aggregate detector metrics do not establish landing safety, controller performance, or real-flight readiness.",
        },
        "summary": summary, "conditions": conditions,
    }


def write_outputs(root: Path, result: dict) -> None:
    result_dir = root / "results" / "phase24_robustness_audit"
    web_dir = root / "deploy" / "vercel" / "data"
    result_dir.mkdir(parents=True, exist_ok=True)
    web_dir.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, indent=2, sort_keys=False) + "\n"
    (result_dir / "summary.json").write_text(payload, encoding="utf-8")
    (web_dir / "phase24-results.json").write_text(payload, encoding="utf-8")

    with (result_dir / "condition_frontier.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("condition", "baseline_recall", "phase23_recall", "recall_delta", "baseline_map50", "phase23_map50", "map50_delta"))
        for row in result["conditions"]:
            writer.writerow((row["condition"], f'{row["baseline"]["recall"]:.12g}', f'{row["phase23"]["recall"]:.12g}', f'{row["delta"]["recall"]:.12g}', f'{row["baseline"]["map50"]:.12g}', f'{row["phase23"]["map50"]:.12g}', f'{row["delta"]["map50"]:.12g}'))

    s = result["summary"]
    sm, sr, tail = s["macro_map50"], s["macro_recall"], s["severe_tail"]
    report = [
        "# Phase 24 · Robustness frontier audit", "",
        "**Type:** Descriptive reanalysis of committed Phase 23 condition aggregates.  ",
        "**New detector training or predictions:** None.  ",
        f"**Source SHA-256:** {result['source']['sha256']}", "",
        "## Readout", "",
        f"- Equal-weight macro mAP50: **{sm['baseline']:.3f} → {sm['phase23']:.3f}** ({sm['delta']:+.3f}, {sm['relative_percent']:+.1f}% relative).",
        f"- Equal-weight macro recall: **{sr['baseline']:.3f} → {sr['phase23']:.3f}** ({sr['delta']:+.3f}, {sr['relative_percent']:+.1f}% relative).",
        f"- mAP50 improves in **{len(s['map50_improved_conditions'])}/6** conditions; it regresses in **{len(s['map50_regressed_conditions'])}/6**.",
        f"- Occlusion + mixed-stress macro mAP50: **{tail['macro_map50_baseline']:.3f} → {tail['macro_map50_phase23']:.3f}** ({tail['macro_map50_delta']:+.3f}, {tail['macro_map50_relative_percent']:+.1f}% relative).",
        "", "## Method and limits", "",
        "The macros are unweighted arithmetic means of the six published condition-level metrics. The occlusion + mixed-stress readout equally averages those two conditions. All conditions reuse the same 86-frame temporal test holdout; the six transformed views are not 516 independent frames.",
        "",
        "The repository contains aggregate metrics, not per-frame predictions, so this audit reports no confidence intervals or significance tests. Detector metrics alone do not establish landing safety, controller performance, or real-flight readiness. safety_acceptance=false; controller_tuning_allowed=false.",
        "", "## Reproduce", "",
        "Run python scripts/analyze_phase24_robustness_frontier.py from the repository root. The script validates the source deltas and writes this summary, summary.json, condition_frontier.csv, and the dashboard data JSON.",
        "",
    ]
    (result_dir / "summary.md").write_text("\n".join(report), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    source = args.root / "results" / "phase23_robust_detector" / "robustness_comparison.csv"
    result = analyze(source)
    write_outputs(args.root, result)
    print(f"Wrote Phase 24 audit from {result['source']['repository_path']}")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
