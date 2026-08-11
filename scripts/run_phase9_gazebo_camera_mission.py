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


async def _hold(drone: System, north: float, east: float, down: float, seconds: float) -> None:
    await drone.offboard.set_position_ned(PositionNedYaw(north, east, down, 0.0))
    await asyncio.sleep(seconds)


def _stop_embedded_mavsdk_server(drone: System) -> None:
    stop_server = getattr(drone, "_stop_mavsdk_server", None)
    if callable(stop_server):
        stop_server()


async def mission(connection: str, metadata_out: Path) -> None:
    drone = System()
    try:
        await drone.connect(system_address=connection)
        await _first_matching(
            drone.core.connection_state(),
            lambda state: state.is_connected,
            90.0,
            "PX4 MAVLink connection timed out",
        )
        await _first_matching(
            drone.telemetry.health(),
            lambda health: health.is_local_position_ok and health.is_armable,
            120.0,
            "PX4 local-position estimator/armability did not become ready",
        )

        metadata = {
            "mission": "phase9_gazebo_camera_visibility_sweep_v1",
            "scope": "simulation_only_external_perception_seen",
            "connection": connection,
            "control_frame": "PX4 local NED",
            "readiness_requirement": "local_position_ok_and_armable",
            "segments": [],
        }

        await drone.offboard.set_position_ned(PositionNedYaw(0.0, 0.0, 0.0, 0.0))
        await drone.action.arm()
        try:
            await drone.offboard.start()
        except OffboardError as error:
            await drone.action.disarm()
            raise RuntimeError(f"PX4 offboard start failed: {error._result.result}") from error

        # Predeclared camera-coverage sweep. The offsets are intentionally modest
        # and remain entirely inside the simulator. They provide centered,
        # off-center, high-altitude and near-edge image geometry without changing
        # any Aegis controller or validation threshold.
        segments = [
            (0.0, 0.0, -1.5, 4.0, "center_1p5m"),
            (0.0, 0.0, -3.5, 4.0, "center_3p5m"),
            (1.2, 0.0, -3.5, 4.0, "north_offset_high"),
            (-1.2, 0.0, -3.0, 4.0, "south_offset_high"),
            (0.0, 1.2, -2.5, 4.0, "east_offset_mid"),
            (0.0, -1.2, -2.0, 4.0, "west_offset_mid"),
            (1.4, 0.0, -1.2, 4.0, "north_near_edge_low"),
            (0.0, 1.4, -1.2, 4.0, "east_near_edge_low"),
            (0.0, 0.0, -1.0, 4.0, "recenter_low"),
        ]
        for north, east, down, seconds, name in segments:
            await _hold(drone, north, east, down, seconds)
            metadata["segments"].append(
                {
                    "name": name,
                    "north_m": north,
                    "east_m": east,
                    "down_m": down,
                    "hold_s": seconds,
                }
            )

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
        metadata_out.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    finally:
        _stop_embedded_mavsdk_server(drone)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the simulation-only Phase 9 PX4/Gazebo camera evidence trajectory."
    )
    parser.add_argument("--connection", default="udpin://0.0.0.0:14550")
    parser.add_argument("--metadata-out", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(asyncio.wait_for(mission(args.connection, args.metadata_out), timeout=360.0))


if __name__ == "__main__":
    main()
