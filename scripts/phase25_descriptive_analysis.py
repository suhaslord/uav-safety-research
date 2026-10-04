"""Versioned descriptive correction of the retained Phase 25 observations.

No detector inference, resampling, significance tests, or historical overwrites.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
from itertools import combinations
import json
import math
import re
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "docs/phase25_descriptive_analysis_v1.json"
OUTPUT = ROOT / "results/phase25_corrected_analysis_v1"
TOPOLOGIES = ("CENTER", "OUTER_RING", "STRIPED", "RANDOM_PATCH")
EDGES = (0.0, 0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75)


def text_sha(path: Path) -> str:
    """Hash LF-normalized text, independent of checkout line endings."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def verify_sources(root: Path, lock: dict) -> None:
    for relative, expected in {**lock["source_text_sha256"], **lock.get("method_text_sha256", {})}.items():
        if text_sha(root / relative) != expected:
            raise ValueError(f"Historical evidence changed: {relative}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def boolean(value: str) -> int:
    if value not in {"True", "False"}:
        raise ValueError(f"Invalid recorded boolean: {value}")
    return int(value == "True")


def dose_bin(dose: float) -> int | None:
    if not math.isfinite(dose) or not 0.0 <= dose <= 1.0:
        raise ValueError(f"Invalid achieved dose: {dose}")
    return next((i for i, (lo, hi) in enumerate(zip(EDGES, EDGES[1:]))
                 if lo <= dose < hi), None)


def first_downward_crossing(rates: list[float | None]) -> float | None:
    """Interpolate the first observed downward crossing between adjacent bins.

    Missing bins are not bridged; upward crossings and flat 50% segments do
    not establish a downward crossing. This is descriptive, not fitted ED50.
    """
    centers = [(lo + hi) / 2 for lo, hi in zip(EDGES, EDGES[1:])]
    for i, (left, right) in enumerate(zip(rates, rates[1:])):
        if left is not None and right is not None and left >= 0.5 >= right and left > right:
            return centers[i] + (0.5 - left) * (centers[i + 1] - centers[i]) / (right - left)
    return None


def outcome_summary(rows: list[dict[str, str]]) -> dict:
    pairs: dict[tuple[str, str], dict[str, int]] = defaultdict(dict)
    for row in rows:
        key = (row["frame_id"], row["condition"])
        if row["model"] in pairs[key]:
            raise ValueError(f"Duplicate model outcome: {key}")
        pairs[key][row["model"]] = boolean(row["frame_success"])
    counts = Counter()
    for key, pair in pairs.items():
        if set(pair) != {"baseline", "phase23"}:
            raise ValueError(f"Incomplete model pair: {key}")
        baseline, robust = pair["baseline"], pair["phase23"]
        counts[(baseline, robust)] += 1
    n = len(pairs)
    baseline = counts[(1, 1)] + counts[(1, 0)]
    robust = counts[(1, 1)] + counts[(0, 1)]
    return {"paired_views": n, "recovered": counts[(0, 1)], "regressed": counts[(1, 0)],
            "both_pass": counts[(1, 1)], "both_fail": counts[(0, 0)],
            "baseline_successes": baseline, "phase23_successes": robust,
            "baseline_rate": baseline / n, "phase23_rate": robust / n,
            "difference_pp": 100 * (robust - baseline) / n}


def topology_summary(rows: list[dict[str, str]]) -> dict:
    groups: dict[tuple[str, int], list[dict[str, str]]] = defaultdict(list)
    frame_bins: dict[tuple[str, str, int], list[int]] = defaultdict(list)
    sequences = {}
    excluded = Counter()
    for row in rows:
        topo, frame = row["topology"], row["frame_id"]
        if topo not in TOPOLOGIES:
            raise ValueError(f"Unexpected topology: {topo}")
        sequences[frame] = row["sequence"]
        index = dose_bin(float(row["achieved_dose"]))
        if index is None:
            excluded[topo] += 1
            continue
        groups[(topo, index)].append(row)
        frame_bins[(topo, frame, index)].append(boolean(row["frame_success"]))
    bins, crossings = {}, {}
    for topo in TOPOLOGIES:
        bins[topo] = []
        for i, (lo, hi) in enumerate(zip(EDGES, EDGES[1:])):
            selected = groups[(topo, i)]
            doses = [float(r["achieved_dose"]) for r in selected]
            successes = sum(boolean(r["frame_success"]) for r in selected)
            bins[topo].append({"low": lo, "high_exclusive": hi, "views": len(selected),
                               "frames": len({r["frame_id"] for r in selected}),
                               "successes": successes,
                               "success_rate": successes / len(selected) if selected else None,
                               "achieved_min": min(doses) if doses else None,
                               "achieved_max": max(doses) if doses else None,
                               "achieved_mean": mean(doses) if doses else None})
        crossings[topo] = first_downward_crossing([b["success_rate"] for b in bins[topo]])
    rates = {key: mean(values) for key, values in frame_bins.items()}
    contrasts = {}
    for left, right in combinations(TOPOLOGIES, 2):
        shared = [(frame, i) for topo, frame, i in rates if topo == left and (right, frame, i) in rates]

        def matched(selected: list[tuple[str, int]]) -> dict:
            differences: dict[str, list[float]] = defaultdict(list)
            for frame, index in selected:
                differences[frame].append(rates[(left, frame, index)] - rates[(right, frame, index)])
            return {"frames": len(differences), "matched_frame_bins": len(selected),
                    "difference_pp": 100 * mean(mean(v) for v in differences.values()) if selected else None}

        contrasts[f"{left}_minus_{right}"] = {
            **matched(shared),
            "by_sequence": {seq: matched([(f, i) for f, i in shared if sequences[f] == seq])
                            for seq in sorted(set(sequences.values()))},
            "by_bin": [matched([(f, i) for f, i in shared if i == index]) for index in range(len(EDGES) - 1)],
        }
    return {"total_views": len(rows), "excluded_outside_common_support": {t: excluded[t] for t in TOPOLOGIES},
            "bins": bins, "first_observed_downward_crossing": crossings, "matched_contrasts": contrasts,
            "contrast_estimand": "Mean within-frame difference of success rates at shared achieved-dose bins, "
                                  "averaging shared bins equally within each frame, then frames equally. "
                                  "Matching is by bin, not exact dose; discrete dose distributions remain unequal."}


def build_summary(root: Path = ROOT) -> dict:
    lock = json.loads((root / "docs/phase25_descriptive_analysis_v1.json").read_text(encoding="utf-8"))
    verify_sources(root, lock)
    canonical = read_csv(root / "results/phase25_failure_atlas/frame_condition_metrics.csv")
    topology = read_csv(root / "results/phase25_occlusion_topology/topology_views.csv")
    clean = {r["frame_id"]: r for r in canonical if r["model"] == "phase23" and r["condition"] == "clean"}
    zero = [r for r in topology if float(r["requested_dose"]) == 0.0]
    zero_drift = {
        "views": len(zero),
        "source_byte_mismatches": sum(r["source_image_sha256"] != r["generated_image_sha256"] for r in zero),
        "fp_count_mismatches": sum(int(r["fp"]) != int(clean[r["frame_id"]]["fp"]) for r in zero),
        "frame_success_mismatches": sum(r["frame_success"] != clean[r["frame_id"]]["frame_success"] for r in zero),
        "note": "Historical controls were JPEG-reencoded. The original aggregate gate evaluated source "
                "clean images, not these generated controls. Lossless v2 inference has not been run.",
    }
    return {"schema_version": 1, "analysis_status": "post_hoc_descriptive_correction",
            "historical_commit": lock["historical_commit"], "source_text_sha256": lock["source_text_sha256"],
            "method_text_sha256": lock["method_text_sha256"],
            "scope": "86 reused frames from two video sequences; repeated views are dependent. "
                     "No population inference or internal feature mechanism is established.",
            "paired": {"overall": outcome_summary(canonical),
                       "by_condition": {c: outcome_summary([r for r in canonical if r["condition"] == c])
                                        for c in sorted({r["condition"] for r in canonical})},
                       "by_sequence": {s: outcome_summary([r for r in canonical if r["sequence"] == s])
                                       for s in sorted({r["sequence"] for r in canonical})}},
            "topology": topology_summary(topology), "historical_zero_dose": zero_drift}


def render_report(summary: dict) -> str:
    pair, topo, zero = summary["paired"]["overall"], summary["topology"], summary["historical_zero_dose"]
    lines = ["# Phase 25 corrected descriptive analysis v1", "", summary["scope"], "",
             "This post hoc correction supersedes the numerical prose and inferential claims in the "
             "archived reports. Historical raw observations and frozen release files are unchanged. "
             "No new detector inference was performed.", "", "## Paired detector outcomes", "",
             f"Across {pair['paired_views']} paired views: {pair['recovered']} recovered, "
             f"{pair['regressed']} regressed, {pair['both_pass']} both pass, {pair['both_fail']} both fail. "
             f"Baseline success: {pair['baseline_successes']}/{pair['paired_views']}; "
             f"Phase 23: {pair['phase23_successes']}/{pair['paired_views']} "
             f"({pair['difference_pp']:+.2f} percentage points).", ""]
    for condition, values in summary["paired"]["by_condition"].items():
        lines.append(f"- {condition}: baseline {values['baseline_successes']}/{values['paired_views']}, "
                     f"Phase 23 {values['phase23_successes']}/{values['paired_views']}; "
                     f"{values['recovered']} recovered, {values['regressed']} regressed.")
    lines += ["", "## Historical topology observations", "", topo["contrast_estimand"], "",
              "Achieved doses outside [0, 0.75) are excluded rather than clamped into the last bin. "
              "summary.json records counts, dose distributions, matched denominators, sequence strata "
              "and every bin. Bin rates below pool views; contrasts instead give frames equal weight.", ""]
    for name in TOPOLOGIES:
        crossing = topo["first_observed_downward_crossing"][name]
        label = f"{crossing:.6f}" if crossing is not None else "no downward crossing observed"
        lines += [f"### {name}", "", f"First observed downward 50% crossing: {label}. "
                  f"Excluded views: {topo['excluded_outside_common_support'][name]}.", ""]
        for b in topo["bins"][name]:
            rate = f"{100 * b['success_rate']:.2f}%" if b["success_rate"] is not None else "unobserved"
            lines.append(f"- [{b['low']:.2f}, {b['high_exclusive']:.2f}): "
                         f"{b['successes']}/{b['views']} ({rate}), {b['frames']} frames.")
        lines.append("")
    lines += ["## Matched exploratory contrasts", ""]
    for name, values in topo["matched_contrasts"].items():
        lines.append(f"- {name}: {values['difference_pp']:+.2f} percentage points; "
                     f"{values['frames']} frames, {values['matched_frame_bins']} shared frame/bin pairs.")
    lines += ["", "## Control limitation", "",
              f"{zero['source_byte_mismatches']}/{zero['views']} generated zero-dose images differ in bytes "
              f"from their sources; {zero['fp_count_mismatches']} have different false-positive counts "
              f"from canonical Phase 23 clean predictions. Frame-success mismatches: "
              f"{zero['frame_success_mismatches']}. {zero['note']}", "",
              "Crossings are interpolation summaries of non-monotonic observations, not robust biological "
              "or physical dose thresholds. The corrected contrasts are exploratory and cannot restore "
              "confirmatory status to the historical JPEG experiment. Two sequences do not justify the "
              "archived frame-bootstrap uncertainty or significance claims. Training-resolution and "
              "central-ring explanations remain untested hypotheses.", ""]
    return "\n".join(lines)


def render_site_sections(summary: dict) -> str:
    pair, topology = summary["paired"]["overall"], summary["topology"]
    contrast = topology["matched_contrasts"]["OUTER_RING_minus_STRIPED"]
    low_bin = topology["bins"]["OUTER_RING"][1]
    reference = "https://github.com/suhaslord/uav-safety-research/blob/codex/phase25-audit-corrections"
    conditions = "\n".join(
        f"          <li><strong>{name}:</strong> baseline {r['baseline_successes']}/{r['paired_views']}, "
        f"Phase 23 {r['phase23_successes']}/{r['paired_views']}; {r['recovered']} recovered, {r['regressed']} regressed.</li>"
        for name, r in summary["paired"]["by_condition"].items())
    return f'''    <section class="atlas-next" aria-labelledby="study-title" style="margin-top:2rem">
      <div><span>04 / Corrected paired outcomes</span><h2 id="study-title">Recovery and regression on reused frames</h2><p>Descriptive comparison across 86 frames and 6 conditions from two video sequences.</p></div>
      <div class="atlas-next__detail">
        <p><strong>Frame-level paired outcomes:</strong> {pair['recovered']} recovered, {pair['regressed']} regressed, {pair['both_pass']} both pass, {pair['both_fail']} both fail across {pair['paired_views']} views.</p>
        <p>Baseline success: {pair['baseline_successes']}/{pair['paired_views']}; Phase 23: {pair['phase23_successes']}/{pair['paired_views']} ({pair['difference_pp']:+.2f} percentage points).</p>
        <ul>
{conditions}
        </ul>
        <p>These repeated views describe the observed frames. Training-resolution and central-ring explanations remain untested hypotheses; the archived significance and uncertainty claims are superseded.</p>
      </div>
    </section>

    <section class="atlas-next" aria-labelledby="topology-title" style="margin-top:2rem">
      <div><span>05 / Corrected exploratory topology analysis</span><h2 id="topology-title">5,160 archived treatment views</h2><p>Post hoc descriptive correction of CENTER, OUTER_RING, STRIPED and RANDOM_PATCH observations.</p></div>
      <div class="atlas-next__detail">
        <ul>
          <li><strong>Matched achieved-dose bins:</strong> OUTER_RING minus STRIPED: {contrast['difference_pp']:+.2f} percentage points across {contrast['frames']} frames and {contrast['matched_frame_bins']} shared frame/bin pairs. Rates are compared within each frame and shared bin, then averaged equally by frame. This is an exploratory contrast.</li>
          <li><strong>Observed crossing:</strong> OUTER_RING success is {low_bin['successes']}/{low_bin['views']} ({100 * low_bin['success_rate']:.2f}%) in achieved-dose bin [0.05, 0.15). Its first downward 50% crossing interpolates to {topology['first_observed_downward_crossing']['OUTER_RING']:.6f}; the curve is non-monotonic.</li>
          <li><strong>Common support:</strong> {sum(topology['excluded_outside_common_support'].values())} views at achieved doses of 0.75 or more are excluded. The corrected summary records denominators, dose distributions and sequence strata.</li>
          <li><strong>Historical control limitation:</strong> JPEG reencoding changed zero-dose image bytes and false-positive counts. The original aggregate gate evaluated source clean images. Lossless v2 inference has not been run.</li>
        </ul>
        <p>Two source sequences do not support the archived confirmatory claims. These synthetic masks describe benchmark sensitivity without establishing internal detector mechanisms.</p>
        <p><a href="{reference}/results/phase25_corrected_analysis_v1/report.md" target="_blank" rel="noreferrer">Corrected descriptive report ↗</a> · <a href="{reference}/results/phase25_corrected_analysis_v1/summary.json" target="_blank" rel="noreferrer">Corrected summary ↗</a> · <a href="{reference}/docs/phase25_corrections.md" target="_blank" rel="noreferrer">Erratum and replay method ↗</a></p>
      </div>
    </section>'''


def render_home_summary(summary: dict) -> str:
    return f'''        <div class="phase25-feature__copy"><span class="phase25-feature__state">Paired outcomes · descriptive correction</span><p>Phase 23 frame-level evidence recovered and reproduced. The {summary['topology']['total_views']:,}-view archived topology study has a corrected exploratory analysis. Reused video frames and the historical JPEG control limit its interpretation.</p><div class="atlas-condition-controls" data-atlas-controls aria-label="Compare generated camera conditions"></div><strong class="phase25-feature__delta" data-atlas-delta></strong><a class="phase25-feature__link" href="/phases/phase25/">Corrected Phase 25 study &amp; Atlas →</a><small>86 protected KIOS frames · 2 sessions · Phase 26 external admission unresolved (0/7 qualified) · no flight safety claims.</small><small hidden data-atlas-error>The condition comparison is unavailable; the research page remains accessible.</small></div>
        <div class="phase25-feature__proof"><span><b>86</b> protected frames</span><span><b>516</b> paired views</span><span><b>5,160</b> archived topology views</span><span><b>2</b> source sessions</span><a href="https://github.com/suhaslord/uav-safety-research/blob/main/docs/phase25_reconstruction_audit.json" target="_blank" rel="noreferrer">Input audit ↗</a><a href="https://github.com/suhaslord/uav-safety-research/blob/codex/phase25-audit-corrections/results/phase25_corrected_analysis_v1/report.md" target="_blank" rel="noreferrer">Corrected descriptive report ↗</a><a href="https://github.com/suhaslord/uav-safety-research/blob/main/results/phase26_independent_generalization/study_report.md" target="_blank" rel="noreferrer">Phase 26 audit ↗</a></div>'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify current outputs without writing")
    args = parser.parse_args()
    summary = build_summary()
    artifacts = {"summary.json": json.dumps(summary, indent=2, allow_nan=False) + "\n",
                 "report.md": render_report(summary)}
    if args.check:
        for name, expected in artifacts.items():
            path = OUTPUT / name
            if not path.is_file() or path.read_text(encoding="utf-8") != expected:
                raise ValueError(f"Corrected analysis is stale: {path}")
    else:
        OUTPUT.mkdir(parents=True, exist_ok=True)
        for name, content in artifacts.items():
            (OUTPUT / name).write_text(content, encoding="utf-8", newline="\n")
    for name, block in (("phase25.html", render_site_sections(summary)), ("index.html", render_home_summary(summary))):
        path = ROOT / "deploy/vercel" / name
        current = path.read_text(encoding="utf-8")
        pattern = r"<!-- phase25-correction:start -->.*?<!-- phase25-correction:end -->"
        replacement = f"<!-- phase25-correction:start -->\n{block}\n<!-- phase25-correction:end -->"
        corrected, count = re.subn(pattern, lambda match: replacement, current, flags=re.DOTALL)
        if count != 1:
            raise ValueError(f"Expected exactly one corrected evidence section: {path}")
        if args.check and corrected != current:
            raise ValueError(f"Corrected site evidence is stale: {path}")
        if not args.check and corrected != current:
            path.write_text(corrected, encoding="utf-8", newline="\n")
    print("Phase 25 descriptive correction verified" if args.check else f"Wrote corrected analysis to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
