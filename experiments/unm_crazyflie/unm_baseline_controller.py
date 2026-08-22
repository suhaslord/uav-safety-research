#!/usr/bin/env python3
"""Deterministic Crazyflie Webots baseline derived from Bitcraze's stock Python controller.

The plant, sensors, and pid_velocity_fixed_height_controller are the Bitcraze
crazyflie-simulation versions pinned by the workflow. This file changes only:
1) keyboard input -> deterministic body-frame velocity commands;
2) CSV telemetry logging;
3) simulation termination after the fixed run.
"""

import csv
import os
import sys
from math import cos, sin
from pathlib import Path

from controller import Supervisor

sys.path.append('../../../../controllers_shared/python_based')
from pid_controller import pid_velocity_fixed_height_controller

FLYING_ALTITUDE_M = 1.0
RUN_DURATION_S = 32.0


def command_for_time(t: float):
    """Return (forward_mps, sideways_mps, yaw_rate_cmd, target_height_m).

    0-5 s: takeoff/settle
    5-10 s: forward
    10-15 s: left
    15-20 s: backward
    20-25 s: right
    25-32 s: hover/settle

    This is deliberately simple so each segment can be explained and repeated.
    """
    if 5.0 <= t < 10.0:
        return 0.25, 0.0, 0.0, FLYING_ALTITUDE_M
    if 10.0 <= t < 15.0:
        return 0.0, 0.25, 0.0, FLYING_ALTITUDE_M
    if 15.0 <= t < 20.0:
        return -0.25, 0.0, 0.0, FLYING_ALTITUDE_M
    if 20.0 <= t < 25.0:
        return 0.0, -0.25, 0.0, FLYING_ALTITUDE_M
    return 0.0, 0.0, 0.0, FLYING_ALTITUDE_M


def main():
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

        vx_global = (gx - past_x) / dt
        vy_global = (gy - past_y) / dt

        cosyaw = cos(yaw)
        sinyaw = sin(yaw)
        vx_body = vx_global * cosyaw + vy_global * sinyaw
        vy_body = -vx_global * sinyaw + vy_global * cosyaw

        forward_cmd, sideways_cmd, yaw_cmd, height_cmd = command_for_time(t)

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
            print(f"UNM_BASELINE_COMPLETE rows={row_count} path={out_path}")
            robot.simulationQuit(0)
            break


if __name__ == "__main__":
    main()
