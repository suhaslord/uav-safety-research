# Hardware-free actuator FDI pilot

This is an AegisLand-owned, software-only pilot for actuator fault detection and isolation. It uses the pinned Bitcraze Crazyflie Webots model on a hosted Linux runner; it needs no physical aircraft, flight controller, camera, or lab hardware.

**This is not a reproduction of Garg et al.** It is a small independent Webots bridge experiment. Its plant, controller, trajectory generation, detector architecture, and training recipe differ from the paper's implementation. It does not include their learned control barrier functions or recovery controller. Do not cite its metrics as reproducing or validating the paper, PX4, or flight safety.

## Pilot protocol

- Plant: Bitcraze `crazyflie-simulation`, commit `7e93752dbc803af2488c1db46bb79b3da55f5d8c`; Webots `R2025a` image.
- Scenario: a deterministic, seeded velocity-command profile with one complete motor command loss beginning at 10 seconds, or no fault.
- Conditions: no fault and failure of each of the four motors; command seeds `11`, `23`, and `47` are run for every condition.
- Inputs: 100 consecutive samples of simulated position, three-axis angular rate, and four commanded motor speeds. The failed motor's commanded input remains visible as the requested command; actuator application is separately faulted.
- Label: healthy if the last sample in the window precedes fault onset; otherwise the failed motor class.
- Split: seeds `11` and `23` train the detector; seed `47` is held out by complete trajectory. Windows are never split across train and holdout.
- Detector: a one-hidden-layer, five-class NumPy MLP, trained with cross-entropy. It is a pilot baseline, not the paper's loss or network.
- Outputs: all raw CSV trajectories, the held-out window predictions, frozen settings, model weights, a result summary, and SHA-256 provenance are uploaded as a workflow artifact. Generated data and weights are not committed to the repository.

The holdout set has only one trajectory per condition and highly overlapping windows; use it only to check that the end-to-end software path runs and preserves evidence. Do not draw generalization conclusions from it. A larger trajectory-level holdout and a preregistered detection threshold are required before performance claims.

## Run

The `Ornik FDI Webots pilot` GitHub Actions workflow performs the headless simulation and fitting on Ubuntu. It is triggered by changes to this directory or can be dispatched manually. The local workstation does not need Webots, a GPU, or aircraft hardware.

See [`docs/ornik_fdi_reproduction_preflight.md`](../../docs/ornik_fdi_reproduction_preflight.md) for the separate, still-open faithful-reproduction gate and source audit.
