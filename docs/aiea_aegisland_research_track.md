# AIEA Lab Research Track Proposal — AegisLand

**Student:** Suhas Beemineni  
**Program:** UCSC AIEA Lab K-12 Research Foundations  
**Proposed track:** Independent research aligned with **Robustifying Autonomous Vehicles**  
**Project:** AegisLand — simulation-only UAV autonomy validation in PX4/Gazebo

## Why AegisLand fits the AIEA program

AegisLand studies how autonomous systems should be evaluated when their behavior is uncertain, safety claims must remain bounded, and simulation evidence can be easily over-interpreted. That maps naturally onto AIEA's Robustifying Autonomous Vehicles pathway while keeping the work centered on UAVs rather than road vehicles.

The project is intentionally **simulation-only**. Results are treated as evidence about simulator behavior and test conditions, not as proof of real-world safety. Failed runs are retained, assumptions are documented, and evaluation metrics are designed to distinguish detection, recovery, and non-recovery rather than collapsing everything into a single success score.

## Proposed research question

> How can we build a reproducible simulation benchmark for autonomous UAV failures that measures not only whether recovery occurs, but how often the system fails, how quickly it recovers, and how confidence or evidence quality should limit the conclusions we draw?

## AIEA onboarding alignment

The AIEA Robustifying AVs track begins by asking students to run an autonomous-vehicle simulator locally, document the simulator setup, execute a baseline experiment, and record evidence. AegisLand can satisfy that foundation with PX4/Gazebo, while extending it into a research-grade UAV validation benchmark.

### Baseline deliverable

1. **Simulator:** PX4 SITL + Gazebo.
2. **Baseline:** nominal autonomous mission with no injected fault.
3. **Evidence retained:** configuration, logs, seeds/parameters, outputs, and failed runs.
4. **Primary metrics:** failure probability and recovery time.
5. **Secondary metrics:** detection latency, isolation accuracy, false-positive/false-negative rate, safety-envelope violations, abstention rate, and non-recovery rate.
6. **Evidence boundary:** simulator results are not converted into real-world safety claims.

## Proposed 10-step research progression

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
- a planned reproduction of model-free neural fault detection and isolation under actuator degradation;
- explicit separation between simulator evidence and real-world safety claims.

## What I want to confirm with AIEA

At the next meeting, I would like to confirm whether AegisLand should be treated as:

1. an **independent research project** under the K-12 research pathway, or
2. a UAV adaptation of the **Robustifying Autonomous Vehicles** track.

If either is acceptable, my next milestone will be to package the existing PX4/Gazebo baseline as the formal AIEA simulator-onboarding deliverable and then continue into the repeated fault-injection benchmark.

## Immediate next milestone

Create a concise AIEA-facing baseline packet containing:

- local simulator setup;
- one nominal run;
- one controlled fault case;
- run configuration and reproducibility notes;
- failure probability / recovery time definitions;
- a short evidence-boundary statement;
- links to the relevant AegisLand code, logs, and evaluation artifacts.
