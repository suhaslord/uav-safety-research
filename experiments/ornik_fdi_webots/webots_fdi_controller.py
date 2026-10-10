#!/usr/bin/env python3
"""Seeded Crazyflie Webots telemetry logger with single-motor loss injection.

The stock Bitcraze plant and PID controller are used unchanged. This controller
only supplies seeded velocity commands, removes one requested motor output at
the configured fault time, logs inputs/outputs/labels, and ends the run.
"""

import csv
import os
import random
import sys
from math import cos, isfinite, sin
from pathlib import Path

from controller import Supervisor

sys.path.append('../../../../controllers_shared/python_based')
from pid_controller import pid_velocity_fixed_height_controller

RUN_DURATION_S = 24.0
FAULT_ONSET_S = 10.0
FLYING_ALTITUDE_M = 1.0
COMMAND_START_S = 4.0
COMMAND_INTERVAL_S = 4.0


def seeded_commands(seed: int):
    rng = random.Random(seed)
    levels = (-0.22, -0.14, 0.0, 0.14, 0.22)
    commands = []
    for _ in range(5):
        forward = rng.choice(levels)
        sideways = rng.choice(levels)
        if abs(forward) + abs(sideways) > 0.32:
            sideways = 0.0
        yaw_rate = rng.choice((-0.15, 0.0, 0.15))
        commands.append((forward, sideways, yaw_rate))
    return commands


def command_at(t: float, commands):
    if t < COMMAND_START_S:
        forward, sideways, yaw_rate = 0.0, 0.0, 0.0
    else:
        index = min(int((t - COMMAND_START_S) // COMMAND_INTERVAL_S), len(commands) - 1)
        forward, sideways, yaw_rate = commands[index]
    return forward, sideways, yaw_rate, FLYING_ALTITUDE_M


def finite(value: float) -> float:
    value = float(value)
    return value if isfinite(value) else 0.0


def main():
    seed = int(os.environ.get("FDI_SEED", "11"))
    failed_motor = int(os.environ.get("FDI_FAILED_MOTOR", "0"))
    output_path = Path(os.environ.get("FDI_TELEMETRY_PATH", "fdi_trace.csv")).resolve()
    if failed_motor not in range(5):
        raise SystemExit("FDI_FAILED_MOTOR must be 0 (healthy) or a motor index 1–4")

    commands = seeded_commands(seed)
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

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "time_s", "x_m", "y_m", "z_m", "gyro_p_rps", "gyro_q_rps", "gyro_r_rps",
        "cmd_m1", "cmd_m2", "cmd_m3", "cmd_m4", "failed_motor", "fault_active", "seed",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()

        past_time = robot.getTime()
        x0, y0, _ = gps.getValues()
        past_x, past_y = finite(x0), finite(y0)
        rows = 0

        while robot.step(timestep) != -1:
            t = robot.getTime()
            dt = t - past_time
            if dt <= 0.0:
                continue

            roll, pitch, yaw = (finite(v) for v in imu.getRollPitchYaw())
            gx, gy, gz = (finite(v) for v in gps.getValues())
            gp, gq, gr = (finite(v) for v in gyro.getValues())
            vx_global = (gx - past_x) / dt
            vy_global = (gy - past_y) / dt
            c_yaw, s_yaw = cos(yaw), sin(yaw)
            # Keep the stock experiment's local planar velocity convention.
            vx_body = vx_global * c_yaw + vy_global * s_yaw
            vy_body = -vx_global * s_yaw + vy_global * c_yaw
            forward, sideways, yaw_rate, height = command_at(t, commands)
            motor_power = pid.pid(
                dt, forward, sideways, yaw_rate, height, roll, pitch, gr, gz,
                vx_body, vy_body,
            )
            fault_active = int(failed_motor > 0 and t >= FAULT_ONSET_S)
            for index, (motor, sign, power) in enumerate(zip(motors, signs, motor_power), start=1):
                applied_power = 0.0 if fault_active and index == failed_motor else float(power)
                motor.setVelocity(sign * applied_power)

            writer.writerow({
                "time_s": f"{t:.6f}",
                "x_m": f"{gx:.9f}", "y_m": f"{gy:.9f}", "z_m": f"{gz:.9f}",
                "gyro_p_rps": f"{gp:.9f}", "gyro_q_rps": f"{gq:.9f}", "gyro_r_rps": f"{gr:.9f}",
                "cmd_m1": f"{float(motor_power[0]):.6f}",
                "cmd_m2": f"{float(motor_power[1]):.6f}",
                "cmd_m3": f"{float(motor_power[2]):.6f}",
                "cmd_m4": f"{float(motor_power[3]):.6f}",
                "failed_motor": failed_motor,
                "fault_active": fault_active,
                "seed": seed,
            })
            rows += 1
            if rows % 50 == 0:
                fh.flush()
            past_time, past_x, past_y = t, gx, gy

            if t >= RUN_DURATION_S:
                for motor in motors:
                    motor.setVelocity(0.0)
                fh.flush()
                print(
                    f"FDI_PILOT_COMPLETE seed={seed} failed_motor={failed_motor} "
                    f"rows={rows} path={output_path}"
                )
                robot.simulationQuit(0)
                break


if __name__ == "__main__":
    main()
