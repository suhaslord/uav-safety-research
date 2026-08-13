from __future__ import annotations

import argparse, csv, json
from pathlib import Path

import numpy as np
import pandas as pd
from pyulog import ULog

from uav_safety.ornik_benchmark_metrics import recovery_outcome


def _dataset(ulog,name):
    d=[x for x in ulog.data_list if x.name==name]
    if not d: raise KeyError(f'ULog missing required topic: {name}')
    return d[0].data

def _arr(data,field):
    if field not in data: raise KeyError(f'missing field {field}')
    return np.asarray(data[field],dtype=float)
def _vec(data,base,n): return np.column_stack([_arr(data,f'{base}[{i}]') for i in range(n)])
def _series(data,values):
    t=_arr(data,'timestamp')*1e-6; values=np.asarray(values,float); valid=np.isfinite(t)&(np.isfinite(values) if values.ndim==1 else np.all(np.isfinite(values),axis=1)); t,values=t[valid],values[valid]
    if len(t)<2: raise ValueError('too few finite samples in required ULog signal')
    order=np.argsort(t); return t[order],values[order]
def _interp(grid,t,v): return np.interp(grid,t,v) if v.ndim==1 else np.column_stack([np.interp(grid,t,v[:,i]) for i in range(v.shape[1])])
def _quat_to_roll_pitch(q):
    w,x,y,z=q[:,0],q[:,1],q[:,2],q[:,3]; roll=np.arctan2(2*(w*x+y*z),1-2*(x*x+y*y)); pitch=np.arcsin(np.clip(2*(w*y-z*x),-1,1)); return roll,pitch

def _receipt(path):
    if path is None or not path.exists(): return None
    with path.open(newline='',encoding='utf-8') as f: rows=list(csv.DictReader(f))
    if len(rows)!=1: raise ValueError('fault receipt must contain exactly one row')
    r=rows[0]; return {'fault_onset_hrt_us':int(r['fault_onset_hrt_us']),'motor':int(r['motor']),'effectiveness':float(r['effectiveness']),'speed_scale':float(r['speed_scale']),'model_thrust_scale':float(r['model_thrust_scale'])}

