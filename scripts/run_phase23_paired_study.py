"""Retired paired-study entry point; use the authenticated canonical runner.

The original implementation is preserved at db7aca05382f608cbe021cabb5c32862123c7633.
The canonical runner requires both frozen checkpoints, archive and reconstructed
source inventories. Run phase25_descriptive_analysis.py for corrected reporting.
"""
import sys
from run_phase25_frame_audit import main

if __name__ == "__main__":
    print("Phase 23 paired replay uses run_phase25_frame_audit.py; see --help for its authenticated inputs.", file=sys.stderr)
    raise SystemExit(main())
