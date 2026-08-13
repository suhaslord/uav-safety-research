from __future__ import annotations

import argparse, hashlib, json
from pathlib import Path
import numpy as np, pandas as pd

from uav_safety.ornik_fdi import TrainingConfig, decide_fault, healthy_label, make_trace_windows, load_lstm, predict_scores, single_fault_label, train_lstm

FEATURES=['y_px','y_py','y_pz','y_roll_rate','y_pitch_rate','y_yaw_rate','u0','u1','u2','u3']
def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(); p.add_argument('--trace',action='append',type=Path,required=True); p.add_argument('--summary',action='append',type=Path,required=True); p.add_argument('--model-out',type=Path,required=True); p.add_argument('--standardizer-out',type=Path,required=True); p.add_argument('--report-out',type=Path,required=True); p.add_argument('--seed',type=int,default=73193); p.add_argument('--epochs',type=int,default=40); a=p.parse_args();
    if len(a.trace)!=len(a.summary): raise SystemExit('trace/summary counts differ')
    xs=[]; ys=[]; sources={}
    for tp,sp in zip(a.trace,a.summary,strict=True):
        df=pd.read_csv(tp); s=json.loads(sp.read_text()); windows,ends=make_trace_windows(df[FEATURES[:6]].to_numpy(np.float32),df[FEATURES[6:]].to_numpy(np.float32),window=100); times=df.time_s.to_numpy(float)[ends]; labels=[]; motor=s.get('fault_motor'); onset=s.get('fault_onset_s')
        for t in times: labels.append(single_fault_label(int(motor)) if motor is not None and onset is not None and t>=float(onset) else healthy_label())
        xs.append(windows); ys.append(np.asarray(labels,np.float32)); sources[tp.name]=sha256(tp)
    x=np.concatenate(xs); y=np.concatenate(ys); cfg=TrainingConfig(window=100,threshold=.1,hidden_dim=128,fc_dim=64,motor_count=4,epsilon=.05,learning_rate=.02,batch_size=256,epochs=a.epochs,seed=a.seed); training=train_lstm(x,y,config=cfg,model_out=a.model_out,standardizer_out=a.standardizer_out)
    model,std,_=load_lstm(a.model_out,a.standardizer_out); scores=predict_scores(model,std,x); expected=[None if z.min()>.5 else int(np.argmin(z)) for z in y]; correct=[]
    for score,e in zip(scores,expected,strict=True): d=decide_fault(score,.1); correct.append((not d.fault_detected) if e is None else (d.fault_detected and d.isolated_motor==e))
    report={'schema':'aegisland.ornik.px4-detector.v1','evidence_role':'development_seen','window_samples':100,'sample_rate_hz':50.0,'health_threshold':.1,'training_seed':a.seed,'epochs':a.epochs,'training_source':'development-only nominal + complete single-motor failures','partial_effectiveness_seen_in_training':False,'model_mismatch_seen_in_training':False,'source_hashes':sources,'training':training,'training_decision_accuracy':float(np.mean(correct)),'model_sha256':sha256(a.model_out),'standardizer_sha256':sha256(a.standardizer_out),'simulation_only':True,'safety_acceptance':False,'controller_tuning_allowed':False}; a.report_out.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n'); print(json.dumps(report,indent=2))
if __name__=='__main__': main()
