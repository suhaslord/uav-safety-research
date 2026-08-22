# AIEA Lab Independent Research Track — AegisLand

**Student:** Suhas Beemineni  
**Program:** UCSC AIEA Lab K-12 Research Foundations  
**Status:** Confirmed independent research project on August 22, 2026  
**Project:** AegisLand — simulation-only UAV autonomy validation in PX4/Gazebo

## Research direction

AegisLand studies how autonomous aerial systems should be evaluated when behavior is uncertain, failures must be measured rather than hidden, and simulation evidence can be easily over-interpreted. The project focuses on reproducible UAV autonomy validation in PX4/Gazebo while keeping claims explicitly bounded to the simulator evidence collected.

The project is intentionally **simulation-only**. Results are treated as evidence about simulator behavior and tested conditions, not as proof of physical-flight safety. Failed runs are retained, assumptions are documented, and evaluation separates detection, recovery, non-recovery, and uncertainty instead of collapsing everything into a single success score.

## Core research question

> How can we build a reproducible simulation benchmark for autonomous UAV failures that measures how often a system fails, how quickly it recovers, and how confidence or evidence quality should limit the conclusions we draw?

## Baseline research foundation

1. **Simulator:** PX4 SITL + Gazebo.
2. **Baseline:** nominal autonomous mission with no injected fault.
3. **Evidence retained:** configuration, logs, seeds/parameters, outputs, and failed runs.
4. **Primary metrics:** failure probability and recovery time.
5. **Secondary metrics:** detection latency, isolation accuracy, false-positive/false-negative rate, safety-envelope violations, abstention rate, and non-recovery rate.
6. **Evidence boundary:** simulator results are not converted into real-world safety claims.

## Research progression

1. Reproduce and document the local PX4/Gazebo baseline.
2. Freeze a nominal mission and evaluation configuration.
3. Add controlled actuator-effectiveness faults.
4. Measure detection latency and fault-isolation behavior.
5. Measure failure probability and recovery time across repeated runs.
6. Sweep fault severity, onset time, noise, and model mismatch.
7. Compare recovery strategies under identical frozen conditions.
8. Add evidence-role labels that state what each result does and does not establish.
9. Preserve negative and non-recovery results and build a reproducible evaluation packet.
10. Produce a final report, plots, and a compact benchmark that another student can reproduce.

## Existing project evidence

AegisLand already contains work on:

- simulation-only PX4/Gazebo autonomy validation;
- frozen evaluation protocols;
- external-perception validation;
- failure-probability and recovery-time metrics;
- planned model-free neural fault detection and isolation under actuator degradation;
- explicit separation between simulator evidence and real-world safety claims.

## First AIEA milestone

The first formal AIEA research packet will package the existing simulator foundation into a concise, reproducible update containing:

- environment and simulator versions;
- setup/reproduction instructions already used by the repository;
- one nominal run;
- one controlled fault case;
- configuration and seed/parameter records;
- log locations and result summaries;
- failure-probability and recovery-time definitions;
- limitations and evidence-boundary statement;
- links to the relevant AegisLand code, logs, and evaluation artifacts.

## Confirmed AIEA workflow

Professor Leilani Gilpin confirmed on August 22, 2026 that AegisLand can continue as Suhas's existing **independent research project** in the AIEA K-12 program. Research deliverables and progress updates can be submitted by **email**.

## Immediate next milestone

Freeze the next AegisLand evaluation slice, preserve the evidence bundle, perform the current failure-case analysis, and turn the result into the first AIEA progress update before expanding the challenge set.

## Evidence boundary

AegisLand remains simulation-only. No simulator result should be represented as physical-flight validation or real-world safety acceptance. Negative results, mismatches, uncertainty, and provenance remain part of the research record.