def main():
    p=argparse.ArgumentParser(); p.add_argument('ulog',type=Path); p.add_argument('--mission-metadata',type=Path,required=True); p.add_argument('--fault-receipt',type=Path); p.add_argument('--rate-hz',type=float,default=50.0); p.add_argument('--evaluation-horizon-s',type=float,default=8.0); p.add_argument('--out',type=Path,required=True); p.add_argument('--summary-out',type=Path,required=True); a=p.parse_args()
    ulog=ULog(str(a.ulog)); local=_dataset(ulog,'vehicle_local_position'); ang=_dataset(ulog,'vehicle_angular_velocity'); motors=_dataset(ulog,'actuator_motors'); truth=_dataset(ulog,'vehicle_local_position_groundtruth'); att=_dataset(ulog,'vehicle_attitude_groundtruth'); spd=_dataset(ulog,'trajectory_setpoint'); status=_dataset(ulog,'vehicle_status')
    tl,lp=_series(local,np.column_stack([_arr(local,'x'),_arr(local,'y'),_arr(local,'z')])); ta,av=_series(ang,_vec(ang,'xyz',3)); tu,u=_series(motors,_vec(motors,'control',4)); tt,gt=_series(truth,np.column_stack([_arr(truth,'x'),_arr(truth,'y'),_arr(truth,'z'),_arr(truth,'vx'),_arr(truth,'vy'),_arr(truth,'vz')])); tq,q=_series(att,_vec(att,'q',4)); ts,sp=_series(spd,_vec(spd,'position',3))
    armed=int(np.nanmax(_arr(status,'armed_time'))); assert armed>0,'ULog has no valid armed_time'
    start=max(tl[0],ta[0],tu[0],tt[0],tq[0],ts[0]); end=min(tl[-1],ta[-1],tu[-1],tt[-1],tq[-1],ts[-1]);
    if end-start<6: raise ValueError(f'insufficient common flight trace: {end-start:.2f}s')
    grid=np.arange(start,end,1/a.rate_hz); yp=_interp(grid,tl,lp); ya=_interp(grid,ta,av); cmd=_interp(grid,tu,u); g=_interp(grid,tt,gt); quat=_interp(grid,tq,q); target=_interp(grid,ts,sp); roll,pitch=_quat_to_roll_pitch(quat); time=grid-start
    mission=json.loads(a.mission_metadata.read_text()); receipt=_receipt(a.fault_receipt); motor=int(mission.get('fault_motor',-1)); analysis_onset=armed*1e-6-start+float(mission.get('fault_after_s',8.0)); onset=None
    if motor>=0:
        if receipt is None: raise ValueError('fault case has no simulator-side onset receipt')
        if receipt['motor']!=motor: raise ValueError('fault receipt motor disagrees with metadata')
        onset=receipt['fault_onset_hrt_us']*1e-6-start; analysis_onset=onset
    horizontal=np.linalg.norm(g[:,:2]-target[:,:2],axis=1); altitude=np.abs(g[:,2]-target[:,2]); tilt=np.degrees(np.maximum(np.abs(roll),np.abs(pitch))); vz=np.abs(g[:,5]); eval_mask=(time>=analysis_onset)&(time<=analysis_onset+a.evaluation_horizon_s)
    degraded=(horizontal>.75)|(altitude>.75)|(tilt>20)|(vz>1.2); recovery_mask=(horizontal<=.50)&(altitude<=.50)&(tilt<=12)&(vz<=.8)
    recovery={'degraded_entered':False,'recovered':True,'non_recovery':False,'recovery_time_s':0.0} if motor<0 else recovery_outcome(time,degraded,recovery_mask,onset_s=float(onset),dwell_s=1.0)
    safety=(horizontal>2)|(altitude>1.5)|(tilt>35)|(vz>2.5); terminal=(g[:,2]>-.35)|(tilt>60)|(vz>5)|(horizontal>4)|(altitude>3); terminal_failure=bool(np.any(terminal[eval_mask])) if np.any(eval_mask) else True
    if motor>=0 and not mission.get('completed',False): terminal_failure=True
    frame=pd.DataFrame({'time_s':time,'y_px':yp[:,0],'y_py':yp[:,1],'y_pz':yp[:,2],'y_roll_rate':ya[:,0],'y_pitch_rate':ya[:,1],'y_yaw_rate':ya[:,2],'u0':cmd[:,0],'u1':cmd[:,1],'u2':cmd[:,2],'u3':cmd[:,3],'gt_x':g[:,0],'gt_y':g[:,1],'gt_z':g[:,2],'gt_vz':g[:,5],'target_x':target[:,0],'target_y':target[:,1],'target_z':target[:,2],'horizontal_error_m':horizontal,'altitude_error_m':altitude,'tilt_deg':tilt,'abs_vz_mps':vz,'degraded':degraded,'recovery_envelope':recovery_mask,'safety_violation':safety,'terminal_failure_condition':terminal}); a.out.parent.mkdir(parents=True,exist_ok=True); frame.to_csv(a.out,index=False)
    summary={'schema':'aegisland.ornik.px4-trace-summary.v1','case_id':mission.get('case_id'),'fault_motor':None if motor<0 else motor,'fault_effectiveness':float(mission.get('fault_effectiveness',1.0)),'fault_severity':float(1-mission.get('fault_effectiveness',1.0)),'model_thrust_scale':float(mission.get('model_thrust_scale',1.0)),'fault_onset_s':onset,'analysis_onset_s':analysis_onset,'sample_rate_hz':a.rate_hz,'samples':len(frame),'mission_completed':bool(mission.get('completed',False)),'terminal_failure':terminal_failure,**recovery,'safety_envelope_violation_rate':float(np.mean(safety[eval_mask])) if np.any(eval_mask) else 1.0,'max_horizontal_error_m':float(np.max(horizontal[eval_mask])) if np.any(eval_mask) else None,'max_altitude_error_m':float(np.max(altitude[eval_mask])) if np.any(eval_mask) else None,'max_tilt_deg':float(np.max(tilt[eval_mask])) if np.any(eval_mask) else None,'max_abs_vz_mps':float(np.max(vz[eval_mask])) if np.any(eval_mask) else None,'simulation_only':True,'safety_acceptance':False,'controller_tuning_allowed':False,'fault_receipt':receipt}; a.summary_out.write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n'); print(json.dumps(summary,indent=2))
if __name__=='__main__': main()
