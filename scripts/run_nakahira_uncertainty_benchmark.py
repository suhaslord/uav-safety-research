from __future__ import annotations

import argparse
from dataclasses import replace
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from uav_safety.config import SimConfig
from uav_safety.image_temporal import fit_synthetic_calibrator
from uav_safety.nakahira_metrics import recovery_outcome, terminal_failure, wilson_interval
from uav_safety.nakahira_simulator import run_nakahira_episode
from uav_safety.phase7_faults import Phase7FaultConfig
from uav_safety.phase7_reference import Phase7SensorStackConfig
from uav_safety.provenance import write_result_manifest
from uav_safety.selective_confidence_v2 import fit_component_calibrator


SCHEMA = "aegisland.nakahira.uncertainty-result-bundle.v1"


def _load_config(path: Path) -> dict:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != "aegisland.nakahira.uncertainty-benchmark-config.v1":
        raise ValueError("unexpected Nakahira benchmark config schema")
    if not cfg.get("frozen_before_heldout"):
        raise ValueError("benchmark config is not marked frozen")
    if not cfg.get("simulation_only") or cfg.get("safety_acceptance") is not False:
        raise ValueError("simulation-only/safety-acceptance boundary missing")
    if cfg.get("analysis", {}).get("combinations_in_final_sweep") is not False:
        raise ValueError("first frozen sweep must exclude combination cells")
    return cfg


def _condition_settings(cell: dict, cfg: dict) -> tuple[Phase7FaultConfig, Phase7SensorStackConfig]:
    window = cfg["latency_fault_window"]
    fault_cfg = replace(
        Phase7FaultConfig(),
        onset_fraction_low=float(window["onset_fraction"]),
        onset_fraction_high=float(window["onset_fraction"]),
        duration_fraction_low=float(window["duration_fraction"]),
        duration_fraction_high=float(window["duration_fraction"]),
        latency_burst_extra_steps=int(cell.get("latency_extra_steps", 0)),
    )
    updates = cell["sensor_updates"]
    sensor_cfg = replace(
        Phase7SensorStackConfig(),
        gnss_update_every_steps=int(updates["gnss"]),
        baro_update_every_steps=int(updates["baro"]),
        range_update_every_steps=int(updates["range"]),
    )
    return fault_cfg, sensor_cfg


def _trace_metrics(trace: list[dict], cfg: dict, outcome: str, final_x: float, final_vz: float) -> dict:
    if not trace:
        return {
            "failure": terminal_failure(outcome, cfg["failure_definition"]["terminal_failure_outcomes"]),
            "degraded_entered": False,
            "recovered": False,
            "recovery_time_s": None,
            "non_recovery": True,
            "degradation_latency_s": None,
            "hold_rate": 0.0,
            "abstention_rate": 0.0,
            "safety_envelope_violation_rate": 0.0,
            "control_confidence_at_failure": None,
            "control_sigma_at_failure_m": None,
            "control_confidence_at_recovery": None,
            "control_sigma_at_recovery_m": None,
            "terminal_position_error_m": float(final_x),
            "terminal_descent_rate_error_mps": float(abs(final_vz - SimConfig().target_descent_rate)),
        }

    t = np.asarray([r["time_s"] for r in trace], dtype=float)
    decision = np.asarray([r["decision"] for r in trace], dtype=object)
    risk = np.asarray([r["risk"] for r in trace], dtype=float)
    vx = np.asarray([r["state_vx_mps"] for r in trace], dtype=float)
    vz = np.asarray([r["state_vz_mps"] for r in trace], dtype=float)
    fault_active = np.asarray([r["fault_active"] for r in trace], dtype=bool)

    degraded_cfg = cfg["degraded_envelope"]
    recovery_cfg = cfg["recovery_envelope"]
    safety_cfg = cfg["safety_envelope_violation"]

    degraded = (
        (decision != "proceed")
        | (risk >= float(degraded_cfg["risk_gte"]))
        | (np.abs(vx) > float(degraded_cfg["max_abs_vx_mps"]))
        | (np.abs(vz) > float(degraded_cfg["max_abs_vz_mps"]))
    )
    recovery = (
        (decision == recovery_cfg["decision"])
        & (risk <= float(recovery_cfg["risk_lte"]))
        & (np.abs(vx) <= float(recovery_cfg["max_abs_vx_mps"]))
        & (np.abs(vz) <= float(recovery_cfg["max_abs_vz_mps"]))
    )
    safety_violation = (
        (risk >= float(safety_cfg["risk_gte"]))
        | (np.abs(vx) > float(safety_cfg["max_abs_vx_mps"]))
        | (np.abs(vz) > float(safety_cfg["max_abs_vz_mps"]))
    )

    onset_s = float(t[np.argmax(fault_active)]) if bool(fault_active.any()) else 0.0
    recovery_result = recovery_outcome(
        t,
        degraded,
        recovery,
        onset_s=onset_s,
        dwell_s=float(recovery_cfg["sustained_s"]),
    )

    first_degraded_index = None
    if recovery_result["degraded_entered"]:
        first_degraded_index = int(np.searchsorted(t, recovery_result["degraded_entry_s"], side="left"))
    degradation_latency = None if first_degraded_index is None else max(0.0, float(t[first_degraded_index] - onset_s))

    any_abstained = np.asarray(
        [bool(r["lateral_abstained"] or r["altitude_abstained"]) for r in trace],
        dtype=bool,
    )
    failure = terminal_failure(outcome, cfg["failure_definition"]["terminal_failure_outcomes"])
    final_row = trace[-1]
    recovery_index = recovery_result["recovery_index"]
    recovery_row = None if recovery_index is None else trace[int(recovery_index)]

    return {
        "failure": bool(failure),
        "degraded_entered": bool(recovery_result["degraded_entered"]),
        "recovered": bool(recovery_result["recovered"]),
        "recovery_time_s": recovery_result["recovery_time_s"],
        "non_recovery": bool(recovery_result["non_recovery"]),
        "degradation_latency_s": degradation_latency,
        "hold_rate": float(np.mean(decision == "hold")),
        "abstention_rate": float(np.mean(any_abstained)),
        "safety_envelope_violation_rate": float(np.mean(safety_violation)),
        "control_confidence_at_failure": float(final_row["control_confidence"]) if failure else None,
        "control_sigma_at_failure_m": float(final_row["control_sigma_pos_m"]) if failure else None,
        "control_confidence_at_recovery": None if recovery_row is None else float(recovery_row["control_confidence"]),
        "control_sigma_at_recovery_m": None if recovery_row is None else float(recovery_row["control_sigma_pos_m"]),
        "terminal_position_error_m": float(final_x),
        "terminal_descent_rate_error_mps": float(abs(final_vz - SimConfig().target_descent_rate)),
    }


