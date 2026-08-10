from __future__ import annotations

from pathlib import Path
import argparse
import json

from uav_safety.provenance import PHASE7_RESULT_MANIFEST_SCHEMA, validate_result_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate an AegisLand result bundle manifest.")
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--schema",
        default=PHASE7_RESULT_MANIFEST_SCHEMA,
        help="Expected manifest schema. Defaults to the historical Phase 7 schema for backward compatibility.",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            validate_result_manifest(args.manifest, expected_schema=args.schema),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
