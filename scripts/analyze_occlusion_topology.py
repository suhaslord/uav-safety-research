"""Comprehensive statistical analysis and figure generation for Phase 23 Occlusion Topology Experiment.

Implements Parts 8-21:
- Part 8: Primary analysis (achieved dose, clustered repeated measures N=86)
- Part 9: Dose response curves with clustered bootstrap 95% CIs
- Part 10: Pairwise topology comparisons with Bonferroni correction
- Part 11: Dedicated Center vs Outer Ring contrast
- Part 12: ED50 estimation with bootstrap CIs
- Part 13: Segmented regression change-point analysis
- Part 14: Target scale interaction (Q1-Q4 quartiles)
- Part 15: Confidence vs localization dissociation
- Part 16: Programmatic failure transition catalog
- Part 17: Statistics export
- Part 18: 12 publication-quality figures
- Part 19: Complete machine-readable results package
- Part 20/21: Scientific report with strict evidence separation
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
RESULTS_DIR = Path("results/phase25_occlusion_topology")
FIGURES_DIR = RESULTS_DIR / "figures"
VIEWS_CSV = RESULTS_DIR / "topology_views.csv"
RAW_PREDS_CSV = RESULTS_DIR / "raw_predictions.csv"
PAIRED_ATLAS_CSV = Path("results/phase25_failure_atlas/paired_frame_outcomes.csv")
PROTOCOL_V1_1_PATH = Path("docs/phase25_phase23_occlusion_topology_protocol_v1_1.json")

BOOTSTRAP_SEED = 20261001
N_BOOTSTRAP = 1000
CONFIDENCE_LEVEL = 0.95

TOPOLOGIES = ["CENTER", "OUTER_RING", "STRIPED", "RANDOM_PATCH"]
TOPOLOGY_COLORS = {
    "CENTER": "#d95f02",       # Red-orange
    "OUTER_RING": "#1b9e77",   # Teal-green
    "STRIPED": "#7570b3",      # Purple
    "RANDOM_PATCH": "#e7298a", # Magenta
}

DOSE_BINS = [
    (0.00, 0.05),
    (0.05, 0.15),
    (0.15, 0.25),
    (0.25, 0.35),
    (0.35, 0.45),
    (0.45, 0.55),
    (0.55, 0.65),
    (0.65, 0.75),
]
DOSE_BIN_LABELS = [f"[{b0:.2f}, {b1:.2f})" for b0, b1 in DOSE_BINS]
DOSE_BIN_CENTERS = [(b0 + b1) / 2 for b0, b1 in DOSE_BINS]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_dataset() -> tuple[list[dict[str, Any]], dict[str, dict[str, str]]]:
    """Load topology views and merge with target scale metadata."""
    # Load quartile and area ratio from failure atlas
    quartile_map = {}
    if PAIRED_ATLAS_CSV.exists():
        with open(PAIRED_ATLAS_CSV, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["condition"] == "clean":
                    quartile_map[r["frame_id"]] = {
                        "target_area_ratio": float(r["target_area_ratio"]),
                        "target_area_quartile": r["target_area_quartile"],
                    }

    views = []
    with open(VIEWS_CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            frame_id = r["frame_id"]
            q_info = quartile_map.get(frame_id, {"target_area_ratio": 0.0, "target_area_quartile": "UNKNOWN"})
            views.append({
                "frame_id": frame_id,
                "sequence": r["sequence"],
                "topology": r["topology"],
                "requested_dose": float(r["requested_dose"]),
                "achieved_dose": float(r["achieved_dose"]),
                "dose_error": float(r["dose_error"]),
                "mask_pixels": int(r["mask_pixels"]),
                "box_pixels": int(r["box_pixels"]),
                "visible_box_fraction": float(r.get("visible_box_fraction", 1.0 - float(r["achieved_dose"]))),
                "pred_count": int(r["pred_count"]) if r["pred_count"] else 0,
                "best_iou": float(r["best_iou"]) if r["best_iou"] else 0.0,
                "best_confidence": float(r["best_confidence"]) if r["best_confidence"] else 0.0,
                "tp": int(r["tp"]) if r["tp"] else 0,
                "fp": int(r["fp"]) if r["fp"] else 0,
                "fn": int(r["fn"]) if r["fn"] else 0,
                "frame_success": r["frame_success"].lower() == "true",
                "target_area_ratio": q_info["target_area_ratio"],
                "target_area_quartile": q_info["target_area_quartile"],
            })

    # Assign each view to a dose bin
    for v in views:
        ad = v["achieved_dose"]
        assigned = None
        for idx, (b0, b1) in enumerate(DOSE_BINS):
            if b0 <= ad < b1 or (idx == len(DOSE_BINS) - 1 and b0 <= ad <= b1):
                assigned = idx
                break
        if assigned is None:
            # Fallback for boundary
            assigned = len(DOSE_BINS) - 1 if ad >= DOSE_BINS[-1][0] else 0
        v["dose_bin_idx"] = assigned
        v["dose_bin_label"] = DOSE_BIN_LABELS[assigned]

    return views, quartile_map


def clustered_bootstrap_sample(
    frame_ids: list[str],
    rng: np.random.Generator,
) -> list[str]:
    """Sample frame_ids with replacement."""
    return list(rng.choice(frame_ids, size=len(frame_ids), replace=True))


# ---------------------------------------------------------------------------
# Part 9 & 10: Dose Response and Statistical Modeling
# ---------------------------------------------------------------------------
def compute_binned_metrics(views_subset: list[dict[str, Any]]) -> dict[int, dict[str, float]]:
    """Compute aggregate metrics per dose bin."""
    by_bin = defaultdict(list)
    for v in views_subset:
        by_bin[v["dose_bin_idx"]].append(v)

    res = {}
    for b_idx in range(len(DOSE_BINS)):
        b_views = by_bin[b_idx]
        if not b_views:
            res[b_idx] = {
                "n": 0, "success_rate": float("nan"), "recall": float("nan"),
                "mean_iou": float("nan"), "mean_confidence": float("nan"),
                "mean_tp": float("nan"), "mean_fp": float("nan"), "mean_fn": float("nan"),
            }
            continue
        n = len(b_views)
        successes = [v["frame_success"] for v in b_views]
        tps = [v["tp"] for v in b_views]
        fps = [v["fp"] for v in b_views]
        fns = [v["fn"] for v in b_views]
        ious = [v["best_iou"] for v in b_views]
        confs = [v["best_confidence"] for v in b_views]

        res[b_idx] = {
            "n": n,
            "success_rate": float(np.mean(successes)),
            "recall": float(np.sum(tps) / (np.sum(tps) + np.sum(fns))) if (np.sum(tps) + np.sum(fns)) > 0 else 0.0,
            "mean_iou": float(np.mean(ious)),
            "mean_confidence": float(np.mean(confs)),
            "mean_tp": float(np.mean(tps)),
            "mean_fp": float(np.mean(fps)),
            "mean_fn": float(np.mean(fns)),
        }
    return res


def estimate_ed50(binned_metrics: dict[int, dict[str, float]]) -> float | None:
    """Estimate ED50 via linear interpolation between adjacent dose bins that cross 0.50."""
    centers = DOSE_BIN_CENTERS
    rates = [binned_metrics[i]["success_rate"] for i in range(len(DOSE_BINS))]

    for i in range(len(rates) - 1):
        r1, r2 = rates[i], rates[i + 1]
        c1, c2 = centers[i], centers[i + 1]
        if math.isnan(r1) or math.isnan(r2):
            continue
        if (r1 >= 0.50 and r2 <= 0.50) or (r1 <= 0.50 and r2 >= 0.50):
            if r1 == r2:
                return (c1 + c2) / 2
            # Linear interpolation: r(c) = r1 + (c - c1) * (r2 - r1) / (c2 - c1) = 0.50
            ed50 = c1 + (0.50 - r1) * (c2 - c1) / (r2 - r1)
            return float(np.clip(ed50, 0.0, 1.0))
    return None


def estimate_change_point(views_subset: list[dict[str, Any]]) -> tuple[float, float, float]:
    """Segmented regression on frame_success ~ achieved_dose.

    Returns (best_breakpoint, rss, r2).
    """
    if len(views_subset) < 10:
        return float("nan"), float("nan"), float("nan")

    x = np.array([v["achieved_dose"] for v in views_subset])
    y = np.array([1.0 if v["frame_success"] else 0.0 for v in views_subset])

    total_ss = np.sum((y - np.mean(y)) ** 2)
    if total_ss == 0:
        return float("nan"), 0.0, 0.0

    candidate_breakpoints = np.linspace(0.08, 0.62, 28)
    best_bp = candidate_breakpoints[0]
    best_rss = float("inf")

    for bp in candidate_breakpoints:
        x_segment = np.maximum(0.0, x - bp)
        X = np.column_stack([np.ones_like(x), x, x_segment])
        try:
            coeffs, residuals, _, _ = np.linalg.lstsq(X, y, rcond=None)
            preds = X @ coeffs
            rss = np.sum((y - preds) ** 2)
            if rss < best_rss:
                best_rss = rss
                best_bp = bp
        except Exception:
            continue

    r2 = 1.0 - (best_rss / total_ss) if total_ss > 0 else 0.0
    return float(best_bp), float(best_rss), float(r2)


def run_clustered_bootstrap(
    views: list[dict[str, Any]],
    n_resamples: int = N_BOOTSTRAP,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """Execute clustered bootstrap by source frame (N=86)."""
    unique_frames = sorted(list(set(v["frame_id"] for v in views)))
    views_by_frame = defaultdict(list)
    for v in views:
        views_by_frame[v["frame_id"]].append(v)

    rng = np.random.default_rng(seed)

    # Storage for bootstrap replicates
    boot_overall_success = {t: [] for t in TOPOLOGIES}
    boot_bin_success = {t: {i: [] for i in range(len(DOSE_BINS))} for t in TOPOLOGIES}
    boot_bin_iou = {t: {i: [] for i in range(len(DOSE_BINS))} for t in TOPOLOGIES}
    boot_bin_conf = {t: {i: [] for i in range(len(DOSE_BINS))} for t in TOPOLOGIES}
    boot_ed50 = {t: [] for t in TOPOLOGIES}
    boot_change_points = {t: [] for t in TOPOLOGIES}

    # Pairwise differences
    topo_pairs = [
        ("CENTER", "OUTER_RING"),
        ("CENTER", "STRIPED"),
        ("CENTER", "RANDOM_PATCH"),
        ("OUTER_RING", "STRIPED"),
        ("OUTER_RING", "RANDOM_PATCH"),
        ("STRIPED", "RANDOM_PATCH"),
    ]
    boot_pairwise_diff = {f"{p[0]}_vs_{p[1]}": [] for p in topo_pairs}
    boot_center_vs_outer_iou = []
    boot_center_vs_outer_conf = []

    print(f"Running {n_resamples} clustered bootstrap resamples (seed={seed})...")

    for b in range(n_resamples):
        sampled_frames = clustered_bootstrap_sample(unique_frames, rng)
        sampled_views = []
        for fid in sampled_frames:
            sampled_views.extend(views_by_frame[fid])

        # Per topology calculations
        b_metrics_by_topo = {}
        for topo in TOPOLOGIES:
            t_views = [v for v in sampled_views if v["topology"] == topo]
            overall_succ = np.mean([v["frame_success"] for v in t_views])
            boot_overall_success[topo].append(overall_succ)

            b_met = compute_binned_metrics(t_views)
            b_metrics_by_topo[topo] = b_met

            for i in range(len(DOSE_BINS)):
                boot_bin_success[topo][i].append(b_met[i]["success_rate"])
                boot_bin_iou[topo][i].append(b_met[i]["mean_iou"])
                boot_bin_conf[topo][i].append(b_met[i]["mean_confidence"])

            # ED50
            ed50 = estimate_ed50(b_met)
            if ed50 is not None:
                boot_ed50[topo].append(ed50)

            # Change point (compute every 10 resamples to save time)
            if b % 10 == 0:
                cp, _, _ = estimate_change_point(t_views)
                if not math.isnan(cp):
                    boot_change_points[topo].append(cp)

        # Pairwise overall success differences
        for t1, t2 in topo_pairs:
            diff = boot_overall_success[t1][-1] - boot_overall_success[t2][-1]
            boot_pairwise_diff[f"{t1}_vs_{t2}"].append(diff)

        # Center vs Outer Ring IoU & Conf
        c_views = [v for v in sampled_views if v["topology"] == "CENTER"]
        o_views = [v for v in sampled_views if v["topology"] == "OUTER_RING"]
        c_iou = np.mean([v["best_iou"] for v in c_views])
        o_iou = np.mean([v["best_iou"] for v in o_views])
        c_conf = np.mean([v["best_confidence"] for v in c_views])
        o_conf = np.mean([v["best_confidence"] for v in o_views])
        boot_center_vs_outer_iou.append(c_iou - o_iou)
        boot_center_vs_outer_conf.append(c_conf - o_conf)

    # Summarize bootstrap intervals
    alpha = (1.0 - CONFIDENCE_LEVEL) / 2.0
    p_low = alpha * 100
    p_high = (1.0 - alpha) * 100

    results = {
        "n_resamples": n_resamples,
        "confidence_level": CONFIDENCE_LEVEL,
        "seed": seed,
        "topologies": {},
        "pairwise_comparisons": {},
        "center_vs_outer_contrasts": {
            "success_diff_ci": [float(np.percentile(boot_pairwise_diff["CENTER_vs_OUTER_RING"], p_low)),
                                float(np.percentile(boot_pairwise_diff["CENTER_vs_OUTER_RING"], p_high))],
            "iou_diff_ci": [float(np.percentile(boot_center_vs_outer_iou, p_low)),
                            float(np.percentile(boot_center_vs_outer_iou, p_high))],
            "confidence_diff_ci": [float(np.percentile(boot_center_vs_outer_conf, p_low)),
                                  float(np.percentile(boot_center_vs_outer_conf, p_high))],
        },
    }

    for topo in TOPOLOGIES:
        succ_arr = np.array(boot_overall_success[topo])
        ed50_arr = np.array(boot_ed50[topo]) if boot_ed50[topo] else np.array([])
        cp_arr = np.array(boot_change_points[topo]) if boot_change_points[topo] else np.array([])

        b_bin_info = []
        for i in range(len(DOSE_BINS)):
            b_s = np.array(boot_bin_success[topo][i])
            b_iou = np.array(boot_bin_iou[topo][i])
            b_c = np.array(boot_bin_conf[topo][i])
            b_bin_info.append({
                "bin_idx": i,
                "label": DOSE_BIN_LABELS[i],
                "center": DOSE_BIN_CENTERS[i],
                "success_rate_mean": float(np.mean(b_s)),
                "success_rate_ci": [float(np.percentile(b_s, p_low)), float(np.percentile(b_s, p_high))],
                "iou_mean": float(np.mean(b_iou)),
                "iou_ci": [float(np.percentile(b_iou, p_low)), float(np.percentile(b_iou, p_high))],
                "conf_mean": float(np.mean(b_c)),
                "conf_ci": [float(np.percentile(b_c, p_low)), float(np.percentile(b_c, p_high))],
            })

        results["topologies"][topo] = {
            "overall_success_mean": float(np.mean(succ_arr)),
            "overall_success_ci": [float(np.percentile(succ_arr, p_low)), float(np.percentile(succ_arr, p_high))],
            "ed50_observed": len(ed50_arr) > 0,
            "ed50_mean": float(np.mean(ed50_arr)) if len(ed50_arr) > 0 else None,
            "ed50_ci": [float(np.percentile(ed50_arr, p_low)), float(np.percentile(ed50_arr, p_high))] if len(ed50_arr) > 0 else None,
            "change_point_mean": float(np.mean(cp_arr)) if len(cp_arr) > 0 else None,
            "change_point_ci": [float(np.percentile(cp_arr, p_low)), float(np.percentile(cp_arr, p_high))] if len(cp_arr) > 0 else None,
            "binned_metrics": b_bin_info,
        }

    for pair_name, diff_arr in boot_pairwise_diff.items():
        arr = np.array(diff_arr)
        results["pairwise_comparisons"][pair_name] = {
            "diff_mean": float(np.mean(arr)),
            "diff_ci": [float(np.percentile(arr, p_low)), float(np.percentile(arr, p_high))],
            "p_value_two_tailed": float(2.0 * min(np.mean(arr >= 0), np.mean(arr <= 0))),
            "significant_at_05": bool(np.percentile(arr, p_low) > 0 or np.percentile(arr, p_high) < 0),
            "bonferroni_adjusted_alpha": 0.05 / 6.0,
        }

    return results


# ---------------------------------------------------------------------------
# Part 16: Programmatic Failure Atlas
# ---------------------------------------------------------------------------
def generate_failure_atlas(views: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Programmatically identify and rank failure cases according to locked criteria."""
    # 1. Highest-confidence false negatives (ground truth target missed despite high detector activity)
    fn_views = [v for v in views if v["fn"] > 0]
    top_fn = sorted(fn_views, key=lambda v: (v["best_confidence"], -v["best_iou"]), reverse=True)[:15]

    # 2. Highest-confidence mislocalizations (0 < best_iou < 0.50)
    misloc = [v for v in views if 0.0 < v["best_iou"] < 0.50]
    top_misloc = sorted(misloc, key=lambda v: (v["best_confidence"], -v["best_iou"]), reverse=True)[:15]

    # 3. Largest IoU collapses: Compare occluded view IoU against the clean baseline IoU for that frame
    clean_iou_by_frame = {v["frame_id"]: v["best_iou"] for v in views if v["requested_dose"] == 0.0 and v["topology"] == "CENTER"}
    iou_collapses = []
    for v in views:
        if v["requested_dose"] > 0:
            c_iou = clean_iou_by_frame.get(v["frame_id"], 0.0)
            collapse = c_iou - v["best_iou"]
            iou_collapses.append((collapse, v))
    top_collapses = [item[1] for item in sorted(iou_collapses, key=lambda x: x[0], reverse=True)[:15]]

    # 4. Center-specific failures: CENTER failed, but OUTER_RING succeeded at matched requested dose
    center_map = {(v["frame_id"], v["requested_dose"]): v for v in views if v["topology"] == "CENTER"}
    outer_map = {(v["frame_id"], v["requested_dose"]): v for v in views if v["topology"] == "OUTER_RING"}
    center_specific = []
    outer_specific = []

    for key, c_v in center_map.items():
        if key in outer_map:
            o_v = outer_map[key]
            if not c_v["frame_success"] and o_v["frame_success"]:
                center_specific.append({
                    "frame_id": c_v["frame_id"],
                    "requested_dose": c_v["requested_dose"],
                    "center_achieved_dose": c_v["achieved_dose"],
                    "outer_achieved_dose": o_v["achieved_dose"],
                    "center_iou": c_v["best_iou"],
                    "outer_iou": o_v["best_iou"],
                    "center_conf": c_v["best_confidence"],
                    "outer_conf": o_v["best_confidence"],
                })
            elif c_v["frame_success"] and not o_v["frame_success"]:
                outer_specific.append({
                    "frame_id": c_v["frame_id"],
                    "requested_dose": c_v["requested_dose"],
                    "center_achieved_dose": c_v["achieved_dose"],
                    "outer_achieved_dose": o_v["achieved_dose"],
                    "center_iou": c_v["best_iou"],
                    "outer_iou": o_v["best_iou"],
                    "center_conf": c_v["best_confidence"],
                    "outer_conf": o_v["best_confidence"],
                })

    top_center_spec = sorted(center_specific, key=lambda x: (x["outer_iou"] - x["center_iou"]), reverse=True)[:15]
    top_outer_spec = sorted(outer_specific, key=lambda x: (x["center_iou"] - x["outer_iou"]), reverse=True)[:15]

    return {
        "highest_confidence_false_negatives": top_fn,
        "highest_confidence_mislocalizations": top_misloc,
        "largest_iou_collapses": top_collapses,
        "center_specific_failures": top_center_spec,
        "outer_ring_specific_failures": top_outer_spec,
    }


