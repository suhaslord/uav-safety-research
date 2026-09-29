"""Offline evaluation of candidate reliability signals from Phase 25 paired outcomes.

This script evaluates whether frame-level observable signals from the Phase 25
paired study could distinguish safe from degraded perception, and recoverable
from catastrophic failures. It is an offline feasibility analysis only.

No frozen V3 equations, thresholds, or supervisor parameters are altered.
No new model is trained or selected. The results inform whether a future
preregistered VASE integration study is warranted.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

PAIRED_OUTCOMES = ROOT / "results/phase25_failure_atlas/paired_frame_outcomes.csv"
OUTPUT_DIR = ROOT / "results/vase_offline_signals"


def compute_auroc(scores: list[float], labels: list[int]) -> float | None:
    """Compute AUROC using the Wilcoxon-Mann-Whitney statistic.

    Returns None if all labels belong to the same class (AUROC undefined).
    """
    if len(scores) != len(labels):
        raise ValueError("scores and labels must have the same length")

    positives = [s for s, y in zip(scores, labels) if y == 1]
    negatives = [s for s, y in zip(scores, labels) if y == 0]

    if len(positives) == 0 or len(negatives) == 0:
        return None

    # Sort-based Wilcoxon-Mann-Whitney
    n_pos = len(positives)
    n_neg = len(negatives)
    count = 0
    ties = 0
    for p in positives:
        for n in negatives:
            if p > n:
                count += 1
            elif p == n:
                ties += 1
    return (count + 0.5 * ties) / (n_pos * n_neg)


def compute_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Compute candidate reliability signals for each paired view.

    Signals:
    - naive_confidence: Phase 23 top-1 TP confidence
    - scale_conditioned_confidence: c_top * sqrt(A_ratio)
    - fp_rate_signal: 1 - (phase23_fp / max(phase23_fp))  [lower FP is better]
    """
    out = df[["frame_id", "condition", "paired_outcome", "phase23_pass"]].copy()

    # Naive confidence: fill NaN with 0
    conf = df["phase23_confidence"].fillna(0.0).to_numpy(dtype=float)
    out["naive_confidence"] = conf

    # Scale-conditioned confidence: S3 = c_top * sqrt(A_ratio)
    area = df["target_area_ratio"].fillna(0.0).to_numpy(dtype=float)
    out["scale_conditioned_confidence"] = conf * np.sqrt(np.clip(area, 0, 1))

    # FP rate signal: invert FP count (lower is better for reliability)
    fp = df["phase23_fp"].fillna(0).to_numpy(dtype=float)
    max_fp = fp.max() if fp.max() > 0 else 1.0
    out["fp_rate_signal"] = 1.0 - (fp / max_fp)

    return out


def evaluate_signals(signals_df: pd.DataFrame) -> dict:
    """Evaluate each signal on two binary classification tasks."""
    signal_names = ["naive_confidence", "scale_conditioned_confidence", "fp_rate_signal"]

    # Task 1: Safe vs Degraded (phase23_pass == True -> 1, else 0)
    safe_labels = signals_df["phase23_pass"].astype(int).tolist()

    # Task 2: Recoverable vs Catastrophic
    # Among RECOVERED and BOTH FAIL only
    rec_mask = signals_df["paired_outcome"].isin(["RECOVERED", "BOTH FAIL"])
    rec_df = signals_df[rec_mask].copy()
    rec_labels = (rec_df["paired_outcome"] == "RECOVERED").astype(int).tolist()

    # Task 3: Safe vs Degraded under severe conditions only (occlusion + mixed)
    severe_mask = signals_df["condition"].isin(["occlusion", "mixed"])
    severe_df = signals_df[severe_mask].copy()
    severe_labels = severe_df["phase23_pass"].astype(int).tolist()

    tasks = []

    for task_name, task_labels, task_df in [
        ("safe_vs_degraded", safe_labels, signals_df),
        ("recoverable_vs_catastrophic", rec_labels, rec_df),
        ("safe_vs_degraded_severe", severe_labels, severe_df),
    ]:
        task_results = []
        for sig in signal_names:
            scores = task_df[sig].tolist()
            auroc = compute_auroc(scores, task_labels)
            n_pos = sum(task_labels)
            n_neg = len(task_labels) - n_pos
            task_results.append({
                "signal": sig,
                "auroc": auroc,
                "n_positive": n_pos,
                "n_negative": n_neg,
            })
        tasks.append({
            "task": task_name,
            "n_total": len(task_labels),
            "results": task_results,
        })

    return {
        "signals": signal_names,
        "tasks": tasks,
        "note": "Offline feasibility analysis only. No V3 equations or thresholds modified.",
    }


def main() -> None:
    """Run the offline signal evaluation and write results."""
    print("Loading Phase 25 paired frame outcomes...")
    df = pd.read_csv(PAIRED_OUTCOMES)
    print(f"  {len(df)} paired views loaded")

    print("Computing candidate reliability signals...")
    signals_df = compute_signals(df)

    print("Evaluating signals on classification tasks...")
    results = evaluate_signals(signals_df)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Write JSON
    json_path = OUTPUT_DIR / "signal_evaluation.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"  JSON report: {json_path}")

    # Write CSV summary
    csv_path = OUTPUT_DIR / "signal_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["signal_name", "task", "auroc", "n_positive", "n_negative"])
        writer.writeheader()
        for task in results["tasks"]:
            for result in task["results"]:
                writer.writerow({
                    "signal_name": result["signal"],
                    "task": task["task"],
                    "auroc": result["auroc"],
                    "n_positive": result["n_positive"],
                    "n_negative": result["n_negative"],
                })
    print(f"  CSV summary: {csv_path}")

    # Print summary
    print("\n=== VASE Offline Signal Evaluation ===")
    print(f"Paired views: {len(df)}")
    for task in results["tasks"]:
        print(f"\n  Task: {task['task']} (n={task['n_total']})")
        for r in task["results"]:
            auroc_str = f"{r['auroc']:.4f}" if r["auroc"] is not None else "undefined"
            print(f"    {r['signal']:40s} AUROC={auroc_str}  (+{r['n_positive']} / -{r['n_negative']})")

    print("\nNote: This is an offline feasibility analysis only.")
    print("No frozen V3 equations or thresholds were modified.")


if __name__ == "__main__":
    main()
