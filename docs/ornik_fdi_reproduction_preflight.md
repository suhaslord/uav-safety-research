# Ornik neural fault detection: reproduction preflight

**Status:** source audit complete; numerical reproduction not run.  
**Scope:** simulation-only actuator-fault research. The reference study does not require access to a physical aircraft.

## References frozen for this audit

- Paper: Garg, Dawson, Xu, Ornik, and Fan, “Model-Free Neural Fault Detection and Isolation for Safe Control,” *IEEE Control Systems Letters*, vol. 7, pp. 3169–3174 (2023), [DOI 10.1109/LCSYS.2023.3302768](https://doi.org/10.1109/LCSYS.2023.3302768). The authors’ public [paper PDF](https://mornik.web.illinois.edu/wp-content/uploads/GDXOF23.pdf) was used for the protocol details.
- Public implementation: [MIT-REALM/NeuralFaultDetector](https://github.com/MIT-REALM/NeuralFaultDetector), audited at commit [733e109d0d143cc8e7a20afb21f3f74c5bf794b7](https://github.com/MIT-REALM/NeuralFaultDetector/tree/733e109d0d143cc8e7a20afb21f3f74c5bf794b7). The README points to the [kunalgarg42 repository](https://github.com/kunalgarg42/NeuralFaultDetector); both repository heads resolved to this same commit during the 2026-10-10 audit.
- Dependency file at that commit: [requirements.txt](https://github.com/MIT-REALM/NeuralFaultDetector/blob/733e109d0d143cc8e7a20afb21f3f74c5bf794b7/requirements.txt), SHA-256 `33ae8246ff501ad063f72c49577b994a536f86c4f45cce65982907cf693695c8`.

No source code from that repository has been copied into AegisLand.

## What the paper actually evaluates

The paper’s Crazyflie simulation uses a 12-state, 6-DOF model with four motor-thrust inputs. Its detector receives the measured output trajectory and commanded motor inputs; the model-free setting omits model-derived residuals. The output consists of position and angular-rate measurements. A fault fully disables one motor at an unknown time.

The reported detection study uses a 100-sample history, tests windows containing between zero and 100 faulted samples, and uses a threshold of 0.1 on the minimum predicted healthy/fault score. The test set contains 200 trajectories for each of four failed motors and 200 no-fault trajectories. The paper reports the worst prediction accuracy across fault/no-fault cases and motors. Parameter perturbation and closed-loop recovery are separate evaluations; they must not be presented as if a detector-only reproduction established them.

These settings define the faithful-reproduction target. AegisLand’s existing UNM/Webots work studies GPS measurement degradation and a constant-velocity estimator; it is related resilience work, not a reproduction of this actuator-failure FDI method.

## Source and environment audit

- The public implementation is a standalone Crazyflie dynamics/training project. It does not require a physical quadrotor or a PX4 flight controller to run its paper simulation.
- The repository has no root license or tracked model-checkpoint/data files at the audited commit. The training script expects `data/CF_cbf_NN_weightsCBF.pth`; the evaluation script also expects saved CBF and detector weights. Those artifacts are not in the checked-in tree. Do not redistribute or port upstream code until its reuse terms are clarified.
- The upstream README specifies Python 3.9. Its requirements pin PyTorch 1.13.1 and include CUDA 11 packages. The training script contains a CPU path, but it still depends on compatible Python/PyTorch packages and the missing checkpoint. The install command in the README is malformed (`pip install -r . requirements.txt`).
- The AegisLand workstation environment inspected on 2026-10-10 is Python 3.12.14 and has no importable `torch`. Therefore no training, detector evaluation, or simulator result was generated in this audit.
- No explicit Python, NumPy, or PyTorch seed-setting call was found in the audited upstream files. A reproducible run must add a documented seed plan in an AegisLand-owned harness and save the generated inputs and outputs.

## Next execution gate

1. Resolve permission to reuse the upstream implementation, or write an independent implementation from the paper description without copying upstream code.
2. Prepare a pinned CPU-compatible environment; preserve the upstream dependency lock separately from any compatibility changes.
3. Recreate or obtain the prerequisite CBF checkpoint with documented provenance. Do not substitute a newly tuned checkpoint and call it a paper reproduction.
4. Freeze and save seeds, initial conditions, raw trajectories, fault labels, model weights, and environment details before reporting the one-motor-failure reproduction.
5. Only after that baseline is reconciled should the team define the PX4/Gazebo translation and its robustness sweep.

**Evidence boundary:** this preflight records source and execution constraints only. It contains no AegisLand actuator-fault detection result, recovery result, flight result, or safety claim.

## Separate AegisLand software pilot

A distinct, AegisLand-owned [Webots motor-failure pilot](../experiments/ornik_fdi_webots/README.md) is now staged for a hosted Linux runner. It uses the pinned Bitcraze Crazyflie simulator, four single-motor shutdown conditions, held-out command seeds, and a small NumPy classifier. This is an independent exploratory bridge; it is not the faithful Phase 1 paper reproduction, does not use the authors' missing weights, and does not evaluate recovery or PX4/Gazebo. The workflow has not yet produced data or metrics, so no result is claimed.
