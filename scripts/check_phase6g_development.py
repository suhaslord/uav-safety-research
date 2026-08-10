from __future__ import annotations

from pathlib import Path
import argparse
import json

import pandas as pd


REFERENCE = "image_aegis_v3"
CANDIDATE = "image_aegis_phase6g"


def _rate(frame: pd.DataFrame, column: str) -> float:
    return float(frame[column].mean())


def _timeout_rate(frame: pd.DataFrame) -> float:
    return float((frame["outcome"] == "timeout").mean())


def main() -> None:
    parser = argparse.ArgumentParser(description="Check preregistered Phase 6G landing-development criteria.")
    parser.add_argument("--results", type=Path, required=True)
    args = parser.parse_args()

    raw = pd.read_csv(args.results / "episodes.csv")
    phase6 = raw[raw["architecture"] == REFERENCE]
    phase6g = raw[raw["architecture"] == CANDIDATE]
    if phase6.empty or phase6g.empty:
        raise ValueError("results must contain original Phase 6 and Phase 6G rows")

    rows: list[dict] = []
    all_pass = True
    total_phase6_success_to_g_failure = 0

    for condition in sorted(phase6g["condition"].unique()):
        r = phase6[phase6["condition"] == condition].set_index("seed")
        c = phase6g[phase6g["condition"] == condition].set_index("seed")
        common = r.index.intersection(c.index)
        if len(common) != 50:
            raise ValueError(f"expected 50 paired episodes for {condition}, got {len(common)}")
        r = r.loc[common]
        c = c.loc[common]

        regressions = int((r["success"] & ~c["success"]).sum())
        total_phase6_success_to_g_failure += regressions
        r_success = _rate(r, "success")
        c_success = _rate(c, "success")
        r_unsafe = _rate(r, "unsafe_touchdown")
        c_unsafe = _rate(c, "unsafe_touchdown")
        r_abort = _rate(r, "aborted")
        c_abort = _rate(c, "aborted")
        r_timeout = _timeout_rate(r)
        c_timeout = _timeout_rate(c)

        condition_pass = bool(
            regressions == 0
            and c_success >= r_success
            and c_unsafe <= r_unsafe
            and c_abort <= r_abort
            and c_timeout <= r_timeout
        )
        rows.append({
            "condition": condition,
            "paired_episodes": len(common),
            "phase6_success_rate": r_success,
            "phase6g_success_rate": c_success,
            "phase6_unsafe_rate": r_unsafe,
            "phase6g_unsafe_rate": c_unsafe,
            "phase6_abort_rate": r_abort,
            "phase6g_abort_rate": c_abort,
            "phase6_timeout_rate": r_timeout,
            "phase6g_timeout_rate": c_timeout,
            "phase6_success_became_phase6g_failure": regressions,
            "condition_pass": condition_pass,
        })
        all_pass &= condition_pass

    paired_condition = pd.DataFrame(rows)
    final_pass = bool(all_pass and total_phase6_success_to_g_failure == 0)
    payload = {
        "phase6g_development_pass": final_pass,
        "protocol": "docs/phase6g_landing_development.md",
        "episode_seed_family": 838381,
        "calibration_seed": 616161,
        "phase6_success_became_phase6g_failure_total": total_phase6_success_to_g_failure,
        "no_post_result_retuning": True,
        "historical_seen_heldout_seeds_do_not_reuse": [868686, 878787],
        "replacement_reserved_unseen_seeds_remain_unrun": [918271, 928271],
    }

    args.results.mkdir(parents=True, exist_ok=True)
    paired_condition.to_csv(args.results / "development_criteria.csv", index=False)
    (args.results / "development_criteria.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (args.results / "development_criteria.md").write_text(
        "# Phase 6G landing-development criteria check\n\n"
        + paired_condition.to_markdown(index=False)
        + "\n\n```json\n" + json.dumps(payload, indent=2) + "\n```\n",
        encoding="utf-8",
    )

    print(paired_condition.to_string(index=False))
    print(json.dumps(payload, indent=2))
    if not final_pass:
        raise SystemExit("Phase 6G does not satisfy the preregistered landing-development criteria")


if __name__ == "__main__":
    main()
