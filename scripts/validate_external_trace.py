from __future__ import annotations

from pathlib import Path
import argparse
import json

from uav_safety.external_trace import load_external_trace


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a simulation-only external trace against the Phase 7 replay schema."
    )
    parser.add_argument("trace", type=Path)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    _, report = load_external_trace(args.trace)
    payload = report.to_dict()
    print(json.dumps(payload, indent=2))

    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
