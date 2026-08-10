from __future__ import annotations

from pathlib import Path
import argparse
import json

from uav_safety.provenance import sha256_file


def validate_manifest(manifest_path: Path) -> dict:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("schema") != "aegisland.phase7.result-bundle.v1":
        raise ValueError("unsupported Phase 7 result manifest schema")

    root = manifest_path.parent
    files = payload.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("result manifest contains no files")

    checked = 0
    for entry in files:
        relative = Path(entry["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe manifest path: {relative}")
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        if path.stat().st_size != int(entry["bytes"]):
            raise ValueError(f"size mismatch: {relative}")
        actual = sha256_file(path)
        if actual != entry["sha256"]:
            raise ValueError(f"SHA-256 mismatch: {relative}")
        checked += 1

    return {
        "schema": payload["schema"],
        "checked_files": checked,
        "git_sha": payload.get("extra", {}).get("git_sha"),
        "valid": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate an AegisLand Phase 7 result bundle manifest.")
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate_manifest(args.manifest), indent=2))


if __name__ == "__main__":
    main()
