"""The separate-data gate must reject known images even if ZIP names are prefixed."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/audit_phase26_candidate.py"
spec = importlib.util.spec_from_file_location("audit_phase26_candidate", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_rejects_exact_bytes_under_renamed_member(tmp_path: Path) -> None:
    reference = tmp_path / "reference"
    reference.mkdir()
    (reference / "frame.jpg").write_bytes(b"example image bytes")
    candidate = tmp_path / "candidate.zip"
    with zipfile.ZipFile(candidate, "w") as archive:
        archive.writestr("Images/Test/102_other_name.jpg", b"example image bytes")
    result = module.candidate_audit(reference, candidate)
    assert result["status"] == "rejected_overlap"
    assert result["reference_exact_byte_matches"] == 1


def test_rejects_matching_source_name_when_reencoded(tmp_path: Path) -> None:
    reference = tmp_path / "reference"
    reference.mkdir()
    (reference / "frame.jpg").write_bytes(b"source bytes")
    candidate = tmp_path / "candidate.zip"
    with zipfile.ZipFile(candidate, "w") as archive:
        archive.writestr("Images/Test/102_frame.jpg", b"different bytes")
    result = module.candidate_audit(reference, candidate)
    assert result["status"] == "rejected_overlap"
    assert result["reference_exact_byte_matches"] == 0
    assert result["reference_matching_source_names"] == 1