def _summarize(raw: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for (dimension, level), group in raw.groupby(["dimension", "severity_level"], sort=True):
        n = len(group)
        failure_n = int(group["failure"].sum())
        non_recovery_n = int(group["non_recovery"].sum())
        failure_ci = wilson_interval(failure_n, n)
        non_recovery_ci = wilson_interval(non_recovery_n, n)
        finite = pd.to_numeric(group["recovery_time_s"], errors="coerce").dropna()
        degradation_latency = pd.to_numeric(group["degradation_latency_s"], errors="coerce").dropna()
        rows.append({
            "dimension": dimension,
            "severity_level": int(level),
            "episodes": int(n),
            "failure_probability": failure_n / n,
            "failure_ci_low": failure_ci[0],
            "failure_ci_high": failure_ci[1],
            "non_recovery_probability": non_recovery_n / n,
            "non_recovery_ci_low": non_recovery_ci[0],
            "non_recovery_ci_high": non_recovery_ci[1],
            "finite_recovery_n": int(len(finite)),
            "median_recovery_time_s": float(finite.median()) if len(finite) else np.nan,
            "q25_recovery_time_s": float(finite.quantile(0.25)) if len(finite) else np.nan,
            "q75_recovery_time_s": float(finite.quantile(0.75)) if len(finite) else np.nan,
            "median_degradation_latency_s": float(degradation_latency.median()) if len(degradation_latency) else np.nan,
            "mean_hold_rate": float(group["hold_rate"].mean()),
            "mean_abstention_rate": float(group["abstention_rate"].mean()),
            "mean_safety_envelope_violation_rate": float(group["safety_envelope_violation_rate"].mean()),
            "unsafe_touchdown_rate": float(group["unsafe_touchdown"].mean()),
            "timeout_rate": float((group["outcome"] == "timeout").mean()),
            "abort_rate": float(group["aborted"].mean()),
            "mean_terminal_position_error_m": float(group["terminal_position_error_m"].mean()),
            "mean_terminal_descent_rate_error_mps": float(group["terminal_descent_rate_error_mps"].mean()),
        })
    return pd.DataFrame(rows)


def _plot(summary: pd.DataFrame, out_dir: Path) -> list[str]:
    paths: list[str] = []
    specs = [
        ("failure_probability", "Failure probability", "failure_probability_vs_severity.png"),
        ("median_recovery_time_s", "Median finite recovery time (s)", "recovery_time_vs_severity.png"),
        ("non_recovery_probability", "Non-recovery probability", "non_recovery_probability_vs_severity.png"),
        ("mean_hold_rate", "Mean HOLD rate", "hold_rate_vs_severity.png"),
    ]
    for column, ylabel, filename in specs:
        fig, ax = plt.subplots(figsize=(7.2, 4.4))
        for dimension, group in summary.groupby("dimension", sort=True):
            ordered = group.sort_values("severity_level")
            ax.plot(ordered["severity_level"], ordered[column], marker="o", label=str(dimension).replace("_", " "))
        ax.set_xlabel("Frozen uncertainty severity level")
        ax.set_ylabel(ylabel)
        ax.set_xticks([0, 1, 2, 3])
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(out_dir / filename, dpi=160)
        plt.close(fig)
        paths.append(filename)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the frozen AegisLand/Nakahira uncertainty-safety benchmark.")
    parser.add_argument("--config", type=Path, default=Path("configs/nakahira_uncertainty_frozen_v1.json"))
    parser.add_argument("--role", choices=["development_seen", "heldout_unseen"], required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--git-sha", default=os.environ.get("GITHUB_SHA", "unknown-local-worktree"))
    args = parser.parse_args()

    cfg = _load_config(args.config)
    seed_key = "development_seeds" if args.role == "development_seen" else "heldout_seeds"
    seeds = [int(x) for x in cfg["evidence"][seed_key]]
    if set(cfg["evidence"]["development_seeds"]) & set(cfg["evidence"]["heldout_seeds"]):
        raise ValueError("development and held-out seeds overlap")

    hist = cfg["historical_components"]
    temporal_calibrator = fit_synthetic_calibrator(seed=int(hist["temporal_calibration_seed"]), samples_per_condition=int(hist["temporal_calibration_samples_per_condition"]))
    component_calibrator = fit_component_calibrator(seed=int(hist["component_calibration_seed"]), samples_per_condition=int(hist["component_calibration_samples_per_condition"]))

    episode_rows: list[dict] = []
    trace_rows: list[dict] = []
    for cell in cfg["cells"]:
        fault_cfg, sensor_cfg = _condition_settings(cell, cfg)
        for seed in seeds:
            result = run_nakahira_episode(
                seed,
                cell["condition"],
                temporal_calibrator,
                component_calibrator,
                fault_scenario=cell["fault_scenario"],
                plant_model=hist["plant_model"],
                severity=float(cell["image_severity"]),
                fault_cfg=fault_cfg,
                sensor_cfg=sensor_cfg,
            )
            metrics = _trace_metrics(result.trace, cfg, result.outcome, result.final_x_error, result.final_vz)
            episode_rows.append({
                **result.episode_dict(),
                "dimension": cell["dimension"],
                "severity_level": int(cell["severity_level"]),
                "evidence_role": args.role,
                "image_severity": float(cell["image_severity"]),
                "latency_extra_steps": int(cell["latency_extra_steps"]),
                "gnss_update_every_steps": int(cell["sensor_updates"]["gnss"]),
                "baro_update_every_steps": int(cell["sensor_updates"]["baro"]),
                "range_update_every_steps": int(cell["sensor_updates"]["range"]),
                **metrics,
            })
            for trace_row in result.trace:
                trace_rows.append({
                    "dimension": cell["dimension"],
                    "severity_level": int(cell["severity_level"]),
                    "seed": int(seed),
                    "evidence_role": args.role,
                    **trace_row,
                })

    args.out.mkdir(parents=True, exist_ok=True)
    raw = pd.DataFrame(episode_rows)
    traces = pd.DataFrame(trace_rows)
    summary = _summarize(raw)

    raw.to_csv(args.out / "episode_results.csv", index=False)
    traces.to_csv(args.out / "step_traces.csv.gz", index=False, compression="gzip")
    summary.to_csv(args.out / "summary_by_severity.csv", index=False)
    plot_files = _plot(summary, args.out)

    metadata = {
        "schema": SCHEMA,
        "evidence_role": args.role,
        "git_sha": args.git_sha,
        "config_path": str(args.config),
        "base_aegis_commit": cfg["base_aegis_commit"],
        "paired_seeds_across_conditions": cfg["evidence"]["paired_seeds_across_conditions"],
        "seed_count_per_cell": len(seeds),
        "cells": len(cfg["cells"]),
        "primary_metrics": cfg["primary_metrics"],
        "mandatory_separate_outcome": cfg["mandatory_separate_outcome"],
        "simulation_only": True,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "negative_results_preserved": True,
        "interpretation_boundary": "Synthetic AegisLand simulation only; not physical-UAV validation or safety acceptance.",
    }
    (args.out / "run_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    (args.out / "frozen_config.json").write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    (args.out / "git_sha.txt").write_text(args.git_sha + "\n", encoding="utf-8")

    report_lines = [
        f"# Nakahira uncertainty-safety benchmark — {args.role}",
        "",
        "Primary result family: failure probability and recovery time.",
        "Non-recovery is reported separately and is never converted to an arbitrary finite recovery time.",
        "",
        f"Executable commit: `{args.git_sha}`",
        "",
        "This is simulation-only evidence. `safety_acceptance = false`.",
        "",
        "## Summary",
        "",
        summary.to_csv(index=False),
    ]
    (args.out / "summary.md").write_text("\n".join(report_lines), encoding="utf-8")

    files = [
        "episode_results.csv",
        "step_traces.csv.gz",
        "summary_by_severity.csv",
        "run_metadata.json",
        "frozen_config.json",
        "git_sha.txt",
        "summary.md",
        *plot_files,
    ]
    write_result_manifest(
        args.out,
        files,
        schema=SCHEMA,
        extra={"git_sha": args.git_sha, "evidence_role": args.role, "simulation_only": True, "safety_acceptance": False},
    )
    print(summary.to_string(index=False))
    print(f"\nSaved {args.role} benchmark to {args.out.resolve()}")


if __name__ == "__main__":
    main()
