# AegisLand Research Documentation

Start here if you want to understand the project without reading every source file.

## Core research documents

| Document | Purpose |
|---|---|
| [`research_plan.md`](research_plan.md) | Research question, hypothesis, variables, phases, statistical plan |
| [`model_vase.md`](model_vase.md) | Unified AegisLand system architecture, evidence map, current answer, and limits |
| [`preregistration_v1.md`](preregistration_v1.md) | Frozen Phase 1 protocol before the main result |
| [`methodology.md`](methodology.md) | Current simulator and modeling assumptions |
| [`literature.md`](literature.md) | Related-work starting map |
| [`ethics_and_safety.md`](ethics_and_safety.md) | Simulation-only safety scope and interpretation limits |

## Research process

| Document | Purpose |
|---|---|
| [`research_log.md`](research_log.md) | Versioned decisions, changes, and future result log |
| [`roadmap_v1.md`](roadmap_v1.md) | Phase 1 milestones |
| [`NEXT_EXPERIMENT.md`](NEXT_EXPERIMENT.md) | Exact next preregistered experiment |
| [`RESULTS_CHECKLIST.md`](RESULTS_CHECKLIST.md) | Checks before publishing any result |

## Phase 26 independent data

| Document | Purpose |
|---|---|
| [`phase26_protocol.md`](phase26_protocol.md) | Frozen separate-data study rules and publication gate |
| [`phase26_imav2025_preregistration.md`](phase26_imav2025_preregistration.md) | Frozen prediction score, threshold rule, and admission requirements |
| [`phase26_capture_campaign_guide.md`](phase26_capture_campaign_guide.md) | Field steps for collecting, partitioning, recording, and screening a new independent campaign |
| [`phase26_capture_manifest_template.csv`](phase26_capture_manifest_template.csv) | Blank image-level intake manifest for the Phase 26 audit script |
| [`phase26_secondary_leads_screen_2026-10-10.md`](phase26_secondary_leads_screen_2026-10-10.md) | Public dataset candidates screened so far |

## External feedback

| Document | Purpose |
|---|---|
| [`reviewer_guide.md`](reviewer_guide.md) | Short guide for technical reviewers |
| [`EXTERNAL_REVIEW_QUESTIONS.md`](EXTERNAL_REVIEW_QUESTIONS.md) | Question bank organized by expertise |
| [`professor_reply_packet.md`](professor_reply_packet.md) | What to send when a researcher replies |

## Reading path for a professor

If you have **5 minutes**:

1. Project `README.md`
2. `research_plan.md`
3. `preregistration_v1.md`

If you have **15 minutes**, add:

4. `methodology.md`
5. `reviewer_guide.md`
6. `src/uav_safety/supervisor.py`

## Current status

The simulation record is frozen through [Phase 22](https://aegisland-research-cockpit.vercel.app/phases/phase22/), with its failures preserved. The separate real-video detector track has a [Phase 23 comparison](../results/phase23_robust_detector/summary.md) and a [Phase 24 descriptive audit](../results/phase24_robustness_audit/summary.md). For the full sequence, start at the [phase archive](https://aegisland-research-cockpit.vercel.app/phases/). None of these results establishes flight safety.

The project is intentionally structured so that **the research trail is visible**, including assumptions, negative results, methodological criticism, and protocol changes.
