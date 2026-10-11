# FDI-H1 follow-up planning note — superseded by H2

**Status: retired planning draft; not an executable independent preregistration.** The next-stage experiment already exists separately as [FDI-H2 draft PR #178](https://github.com/suhaslord/uav-safety-research/pull/178), with the authoritative [H2 prospective protocol](https://github.com/suhaslord/uav-safety-research/blob/research/fdi-h2-prospective-stress-20261011/docs/fdi_h2_prospective_protocol.md) and [H2 results report](https://github.com/suhaslord/uav-safety-research/blob/research/fdi-h2-prospective-stress-20261011/docs/fdi_h2_prospective_results.md).

This document was an early design draft for testing the unchanged H1 gyroscope rule under noise, partial motor loss and varied fault onset. **Do not execute the earlier R1 72-scenario design as fresh independent research.** It reused proposed command seeds 89, 97, 101, 103, 107, 109, 113, 127, which were already preregistered and tested in H2's **144-trace** study. Calling them new untouched holdouts in another experiment would be incorrect.

## Scientific continuity

- **FDI-H1** (#175): a completed, frozen 70-trace pre-contact study, with **40 protected test trajectories** using seeds 53, 59, 61, 67, 71, 73, 79, 83. Its frozen evaluator, source observations and archived results remain unchanged.
- **FDI-H2** (#178): the separate prospective study using seeds 89, 97, 101, 103, 107, 109, 113, 127, two fault onset times (9 and 13 seconds), full and 50%-retained commanded motor speed, and **offline-only** gyro noise. These are no longer untouched seeds. Treat H2's recorded results as an outcome, not as a new development set for a future supposedly protected study.
- Do **not** pool H1/H2 command-seed clusters as though they came from independently varied aircraft physics or real-world sensors. Both studies use one pinned Crazyflie/Webots plant.
- The H1 70-trace source archive and its frozen rule remain independent evidence. H2 must not retrospectively alter H1's published endpoint or use its protected results for further threshold selection.

## Remaining instrumentation and validity gates for any future H3

1. **Actual actuator-input logging:** historical H1 `cmd_m1..4` represent *pre-injection* PID requests rather than the controller's applied motor velocities or measured rotor speeds. A new controller should log requested and applied signals separately, with the actual injection fraction and timestamp. Commanded motor-speed retention is not the same as verified rotor speed or thrust.
2. **Raw sensor validity:** historical `finite()` silently substitutes zero for nonfinite upstream samples. A new study should record upstream validity flags/counters and handle invalid trajectories transparently instead of silently masking sensor anomalies.
3. **Temporal fairness and censoring:** for variable onset, use a preregistered *onset-relative* observation deadline (for example onset +0.70 s) and earlier physically justified contact censor. A pre-onset alert counts as an error. Never revise H1's historical scoring.
4. **Different physics and online perturbations:** noise added to saved gyro traces after the simulator runs does not test sensor noise interacting with the vehicle controller. Any stronger claim needs an independent dynamics setting and/or noisy closed-loop evolution, with enough new predeclared seeds and meaningful independent experimental units.
5. **Hard provenance and negative outcomes:** freeze source, simulator/plant digest, planned scenarios and random seeds before execution. Log applied-fault outcomes and every invalid or premature/missed/wrong-motor case. Archive raw telemetry, scenario manifest, checksum list and code identity; report negative outcomes without changing thresholds on the same test.

**No real-flight or flight-safety implication follows from either H1 or H2.** This file is a retrospective planning record and is *not* an active experiment awaiting execution.