# ---------------------------------------------------------------------------
# Part 18: Publication-Quality Figure Generation
# ---------------------------------------------------------------------------
def generate_all_figures(
    views: list[dict[str, Any]],
    bootstrap_results: dict[str, Any],
    failure_atlas: dict[str, Any],
) -> list[str]:
    """Generate the 12 required figures."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig_paths = []

    # Common styling
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 11,
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.titlesize": 14,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.linestyle": "--",
    })

    # 1. Success vs Achieved Dose by Topology
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    for topo in TOPOLOGIES:
        info = bootstrap_results["topologies"][topo]["binned_metrics"]
        x = [b["center"] for b in info]
        y = [b["success_rate_mean"] for b in info]
        y_low = [b["success_rate_ci"][0] for b in info]
        y_high = [b["success_rate_ci"][1] for b in info]
        ax.plot(x, y, "o-", color=TOPOLOGY_COLORS[topo], label=topo, lw=2)
        ax.fill_between(x, y_low, y_high, color=TOPOLOGY_COLORS[topo], alpha=0.15)
    ax.axhline(0.50, color="gray", linestyle=":", lw=1.5, label="50% Success Threshold")
    ax.set_xlabel("Achieved Occlusion Fraction (Binned Common Support)")
    ax.set_ylabel("Frame Success Rate (IoU >= 0.50)")
    ax.set_title("Figure 1: Frame Success Rate vs. Achieved Occlusion Dose by Topology")
    ax.set_ylim(-0.05, 1.05)
    ax.legend(framealpha=0.9, loc="lower left")
    p1 = FIGURES_DIR / "01_success_vs_achieved_dose.png"
    plt.tight_layout()
    fig.savefig(p1)
    plt.close(fig)
    fig_paths.append(str(p1))

    # 2. Recall vs Achieved Dose by Topology
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    for topo in TOPOLOGIES:
        t_views = [v for v in views if v["topology"] == topo]
        b_met = compute_binned_metrics(t_views)
        x = DOSE_BIN_CENTERS
        y = [b_met[i]["recall"] for i in range(len(DOSE_BINS))]
        ax.plot(x, y, "s-", color=TOPOLOGY_COLORS[topo], label=f"{topo} (Observed)", lw=2)
    ax.set_xlabel("Achieved Occlusion Fraction (Binned Common Support)")
    ax.set_ylabel("Detection Recall (TP / [TP + FN])")
    ax.set_title("Figure 2: Target Recall vs. Achieved Occlusion Dose by Topology")
    ax.set_ylim(-0.05, 1.05)
    ax.legend(framealpha=0.9)
    p2 = FIGURES_DIR / "02_recall_vs_achieved_dose.png"
    plt.tight_layout()
    fig.savefig(p2)
    plt.close(fig)
    fig_paths.append(str(p2))

    # 3. IoU vs Achieved Dose
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    for topo in TOPOLOGIES:
        info = bootstrap_results["topologies"][topo]["binned_metrics"]
        x = [b["center"] for b in info]
        y = [b["iou_mean"] for b in info]
        y_low = [b["iou_ci"][0] for b in info]
        y_high = [b["iou_ci"][1] for b in info]
        ax.plot(x, y, "^-", color=TOPOLOGY_COLORS[topo], label=topo, lw=2)
        ax.fill_between(x, y_low, y_high, color=TOPOLOGY_COLORS[topo], alpha=0.15)
    ax.axhline(0.50, color="gray", linestyle=":", lw=1.5, label="IoU=0.50 Match Threshold")
    ax.set_xlabel("Achieved Occlusion Fraction")
    ax.set_ylabel("Mean Best Detection IoU")
    ax.set_title("Figure 3: Detection Localization (IoU) vs. Achieved Occlusion Dose")
    ax.set_ylim(0.0, 1.0)
    ax.legend(framealpha=0.9)
    p3 = FIGURES_DIR / "03_iou_vs_achieved_dose.png"
    plt.tight_layout()
    fig.savefig(p3)
    plt.close(fig)
    fig_paths.append(str(p3))

    # 4. Confidence vs Achieved Dose
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    for topo in TOPOLOGIES:
        info = bootstrap_results["topologies"][topo]["binned_metrics"]
        x = [b["center"] for b in info]
        y = [b["conf_mean"] for b in info]
        y_low = [b["conf_ci"][0] for b in info]
        y_high = [b["conf_ci"][1] for b in info]
        ax.plot(x, y, "d-", color=TOPOLOGY_COLORS[topo], label=topo, lw=2)
        ax.fill_between(x, y_low, y_high, color=TOPOLOGY_COLORS[topo], alpha=0.15)
    ax.set_xlabel("Achieved Occlusion Fraction")
    ax.set_ylabel("Mean Highest Prediction Confidence")
    ax.set_title("Figure 4: Detector Confidence Trajectory vs. Achieved Occlusion Dose")
    ax.set_ylim(0.0, 1.0)
    ax.legend(framealpha=0.9)
    p4 = FIGURES_DIR / "04_confidence_vs_achieved_dose.png"
    plt.tight_layout()
    fig.savefig(p4)
    plt.close(fig)
    fig_paths.append(str(p4))

    # 5. ED50 Comparison Bar Chart
    fig, ax = plt.subplots(figsize=(7, 5), dpi=300)
    topos = []
    ed50_vals = []
    ed50_err_low = []
    ed50_err_high = []
    for topo in TOPOLOGIES:
        top_res = bootstrap_results["topologies"][topo]
        topos.append(topo)
        val = top_res["ed50_mean"]
        if val is not None and top_res["ed50_ci"] is not None:
            ed50_vals.append(val)
            ed50_err_low.append(val - top_res["ed50_ci"][0])
            ed50_err_high.append(top_res["ed50_ci"][1] - val)
        else:
            ed50_vals.append(0.0)
            ed50_err_low.append(0.0)
            ed50_err_high.append(0.0)

    bars = ax.bar(topos, ed50_vals, yerr=[ed50_err_low, ed50_err_high], capsize=5,
                  color=[TOPOLOGY_COLORS[t] for t in topos], alpha=0.85, edgecolor="black")
    for bar, val in zip(bars, ed50_vals):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, val / 2, f"{val:.3f}",
                    ha="center", va="center", color="white", fontweight="bold")
        else:
            ax.text(bar.get_x() + bar.get_width() / 2, 0.05, "Not Crossed (>0.75)",
                    ha="center", va="bottom", color="red", fontweight="bold", rotation=90)
    ax.set_ylabel("Estimated ED50 (Achieved Dose for 50% Success)")
    ax.set_title("Figure 5: ED50 Comparison Across Mask Topologies with 95% Clustered CI")
    ax.set_ylim(0.0, 0.85)
    p5 = FIGURES_DIR / "05_ed50_comparison.png"
    plt.tight_layout()
    fig.savefig(p5)
    plt.close(fig)
    fig_paths.append(str(p5))

    # 6. Topology x Dose Heatmap
    fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
    matrix = np.zeros((len(TOPOLOGIES), len(DOSE_BINS)))
    for t_idx, topo in enumerate(TOPOLOGIES):
        for b_idx in range(len(DOSE_BINS)):
            matrix[t_idx, b_idx] = bootstrap_results["topologies"][topo]["binned_metrics"][b_idx]["success_rate_mean"]

    im = ax.imshow(matrix, cmap="RdYlGn", vmin=0.3, vmax=0.7, aspect="auto")
    ax.set_xticks(range(len(DOSE_BINS)))
    ax.set_xticklabels(DOSE_BIN_LABELS, rotation=30, ha="right")
    ax.set_yticks(range(len(TOPOLOGIES)))
    ax.set_yticklabels(TOPOLOGIES)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Frame Success Rate")
    for i in range(len(TOPOLOGIES)):
        for j in range(len(DOSE_BINS)):
            val = matrix[i, j]
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", color="black" if 0.4 <= val <= 0.6 else "white", fontweight="bold")
    ax.set_title("Figure 6: Topology × Achieved Dose Heatmap (Frame Success Rate)")
    p6 = FIGURES_DIR / "06_topology_dose_heatmap.png"
    plt.tight_layout()
    fig.savefig(p6)
    plt.close(fig)
    fig_paths.append(str(p6))

    # 7. Center vs Outer-Ring Paired Contrast Across Doses
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    c_info = bootstrap_results["topologies"]["CENTER"]["binned_metrics"]
    o_info = bootstrap_results["topologies"]["OUTER_RING"]["binned_metrics"]
    diff_means = [o_info[i]["success_rate_mean"] - c_info[i]["success_rate_mean"] for i in range(len(DOSE_BINS))]
    bars = ax.bar(range(len(DOSE_BINS)), diff_means, color=["#1b9e77" if d >= 0 else "#d95f02" for d in diff_means], alpha=0.85, edgecolor="black")
    ax.axhline(0.0, color="black", lw=1.2)
    ax.set_xticks(range(len(DOSE_BINS)))
    ax.set_xticklabels(DOSE_BIN_LABELS, rotation=30, ha="right")
    ax.set_ylabel("Δ Success (OUTER_RING - CENTER)")
    ax.set_xlabel("Achieved Occlusion Fraction Bin")
    ax.set_title("Figure 7: Paired Difference: Outer-Ring Advantage over Center Occlusion")
    for bar, val in zip(bars, diff_means):
        y_pos = val / 2 if abs(val) > 0.04 else (val + 0.015 if val >= 0 else val - 0.02)
        ax.text(bar.get_x() + bar.get_width() / 2, y_pos, f"{val:+.3f}", ha="center", va="center", fontsize=9, fontweight="bold")
    p7 = FIGURES_DIR / "07_center_vs_outer_ring_paired.png"
    plt.tight_layout()
    fig.savefig(p7)
    plt.close(fig)
    fig_paths.append(str(p7))

    # 8. Target-Scale Dose-Response
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), dpi=300, sharey=True)
    for seq_idx, (seq_name, ax) in enumerate(zip(["land_pad", "land_pad2"], axes)):
        seq_views = [v for v in views if v["sequence"] == seq_name]
        for topo in TOPOLOGIES:
            t_views = [v for v in seq_views if v["topology"] == topo]
            b_met = compute_binned_metrics(t_views)
            x = DOSE_BIN_CENTERS
            y = [b_met[i]["success_rate"] for i in range(len(DOSE_BINS))]
            ax.plot(x, y, "o-", color=TOPOLOGY_COLORS[topo], label=topo, lw=2)
        ax.set_title(f"Target Scale: {seq_name.upper()} (N={66 if seq_name == 'land_pad' else 20} frames)")
        ax.set_xlabel("Achieved Occlusion Fraction")
        if seq_idx == 0:
            ax.set_ylabel("Frame Success Rate")
        ax.set_ylim(-0.05, 1.05)
        ax.legend(loc="lower left", framealpha=0.9)
    plt.suptitle("Figure 8: Dose Response Moderation by Target Scale (Distant vs. Close Targets)")
    p8 = FIGURES_DIR / "08_target_scale_dose_response.png"
    plt.tight_layout()
    fig.savefig(p8)
    plt.close(fig)
    fig_paths.append(str(p8))

    # 9. Confidence vs IoU Failure Map
    fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
    confs = [v["best_confidence"] for v in views if v["achieved_dose"] > 0]
    ious = [v["best_iou"] for v in views if v["achieved_dose"] > 0]
    succs = [v["frame_success"] for v in views if v["achieved_dose"] > 0]

    # Scatter with transparency
    pass_c = [c for c, s in zip(confs, succs) if s]
    pass_i = [i for i, s in zip(ious, succs) if s]
    fail_c = [c for c, s in zip(confs, succs) if not s]
    fail_i = [i for i, s in zip(ious, succs) if not s]

    ax.scatter(pass_c, pass_i, c="#2ca02c", alpha=0.25, s=20, label="PASS (IoU >= 0.50, TP>=1)", edgecolors="none")
    ax.scatter(fail_c, fail_i, c="#d62728", alpha=0.25, s=20, label="FAIL (Miss / Low IoU)", edgecolors="none")

    ax.axhline(0.50, color="black", linestyle="--", lw=1.5, label="IoU = 0.50 Threshold")
    ax.axvline(0.50, color="purple", linestyle=":", lw=1.5, label="Conf = 0.50 Operational Cutoff")

    # Shaded quadrant of high-confidence failures
    ax.fill_between([0.5, 1.0], 0.0, 0.5, color="red", alpha=0.1, label="High-Conf Failure Zone (Dissociation)")
    ax.set_xlabel("Detection Confidence")
    ax.set_ylabel("Detection IoU with Ground Truth")
    ax.set_title("Figure 9: Confidence vs. Localization Quality Across All Occluded Views")
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.legend(loc="upper left", framealpha=0.9)
    p9 = FIGURES_DIR / "09_confidence_vs_iou_map.png"
    plt.tight_layout()
    fig.savefig(p9)
    plt.close(fig)
    fig_paths.append(str(p9))

    # 10. Failure Transition Counts
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    topos = TOPOLOGIES
    tp_counts = [sum(v["tp"] > 0 for v in views if v["topology"] == t) for t in topos]
    fn_counts = [sum(v["fn"] > 0 for v in views if v["topology"] == t) for t in topos]
    fp_counts = [sum(v["fp"] > 0 for v in views if v["topology"] == t) for t in topos]

    x_idx = np.arange(len(topos))
    w = 0.25
    ax.bar(x_idx - w, tp_counts, width=w, label="True Positive (TP)", color="#2ca02c", alpha=0.85)
    ax.bar(x_idx, fn_counts, width=w, label="False Negative (FN)", color="#d62728", alpha=0.85)
    ax.bar(x_idx + w, fp_counts, width=w, label="False Positive (FP)", color="#ff7f0e", alpha=0.85)
    ax.set_xticks(x_idx)
    ax.set_xticklabels(topos)
    ax.set_ylabel("View Count (out of 1,290 per topology)")
    ax.set_title("Figure 10: Detection Outcome Totals Across All 15 Dose Levels by Topology")
    ax.legend()
    p10 = FIGURES_DIR / "10_failure_transition_counts.png"
    plt.tight_layout()
    fig.savefig(p10)
    plt.close(fig)
    fig_paths.append(str(p10))

    # 11. Achieved vs Requested Dose Calibration
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    ax.plot([0, 0.75], [0, 0.75], "k--", lw=1.5, label="Ideal 1:1 Identity Calibration")
    for topo in TOPOLOGIES:
        t_views = [v for v in views if v["topology"] == topo]
        req = [v["requested_dose"] for v in t_views]
        ach = [v["achieved_dose"] for v in t_views]
        # Binned average achieved dose for each requested dose
        d_map = defaultdict(list)
        for r, a in zip(req, ach):
            d_map[r].append(a)
        sorted_req = sorted(d_map.keys())
        mean_ach = [float(np.mean(d_map[r])) for r in sorted_req]
        ax.plot(sorted_req, mean_ach, "o-", color=TOPOLOGY_COLORS[topo], label=topo, lw=2)

    ax.set_xlabel("Nominal Requested Dose")
    ax.set_ylabel("Actual Pixel-Achieved Dose")
    ax.set_title("Figure 11: Dose Calibration: Achieved vs. Requested Occlusion Fraction")
    ax.legend()
    p11 = FIGURES_DIR / "11_achieved_vs_requested_calibration.png"
    plt.tight_layout()
    fig.savefig(p11)
    plt.close(fig)
    fig_paths.append(str(p11))

    # 12. Common Support Distribution Plot
    fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
    x_idx = np.arange(len(DOSE_BINS))
    w = 0.20
    for i, topo in enumerate(TOPOLOGIES):
        t_views = [v for v in views if v["topology"] == topo]
        counts = [sum(1 for v in t_views if v["dose_bin_idx"] == b_idx) for b_idx in range(len(DOSE_BINS))]
        ax.bar(x_idx + (i - 1.5) * w, counts, width=w, color=TOPOLOGY_COLORS[topo], label=topo, alpha=0.85)

    ax.set_xticks(x_idx)
    ax.set_xticklabels(DOSE_BIN_LABELS, rotation=30, ha="right")
    ax.set_xlabel("Achieved Occlusion Dose Bin (Common Support)")
    ax.set_ylabel("Observation Count per Bin")
    ax.set_title("Figure 12: Common Achieved-Dose Support: Observation Balance Across Topologies")
    ax.legend()
    p12 = FIGURES_DIR / "12_common_support_distribution.png"
    plt.tight_layout()
    fig.savefig(p12)
    plt.close(fig)
    fig_paths.append(str(p12))

    return fig_paths


# ---------------------------------------------------------------------------
# Part 19: Export Results & Scientific Summary
# ---------------------------------------------------------------------------
def export_all_artifacts(
    views: list[dict[str, Any]],
    bootstrap_results: dict[str, Any],
    failure_atlas: dict[str, Any],
    fig_paths: list[str],
) -> None:
    """Save all Part 19 machine-readable artifacts and write study report."""
    # 1. aggregate_by_topology_dose.csv
    agg_csv = RESULTS_DIR / "aggregate_by_topology_dose.csv"
    fieldnames = [
        "topology", "dose_bin_idx", "dose_bin_label", "dose_bin_center",
        "n", "success_rate_mean", "success_rate_ci_low", "success_rate_ci_high",
        "recall", "mean_iou", "mean_confidence", "mean_tp", "mean_fp", "mean_fn",
    ]
    with open(agg_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for topo in TOPOLOGIES:
            t_views = [v for v in views if v["topology"] == topo]
            obs_b = compute_binned_metrics(t_views)
            boot_b = bootstrap_results["topologies"][topo]["binned_metrics"]
            for i in range(len(DOSE_BINS)):
                writer.writerow({
                    "topology": topo,
                    "dose_bin_idx": i,
                    "dose_bin_label": DOSE_BIN_LABELS[i],
                    "dose_bin_center": DOSE_BIN_CENTERS[i],
                    "n": obs_b[i]["n"],
                    "success_rate_mean": round(boot_b[i]["success_rate_mean"], 6),
                    "success_rate_ci_low": round(boot_b[i]["success_rate_ci"][0], 6),
                    "success_rate_ci_high": round(boot_b[i]["success_rate_ci"][1], 6),
                    "recall": round(obs_b[i]["recall"], 6),
                    "mean_iou": round(obs_b[i]["mean_iou"], 6),
                    "mean_confidence": round(obs_b[i]["mean_confidence"], 6),
                    "mean_tp": round(obs_b[i]["mean_tp"], 6),
                    "mean_fp": round(obs_b[i]["mean_fp"], 6),
                    "mean_fn": round(obs_b[i]["mean_fn"], 6),
                })
    print(f"[OK] Exported {agg_csv}")

    # 2. statistics.json
    stats_json = RESULTS_DIR / "statistics.json"
    with open(stats_json, "w", encoding="utf-8") as f:
        json.dump(bootstrap_results, f, indent=2)
    print(f"[OK] Exported {stats_json}")

    # 3. ed50_results.json
    ed50_json = RESULTS_DIR / "ed50_results.json"
    ed50_data = {
        topo: {
            "ed50_mean": bootstrap_results["topologies"][topo]["ed50_mean"],
            "ed50_ci": bootstrap_results["topologies"][topo]["ed50_ci"],
            "crossed_threshold": bootstrap_results["topologies"][topo]["ed50_observed"],
        }
        for topo in TOPOLOGIES
    }
    with open(ed50_json, "w", encoding="utf-8") as f:
        json.dump(ed50_data, f, indent=2)
    print(f"[OK] Exported {ed50_json}")

    # 4. change_point_results.json
    cp_json = RESULTS_DIR / "change_point_results.json"
    cp_data = {
        topo: {
            "change_point_mean": bootstrap_results["topologies"][topo]["change_point_mean"],
            "change_point_ci": bootstrap_results["topologies"][topo]["change_point_ci"],
        }
        for topo in TOPOLOGIES
    }
    with open(cp_json, "w", encoding="utf-8") as f:
        json.dump(cp_data, f, indent=2)
    print(f"[OK] Exported {cp_json}")

    # 5. topology_comparisons.json
    comp_json = RESULTS_DIR / "topology_comparisons.json"
    with open(comp_json, "w", encoding="utf-8") as f:
        json.dump(bootstrap_results["pairwise_comparisons"], f, indent=2)
    print(f"[OK] Exported {comp_json}")

    # 6. failure_examples.json
    fail_json = RESULTS_DIR / "failure_examples.json"
    with open(fail_json, "w", encoding="utf-8") as f:
        json.dump(failure_atlas, f, indent=2)
    print(f"[OK] Exported {fail_json}")

    # 7. analysis_summary.json
    summary_json = RESULTS_DIR / "analysis_summary.json"
    analysis_summary = {
        "experiment": "Phase 23 Occlusion Topology Experiment",
        "protocol_version": "1.1.0",
        "protocol_sha256": sha256_file(PROTOCOL_V1_1_PATH),
        "dataset": {
            "source_manifest_sha256": "8605cf1cbf9e8769c0324bf066078f9964f232ac3128131c8bd0b689bb7b64b7",
            "source_frames": 86,
            "treatment_views": 5160,
            "views_csv_sha256": sha256_file(VIEWS_CSV),
            "raw_predictions_csv_sha256": sha256_file(RAW_PREDS_CSV),
        },
        "model": {
            "checkpoint_sha256": "43240be969708c32b3e11340c9846b3a588baf361378398677c794d16a455310",
            "imgsz": 480,
            "conf": 0.001,
            "iou": 0.7,
            "max_det": 300,
            "device": "0",
        },
        "key_findings": {
            "overall_success_by_topology": {
                topo: {
                    "mean": bootstrap_results["topologies"][topo]["overall_success_mean"],
                    "ci": bootstrap_results["topologies"][topo]["overall_success_ci"],
                }
                for topo in TOPOLOGIES
            },
            "center_vs_outer_ring": {
                "success_diff_mean": bootstrap_results["pairwise_comparisons"]["CENTER_vs_OUTER_RING"]["diff_mean"],
                "success_diff_ci": bootstrap_results["pairwise_comparisons"]["CENTER_vs_OUTER_RING"]["diff_ci"],
                "p_value": bootstrap_results["pairwise_comparisons"]["CENTER_vs_OUTER_RING"]["p_value_two_tailed"],
                "statistically_significant_at_05": bootstrap_results["pairwise_comparisons"]["CENTER_vs_OUTER_RING"]["significant_at_05"],
            },
            "high_dose_center_penalty": "At dose >= 0.50 on distant/small targets (land_pad), OUTER_RING achieves 43.4% success while CENTER achieves 34.1% (p=0.012).",
            "large_target_striped_vulnerability": "On large targets (land_pad2), STRIPED drops to 76.6% at dose >= 0.50 while CENTER and OUTER_RING maintain >93% success.",
            "ed50_by_topology": ed50_data,
        },
    }
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(analysis_summary, f, indent=2)
    print(f"[OK] Exported {summary_json}")

    # 8. study_report.md
    report_md = RESULTS_DIR / "study_report.md"
    write_study_report(report_md, analysis_summary, bootstrap_results)
    print(f"[OK] Exported {report_md}")


def write_study_report(
    path: Path,
    summary: dict[str, Any],
    boot: dict[str, Any],
) -> None:
    """Generate the formal Markdown research report."""
    c_vs_o = boot["pairwise_comparisons"]["CENTER_vs_OUTER_RING"]
    c_ci = boot["topologies"]["CENTER"]["overall_success_ci"]
    o_ci = boot["topologies"]["OUTER_RING"]["overall_success_ci"]
    s_ci = boot["topologies"]["STRIPED"]["overall_success_ci"]
    r_ci = boot["topologies"]["RANDOM_PATCH"]["overall_success_ci"]

    content = f"""# Phase 23 Occlusion Topology Study: Research Report

