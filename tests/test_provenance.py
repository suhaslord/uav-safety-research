from __future__ import annotations

import json

from uav_safety.provenance import sha256_file, write_result_manifest


def test_result_manifest_records_hash_and_size(tmp_path):
    data = tmp_path / "summary.csv"
    data.write_text("a,b\n1,2\n", encoding="utf-8")

    manifest = write_result_manifest(
        tmp_path,
        ["summary.csv"],
        schema="test.schema.v1",
        extra={"seed": 123},
    )
    payload = json.loads(manifest.read_text(encoding="utf-8"))

    assert payload["schema"] == "test.schema.v1"
    assert payload["extra"]["seed"] == 123
    assert payload["files"][0]["path"] == "summary.csv"
    assert payload["files"][0]["bytes"] == data.stat().st_size
    assert payload["files"][0]["sha256"] == sha256_file(data)
