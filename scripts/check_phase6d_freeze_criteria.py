from __future__ import annotations

from pathlib import Path
import argparse
import json

import pandas as pd


REFERENCE = "image_aegis_v3"
CANDIDATE = "image_aegis_phase6d"


def rate(frame: pd.DataFrame, column: str) -> float:
    return float(frame[column].mean())


def timeout_rate(frame: pd.DataFrame) -> float:
    return float((frame["outcome"] == "timeout").mean())


def main() -> None:
    parser = argparse.ArgumentParser(description="Check preregistered Phase 6D development freeze criteria.")
    parser.add_argument("--results", type=Path, required=True)
    args = parser.parse_args()

    raw = pd.read_csv(args.results / "episodes.csv")
    candidate_all = raw[raw["architecture"] == CANDIDATE].copy()
    reference_all = raw[raw["architecture"] == REFERENCE].copy()
    if candidate_all.empty or reference_all.empty:
        raise ValueError("results must contain original Phase 6 and Phase 6D rows")

    rows: list[dict] = []
    pass_all = True

    for condition in sorted(candidate_all["condition"].unique()):
        c = candidate_all[candidate_all["condition"] == condition].set_index("seed")
        r = reference_all[reference_all["condition"] == condition].set_index("seed")
        common = c.index.intersection(r.index)
        c = c.loc[common]
        r = r.loc[common]
        if len(common) == 0:
            raise ValueError(f"no paired episodes for {condition}")

        reference_success_became_failure = int((r["success"] & ~c["success"]).sum())
        condition_pass = reference_success_became_failure == 0

        reference_success = rate(r, "success")
        candidate_success = rate(c, "success")
        reference_unsafe = rate(r, "unsafe_touchdown")
        candidate_unsafe = rate(c, "unsafe_touchdown")
        reference_abort = rate(r, "aborted")
        candidate_abort = rate(c, "aborted")
        reference_timeout = timeout_rate(r)
        candidate_timeout = timeout_rate(c)

        if condition in {"clean", "blur"}:
            condition_pass &= candidate_success >= reference_success
        if condition in {"low_light", "mixed"}:
            condition_pass &= (
                candidate_success >= reference_success
                and candidate_unsafe <= reference_unsafe
                and candidate_abort <= reference_abort
                and candidate_timeout <= reference_timeout
            )
        if condition == "occlusion":
            condition_pass &= (
                candidate_success >= reference_success
                and candidate_unsafe <= reference_unsafe
            )

        alias_frames = pd.to_numeric(c.get("hard_altitude_alias_frames"), errors="coerce")
        episodes_with_alias = int((alias_frames.fillna(0) > 0).sum())
        alias_episode_rate = episodes_with_alias / len(c)

        rows.append({
            "condition": condition,
            "paired_episodes": len(common),
            "reference_success_rate": reference_success,
            "candidate_success_rate": candidate_success,
            "reference_unsafe_rate": reference_unsafe,
            "candidate_unsafe_rate": candidate_unsafe,
            "reference_abort_rate": reference_abort,
            "candidate_abort_rate": candidate_abort,
            "reference_timeout_rate": reference_timeout,
            "candidate_timeout_rate": candidate_timeout,
            "reference_success_became_candidate_failure": reference_success_became_failure,
            "episodes_with_hard_alias": episodes_with_alias,
            "hard_alias_episode_rate": alias_episode_rate,
            "condition_freeze_pass": bool(condition_pass),
        })
        pass_all &= bool(condition_pass)

    report = pd.DataFrame(rows)
    clean_blur_alias_review = bool(
        report[report["condition"].isin(["clean", "blur"])]["hard_alias_episode_rate"].max() > 0.10
    )
    final_pass = bool(pass_all and not clean_blur_alias_review)

    payload = {
        "phase6d_development_freeze_pass": final_pass,
        "paired_condition_criteria_pass": bool(pass_all),
        "clean_blur_alias_review_triggered": clean_blur_alias_review,
        "alias_review_rule": "manual review is required if hard-altitude-alias activation appears in more than 10% of clean or blur development episodes; this is an audit trigger, not a tuned landing threshold",
        "reserved_unseen_seeds_remain_unrun": [868686, 878787],
    }

    report.to_csv(args.results / "freeze_criteria.csv", index=False)
    (args.results / "freeze_criteria.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (args.results / "freeze_criteria.md").write_text(
        "# Phase 6D development freeze check\n\n"
        + report.to_markdown(index=False)
        + "\n\n```json\n"
        + json.dumps(payload, indent=2)
        + "\n```\n",
        encoding="utf-8",
    )

    print(report.to_string(index=False))
    print(json.dumps(payload, indent=2))

    if not final_pass:
        raise SystemExit("Phase 6D does not satisfy the preregistered development freeze criteria")


if __name__ == "__main__":
    main()