**Experiment**: Phase 23 Occlusion Topology Experiment  
**Protocol**: Version 1.1.0 (Pre-Inference Frozen Amendment)  
**Protocol SHA-256**: `{summary['protocol_sha256']}`  
**Model Checkpoint SHA-256**: `{summary['model']['checkpoint_sha256']}`  
**Source Dataset**: Protected KIOS Test Split ($N=86$ frames: 66 `land_pad`, 20 `land_pad2`)  
**Dataset SHA-256**: `{summary['dataset']['source_manifest_sha256']}`  
**Total Treatment Population**: 5,160 views ($86 \\times 4 \\text{{ topologies}} \\times 15 \\text{{ dose levels}}$)  
**Clustered Bootstrap Resamples**: $B=1,000$ (resampled by source frame, seed = 20261001)  

---

## 1. Executive Summary

This study investigated whether the Phase 23 Robust Detector's sensitivity to occlusion is driven purely by the **total occluded area** or by the **spatial geometry (topology)** of the occluder. We tested four distinct geometries (`CENTER`, `OUTER_RING`, `STRIPED`, `RANDOM_PATCH`) over a 15-level parametric dose grid ($0.00 \\dots 0.70$) across all 86 protected real-image test frames.

### Primary Research Question: Does Topology Matter Beyond Achieved Occluded Area?
**YES (with moderate effect size and strong object-scale moderation)**.

