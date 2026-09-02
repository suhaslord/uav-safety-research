# Simplified recoverable-set invariance benchmark

This benchmark follows external methodological guidance to make **invariance of a predeclared recoverable set** the primary verification question, with recovery time secondary.

## Scope

This is a deliberately small **verification surrogate**. It is **not** a proof that PX4/Gazebo or any physical UAV is safe, and the surrogate dynamics/disturbance bounds are not claimed to be identified from flight data.

State:

- lateral error `e_x`
- altitude error `e_z`

Recoverable set, defined before the check:

- `|e_x| <= 0.30 m`
- `|e_z| <= 0.85 m`

These reuse AegisLand's existing good-estimate error scales rather than being retuned after observing this result.

## Simplified model

The bounded-disturbance discrete-time surrogate is

`e[k+1] = A e[k] + w[k]`

with

`A = diag(0.65, 0.70)`

and frozen disturbance bounds

- `|w_x| <= 0.05 m/step`
- `|w_z| <= 0.12 m/step`

For an axis-aligned box with half-width vector `r`, the one-step robust-positive-invariance check is

`|A| r + w_max <= r`.

## Result

At the boundary of the recoverable set, the worst-case one-step image is

- lateral: `0.245 m`, leaving `0.055 m` margin to the `0.30 m` bound
- altitude: `0.715 m`, leaving `0.135 m` margin to the `0.85 m` bound

**Result: PASS for this simplified surrogate.** The recoverable box is robust positively invariant under the stated model and disturbance bounds.

The corresponding minimal robust invariant box for this diagonal surrogate has half-widths

- lateral: `0.142857 m`
- altitude: `0.400000 m`

## Interpretation and next validation step

This closes only the narrow surrogate question: the set was defined first, uncertainty was represented as a frozen bounded disturbance, and invariance was checked without changing the set after seeing the result.

It does **not** establish that the real PX4/Gazebo closed loop obeys this `A` matrix or these disturbance bounds. A stronger next experiment is to estimate conservative surrogate dynamics and uncertainty bounds from a frozen PX4/Gazebo trace, then rerun this same predeclared invariance gate without retuning the recoverable set.
