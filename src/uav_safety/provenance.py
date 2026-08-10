from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
from typing import Iterable


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
        path = out_dir / name
        if not path.is_file():
            raise FileNotFoundError(path)
        entries.append({
            "path": name,
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
