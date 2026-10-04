# Paper Workspace

This folder retains the historical simulation write-up and planning material. The original Phase 1 planning below is archival, not a claim that the current experiments are pending.

The current retrospective detector supplement is [Original-detector replay and controlled-occlusion evidence](detector_revalidation_report.md), with generated tables/figures, verified model/runtime provenance and explicit independent-data limitations. It does not rewrite the historical simulation paper or claim detector-to-controller/flight validation.

Use [REPRODUCE.md](../REPRODUCE.md) for the scoped release-candidate gate and [citation/provenance](../docs/citation_provenance.md) for sources and rights. Write results from saved experiment artifacts, not from memory.

## Original Phase 1 planned structure (archival)

1. **Abstract** — question, method, primary result, limitation
2. **Introduction** — why uncertainty-aware autonomy matters
3. **Related work** — UAV landing, uncertainty, safety supervision
4. **Methods** — simulator, perception stress model, controller, supervisor, experimental matrix
5. **Preregistration** — primary endpoint and frozen analysis plan
6. **Results** — raw event counts, rates, confidence intervals, effect sizes
7. **Ablations** — threshold sweep and risk-component comparisons
8. **Failure analysis** — examples where supervision helps and hurts
9. **Limitations** — simulation assumptions and external-validity limits
10. **Next work** — image-based perception and calibration
11. **Conclusion**

## Writing rules

- Do not write the abstract's result sentence until the preregistered experiment has actually run.
- Do not describe exploratory threshold tuning as confirmatory evidence.
- Do not imply validation on a physical aircraft.
- Report null and negative findings.
- Keep measured findings separate from proposed explanations.

## Figures planned

- system architecture
- unsafe-touchdown rate by degradation profile
- success rate by degradation profile
- safety–availability threshold frontier
- confidence/reliability diagram
- selected failure trajectories

## Tables planned

- simulator and supervisor parameters
- experiment matrix
- primary outcomes with event counts and intervals
- ablation results

A technically honest null result is preferable to an impressive-looking result produced by changing the question after seeing the data.