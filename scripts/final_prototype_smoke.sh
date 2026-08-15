#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TMP_ROOT="${TMPDIR:-/tmp}/aegisland-final-prototype-smoke"
rm -rf "$TMP_ROOT"
mkdir -p "$TMP_ROOT"

echo "[1/4] Compile Python sources"
python -m compileall -q src scripts tests

echo "[2/4] Run regression suite"
pytest -q

echo "[3/4] Generate non-authoritative Phase 9 fixture"
python scripts/generate_phase9_perception_fixture.py \
  --rows 40 \
  --seed 909090 \
  --out "$TMP_ROOT/phase9-fixture"

echo "[4/4] Verify fixture trace + every raw-frame SHA-256"
python scripts/validate_phase9_perception_trace.py \
  "$TMP_ROOT/phase9-fixture/perception_trace.csv" \
  --frame-root "$TMP_ROOT/phase9-fixture" \
  --verify-frame-hashes \
  --summary-out "$TMP_ROOT/phase9-fixture/validation_summary.json"

python - <<'PY'
import json
from pathlib import Path
import os

root = Path(os.environ.get("TMPDIR", "/tmp")) / "aegisland-final-prototype-smoke" / "phase9-fixture"
metadata = json.loads((root / "fixture_metadata.json").read_text())
summary = json.loads((root / "validation_summary.json").read_text())

assert metadata["external_perception_evidence_status"] == "fixture_non_authoritative"
assert metadata["claim_level"] == "pipeline_validation_only"
assert metadata["controller_tuning_allowed"] is False
assert metadata["safety_acceptance"] is False
assert metadata["simulation_only"] is True
assert metadata["raw_frames_preserved"] is True
assert summary["validation"]["verified_frame_hashes"] == 40

print("\nAegisLand final-prototype smoke test: PASS")
print("- regression suite: pass")
print("- Phase 9 fixture schema: pass")
print("- raw-frame hash verification: pass")
print("- evidence role remains non-authoritative / simulation-only")
print("\nThis smoke test does not claim physical-flight validation or Phase 9 external-camera acceptance.")
PY
