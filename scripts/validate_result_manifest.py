from __future__ import annotations

from pathlib import Path
import argparse
import json

from uav_safety.provenance import validate_result_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate an AegisLand Phase 7 result bundle manifest.")
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate_result_manifest(args.manifest), indent=2))


if __name__ == "__main__":
    main()
