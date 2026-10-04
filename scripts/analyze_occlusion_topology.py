"""Compatibility entry point for corrected descriptive Phase 25 analysis.

The archived inferential implementation remains at commit db7aca05382f608cbe021cabb5c32862123c7633.
Outputs now go to results/phase25_corrected_analysis_v1; historical files are preserved.
"""
from phase25_descriptive_analysis import main

if __name__ == "__main__":
    raise SystemExit(main())
