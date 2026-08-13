# Ornik/Garg model-free neural FDI reproduction boundary

This benchmark implements the fault-detection/isolation method from Garg, Dawson, Xu, Ornik, and Fan, **“Model-Free Neural Fault Detection and Isolation for Safe Control”** (IEEE Control Systems Letters, 2023), then translates that method into a simulation-only PX4/Gazebo benchmark.

## Paper-fixed elements reproduced

- finite history of measured output `y` and commanded actuator input `u`; no explicit plant-residual model is supplied to the detector;
- quadrotor mapping uses position plus angular-rate measurements and four motor commands;
- 100-sample history;
- LSTM recurrent dimension 128, then 64-dimensional linear hidden layer and four actuator-health outputs;
- healthy target 1 and failed-actuator target 0 for single complete faults;
- fault only if the minimum health score is **strictly below 0.1**, then isolate by `argmin`;
- tolerance/hinge training objective;
- paper-style reference evaluation uses healthy plus four single-motor-fault classes, 200 samples per trajectory, with faults beginning at sample 100.

## Explicit assumptions, not paper certainties

No reference implementation is linked from the publication page, and the paper does not fully specify every checkpoint/training detail. This implementation therefore records: a transparent Crazyflie-scale 12-state reference approximation; 100 Hz reference sampling; ReLU between post-LSTM linear layers; no output activation; SGD with learning rate 0.02; hinge epsilon 0.05; and a resource-bounded 2,500-window / 40-epoch training run. These are implementation assumptions, not claims about the authors' exact code.

The reference mismatch check scales mass and inertias by 1.45. Its numerical result is reported as an AegisLand reproduction diagnostic, not as replication of the paper's published figure values.

## PX4/Gazebo translation

The adapted detector retains the same 100-sample `(y,u)` interface and 0.1 decision rule. In PX4 v1.17.0, `y = [local position x/y/z, body roll/pitch/yaw rates]` and `u = actuator_motors.control[0:4]` before the simulator-only perturbation. The adapted sample rate is frozen at 50 Hz, so the history spans 2 seconds.

Partial actuator effectiveness is an AegisLand extension. The simulator-bound rotor-speed command is multiplied by `sqrt(effectiveness)` because thrust in the x500 multicopter motor model is quadratic in rotor speed. PX4's original commanded motor value remains unchanged for detector input.

A 1.45 global simulated thrust-effectiveness scale is a preregistered held-out plant/actuator-model mismatch. It is not part of detector training.

## Evidence boundary

The neural detector is scored offline on genuine ULog traces. Recovery time measures whether the existing PX4 closed loop returns to a frozen trajectory/safety envelope after simulated degradation. This does **not** reproduce the paper's post-fault CBF controller and does not establish physical-UAV safety.

`simulation_only = true`  
`safety_acceptance = false`  
`controller_tuning_allowed = false`
