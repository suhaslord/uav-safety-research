#!/usr/bin/env python3
"""Read-only verification of the currently published Phase 25A artifact family.

This is a release *candidate* check, not a full rerun of detector inference.
No Phase 23 or Phase 26 result is claimed or generated here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "results/phase25_baseline_diagnostic/run_manifest.json"
RESULTS = MANIFEST.parent


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def verify(check_site: bool = True) -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    checks = []
    for section, base in (("table_sha256", RESULTS), ("method_sha256", ROOT)):
        for name, expected in manifest[section].items():
            path = (base / name).resolve()
            if not path.is_relative_to(base.resolve()):
                raise ValueError(f"Unsafe manifest path: {name}")
            if not path.is_file():
                actual = None
                passed = False
            else:
                raw = path.read_bytes()
                raw_hash = hashlib.sha256(raw).hexdigest()
                if raw_hash == expected:
                    actual = raw_hash
                    passed = True
                elif not path.name.endswith(".gz"):
                    norm_lf_hash = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
                    norm_crlf_hash = hashlib.sha256(raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")).hexdigest()
                    if norm_lf_hash == expected or norm_crlf_hash == expected:
                        actual = expected
                        passed = True
                    else:
                        actual = raw_hash
                        passed = False
                else:
                    actual = raw_hash
                    passed = False
            checks.append({"artifact": name, "expected": expected, "actual": actual,
                           "passed": passed})
    site_checks = []
    if check_site:
        for name in ("build_failure_atlas_data.py", "build_phase25_site_data.py"):
            result = subprocess.run([sys.executable, str(ROOT / "scripts" / name), "--check"],
                                    cwd=ROOT, capture_output=True, text=True, check=False)
            site_checks.append({"command": f"python scripts/{name} --check",
                                "passed": result.returncode == 0,
                                "message": (result.stderr or result.stdout)[-400:].strip()})
    passed = all(row["passed"] for row in checks + site_checks)
    manifest_bytes = MANIFEST.read_bytes().replace(b"\r\n", b"\n") if MANIFEST.is_file() else b""
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest() if manifest_bytes else sha256(MANIFEST)
    return {
        "status": "committed_phase25a_verified" if passed else "committed_artifact_mismatch",
        "scope": "Read-only replay of committed Phase 25A table/method hashes and generated site snapshots",
        "phase23": "NOT_ASSESSED_BY_THIS_BASELINE_ONLY_COMMAND",
        "phase26": "PENDING_independent_test_admission",
        "inputs_replayed": False,
        "note": "This verifies Phase 25A only, not current Phase 23 recovery status. Use scripts/validate_research_release.py for the current detector/controlled-occlusion/admission artifact family. Exact inference still needs the external inputs; neither check by itself reruns inference or establishes independent validation.",
        "manifest_sha256": manifest_hash,
        "checks": checks, "site_checks": site_checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="Optional new JSON report; existing files are never overwritten")
    parser.add_argument("--skip-site", action="store_true", help="Verify hashes only")
    args = parser.parse_args()
    report = verify(check_site=not args.skip_site)
    output = json.dumps(report, indent=2) + "\n"
    if args.out:
        if args.out.exists():
            parser.error("Refusing to overwrite an existing report")
        args.out.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if report["status"] == "committed_phase25a_verified" else 2


if __name__ == "__main__":
    raise SystemExit(main())
