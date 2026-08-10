from __future__ import annotations

import json
import pytest

from uav_safety.provenance import (
    PHASE7_RESULT_MANIFEST_SCHEMA,
    sha256_file,
    validate_result_manifest,
    write_result_manifest,
)


def test_result_manifest_records_hash_and_size(tmp_path):
    data = tmp_path / "summary.csv"
    data.write_text("a,b\n1,2\n", encoding="utf-8")

    manifest = write_result_manifest(
        tmp_path,
        ["summary.csv"],
        schema=PHASE7_RESULT_MANIFEST_SCHEMA,
        extra={"git_sha": "abc123", "seed": 123},
    )
    payload = json.loads(manifest.read_text(encoding="utf-8"))

    assert payload["schema"] == PHASE7_RESULT_MANIFEST_SCHEMA
    assert payload["extra"]["seed"] == 123
    assert payload["files"][0]["path"] == "summary.csv"
    assert payload["files"][0]["bytes"] == data.stat().st_size
    assert payload["files"][0]["sha256"] == sha256_file(data)

    report = validate_result_manifest(manifest)
    assert report["valid"] is True
    assert report["checked_files"] == 1
    assert report["git_sha"] == "abc123"


def test_result_manifest_detects_tampering(tmp_path):
    data = tmp_path / "summary.csv"
    data.write_text("a,b\n1,2\n", encoding="utf-8")
    manifest = write_result_manifest(
        tmp_path,
        ["summary.csv"],
        schema=PHASE7_RESULT_MANIFEST_SCHEMA,
    )

    data.write_text("a,b\n9,9\n", encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        validate_result_manifest(manifest)


def test_result_manifest_rejects_unsafe_paths(tmp_path):
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="unsafe manifest path"):
        write_result_manifest(
            tmp_path,
            ["../outside.txt"],
            schema=PHASE7_RESULT_MANIFEST_SCHEMA,
        )
