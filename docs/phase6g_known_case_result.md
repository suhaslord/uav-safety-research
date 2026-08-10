# Phase 6G known-case development gate

## Status

**Passed.** Phase 6G was allowed to proceed to the preregistered fresh `838381` landing-development matrix.

This gate used only already-seen development episode seeds and is diagnostic evidence, not held-out validation.

GitHub Actions run: `31360137898`
Artifact: `phase6g-known-cases` (`9052074982`)
Full test suite before replay: **78 passed**.

## Architecture under test

Phase 6G combines:

- frozen Phase 6E robust-background perception;
- the existing Phase 6 temporal tracker;
- the historical scalar temporal calibrator unchanged;
- frozen Phase 6E component confidence at fixed 0.80/0.80 x/z gates;
- Phase 6 robust image-derived velocity filtering;
- independent reference estimator;
- Phase 6C component fusion, including z-only altitude fallback that preserves the established visual/temporal vz;
- original controller and frozen V3 supervisor;
- no Phase 6D 3-sigma hard-alias rule.

## Replay outcomes

| condition | seed | historical role | Phase 6 | Phase 6C | Phase 6G |
|---|---:|---|---|---|---|
| low light | `327915747` | Phase 6B altitude-vz coupling timeout | success | success | **success** |
| mixed | `404641207` | Phase 6B vertical-speed regression | success | success | **success** |
| occlusion | `1033307971` | Phase 6C near-ground altitude-alias regression | success | unsafe touchdown | **success** |
| occlusion | `1488232361` | shared historical horizontal-speed failure | unsafe touchdown | unsafe touchdown | **success** |

Phase 6G therefore did not reintroduce the low-light or mixed regressions, repaired the known Phase 6C near-ground alias case, and also rescued the historically shared horizontal-speed failure on this already-seen episode.

Selected exact Phase 6G touchdown diagnostics:

- low light `327915747`: final x error `0.0189 m`, final vx `+0.0492 m/s`, final vz `-0.4111 m/s`;
- mixed `404641207`: final x error `0.0104 m`, final vx `+0.0190 m/s`, final vz `-0.4268 m/s`;
- occlusion alias `1033307971`: final x error `0.1550 m`, final vx `+0.1794 m/s`, final vz `-0.4324 m/s`;
- shared occlusion failure `1488232361`: final x error `0.1830 m`, final vx `+0.2471 m/s`, final vz `-0.4266 m/s`.

These four outcomes justify running the fresh development family but are not sufficient to freeze Phase 6G. The pass/fail decision is governed by `docs/phase6g_landing_development.md` on 50 new paired episodes per condition.

Final replacement held-out seeds remain untouched:

- landing: `918271`
- selective perception: `928271`
