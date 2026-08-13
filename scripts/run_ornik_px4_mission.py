from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import traceback

import numpy as np
from mavsdk import System
from mavsdk.offboard import OffboardError, PositionNedYaw


async def _first_matching(stream, predicate, timeout_s: float, description: str):
    async def wait():
        async for item in stream:
            if predicate(item):
                return item
    try:
        return await asyncio.wait_for(wait(), timeout=timeout_s)
    except asyncio.TimeoutError as exc:
        raise TimeoutError(description) from exc


async def wait_ready(drone: System) -> None:
    await _first_matching(drone.core.connection_state(), lambda s: s.is_connected, 90.0, 'PX4 MAVLink connection timed out')
    await _first_matching(drone.telemetry.health(), lambda h: h.is_local_position_ok and h.is_armable, 120.0,
                          'PX4 local position / armability did not become ready')


async def hold(drone: System, north: float, east: float, down: float, seconds: float) -> None:
    await drone.offboard.set_position_ned(PositionNedYaw(north, east, down, 0.0))
    await asyncio.sleep(seconds)


def _stop_server(drone: System) -> None:
    stop = getattr(drone, '_stop_mavsdk_server', None)
    if callable(stop):
        stop()


async def mission(args) -> dict:
    rng = np.random.default_rng(args.path_seed)
    drone = System()
    metadata = {
        'schema': 'aegisland.ornik.px4-mission.v1',
        'case_id': args.case_id,
        'fault_motor': args.fault_motor,
        'fault_effectiveness': args.effectiveness,
        'fault_after_s': args.fault_after_s,
        'model_thrust_scale': args.model_thrust_scale,
        'path_seed': args.path_seed,
        'simulation_only': True,
        'safety_acceptance': False,
        'controller_tuning_allowed': False,
        'completed': False,
        'armed_and_offboard': False,
        'segments': [],
    }
    trigger_task = None
    try:
        await drone.connect(system_address=args.connection)
        await wait_ready(drone)
        await drone.offboard.set_position_ned(PositionNedYaw(0.0, 0.0, 0.0, 0.0))
        await drone.action.arm()
        try:
            await drone.offboard.start()
        except OffboardError as error:
            await drone.action.disarm()
            raise RuntimeError(f'PX4 offboard start failed: {error._result.result}') from error
        metadata['armed_and_offboard'] = True

        async def trigger_fault():
            await asyncio.sleep(args.fault_after_s)
            args.trigger_file.parent.mkdir(parents=True, exist_ok=True)
            args.trigger_file.write_text(f'{args.case_id}\n', encoding='utf-8')
            metadata['trigger_written'] = True

        if args.fault_motor >= 0:
            trigger_task = asyncio.create_task(trigger_fault())
        else:
            metadata['trigger_written'] = False

        dx = float(rng.uniform(0.45, 1.15))
        dy = float(rng.uniform(-0.65, 0.65))
        segments = [
            (0.0, 0.0, -2.5, 4.0, 'ascent'),
            (dx, dy, -3.5, 4.0, 'lateral_step'),
            (-0.45 * dx, -0.45 * dy, -3.5, 4.0, 'cross_center'),
            (0.0, 0.0, -3.0, 12.0, 'evaluation_hold'),
        ]
        for north, east, down, seconds, name in segments:
            await hold(drone, north, east, down, seconds)
            metadata['segments'].append({'name': name, 'north_m': north, 'east_m': east, 'down_m': down, 'hold_s': seconds})

        try:
            await drone.offboard.stop()
        except OffboardError:
            pass
        await drone.action.land()
        await _first_matching(drone.telemetry.armed(), lambda armed: not armed, 60.0, 'PX4 did not disarm after simulated landing')
        metadata['completed'] = True
        return metadata
    except Exception as exc:
        metadata['error_type'] = type(exc).__name__
        metadata['error'] = str(exc)
        metadata['traceback'] = traceback.format_exc()
        if not metadata['armed_and_offboard']:
            raise
        return metadata
    finally:
        if trigger_task is not None and not trigger_task.done():
            trigger_task.cancel()
        _stop_server(drone)


def main() -> None:
    p = argparse.ArgumentParser(description='Run a frozen simulation-only PX4/Gazebo trajectory for the Ornik FDI benchmark.')
    p.add_argument('--connection', default='udpin://0.0.0.0:14550')
    p.add_argument('--case-id', required=True)
    p.add_argument('--fault-motor', type=int, default=-1)
    p.add_argument('--effectiveness', type=float, default=1.0)
    p.add_argument('--fault-after-s', type=float, default=8.0)
    p.add_argument('--model-thrust-scale', type=float, default=1.0)
    p.add_argument('--path-seed', type=int, required=True)
    p.add_argument('--trigger-file', type=Path, required=True)
    p.add_argument('--metadata-out', type=Path, required=True)
    args = p.parse_args()
    if args.fault_motor not in {-1, 0, 1, 2, 3}:
        raise SystemExit('fault motor must be -1 or 0..3')
    if not 0.0 <= args.effectiveness <= 1.0:
        raise SystemExit('effectiveness must be in [0,1]')
    metadata = asyncio.run(asyncio.wait_for(mission(args), timeout=360.0))
    args.metadata_out.parent.mkdir(parents=True, exist_ok=True)
    args.metadata_out.write_text(json.dumps(metadata, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    main()
