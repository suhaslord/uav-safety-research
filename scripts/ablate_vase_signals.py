import csv
import json
import math
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAIRED_OUTCOMES = ROOT / "results/phase25_failure_atlas/paired_frame_outcomes.csv"
OUTPUT_DIR = ROOT / "results/vase_offline_signals"

def compute_auroc(scores, labels):
    if len(scores) != len(labels):
        return None
    positives = [s for s, y in zip(scores, labels) if y == 1]
    negatives = [s for s, y in zip(scores, labels) if y == 0]
    if not positives or not negatives:
        return None
    
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

def bootstrap_auroc(scores, labels, n_bootstraps=1000):
    np.random.seed(42)
    aurocs = []
    scores = np.array(scores)
    labels = np.array(labels)
    n = len(scores)
    for _ in range(n_bootstraps):
        idx = np.random.choice(np.arange(n), size=n, replace=True)
        boot_scores = scores[idx]
        boot_labels = labels[idx]
        if len(np.unique(boot_labels)) > 1:
            a = compute_auroc(boot_scores, boot_labels)
            if a is not None:
                aurocs.append(a)
    if not aurocs:
        return None, None
    return np.percentile(aurocs, 2.5), np.percentile(aurocs, 97.5)

def main():
    df = pd.read_csv(PAIRED_OUTCOMES)
    
    # Fill NAs
    df["phase23_confidence"] = df["phase23_confidence"].fillna(0.0)
    df["target_area_ratio"] = df["target_area_ratio"].fillna(0.0)
    df["phase23_iou"] = df["phase23_iou"].fillna(0.0)
    df["view_brightness_mean"] = df["view_brightness_mean"].fillna(0.0)
    df["view_sharpness"] = df["view_sharpness"].fillna(0.0)
    df["phase23_fp"] = df["phase23_fp"].fillna(0.0)
    
    # Compute signals
    signals = {}
    signals["naive_confidence"] = df["phase23_confidence"].to_numpy()
    signals["scale_only"] = np.sqrt(np.clip(df["target_area_ratio"].to_numpy(), 0, 1))
    signals["scale_conditioned_confidence"] = signals["naive_confidence"] * signals["scale_only"]
    
    max_fp = df["phase23_fp"].max() if df["phase23_fp"].max() > 0 else 1.0
    signals["fp_rate_signal"] = 1.0 - (df["phase23_fp"].to_numpy() / max_fp)
    
    signals["iou_derived"] = df["phase23_iou"].to_numpy()
    signals["confidence_iou_combo"] = signals["naive_confidence"] * signals["iou_derived"]
    
    signals["brightness_derived"] = df["view_brightness_mean"].to_numpy()
    signals["sharpness_derived"] = df["view_sharpness"].to_numpy()

    df_signals = pd.DataFrame(signals)
    df_signals["phase23_pass"] = df["phase23_pass"].astype(int)
    df_signals["condition"] = df["condition"]
    df_signals["size_bin"] = df["target_area_quartile"]
    
    # 1. VERIFY Original AUROC Numbers
    print("=== Verification of reported AUROC ===")
    safe_labels = df_signals["phase23_pass"].tolist()
    severe_mask = df_signals["condition"].isin(["occlusion", "mixed"])
    severe_labels = df_signals.loc[severe_mask, "phase23_pass"].tolist()
    
    for sig in ["scale_conditioned_confidence", "naive_confidence", "fp_rate_signal"]:
        s_safe = df_signals[sig].tolist()
        s_sev = df_signals.loc[severe_mask, sig].tolist()
        a_safe = compute_auroc(s_safe, safe_labels)
        a_sev = compute_auroc(s_sev, severe_labels)
        print(f"{sig:30s} Safe-vs-Degraded: {a_safe:.4f}, Severe: {a_sev:.4f}")

    # 2 & 3. Perform ablations and stability tests
    tasks = []
    
    signal_names = [
        "naive_confidence", "scale_only", "scale_conditioned_confidence", 
        "iou_derived", "confidence_iou_combo", "brightness_derived", "sharpness_derived"
    ]
    
    ablation_records = []
    ablation_report = {"signals": {}}
    
    for sig in signal_names:
        sig_scores = df_signals[sig].tolist()
        
        # Overall Safe vs Degraded
        auroc_all = compute_auroc(sig_scores, safe_labels)
        ci_lower, ci_upper = bootstrap_auroc(sig_scores, safe_labels)
        
        ablation_records.append({
            "signal": sig,
            "task": "safe_vs_degraded_overall",
            "auroc": auroc_all,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "n": len(safe_labels)
        })
        
        report_data = {
            "overall_auroc": auroc_all,
            "ci_95": [ci_lower, ci_upper],
            "per_condition": {},
            "per_size": {}
        }
        
        # Per condition
        for cond in df_signals["condition"].unique():
            mask = df_signals["condition"] == cond
            c_scores = df_signals.loc[mask, sig].tolist()
            c_labels = df_signals.loc[mask, "phase23_pass"].tolist()
            if len(np.unique(c_labels)) > 1:
                a_cond = compute_auroc(c_scores, c_labels)
                report_data["per_condition"][cond] = a_cond
                
        # Per size bin
        for sz in df_signals["size_bin"].unique():
            if pd.isna(sz): continue
            mask = df_signals["size_bin"] == sz
            s_scores = df_signals.loc[mask, sig].tolist()
            s_labels = df_signals.loc[mask, "phase23_pass"].tolist()
            if len(np.unique(s_labels)) > 1:
                a_sz = compute_auroc(s_scores, s_labels)
                report_data["per_size"][sz] = a_sz
                
        ablation_report["signals"][sig] = report_data

    # Output files
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    ablation_df = pd.DataFrame(ablation_records)
    ablation_df.to_csv(OUTPUT_DIR / "ablation_table.csv", index=False)
    
    with open(OUTPUT_DIR / "ablation_report.json", "w") as f:
        json.dump(ablation_report, f, indent=2)

    print("\n=== Ablation Results ===")
    print(ablation_df.to_string(index=False))
    
if __name__ == "__main__":
    main()
