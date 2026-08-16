from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from mavsdk import System
from mavsdk.offboard import OffboardError, PositionNedYaw

async def _first_matching(stream,predicate,timeout_s,description):
    async def wait():
        async for item in stream:
            if predicate(item): return
    try: await asyncio.wait_for(wait(),timeout=timeout_s)
    except asyncio.TimeoutError as exc: raise TimeoutError(description) from exc

async def _hold(drone,north,east,down,yaw,seconds):
    await drone.offboard.set_position_ned(PositionNedYaw(north,east,down,yaw)); await asyncio.sleep(seconds)

def _stop_embedded_mavsdk_server(drone):
    stop_server=getattr(drone,"_stop_mavsdk_server",None)
    if callable(stop_server): stop_server()

async def mission(connection,metadata_out):
    drone=System()
    try:
        await drone.connect(system_address=connection)
        await _first_matching(drone.core.connection_state(),lambda state:state.is_connected,90.0,"PX4 MAVLink connection timed out")
        await _first_matching(drone.telemetry.health(),lambda health:health.is_local_position_ok and health.is_armable,120.0,"PX4 local-position estimator/armability did not become ready")
        segments=[
          (0.20,-0.25,-1.80,12.0,3.5,"offset_bootstrap_low"),(0.55,0.45,-3.10,-18.0,3.5,"diagonal_high_a"),(-0.85,-0.35,-2.75,24.0,3.5,"diagonal_high_b"),(1.00,0.70,-2.45,-32.0,3.5,"northeast_mid"),(-1.05,0.65,-2.20,37.0,3.5,"south_east_mid"),(0.65,-1.00,-1.95,-27.0,3.5,"north_west_mid"),(-0.70,-1.05,-1.65,18.0,3.5,"south_west_lower"),(1.10,0.10,-1.45,42.0,3.5,"north_edge_low"),(-0.10,1.10,-1.30,-40.0,3.5,"east_edge_low"),(0.38,0.32,-0.92,16.0,3.5,"near_target_offset"),(0.00,0.00,-1.10,0.0,3.5,"recenter_finish")]
        metadata={"mission":"phase10_frozen_holdout_trajectory_v1","evidence_role":"phase10_holdout_unseen","scope":"simulation_only_external_perception_holdout","connection":connection,"control_frame":"PX4 local NED","readiness_requirement":"local_position_ok_and_armable","segments":[]}
        await drone.offboard.set_position_ned(PositionNedYaw(0,0,0,0)); await drone.action.arm()
        try: await drone.offboard.start()
        except OffboardError as error:
            await drone.action.disarm(); raise RuntimeError(f"PX4 offboard start failed: {error._result.result}") from error
        for north,east,down,yaw,seconds,name in segments:
            await _hold(drone,north,east,down,yaw,seconds); metadata["segments"].append({"name":name,"north_m":north,"east_m":east,"down_m":down,"yaw_deg":yaw,"hold_s":seconds})
        try: await drone.offboard.stop()
        except OffboardError: pass
        await drone.action.land(); await _first_matching(drone.telemetry.armed(),lambda armed:not armed,60.0,"PX4 did not disarm after simulated landing")
        metadata["completed"]=True; metadata_out.parent.mkdir(parents=True,exist_ok=True); metadata_out.write_text(json.dumps(metadata,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    finally: _stop_embedded_mavsdk_server(drone)

def main():
    parser=argparse.ArgumentParser(description="Run frozen Phase 10 simulation-only Gazebo camera holdout trajectory."); parser.add_argument("--connection",default="udpin://0.0.0.0:14550"); parser.add_argument("--metadata-out",type=Path,required=True); args=parser.parse_args(); asyncio.run(asyncio.wait_for(mission(args.connection,args.metadata_out),timeout=420.0))

if __name__=="__main__": main()
