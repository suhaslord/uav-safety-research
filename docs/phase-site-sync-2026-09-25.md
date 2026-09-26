# Phase archive and website sync · September 25, 2026

Scope: the live homepage, archive, and every linked phase record; repository entrypoints and the committed Phase 23/24 summaries. This pass changes presentation and explanatory text, not numerical result artifacts or frozen verdicts.

| Finding | Resolution |
| --- | --- |
| The public archive jumped directly from Phase 22 to Phase 24 despite committed Phase 23 detector results. | Added a dedicated Phase 23 page, route, archive card, taxonomy entry, adjacent navigation, and representative visual capture. The archive now has 28 records. |
| Phase 24 used a one-off inline style while the other newer detector result had no detail page. | Phases 23 and 24 now share `phase-report.css`, the same header, spacing, table treatment, and track navigation. Earlier pages retain their existing shared theme and frozen findings. |
| The phase browser said 26 records and reported a legacy page as “Frozen evidence record.” | Counts now come from the taxonomy length; legacy phase labels say “Historical research record.” |
| “Phase 22 baseline” in detector UI looked like the frozen Phase 22 simulation model. | The UI says “Detector baseline”; both report pages explain the source naming and the separate evidence tracks. |
| README and docs landing pages still treated the completed detector work as a future task, and several historical source links used an old branch. | Updated entrypoints through Phase 24 and pointed existing source documents to `main`. The initial heuristic result remains labeled historical. |
| One detector summary used relative-percent wording for a percentage-point delta and another overstated what recall and stress scores proved. | Corrected the units and narrowed the prose to the recorded measurements. |
| Route and visual QA did not include Phase 23, and a craft gate still expected an older archive size. | Added Phase 23 to local and production route sweeps and refreshed archive expectations. |

The Phase 1–22 simulation lineage remains frozen at six PASS and seven FAIL records. Phase 23 is a KIOS detector comparison on one protected 86-frame temporal split. Phase 24 only reanalyzes its aggregate condition metrics. None of these detector results measures controller behavior or landing safety.