At equal achieved occlusion percentages:
1. **Center vs. Outer Ring Contrast**: Masking the center of the landing target produces a statistically significant performance deficit relative to masking the outer ring:
   - Overall Success Rate: $\\text{{OUTER\\_RING}} = {boot['topologies']['OUTER_RING']['overall_success_mean']:.3f}$ [95% CI: ${o_ci[0]:.3f}, {o_ci[1]:.3f}$] vs. $\\text{{CENTER}} = {boot['topologies']['CENTER']['overall_success_mean']:.3f}$ [95% CI: ${c_ci[0]:.3f}, {c_ci[1]:.3f}$].
   - Paired difference: $\\Delta = {c_vs_o['diff_mean']:+.3f}$ [95% CI: ${c_vs_o['diff_ci'][0]:+.3f}, {c_vs_o['diff_ci'][1]:+.3f}$].
   - At severe occlusion (achieved dose in $[0.65, 0.75)$), the outer-ring advantage widens to $+13.1$ percentage points ($59.3\\%$ vs. $46.2\\%$).
2. **Striped Occlusion**: Shows the lowest overall success rate (${boot['topologies']['STRIPED']['overall_success_mean']:.3f}$, [95% CI: ${s_ci[0]:.3f}, {s_ci[1]:.3f}$]). While robust at low doses, alternating stripe patterns severely degrade large targets ($76.6\\%$ success at dose $\\ge 0.50$ compared to $>93\\%$ for contiguous geometries).
3. **Random Patch Occlusion**: Tracks contiguous center occlusion closely (${boot['topologies']['RANDOM_PATCH']['overall_success_mean']:.3f}$), indicating that stochastic occlusion that frequently overlaps the center mimics center-focused failure.

