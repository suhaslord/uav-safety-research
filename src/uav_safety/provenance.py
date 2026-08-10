from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
from typing import Iterable


PHASE7_RESULT_MANIFEST_SCHEMA = "aegisland.phase7.result-bundle.v1"


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_result_manifest(
    out_dir: Path,
    filenames: Iterable[str],
    *,
    schema: str,
    extra: dict | None = None,
) -> Path:
    """Write a deterministic integrity manifest for an experiment bundle."""

    entries: list[dict] = []
    for name in sorted(set(filenames)):
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe manifest path: {relative}")
        path = out_dir / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        entries.append({
            "path": relative.as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })

    payload = {
        "schema": schema,
        "files": entries,
        "extra": extra or {},
    }
    manifest_path = out_dir / "result_manifest.json"
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def validate_result_manifest(
    manifest_path: Path,
    *,
    expected_schema: str = PHASE7_RESULT_MANIFEST_SCHEMA,
) -> dict:
    """Verify every file recorded in a result-bundle manifest."""

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("schema") != expected_schema:
        raise ValueError(
            f"unsupported result manifest schema: {payload.get('schema')!r}; "
            f"expected {expected_schema!r}"
        )

    files = payload.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("result manifest contains no files")

    root = manifest_path.parent
    checked = 0
    for entry in files:
        relative = Path(str(entry["path"]))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe manifest path: {relative}")
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        if path.stat().st_size != int(entry["bytes"]):
            raise ValueError(f"size mismatch: {relative}")
        if sha256_file(path) != entry["sha256"]:
            raise ValueError(f"SHA-256 mismatch: {relative}")
        checked += 1

    return {
        "schema": payload["schema"],
        "checked_files": checked,
        "git_sha": payload.get("extra", {}).get("git_sha"),
        "valid": True,
    }
