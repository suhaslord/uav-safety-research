from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from mavsdk import System
from mavsdk.offboard import OffboardError, PositionNedYaw


async def _first_matching(stream, predicate, timeout_s: float, description: str):
    async def wait() -> None:
        async for item in stream:
            if predicate(item):
                return
    try:
        await asyncio.wait_for(wait(), timeout=timeout_s)
    except asyncio.TimeoutError as exc:
        raise TimeoutError(description) from exc


def _health_ready_for_local_offboard(health) -> bool:
    """Require both a usable local estimate and PX4's own armability verdict."""
    return bool(health.is_local_position_ok and health.is_armable)


async def wait_for_connection(drone: System, timeout_s: float) -> None:
    await _first_matching(
        drone.core.connection_state(),
        lambda state: state.is_connected,
        timeout_s,
        "PX4 MAVLink connection timed out",
    )


async def wait_for_health(drone: System, timeout_s: float) -> None:
    await _first_matching(
        drone.telemetry.health(),
        _health_ready_for_local_offboard,
        timeout_s,
        "PX4 local-position estimator/armability did not become ready",
    )


async def hold(drone: System, north: float, east: float, down: float, seconds: float) -> None:
    await drone.offboard.set_position_ned(PositionNedYaw(north, east, down, 0.0))
    await asyncio.sleep(seconds)


def _stop_embedded_mavsdk_server(drone: System) -> None:
    """Stop the exact MAVSDK server process spawned by this System instance.

    MAVSDK-Python starts an embedded ``mavsdk_server`` when ``System`` is used
    without an externally managed server address. Explicit cleanup keeps the
    evidence command bounded after a completed or failed simulated mission and
    avoids leaving a helper process holding the GitHub Actions step open.
    """

    stop_server = getattr(drone, "_stop_mavsdk_server", None)
    if callable(stop_server):
        stop_server()


async def mission(connection: str, metadata_out: Path) -> None:
    drone = System()
    try:
        await drone.connect(system_address=connection)
        await wait_for_connection(drone, 90.0)
        await wait_for_health(drone, 120.0)

        metadata = {
            "mission": "phase8_px4_gazebo_lateral_descent_v3",
            "connection": connection,
            "readiness_requirement": "local_position_ok_and_armable",
            "control_frame": "local NED only",
            "segments": [],
        }

        # PX4's own armability state is now part of the readiness gate. Prime a
        # local setpoint immediately before arming/offboard so this harness does
        # not race transient preflight checks during simulator startup.
        await drone.offboard.set_position_ned(PositionNedYaw(0.0, 0.0, 0.0, 0.0))
        await drone.action.arm()
        try:
            await drone.offboard.start()
        except OffboardError as error:
            await drone.action.disarm()
            raise RuntimeError(f"PX4 offboard start failed: {error._result.result}") from error

        segments = [
            (0.0, 0.0, -1.0, 3.0, "local_ascent_1m"),
            (0.0, 0.0, -2.5, 4.0, "local_ascent_2p5m"),
            (0.0, 0.0, -4.0, 4.0, "local_ascent_4m"),
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
        await _first_matching(
            drone.telemetry.armed(),
            lambda armed: not armed,
            60.0,
            "PX4 did not disarm after simulated landing",
        )

        metadata["completed"] = True
        metadata_out.parent.mkdir(parents=True, exist_ok=True)
        metadata_out.write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    finally:
        _stop_embedded_mavsdk_server(drone)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a deterministic, simulation-only PX4/Gazebo landing trajectory for Phase 8 evidence capture."
    )
    # PX4 v1.17.0's default SITL MAVLink instance in this headless Gazebo setup
    # sends to localhost UDP 14550. The evidence harness listens there rather
    # than assuming the 14540 offboard port used by other PX4 launch layouts.
    parser.add_argument("--connection", default="udpin://0.0.0.0:14550")
    parser.add_argument("--metadata-out", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(asyncio.wait_for(mission(args.connection, args.metadata_out), timeout=300.0))


if __name__ == "__main__":
    main()
