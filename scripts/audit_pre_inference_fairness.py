"""Pre-inference fairness analysis script.
Evaluates achieved dose distribution per topology x requested dose,
computes N, mean, median, SD, min, max, p5, p95, and checks common support.
"""
import csv
import json
from collections import defaultdict
from pathlib import Path
import numpy as np

CSV_PATH = Path("results/phase25_occlusion_topology/topology_views.csv")

def main():
    rows = []
    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    print(f"Loaded {len(rows)} rows from {CSV_PATH}")

    # Group by (topology, requested_dose)
    grouped = defaultdict(list)
    topologies = sorted(list(set(r["topology"] for r in rows)))
    doses = sorted(list(set(float(r["requested_dose"]) for r in rows)))

    for r in rows:
        topo = r["topology"]
        req_d = float(r["requested_dose"])
        ach_d = float(r["achieved_dose"])
        grouped[(topo, req_d)].append(ach_d)

    summary = {}
    print("\n" + "="*80)
    print(f"{'Topology':<14} {'ReqDose':<8} {'N':<4} {'Mean':<8} {'Median':<8} {'SD':<8} {'Min':<8} {'Max':<8} {'P5':<8} {'P95':<8}")
    print("="*80)

    for topo in topologies:
        for d in doses:
            vals = np.array(grouped[(topo, d)])
            n = len(vals)
            mean = np.mean(vals)
            med = np.median(vals)
            sd = np.std(vals)
            vmin = np.min(vals)
            vmax = np.max(vals)
            p5 = np.percentile(vals, 5)
            p95 = np.percentile(vals, 95)
            key = f"{topo}__dose_{d:.2f}"
            summary[key] = {
                "topology": topo,
                "requested_dose": d,
                "n": n,
                "mean": float(mean),
                "median": float(med),
                "sd": float(sd),
                "min": float(vmin),
                "max": float(vmax),
                "p5": float(p5),
                "p95": float(p95),
            }
            print(f"{topo:<14} {d:<8.2f} {n:<4} {mean:<8.4f} {med:<8.4f} {sd:<8.4f} {vmin:<8.4f} {vmax:<8.4f} {p5:<8.4f} {p95:<8.4f}")

    # Check common support between topologies
    # Specifically for each topology, what is the range of achieved doses?
    print("\n" + "="*80)
    print("ACHIEVED DOSE RANGE BY TOPOLOGY (over all non-zero doses)")
    print("="*80)
    topo_achieved = {}
    for topo in topologies:
        all_vals = [float(r["achieved_dose"]) for r in rows if r["topology"] == topo and float(r["requested_dose"]) > 0]
        topo_achieved[topo] = np.array(all_vals)
        print(f"{topo:<14}: min={np.min(all_vals):.4f}, max={np.max(all_vals):.4f}, median={np.median(all_vals):.4f}, p5={np.percentile(all_vals, 5):.4f}, p95={np.percentile(all_vals, 95):.4f}")

    # Check dose overlap by dose bins
    bins = [(0.0, 0.05), (0.05, 0.15), (0.15, 0.25), (0.25, 0.35), (0.35, 0.45), (0.45, 0.55), (0.55, 0.65), (0.65, 0.75)]
    print("\n" + "="*80)
    print("COUNT OF OBSERVATIONS IN ACHIEVED-DOSE BINS ACROSS TOPOLOGIES")
    print("="*80)
    header = f"{'Bin':<16} " + " ".join(f"{topo:<14}" for topo in topologies)
    print(header)
    for b_low, b_high in bins:
        counts = []
        for topo in topologies:
            c = sum(1 for r in rows if r["topology"] == topo and b_low <= float(r["achieved_dose"]) < b_high)
            counts.append(c)
        bin_str = f"[{b_low:.2f}, {b_high:.2f})"
        row_str = f"{bin_str:<16} " + " ".join(f"{c:<14}" for c in counts)
        print(row_str)

    # Let's also check STRIPED specifically: why did STRIPED have mean error 0.0586 and max 0.3667?
    print("\n" + "="*80)
    print("STRIPED BREAKDOWN BY OBJECT SIZE (SEQUENCE):")
    print("="*80)
    for seq in ["land_pad", "land_pad2"]:
        seq_striped_err = [float(r["dose_error"]) for r in rows if r["topology"] == "STRIPED" and r["sequence"] == seq and float(r["requested_dose"]) > 0]
        print(f"Sequence {seq}: N={len(seq_striped_err)}, mean_error={np.mean(seq_striped_err):.4f}, max_error={np.max(seq_striped_err):.4f}, median={np.median(seq_striped_err):.4f}")

    # Save summary json
    out_json = Path("results/phase25_occlusion_topology/pre_inference_fairness_summary.json")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved fairness summary to {out_json}")

if __name__ == "__main__":
    main()
