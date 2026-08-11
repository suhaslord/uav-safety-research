from __future__ import annotations

from pathlib import Path
import argparse
import json
import subprocess

from uav_safety.trace_validation import EXTERNAL_EVIDENCE_STATUSES, write_phase8_comparison


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compare an audited Phase 7 surrogate trace with an offline external-simulator trace. "
            "This produces model-resemblance diagnostics only; it does not tune or accept the controller."
        )
    )
    parser.add_argument("surrogate", type=Path, help="Phase 7 surrogate trace CSV")
    parser.add_argument("external", type=Path, help="External-simulator trace CSV")
    parser.add_argument("--out", type=Path, default=Path("results/phase8_trace_validation"))
    parser.add_argument("--git-sha", default=None, help="Executable repository SHA; defaults to git rev-parse HEAD")
    parser.add_argument(
        "--external-evidence-status",
        choices=EXTERNAL_EVIDENCE_STATUSES,
        default="fixture_non_authoritative",
        help=(
            "Evidence role. The default is deliberately non-authoritative; select an external-simulator role "
            "only when the input really came from an independent simulator."
        ),
    )
    parser.add_argument("--surrogate-source", default="phase7_surrogate")
    parser.add_argument("--external-source", default="synthetic_interface_fixture")
    args = parser.parse_args()

    git_sha = args.git_sha or _git_sha()
    if git_sha == "unknown":
        raise SystemExit("Could not determine git SHA; pass --git-sha explicitly so provenance is not ambiguous.")

    result = write_phase8_comparison(
        args.surrogate,
        args.external,
        args.out,
        git_sha=git_sha,
        external_evidence_status=args.external_evidence_status,
        surrogate_source=args.surrogate_source,
        external_source=args.external_source,
    )
    bundle = result["bundle"]
    print(json.dumps({
        "schema": bundle["schema"],
        "overall_diagnostic": bundle["overall_diagnostic"],
        "claim_level": bundle["claim_level"],
        "external_evidence_status": bundle["external_evidence_status"],
        "status_counts": bundle["status_counts"],
        "out_dir": str(args.out.resolve()),
        "manifest": str(result["manifest_path"].resolve()),
    }, indent=2))


if __name__ == "__main__":
    main()
