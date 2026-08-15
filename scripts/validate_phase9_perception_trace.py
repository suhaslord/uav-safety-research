from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import argparse
import json

from uav_safety.perception_trace import load_perception_trace


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a Phase 9 external-perception trace and optional raw-frame hashes.")
    parser.add_argument("trace", type=Path)
    parser.add_argument("--frame-root", type=Path, default=None)
    parser.add_argument("--verify-frame-hashes", action="store_true")
    parser.add_argument("--summary-out", type=Path, default=None)
    args = parser.parse_args()

    _, report = load_perception_trace(
        args.trace,
        frame_root=args.frame_root,
        verify_frame_hashes=args.verify_frame_hashes,
    )
    summary = {
        "trace_file": args.trace.name,
        "trace_sha256": _sha256_file(args.trace),
        "frame_root": str(args.frame_root) if args.frame_root is not None else None,
        "verify_frame_hashes": bool(args.verify_frame_hashes),
        "validation": report.to_dict(),
    }
    text = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if args.summary_out is not None:
        args.summary_out.parent.mkdir(parents=True, exist_ok=True)
        args.summary_out.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
