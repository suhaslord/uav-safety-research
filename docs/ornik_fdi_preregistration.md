# Ornik FDI PX4/Gazebo preregistration — frozen v1

Machine-readable source of truth: `configs/ornik_fdi_frozen_v1.json`.

## Evidence separation

1. **Method development:** paper-method reproduction on a transparent 12-state reference plant.
2. **PX4 development / seen:** one nominal trace and one complete single-motor-failure trace for each motor. These traces may train the adapted LSTM.
3. **PX4 held-out / unseen:** four nominal episodes; four-motor sweeps at 25%, 50%, 75%, and 100% loss of effectiveness with frozen onset times; plus four 50%-loss episodes under a 1.45 global simulated thrust-effectiveness mismatch.

Partial-effectiveness and mismatch cases are forbidden from detector training.

## Primary outcomes

**Failure probability:** fraction of episodes meeting the frozen terminal definition within the 8-second evaluation interval. Terminal failure is ground contact (`ground-truth NED z > -0.35 m`), tilt >60°, absolute vertical speed >5 m/s, horizontal setpoint error >4 m, altitude setpoint error >3 m, or an incomplete planned mission for a fault case.

**Recovery time:** elapsed simulated time from the first entry into the frozen degraded envelope until first return to the frozen recovery envelope sustained for 1.0 second. Degraded means horizontal error >0.75 m, altitude error >0.75 m, tilt >20°, or |vertical speed| >1.2 m/s. Recovery requires horizontal error <=0.50 m, altitude error <=0.50 m, tilt <=12°, and |vertical speed| <=0.8 m/s.

A non-recovery has `recovery_time = null` and is reported separately. No finite sentinel value is permitted.

## Supporting outcomes

Detection latency from the simulator-side HRT fault receipt, isolation accuracy, false positives, false negatives, safety-envelope violation rate, and mission completion.

## Fault injection

Only the PX4-to-Gazebo ESC bridge is perturbed. The selected outgoing simulated rotor-speed value is scaled while the unmodified PX4 command remains in ULog. The first actually degraded outgoing sample writes an HRT timestamp receipt used for onset alignment.

No detector threshold, architecture, training inclusion rule, severity, onset time, seed, safety envelope, or outcome definition may change after the held-out trace generation step begins. Failed/missed/non-recovered episodes remain in the artifact bundle.

`simulation_only = true`  
`safety_acceptance = false`  
`controller_tuning_allowed = false`
