#!/usr/bin/env python3
"""Freeze a verified original-model replay and clean-versus-stress pairs.

No inference, training, source substitution, or numerical result replacement.
The preceding run_phase25_frame_audit command must already have passed the
original checkpoint, image-byte, runtime and aggregate gates.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from phase25_lib import CONDITIONS, sha256_file
from analyze_phase25_failures import _validate_inputs

RECOVERY_COMMIT = "f090da03d20b2425c5addccb4d19117c8991bcc1"
RECOVERED_PATHS = (
    "docs/phase25_occlusion_sweep_protocol.md", "docs/phase25_occlusion_sweep_reproduce.md",
    "results/phase25_control_input_diagnostic/clean_reconciliation.csv",
    "results/phase25_control_input_diagnostic/diagnostic.json",
    "results/phase25_occlusion_sweep/historical_attempt.json",
    "results/phase25_occlusion_sweep_recovered/restoration_record.json",
    "results/phase25_occlusion_sweep_recovered/summary.md",
    "results/phase25_occlusion_sweep_recovered/zero_dose_gate.json",
    "scripts/run_phase25_occlusion_sweep.py", "tests/test_phase25_occlusion_sweep_publication.py",
)
TABLES = ("aggregate_validation.csv", "frame_condition_metrics.csv", "prediction_boxes.csv", "ground_truth_targets.csv")
METRICS = ("precision", "recall", "map50", "map50_95")


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def boolean(value) -> bool:
    if value is True or value == "True":
        return True
    if value is False or value == "False":
        return False
    raise ValueError(f"Invalid outcome flag: {value!r}")


def clean_stress_pairs(rows: list[dict], frames: list[dict]) -> list[dict]:
    lookup = {(r["model"], r["frame_id"], r["condition"]): r for r in rows}
    expected = {(m, f["image"], c) for m in ("baseline", "phase23") for f in frames for c in CONDITIONS}
    if len(lookup) != len(rows) or set(lookup) != expected:
        raise ValueError("Missing or duplicate model/frame/condition cases")
    pairs = []
    for model in ("baseline", "phase23"):
        for frame in frames:
            clean = lookup[model, frame["image"], "clean"]
            for condition in CONDITIONS[1:]:
                stressed = lookup[model, frame["image"], condition]
                a, b = boolean(clean["frame_success"]), boolean(stressed["frame_success"])
                outcome = ("both_pass" if a and b else "regressed" if a else "recovered" if b else "both_fail")
                pairs.append({"model": model, "frame_id": frame["image"], "sequence": frame["sequence"],
                              "condition": condition, "clean_success": a, "stressed_success": b,
                              "outcome": outcome, "clean_tp": int(clean["tp"]), "stressed_tp": int(stressed["tp"]),
                              "clean_fp": int(clean["fp"]), "stressed_fp": int(stressed["fp"]),
                              "clean_fn": int(clean["fn"]), "stressed_fn": int(stressed["fn"])})
    return pairs


def authenticate_recovery() -> list[dict]:
    evidence = []
    for name in RECOVERED_PATHS:
        original = subprocess.check_output(["git", "show", f"{RECOVERY_COMMIT}:{name}"], cwd=ROOT)
        actual = (ROOT / name).read_bytes()
        if actual != original:
            raise ValueError(f"Recovered file is not exact {RECOVERY_COMMIT}: {name}")
        evidence.append({"path": name, "sha256": hashlib.sha256(actual).hexdigest()})
    return evidence


def verify(replay: Path) -> tuple[dict, list[dict]]:
    protected = ROOT / "results/phase25_failure_atlas/protected_test_manifest.csv"
    rows, _, _, aggregates = _validate_inputs(replay, protected)
    frames = read_rows(protected)
    manifest = json.loads((replay / "run_manifest.json").read_text(encoding="utf-8"))
    lock = json.loads((ROOT / "docs/phase25_input_lock.json").read_text(encoding="utf-8"))
    observed = {"python_version": platform.python_version(), **{k: importlib.metadata.version(p) for k, p in
                [("ultralytics_version", "ultralytics"), ("torch_version", "torch"),
                 ("numpy_version", "numpy"), ("pillow_version", "Pillow")]}}
    for key, value in observed.items():
        if value != lock["phase25_runtime"][key] or manifest[key] != value:
            raise ValueError(f"Original runtime mismatch: {key}")
    for field, section in [("baseline_weights_sha256", "phase22_baseline"), ("phase23_weights_sha256", "phase23_robust")]:
        if manifest[field] != lock[section]["checkpoint_sha256"]:
            raise ValueError(f"Original checkpoint mismatch: {field}")
    for name, expected in manifest["method_files_sha256"].items():
        recorded = subprocess.check_output(["git", "show", f"{manifest['git_commit']}:{name}"], cwd=ROOT)
        if hashlib.sha256(recorded).hexdigest() != expected:
            raise ValueError(f"Replay method is not authenticated at its recorded commit: {name}")
    published = {r["condition"]: r for r in read_rows(ROOT / "results/phase23_robust_detector/robustness_metrics.csv")}
    differences = {r["condition"]: {m: float(r[m]) - float(published[r["condition"]][m]) for m in METRICS}
                   for r in aggregates if r["model"] == "phase23"}
    maximum = max(abs(d) for delta in differences.values() for d in delta.values())
    if len(differences) != 6 or maximum > lock["inference_settings"]["metric_tolerance"]:
        raise ValueError("Phase 23 published aggregate reconciliation failed")
    frozen = ROOT / "results/phase25_failure_atlas"
    equality = {name: sha256_file(replay / name) == sha256_file(frozen / name) for name in TABLES}
    if not all(equality.values()):
        raise ValueError(f"Replayed prediction tables differ from frozen tables: {equality}")
    pairs = clean_stress_pairs(rows, frames)
    cross_model = Counter()
    lookup = {(r["model"], r["frame_id"], r["condition"]): r for r in rows}
    for frame in frames:
        for condition in CONDITIONS:
            a = boolean(lookup["baseline", frame["image"], condition]["frame_success"])
            b = boolean(lookup["phase23", frame["image"], condition]["frame_success"])
            cross_model["both_pass" if a and b else "regressed" if a else "recovered" if b else "both_fail"] += 1
    summary = [{"model": model, "condition": condition,
                "counts": dict(Counter(r["outcome"] for r in pairs if r["model"] == model and r["condition"] == condition))}
               for model in ("baseline", "phase23") for condition in CONDITIONS[1:]]
    return {"schema": "aegisland.original-detector-replay.v1", "status": "PASS",
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(), "inference_commit": manifest["git_commit"],
            "runtime": observed, "checkpoint_sha256": manifest["phase23_weights_sha256"],
            "baseline_checkpoint_sha256": manifest["baseline_weights_sha256"],
            "protected_manifest_sha256": manifest["protected_manifest_sha256"],
            "source_archive_sha256": manifest["source_archive_sha256"],
            "comparison": "EXACT_MATCH" if maximum == 0 else "MATCH_WITHIN_FROZEN_TOLERANCE",
            "phase23_cells_checked": 24, "maximum_absolute_delta": maximum, "deltas": differences,
            "frozen_tables_byte_identical": equality,
            "replay_table_sha256": {name: sha256_file(replay / name) for name in TABLES},
            "cross_model_transition_counts": dict(cross_model), "clean_stressed_pair_count": len(pairs),
            "clean_stressed_summaries": summary,
            "controlled_occlusion_recovery_source_commit": RECOVERY_COMMIT,
            "controlled_occlusion_recovery_files": authenticate_recovery(),
            "scope": "Retrospective KIOS replay; clean/stress pairs are within the same model. Cross-model transitions are a separate comparison. No independent validation, deployment threshold, or flight-safety claim."}, pairs


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--replay-dir", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    if args.out_dir.exists():
        p.error("Use a new output directory; never replace frozen evidence")
    receipt, pairs = verify(args.replay_dir)
    args.out_dir.mkdir(parents=True)
    table = args.out_dir / "paired_clean_vs_stressed.csv"
    with table.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(pairs[0])); w.writeheader(); w.writerows(pairs)
    receipt["paired_clean_vs_stressed_sha256"] = sha256_file(table)
    receipt["replay_run_manifest_sha256"] = sha256_file(args.replay_dir / "run_manifest.json")
    receipt["verification_script_sha256"] = sha256_file(Path(__file__))
    (args.out_dir / "replay_receipt.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "comparison": receipt["comparison"],
                      "maximum_absolute_delta": receipt["maximum_absolute_delta"],
                      "cross_model_transitions": receipt["cross_model_transition_counts"],
                      "clean_stressed_pairs": len(pairs)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
