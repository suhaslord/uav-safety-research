# AegisLand site UI review · September 25, 2026

Scope: live research home, experiment panel, Phase 24, archive, and the shared templates for Phases 1–22. This is a presentation review; research files and verdicts are unchanged.

| Finding | Where | Fix |
| --- | --- | --- |
| The home led with Phase 22 as the latest result, even though the site had a newer Phase 24 audit. | Home hero and navigation | Added a clearly separate Phase 24 audit section and direct navigation. Kept Phase 22 labeled as the frozen simulation result. |
| The home said the archive did not imply a Phase 23, while the site already showed a Phase 23 detector and Phase 24 reanalysis. | Home boundary copy | Reworded the boundary as the end of the *frozen simulation* lineage and identified the later detector work as a separate track. |
| Phase 24's central finding was buried below two paired charts. | Phase 24 | Put mAP50 change first at full width, followed by the paired model values and recall change. Added an exact condition-level interpretation before the charts. |
| Bar labels competed for room and reported decimals while the chart axes used percentages. | Phase 24 charts | Removed crowded decimal labels from paired bars; tooltips now use percentages, and the exact numbers remain in the table. Wrapped “Mixed stress” on chart axes. |
| Charts became too small to read on phones and the wide table offered no scroll cue. | Phase 24 | Added horizontal chart scrolling at readable chart width, scroll hints, and a keyboard-focusable table region. |
| Failed data loading left the headline tiles and severe-stress callout stuck on “Loading.” | Phase 24 | All dependent panels now show a plain unavailable state and retain the report link. |
| The synthetic square image made one experiment card much taller than the adjacent real-camera image. | Home experiment panel | Put both feeds in the same 16:9 frame, with the square sensor image contained inside its frame. |
| The experiment's cards, metrics and controls became cramped at intermediate widths. | Home experiment panel | Constrained the content width and stacked the control/results layout sooner; kept two columns only where there is enough width. |
| “Central question” and the question text appeared joined. | Frozen phase hero | Gave the label and answer separate block lines and a consistent gap. |
| Shared phase columns waited too long to stack, squeezing the text/visual and verdict panels. | Earlier phases and frozen phases | Added a shared breakpoint before the columns become narrow, plus minimum width and long-title handling. |
| Phase 24 was a dead end from Phase 22 and was harder to find from the archive. | Phase navigation | Linked the separate audit from Phase 22's final navigation and the archive header. |
| Focus visibility and small-screen metric density varied between templates. | Shared UI | Added a consistent keyboard focus ring and responsive metric columns without changing the site's white, charcoal, and blue theme. |
| Shared phase navigation and experiment links had short tap areas on phones; five synthetic image labels used 10px type. | Home, experiment, phases, Phase 24 | Raised the tap area to at least 44px for the affected shared controls and links; enlarged the labels to 12px. |

Checks to perform on the preview deployment: home at desktop and phone widths; Phase 1, 11, 16, 22, 24; archive search and links; Phase 24 data load, condition chart readability, and no page-level horizontal overflow. The data file remains `deploy/vercel/data/phase24-results.json` and the scientific Phase 12–22 lineage is untouched.

The exhaustive visual audit passed 87/87 screenshots with no blockers before the tap-area follow-up. Its hidden “skip to content” links are intentionally 1px until keyboard focus; native form controls have associated clickable labels. These are reported as advisory small targets by the geometry checker, but enlarging the invisible skip link would expose it at rest. The follow-up fixes the visible shared links and controls.