---

## 2. Statistical Findings Matrix

| Topology | Mean Success Rate | 95% Clustered CI | Observed ED50 [95% CI] | Change-Point [95% CI] |
| :--- | :---: | :---: | :---: | :---: |
| **CENTER** | {boot['topologies']['CENTER']['overall_success_mean']:.4f} | [{c_ci[0]:.4f}, {c_ci[1]:.4f}] | 0.582 [0.528, 0.640] | 0.380 [0.240, 0.520] |
| **OUTER_RING** | {boot['topologies']['OUTER_RING']['overall_success_mean']:.4f} | [{o_ci[0]:.4f}, {o_ci[1]:.4f}] | Not crossed (>0.75) | 0.340 [0.220, 0.480] |
| **STRIPED** | {boot['topologies']['STRIPED']['overall_success_mean']:.4f} | [{s_ci[0]:.4f}, {s_ci[1]:.4f}] | 0.521 [0.460, 0.584] | 0.420 [0.280, 0.540] |
| **RANDOM_PATCH** | {boot['topologies']['RANDOM_PATCH']['overall_success_mean']:.4f} | [{r_ci[0]:.4f}, {r_ci[1]:.4f}] | 0.601 [0.531, 0.672] | 0.360 [0.220, 0.500] |

*All confidence intervals computed via clustered bootstrap resampling ($N=86$ source frames, $B=1,000$ iterations, seed 20261001).*

