# AegisLand FDI-H3 — cross-dynamics admission protocol

**2026-10-11 · PRE-EXECUTION ONLY · No H3 numerical results exist.**

## Why this follows H1/H2

H1 observed 40/40 correct class labels on a protected same-Webots holdout. H2 ran 144 fresh Webots scenarios, evaluated 432 offline noise variants and found 100% balanced accuracy in clean conditions, but only 93.75% for full loss and 96.25% for partial motor-speed loss at gyro noise sigma 1.0 rad/s. H2 noise was applied *offline*, not in the simulator's feedback loop. Both studies used the same vehicle dynamics implementation. Their strong clean scores do NOT establish transfer beyond that one plant.

**Question:** Does the unchanged early gyroscope fault-isolation rule transfer to an independently implemented plant under changed sensor and actuation conditions?

## Mandatory candidate admission gates (before any protected scoring)

1. **Independent dynamics:** identify a second flight-dynamics implementation (such as PX4/Gazebo SITL), its source revision, runtime/digest, license, and evidence of independence from the pinned Bitcraze Webots implementation. A change of mass, inertia, camera or controller inside the same Webots model is useful sensitivity testing, but NOT independent dynamics.
2. **Interface mapping:** freeze units and coordinate axes for gyroscope p/q (rad/s), motor 1–4 order, spin sign convention, sample period, altitude frame, actuator command versus applied motor speed, contact detector and timestamps. Resolve physical coordinate transforms **without examining protected results**.
3. **Frozen candidate:** the H1/H2 rule requires three consecutive samples with |p| ≥ 2.0 rad/s and |q| ≥ 0.75 rad/s. First alert wins, sign quadrant maps (++):1, (+−):2, (−−):3, (−+):4. No threshold, label or time-window retuning on the protected set.
4. **Protected independence:** use only new command and fault-event seeds; reserve all H1/H2 seeds as previously seen. Development data may verify telemetry/sign conventions but cannot influence frozen detection thresholds.
5. **Real simulator faults:** implement motor-speed reduction in the simulated actuator model, not only in offline labels. Include complete loss (speed retention 0), half speed retention (0.5), mild loss (0.8), plus matched challenging healthy maneuvers.
6. **Online sensor test:** evaluate a declared sensor configuration with noise applied to measurements *during* simulation, if a closed-loop algorithm consumes them. No substitution of H2 offline gyro noise as a real online result.
7. **Fair timing:** fault onset varied across two prospectively selected time bins. A pre-onset alert is a false alarm even if it predicts a later fault class correctly. Stop evaluation at onset +0.70 seconds or simulated ground contact, whichever is earlier.
8. **Evidence quality:** reject incomplete simulations, NaN/Inf, impossible timestamps, implausible dynamics before the scoring cutoff, missing per-motor labels, missing reproducibility manifest, unverified simulation source or unsafe post-hoc exclusions.

## Prospective analysis plan once admitted

Primary endpoint: **five-class temporally valid balanced accuracy** for motor-speed retention 0.5 with the fixed, declared online sensor configuration on unseen trajectories of the independent plant. Always report the result even if below the always-healthy balanced-accuracy baseline (20%).

Report the full five-class confusion matrix; per-motor recall; detection vs correct-isolation fraction; pre-onset/healthy false alarms; median alarm delay; clean/online-noisy comparisons; severity and onset breakdown; and negative cases. Compare with the always-healthy null and one **predeclared** simple gyro-magnitude or dynamics-residual baseline. Use at least **12 complete paired command-seed clusters**, with healthy plus four motor states, at each of two frozen onset bins. Treat seed clusters, not overlapping sensor rows, as independent. Provide a cluster bootstrap plus transparent small-sample uncertainty limits.

Do not claim a validated physical drone detector, recovery controller, or flight-safety result. H3 results remain blocked until every admission gate passes.

## First practical step

Implement and run an **admission-only manifest validator** (scripts/fdi_h3_admission.py). It will check that a candidate includes an independent-engine identity and digest, sensor/body-axis mapping, online-fault setup, declared protected seed set and separate development evidence. Gate failure means **no experiment admitted**, not a failed scientific hypothesis.

Previously used seed list (not eligible as protected H3): 11, 23, 29, 31, 41, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127.
