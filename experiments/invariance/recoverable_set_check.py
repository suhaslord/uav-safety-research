#!/usr/bin/env python3
"""
AegisLand simplified recoverable-set invariance check.

This is a deliberately small verification surrogate, not a safety proof for
PX4/Gazebo or any physical UAV.

State:
    e = [lateral_error_m, altitude_error_m]

Surrogate:
    e[k+1] = A e[k] + w[k]
    |w[k]| <= w_max

Recoverable set R:
    |e_x| <= 0.30 m
    |e_z| <= 0.85 m

For an axis-aligned box and linear bounded-disturbance system, R is robust
positively invariant if:
    |A| r + w_max <= r
componentwise.
"""
import json
import numpy as np

r = np.array([0.30, 0.85])
A = np.diag([0.65, 0.70])
w_max = np.array([0.05, 0.12])

image = np.abs(A) @ r + w_max
margin = r - image
ok = bool(np.all(image <= r))

result = {
    "recoverable_half_width_m": r.tolist(),
    "one_step_image_half_width_m": image.tolist(),
    "margin_m": margin.tolist(),
    "robust_positive_invariant": ok,
    "minimal_rpi_half_width_m": (w_max / (1 - np.diag(A))).tolist(),
    "scope": "simplified 2-state bounded-disturbance surrogate; not PX4/Gazebo or flight proof",
}
print(json.dumps(result, indent=2))
if not ok:
    raise SystemExit(1)