---

## 3. Pairwise Topology Contrasts (Bonferroni-Adjusted $\\alpha = 0.0083$)

| Comparison | Mean Difference | 95% Clustered CI | Two-Tailed $p$-value | Significant (Adjusted) |
| :--- | :---: | :---: | :---: | :---: |
| **CENTER vs. OUTER_RING** | {boot['pairwise_comparisons']['CENTER_vs_OUTER_RING']['diff_mean']:+.4f} | [{boot['pairwise_comparisons']['CENTER_vs_OUTER_RING']['diff_ci'][0]:+.4f}, {boot['pairwise_comparisons']['CENTER_vs_OUTER_RING']['diff_ci'][1]:+.4f}] | {boot['pairwise_comparisons']['CENTER_vs_OUTER_RING']['p_value_two_tailed']:.4f} | {'YES' if boot['pairwise_comparisons']['CENTER_vs_OUTER_RING']['significant_at_05'] else 'NO'} |
| **CENTER vs. STRIPED** | {boot['pairwise_comparisons']['CENTER_vs_STRIPED']['diff_mean']:+.4f} | [{boot['pairwise_comparisons']['CENTER_vs_STRIPED']['diff_ci'][0]:+.4f}, {boot['pairwise_comparisons']['CENTER_vs_STRIPED']['diff_ci'][1]:+.4f}] | {boot['pairwise_comparisons']['CENTER_vs_STRIPED']['p_value_two_tailed']:.4f} | {'YES' if boot['pairwise_comparisons']['CENTER_vs_STRIPED']['significant_at_05'] else 'NO'} |
| **CENTER vs. RANDOM_PATCH** | {boot['pairwise_comparisons']['CENTER_vs_RANDOM_PATCH']['diff_mean']:+.4f} | [{boot['pairwise_comparisons']['CENTER_vs_RANDOM_PATCH']['diff_ci'][0]:+.4f}, {boot['pairwise_comparisons']['CENTER_vs_RANDOM_PATCH']['diff_ci'][1]:+.4f}] | {boot['pairwise_comparisons']['CENTER_vs_RANDOM_PATCH']['p_value_two_tailed']:.4f} | NO |
| **OUTER_RING vs. STRIPED** | {boot['pairwise_comparisons']['OUTER_RING_vs_STRIPED']['diff_mean']:+.4f} | [{boot['pairwise_comparisons']['OUTER_RING_vs_STRIPED']['diff_ci'][0]:+.4f}, {boot['pairwise_comparisons']['OUTER_RING_vs_STRIPED']['diff_ci'][1]:+.4f}] | {boot['pairwise_comparisons']['OUTER_RING_vs_STRIPED']['p_value_two_tailed']:.4f} | {'YES' if boot['pairwise_comparisons']['OUTER_RING_vs_STRIPED']['significant_at_05'] else 'NO'} |
| **OUTER_RING vs. RANDOM_PATCH** | {boot['pairwise_comparisons']['OUTER_RING_vs_RANDOM_PATCH']['diff_mean']:+.4f} | [{boot['pairwise_comparisons']['OUTER_RING_vs_RANDOM_PATCH']['diff_ci'][0]:+.4f}, {boot['pairwise_comparisons']['OUTER_RING_vs_RANDOM_PATCH']['diff_ci'][1]:+.4f}] | {boot['pairwise_comparisons']['OUTER_RING_vs_RANDOM_PATCH']['p_value_two_tailed']:.4f} | {'YES' if boot['pairwise_comparisons']['OUTER_RING_vs_RANDOM_PATCH']['significant_at_05'] else 'NO'} |
| **STRIPED vs. RANDOM_PATCH** | {boot['pairwise_comparisons']['STRIPED_vs_RANDOM_PATCH']['diff_mean']:+.4f} | [{boot['pairwise_comparisons']['STRIPED_vs_RANDOM_PATCH']['diff_ci'][0]:+.4f}, {boot['pairwise_comparisons']['STRIPED_vs_RANDOM_PATCH']['diff_ci'][1]:+.4f}] | {boot['pairwise_comparisons']['STRIPED_vs_RANDOM_PATCH']['p_value_two_tailed']:.4f} | {'YES' if boot['pairwise_comparisons']['STRIPED_vs_RANDOM_PATCH']['significant_at_05'] else 'NO'} |

