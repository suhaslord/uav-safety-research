from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

from mavsdk import System
from mavsdk.offboard import OffboardError, PositionNedYaw


async def wait_for_connection(drone: System, timeout_s: float) -> None:
    deadline = time.monotonic() + timeout_s
    async for state in drone.core.connection_state():
        if state.is_connected:
            return
        if time.monotonic() > deadline:
            raise TimeoutError("PX4 MAVLink connection timed out")


async def wait_for_health(drone: System, timeout_s: float) -> None:
    deadline = time.monotonic() + timeout_s
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            return
        if time.monotonic() > deadline:
            raise TimeoutError("PX4 estimator/home did not become ready")


async def hold(drone: System, north: float, east: float, down: float, seconds: float) -> None:
    await drone.offboard.set_position_ned(PositionNedYaw(north, east, down, 0.0))
    await asyncio.sleep(seconds)


async def mission(connection: str, metadata_out: Path) -> None:
    drone = System()
    await drone.connect(system_address=connection)
    await wait_for_connection(drone, 60.0)
    await wait_for_health(drone, 120.0)

    metadata = {
        "mission": "phase8_px4_gazebo_lateral_descent_v1",
        "connection": connection,
        "segments": [],
    }

    await drone.action.arm()
    await drone.action.set_takeoff_altitude(4.0)
    await drone.action.takeoff()
    await asyncio.sleep(7.0)

    # Prime offboard before starting, as required by MAVSDK/PX4.
    await drone.offboard.set_position_ned(PositionNedYaw(0.0, 0.0, -4.0, 0.0))
    await drone.offboard.start()

    segments = [
        (0.0, 0.0, -4.0, 3.0, "settle"),
        (1.5, 0.0, -4.0, 4.0, "north_step"),
        (-1.0, 0.0, -3.2, 4.0, "cross_center"),
        (0.6, 0.0, -2.4, 4.0, "return_and_descend"),
        (0.2, 0.0, -1.5, 4.0, "near_pad"),
        (0.0, 0.0, -0.8, 4.0, "final_approach"),
    ]
    for north, east, down, seconds, name in segments:
        await hold(drone, north, east, down, seconds)
        metadata["segments"].append({
            "name": name,
            "north_m": north,
            "east_m": east,
            "down_m": down,
            "hold_s": seconds,
        })

    try:
        await drone.offboard.stop()
    except OffboardError:
        pass
    await drone.action.land()

    deadline = time.monotonic() + 45.0
    async for armed in drone.telemetry.armed():
        if not armed:
            break
        if time.monotonic() > deadline:
            raise TimeoutError("PX4 did not disarm after landing")

    metadata["completed"] = True
    metadata_out.parent.mkdir(parents=True, exist_ok=True)
    metadata_out.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a deterministic, simulation-only PX4/Gazebo landing trajectory for Phase 8 evidence capture.")
    parser.add_argument("--connection", default="udp://:14540")
    parser.add_argument("--metadata-out", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(mission(args.connection, args.metadata_out))


if __name__ == "__main__":
    main()
