from __future__ import annotations

import argparse, hashlib, json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np, pandas as pd

from uav_safety.metrics import wilson_interval
from uav_safety.ornik_benchmark_metrics import detection_outcome
from uav_safety.ornik_fdi import load_lstm, make_trace_windows, predict_scores

Y=['y_px','y_py','y_pz','y_roll_rate','y_pitch_rate','y_yaw_rate']; U=['u0','u1','u2','u3']
def sha256(p):
    h=hashlib.sha256();
    with Path(p).open('rb') as f:
        for c in iter(lambda:f.read(1<<20),b''): h.update(c)
    return h.hexdigest()
def main():
    p=argparse.ArgumentParser(); p.add_argument('--model',type=Path,required=True); p.add_argument('--standardizer',type=Path,required=True); p.add_argument('--trace',action='append',type=Path,required=True); p.add_argument('--summary',action='append',type=Path,required=True); p.add_argument('--out',type=Path,required=True); p.add_argument('--git-sha',required=True); p.add_argument('--px4-sha',required=True); a=p.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    if len(a.trace)!=len(a.summary): raise SystemExit('trace/summary counts differ')
    model,std,meta=load_lstm(a.model,a.standardizer); rows=[]
    for tp,sp in zip(a.trace,a.summary,strict=True):
        df=pd.read_csv(tp); s=json.loads(sp.read_text()); windows,ends=make_trace_windows(df[Y].to_numpy(np.float32),df[U].to_numpy(np.float32),window=100); times=df.time_s.to_numpy(float)[ends]; scores=predict_scores(model,std,windows); det=detection_outcome(times,scores,threshold=.1,fault_onset_s=s.get('fault_onset_s'),true_fault_motor=s.get('fault_motor'))
        rows.append({'case_id':s['case_id'],'fault_motor':s.get('fault_motor'),'effectiveness':s['fault_effectiveness'],'severity':s['fault_severity'],'model_thrust_scale':s['model_thrust_scale'],'terminal_failure':bool(s['terminal_failure']),'recovery_time_s':s['recovery_time_s'],'non_recovery':bool(s['non_recovery']),'degraded_entered':bool(s['degraded_entered']),'safety_envelope_violation_rate':s['safety_envelope_violation_rate'],'mission_completed':s['mission_completed'],**det,'trace_sha256':sha256(tp),'summary_sha256':sha256(sp)})
    raw=pd.DataFrame(rows); raw_path=a.out/'heldout_episode_results.csv'; raw.to_csv(raw_path,index=False); groups=[]
    for (sev,mismatch),g in raw.groupby(['severity','model_thrust_scale'],sort=True):
        n=len(g); failures=int(g.terminal_failure.sum()); nr=int(g.non_recovery.sum()); flo,fhi=wilson_interval(failures,n); nlo,nhi=wilson_interval(nr,n); recovered=pd.to_numeric(g.recovery_time_s,errors='coerce').dropna(); fault=g[g.fault_motor.notna()]
        groups.append({'severity':float(sev),'model_thrust_scale':float(mismatch),'episodes':n,'failure_probability':failures/n,'failure_ci_low':flo,'failure_ci_high':fhi,'non_recovery_probability':nr/n,'non_recovery_ci_low':nlo,'non_recovery_ci_high':nhi,'median_recovery_time_s':None if recovered.empty else float(recovered.median()),'recovered_episodes':len(recovered),'detection_rate':None if fault.empty else float(fault.detected.mean()),'isolation_accuracy':None if fault.empty else float(fault.isolation_correct.mean()),'false_negative_rate':None if fault.empty else float(fault.false_negative.mean()),'mean_safety_violation_rate':float(g.safety_envelope_violation_rate.mean())})
    grouped=pd.DataFrame(groups); grouped_path=a.out/'summary_by_severity.csv'; grouped.to_csv(grouped_path,index=False); base=grouped[np.isclose(grouped.model_thrust_scale,1.0)]; plots=[]
    for col,ylabel,name in [('failure_probability','Failure probability','failure_probability_vs_severity.png'),('median_recovery_time_s','Median finite recovery time (s)','recovery_time_vs_severity.png'),('non_recovery_probability','Non-recovery probability','non_recovery_probability_vs_severity.png'),('detection_rate','Detection rate','detection_rate_vs_severity.png')]:
        fig,ax=plt.subplots(figsize=(7.2,4.4)); ax.plot(base.severity,base[col],marker='o'); ax.set_xlabel('Actuator degradation severity (1 - effectiveness)'); ax.set_ylabel(ylabel); ax.set_ylim(bottom=0); fig.tight_layout(); fp=a.out/name; fig.savefig(fp,dpi=160); plt.close(fig); plots.append(fp)
    result={'schema':'aegisland.ornik.px4-benchmark-result.v1','evidence_role':'heldout_unseen_px4_gazebo','aegis_git_sha':a.git_sha,'px4_git_sha':a.px4_sha,'model_sha256':sha256(a.model),'standardizer_sha256':sha256(a.standardizer),'primary_metrics':['failure_probability','recovery_time_s'],'non_recovery_handling':'separate probability; never replaced by finite recovery time','heldout_episodes':len(raw),'groups':groups,'simulation_only':True,'safety_acceptance':False,'controller_tuning_allowed':False,'limitations':['neural FDI is evaluated offline on genuine ULog traces, not embedded in flight control','recovery is the existing PX4 closed-loop return to the frozen envelope, not reproduction of the paper post-fault CBF controller']}; result_path=a.out/'result_summary.json'; result_path.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n'); files=[raw_path,grouped_path,result_path,*plots]; (a.out/'result_manifest.json').write_text(json.dumps({'schema':'aegisland.ornik.px4-result-manifest.v1','files':{f.name:{'sha256':sha256(f),'bytes':f.stat().st_size} for f in files},'simulation_only':True,'safety_acceptance':False},indent=2,sort_keys=True)+'\n'); print(json.dumps(result,indent=2))
if __name__=='__main__': main()
