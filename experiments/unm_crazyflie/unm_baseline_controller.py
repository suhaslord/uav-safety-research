#!/usr/bin/env python3
"""Deterministic Crazyflie Webots logger derived from Bitcraze's stock controller.

The plant, sensors, and pid_velocity_fixed_height_controller are the Bitcraze
crazyflie-simulation versions pinned by the workflow. This file changes only:
1) keyboard input -> deterministic body-frame velocity commands;
2) CSV telemetry logging;
3) simulation termination after the fixed run.

`UNM_COMMAND_PROFILE=holdout` selects a second no-fault trajectory with different
command timings and speeds. The default remains the original baseline profile.
"""

import csv
import os
import sys
from math import cos, isfinite, sin
from pathlib import Path

from controller import Supervisor

sys.path.append('../../../../controllers_shared/python_based')
from pid_controller import pid_velocity_fixed_height_controller

FLYING_ALTITUDE_M = 1.0
RUN_DURATION_S = 32.0
VALID_COMMAND_PROFILES = {"baseline", "holdout"}


def command_for_time(t: float, profile: str = "baseline"):
    """Return (forward_mps, sideways_mps, yaw_rate_cmd, target_height_m)."""
    if profile == "baseline":
        # 0-5 settle; then four 5 s cardinal segments; 25-32 settle.
        if 5.0 <= t < 10.0:
            return 0.25, 0.0, 0.0, FLYING_ALTITUDE_M
        if 10.0 <= t < 15.0:
            return 0.0, 0.25, 0.0, FLYING_ALTITUDE_M
        if 15.0 <= t < 20.0:
            return -0.25, 0.0, 0.0, FLYING_ALTITUDE_M
        if 20.0 <= t < 25.0:
            return 0.0, -0.25, 0.0, FLYING_ALTITUDE_M
        return 0.0, 0.0, 0.0, FLYING_ALTITUDE_M

    if profile == "holdout":
        # Different, deliberately uneven timings and speeds. No fault is added.
        if 6.0 <= t < 10.0:
            return 0.18, 0.0, 0.0, FLYING_ALTITUDE_M
        if 10.0 <= t < 14.5:
            return 0.0, 0.28, 0.0, FLYING_ALTITUDE_M
        if 14.5 <= t < 19.0:
            return -0.20, 0.0, 0.0, FLYING_ALTITUDE_M
        if 19.0 <= t < 24.0:
            return 0.0, -0.32, 0.0, FLYING_ALTITUDE_M
        if 24.0 <= t < 28.0:
            return 0.12, 0.0, 0.0, FLYING_ALTITUDE_M
        return 0.0, 0.0, 0.0, FLYING_ALTITUDE_M

    raise ValueError(f"unknown UNM command profile: {profile}")


def finite_difference(current: float, previous: float, dt: float) -> float:
    """Return a safe first derivative while Webots sensors are warming up."""
    if dt <= 0.0 or not (isfinite(current) and isfinite(previous)):
        return 0.0
    return (current - previous) / dt


def main():
    profile = os.environ.get("UNM_COMMAND_PROFILE", "baseline").strip().lower()
    if profile not in VALID_COMMAND_PROFILES:
        raise SystemExit(
            f"UNM_COMMAND_PROFILE must be one of {sorted(VALID_COMMAND_PROFILES)}, got {profile!r}"
        )

    robot = Supervisor()
    timestep = int(robot.getBasicTimeStep())

    motors = [robot.getDevice(f"m{i}_motor") for i in range(1, 5)]
    signs = [-1.0, 1.0, -1.0, 1.0]
    for motor, sign in zip(motors, signs):
        motor.setPosition(float("inf"))
        motor.setVelocity(sign)

    imu = robot.getDevice("inertial_unit")
    imu.enable(timestep)
    gps = robot.getDevice("gps")
    gps.enable(timestep)
    gyro = robot.getDevice("gyro")
    gyro.enable(timestep)

    pid = pid_velocity_fixed_height_controller()

    out_path = Path(os.environ.get("UNM_TELEMETRY_PATH", "unm_baseline.csv")).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fh = out_path.open("w", newline="", encoding="utf-8")
    writer = csv.writer(fh)
    writer.writerow([
        "time_s",
        "x_m", "y_m", "z_m",
        "vx_global_mps", "vy_global_mps",
        "vx_body_mps", "vy_body_mps",
        "roll_rad", "pitch_rad", "yaw_rad", "yaw_rate_rps",
        "cmd_forward_mps", "cmd_sideways_mps", "cmd_yaw_rate", "cmd_height_m",
    ])

    past_time = robot.getTime()
    x0, y0, _ = gps.getValues()
    past_x = x0
    past_y = y0
    row_count = 0

    while robot.step(timestep) != -1:
        t = robot.getTime()
        dt = t - past_time
        if dt <= 0.0:
            continue

        roll, pitch, yaw = imu.getRollPitchYaw()
        gx, gy, gz = gps.getValues()
        yaw_rate = gyro.getValues()[2]

        # Webots can report NaN from GPS before its first enabled sensor sample.
        # Treat that unavailable predecessor as zero measured velocity for the
        # first derivative only; subsequent samples use the normal difference.
        vx_global = finite_difference(gx, past_x, dt)
        vy_global = finite_difference(gy, past_y, dt)

        cosyaw = cos(yaw)
        sinyaw = sin(yaw)
        vx_body = vx_global * cosyaw + vy_global * sinyaw
        vy_body = -vx_global * sinyaw + vy_global * cosyaw

        forward_cmd, sideways_cmd, yaw_cmd, height_cmd = command_for_time(t, profile)

        motor_power = pid.pid(
            dt,
            forward_cmd,
            sideways_cmd,
            yaw_cmd,
            height_cmd,
            roll,
            pitch,
            yaw_rate,
            gz,
            vx_body,
            vy_body,
        )

        for motor, sign, power in zip(motors, signs, motor_power):
            motor.setVelocity(sign * power)

        writer.writerow([
            f"{t:.6f}",
            f"{gx:.9f}", f"{gy:.9f}", f"{gz:.9f}",
            f"{vx_global:.9f}", f"{vy_global:.9f}",
            f"{vx_body:.9f}", f"{vy_body:.9f}",
            f"{roll:.9f}", f"{pitch:.9f}", f"{yaw:.9f}", f"{yaw_rate:.9f}",
            f"{forward_cmd:.6f}", f"{sideways_cmd:.6f}", f"{yaw_cmd:.6f}", f"{height_cmd:.6f}",
        ])
        row_count += 1
        if row_count % 50 == 0:
            fh.flush()

        past_time = t
        past_x = gx
        past_y = gy

        if t >= RUN_DURATION_S:
            for motor in motors:
                motor.setVelocity(0.0)
            fh.flush()
            fh.close()
            print(f"UNM_BASELINE_COMPLETE profile={profile} rows={row_count} path={out_path}")
            robot.simulationQuit(0)
            break


if __name__ == "__main__":
    main()
