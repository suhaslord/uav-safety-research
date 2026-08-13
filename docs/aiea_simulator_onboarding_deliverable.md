# AIEA Simulator Onboarding Deliverable — AegisLand

**Student:** Suhas Beemineni  
**Program:** UCSC AIEA Lab K-12 Research Foundations  
**Track fit:** Independent research aligned with Robustifying Autonomous Vehicles  
**Project:** AegisLand — simulation-only UAV autonomy validation

## Goal

The AIEA Robustifying Autonomous Vehicles onboarding asks students to choose an autonomous-vehicle simulator, get it running locally, execute a baseline experiment, and document the setup and evidence. AegisLand uses **PX4 SITL + Gazebo** as the simulator stack and already contains an audited simulator run that satisfies the technical core of that requirement.

## Simulator choice

I chose **PX4 SITL + Gazebo** because AegisLand focuses on UAV autonomy rather than road vehicles. The simulator-onboarding instructions allow an autonomous-vehicle simulator of choice, so PX4/Gazebo is the closest domain match.

Frozen external-simulator evidence used for this onboarding packet:

- PX4 release: `v1.17.0`
- PX4 git SHA: `d6f12ad1c4f70ad3230afd7d86e971421e02fef4`
- Gazebo vehicle: `gz_x500`
- control frame: local NED
- evidence role: `external_simulator_seen`
- physical flight: out of scope

## What I ran

AegisLand executed a complete simulated PX4/Gazebo mission and preserved the resulting ULog and simulator evidence rather than treating a successful launch as sufficient.

The completed run recorded:

- `completed=true`
- 8 planned mission segments
- 41.772 s ground-truth duration
- 2.5946 m lateral span
- 4.0490 m vertical span
- 419 GPS samples
- 5,222 PX4 local-position samples
- real simulated arm/takeoff timestamps
- raw ULog SHA-256: `90d9000fbd18900f15d82f0bb3b5df2b3f5b1581a5be21aec2e804f3d5b0eb5f`

The standard `gz_x500` run did not provide `vehicle_visual_odometry`; AegisLand records that absence explicitly instead of inventing a measurement. This became part of the research result rather than something to hide.

## Baseline result and evidence boundary

The simulator run was compared against AegisLand's frozen Phase 8 trace-validation machinery. The result was **diagnostic_mismatch**, with 1 metric classified `close`, 2 `watch`, 9 `mismatch`, and 14 `insufficient`.

I kept that mismatch instead of changing thresholds after seeing the result. This is important to how I want to approach AIEA research: simulator evidence should be allowed to disagree with the model.

The evidence boundary is explicit:

- `safety_acceptance = false`
- `controller_tuning_allowed = false`
- simulation evidence is not presented as real-world flight validation
- failed and incomplete earlier attempts remain documented as diagnostics rather than being deleted

## Reproducibility

The audited PX4/Gazebo evidence was validated at one pinned commit and packaged with:

- raw ULog
- PX4/Gazebo logs
- mission metadata
- ULog sanity report
- converted external trace
- trace metadata
- frozen surrogate trace
- comparison bundle
- result manifest
- evidence receipt and hashes

The final evidence artifact was independently re-hashed after CI and all receipt-controlled files matched.

## How this becomes the AIEA research project

This onboarding baseline gives AegisLand a concrete starting point for the AIEA pathway. My proposed next research stage is a controlled UAV-failure benchmark that measures:

1. failure probability;
2. recovery time;
3. detection latency;
4. fault-isolation accuracy;
5. false-positive/false-negative behavior;
6. safety-envelope violations;
7. non-recovery outcomes;
8. uncertainty/evidence quality so conclusions stay bounded.

The experiments will vary fault severity, onset time, sensor noise, and model mismatch while preserving configuration, seeds/parameters, failed runs, and provenance.

## Reflection

The most useful part of getting PX4/Gazebo working was learning that a simulator run being green is not the same thing as the research result being favorable. An earlier `gz_x500_vision` attempt was rejected because the expected external-vision data were not actually being supplied. After switching to standard `gz_x500`, waiting for local-position health and armability, and preserving the full ULog, the mission completed—but the frozen comparison still produced a mismatch. Keeping that result made the project more rigorous and directly motivated the later external-perception work.

## Evidence links

- AegisLand repository: https://github.com/suhaslord/uav-safety-research
- Audited PX4/Gazebo evidence PR: https://github.com/suhaslord/uav-safety-research/pull/12
- AIEA integration PR: https://github.com/suhaslord/uav-safety-research/pull/17

**Status:** Technical simulator-onboarding deliverable prepared. Administrative submission location / K-12 track confirmation remains to be confirmed with Professor Gilpin.