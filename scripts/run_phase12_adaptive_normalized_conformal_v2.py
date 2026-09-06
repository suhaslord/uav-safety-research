from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scripts import run_phase12_adaptive_normalized_conformal as v1
except ModuleNotFoundError:
    import run_phase12_adaptive_normalized_conformal as v1

CONTINUITY_SCALE_SHRINKAGE = 0.5
CONTINUITY_GROUPS = (v1.p11.GROUP_H3, v1.p11.GROUP_H45, v1.p11.GROUP_H67)
CANDIDATE_SCHEMA = "aegisland.phase12.adaptive-normalized-conformal.candidate.v2"


def _scale_values(df: pd.DataFrame, models: dict[str, object], axis: str) -> np.ndarray:
    """V2 scale: V1 clipped-linear severity scale with bounded continuity contrast.

    The exponent is applied only within continuity groups. Uniform rescaling would
    cancel under conformal calibration; this changes only relative width allocation
    within a group while preserving monotonicity in the inference-visible severity.
    """
    groups = v1.p11._groups(df).astype(str).to_numpy()
    severity = df["severity"].to_numpy(float)
    out = np.empty(len(df), dtype=float)

    for i, group in enumerate(groups):
        if not np.isfinite(severity[i]):
            raise RuntimeError("phase12 inference-visible severity is non-finite")
        m = models[group][axis]
        lo_s = float(m["severity_10"])
        hi_s = float(m["severity_90"])
        t = float(np.clip((severity[i] - lo_s) / (hi_s - lo_s), 0.0, 1.0))
        lo = float(m["scale_low_m"])
        hi = float(m["scale_high_m"])
        floor = float(m["scale_floor_m"])
        raw = max(floor, lo + t * (hi - lo))

        if group in CONTINUITY_GROUPS and hi > lo:
            center = max(floor, float(np.sqrt(lo * hi)))
            raw = center * (raw / center) ** CONTINUITY_SCALE_SHRINKAGE

        out[i] = max(floor, raw)
    return out


def _with_v2_scale(fn, *args, **kwargs):
    original = v1._scale_values
    v1._scale_values = _scale_values
    try:
        return fn(*args, **kwargs)
    finally:
        v1._scale_values = original


def _build_candidate(predecessor_path: Path, git_sha: str | None) -> dict[str, object]:
    candidate = _with_v2_scale(v1._build_candidate, predecessor_path, git_sha)
    candidate["schema"] = CANDIDATE_SCHEMA
    candidate["method"] = "continuity_shrunk_adaptive_normalized_robust_conformal"
    candidate["continuity_scale_shrinkage_exponent"] = CONTINUITY_SCALE_SHRINKAGE
    candidate["development_iteration"] = 2
    return candidate


def _summarize(
    df: pd.DataFrame,
    candidate: dict[str, object],
    role: str,
    seed: int,
    minimums: dict[str, int],
) -> dict[str, object]:
    return _with_v2_scale(v1._summarize, df, candidate, role, seed, minimums)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Phase 12 iteration 2: continuity-shrunk adaptive normalized robust conformal"
    )
    p.add_argument("--stage", choices=("freeze", "dev", "transfer", "validation", "final"), required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--predecessor", type=Path)
    p.add_argument("--candidate", type=Path)
    p.add_argument("--git-sha")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    if args.stage == "freeze":
        if args.predecessor is None:
            raise SystemExit("--predecessor is required for --stage freeze")
        candidate = _build_candidate(args.predecessor, args.git_sha)
        path = args.out / "candidate_freeze.json"
        path.write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("PHASE12_V2_CANDIDATE_SHA256=" + v1._sha256_file(path))
        print("PHASE12_V2_SCALE_COUNTS=" + json.dumps(candidate["group_counts"], sort_keys=True))
        return

    if args.candidate is None:
        raise SystemExit("--candidate is required for evaluation stages")
    candidate = v1._load_json(args.candidate)
    if candidate.get("schema") != CANDIDATE_SCHEMA:
        raise RuntimeError("unexpected Phase 12 iteration-2 candidate schema")
    if float(candidate.get("continuity_scale_shrinkage_exponent", -1.0)) != CONTINUITY_SCALE_SHRINKAGE:
        raise RuntimeError("Phase 12 iteration-2 shrinkage exponent mismatch")

    seed, families, domains, strata, minimums, filename = v1._stage_config(args.stage)
    df = v1._event(f"phase12_v2_{args.stage}", seed, families, domains, strata, candidate)
    result = _summarize(df, candidate, f"phase12_v2_{args.stage}", seed, minimums)
    result["schema"] = f"aegisland.phase12.v2.{args.stage}-result.v1"
    result["candidate_sha256"] = v1._sha256_file(args.candidate)
    result["scientific_git_sha"] = args.git_sha
    result["simulation_only"] = True
    result["safety_acceptance"] = False
    result["continuity_scale_shrinkage_exponent"] = CONTINUITY_SCALE_SHRINKAGE
    if args.stage == "dev":
        result["development_only"] = True
        result["eligible_for_progression"] = False

    (args.out / "candidate_freeze.json").write_text(
        args.candidate.read_text(encoding="utf-8"), encoding="utf-8"
    )
    result_path = args.out / filename
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PHASE12_V2_{args.stage.upper()}_RESULT_SHA256=" + v1._sha256_file(result_path))
    print(
        f"PHASE12_V2_{args.stage.upper()}_ALL_PRIMARY_GATES_PASS="
        + str(bool(result.get("all_primary_gates_pass", False))).lower()
    )
    print(json.dumps(result.get("gates", {}), sort_keys=True))


if __name__ == "__main__":
    main()