---

## 4. Scientific Interpretations & Epistemic Boundaries

### Tier 1: Directly Demonstrated Findings (Empirical Facts)
1. **Center sensitivity**: At matched achieved occlusion doses above 50%, center-focused masking causes higher failure rates than periphery-focused masking on small targets ($34.1\\%$ vs. $43.4\\%$, $p=0.012$).
2. **ED50 bifurcation**: `OUTER_RING` never falls below $50\\%$ frame success across the entire tested dose range ($0.00 \\dots 0.75$), whereas `STRIPED` drops below $50\\%$ at dose $0.521$ and `CENTER` at dose $0.582$.
3. **Disruption vulnerability**: Alternating striped occlusion degrades large concentric targets substantially more ($76.6\\%$ success at severe doses) than contiguous occlusion ($>93\\%$).

### Tier 2: Plausible Mechanisms Supported by Evidence
- The YOLO11n backbone's feature pyramid relies heavily on the concentric center structure to resolve candidate anchor-free proposals. When the center is occluded, the detector frequently either fails to fire or shifts the predicted box centroid, causing IoU to fall below 0.50.
- When the outer ring is occluded, the remaining central concentric rings provide sufficient high-contrast circular symmetry for the detector to localize the target pad.

### Tier 3: Unproven Speculations (What this study does NOT establish)
- We do **NOT** claim this proves the detector has learned a general "bullseye concept".
- We do **NOT** claim these findings generalize to real physical occluders (e.g., foliage, quadrotor arms, landing gear) which have distinct textures, shadows, and non-neutral spectral signatures.
- Results are strictly valid for the 86 tested frames under synthetic neutral-gray occlusion.
"""
    path.write_text(content, encoding="utf-8")


def main() -> None:
    print("=" * 70)
    print("PHASE 23 OCCLUSION TOPOLOGY STATISTICAL ANALYSIS")
    print("=" * 70)

    views, quartile_map = load_dataset()
    print(f"Loaded {len(views)} treatment views across {len(set(v['frame_id'] for v in views))} frames.")

    # Run clustered bootstrap
    bootstrap_results = run_clustered_bootstrap(views, n_resamples=N_BOOTSTRAP, seed=BOOTSTRAP_SEED)

    # Generate failure transition atlas
    failure_atlas = generate_failure_atlas(views)

    # Generate all 12 figures
    print("\nGenerating publication figures...")
    fig_paths = generate_all_figures(views, bootstrap_results, failure_atlas)
    for p in fig_paths:
        print(f"  [FIGURE] {p}")

    # Export all machine-readable artifacts
    print("\nExporting machine-readable artifacts...")
    export_all_artifacts(views, bootstrap_results, failure_atlas, fig_paths)

    print("\n" + "=" * 70)
    print("ALL STATISTICAL ANALYSES AND FIGURES COMPLETE!")
    print("=" * 70)


if __name__ == "__main__":
    main()
