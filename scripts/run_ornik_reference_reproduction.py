from __future__ import annotations

import argparse, csv, hashlib, json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from uav_safety.ornik_fdi import PAPER_FAULT_THRESHOLD, TrainingConfig, decide_fault, load_lstm, predict_scores, train_lstm
from uav_safety.ornik_reference import make_paper_style_test, make_training_set


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''): h.update(chunk)
    return h.hexdigest()


def evaluate(rows, model, standardizer, faulty_lengths, label):
    out=[]
    for faulty_len in faulty_lengths:
        windows=[]; metadata=[]
        for row in rows:
            end=99+faulty_len; start=end-99
            windows.append(np.concatenate([row['y'][start:end+1],row['u'][start:end+1]],axis=1))
            metadata.append(row['fault_motor'])
        scores=predict_scores(model,standardizer,np.asarray(windows,np.float32))
        classes={k:[] for k in ['healthy','m0','m1','m2','m3']}
        for score,fault in zip(scores,metadata,strict=True):
            d=decide_fault(score,PAPER_FAULT_THRESHOLD); key='healthy' if fault is None else f'm{fault}'
            classes[key].append((not d.fault_detected) if fault is None else (d.fault_detected and d.isolated_motor==fault))
        acc={k:float(np.mean(v)) for k,v in classes.items()}
        out.append({'condition':label,'faulty_samples_in_window':faulty_len,'minimum_class_accuracy':min(acc.values()),'mean_class_accuracy':float(np.mean(list(acc.values()))),**{f'accuracy_{k}':v for k,v in acc.items()}})
    return out


def main():
    p=argparse.ArgumentParser(); p.add_argument('--out',type=Path,required=True); p.add_argument('--training-windows',type=int,default=2500); p.add_argument('--epochs',type=int,default=40); p.add_argument('--training-seed',type=int,default=23031); p.add_argument('--test-seed',type=int,default=23032); p.add_argument('--trajectories-per-class',type=int,default=200); args=p.parse_args(); args.out.mkdir(parents=True,exist_ok=True)
    x,y=make_training_set(seed=args.training_seed,windows=args.training_windows)
    model_path=args.out/'reference_detector.pt'; standardizer_path=args.out/'reference_standardizer.json'
    cfg=TrainingConfig(window=100,threshold=.1,hidden_dim=128,fc_dim=64,motor_count=4,epsilon=.05,learning_rate=.02,batch_size=256,epochs=args.epochs,seed=args.training_seed+17)
    training=train_lstm(x,y,config=cfg,model_out=model_path,standardizer_out=standardizer_path)
    model,standardizer,_=load_lstm(model_path,standardizer_path)
    faulty_lengths=[1,10,25,50,75,100]
    nominal=make_paper_style_test(seed=args.test_seed,trajectories_per_class=args.trajectories_per_class)
    mismatch=make_paper_style_test(seed=args.test_seed,trajectories_per_class=args.trajectories_per_class,mismatch_scale=1.45)
    metrics=evaluate(nominal,model,standardizer,faulty_lengths,'reference_plant')+evaluate(mismatch,model,standardizer,faulty_lengths,'plant_parameters_x1.45')
    raw=args.out/'reference_accuracy_by_window.csv'
    with raw.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(metrics[0])); w.writeheader(); w.writerows(metrics)
    fig_path=args.out/'reference_min_accuracy.png'; fig,ax=plt.subplots(figsize=(7.2,4.4))
    for condition in ['reference_plant','plant_parameters_x1.45']:
        r=[x for x in metrics if x['condition']==condition]; ax.plot([x['faulty_samples_in_window'] for x in r],[x['minimum_class_accuracy'] for x in r],marker='o',label=condition)
    ax.set_xlabel('Faulty samples in 100-sample history'); ax.set_ylabel('Minimum class accuracy'); ax.set_ylim(0,1.02); ax.legend(); fig.tight_layout(); fig.savefig(fig_path,dpi=160); plt.close(fig)
    summary={'schema':'aegisland.ornik.reference-result.v1','evidence_role':'method_development','paper_fixed':{'window_samples':100,'health_threshold':.1,'test_trajectories':args.trajectories_per_class*5},'implementation_assumptions':{'optimizer':'SGD','learning_rate':.02,'hinge_epsilon':.05,'epochs':args.epochs,'training_windows':args.training_windows,'reference_plant':'transparent Crazyflie-scale 12-state approximation','mismatch_scale':1.45},'training':training,'metrics':metrics,'simulation_only':True,'safety_acceptance':False}
    summary_path=args.out/'reference_summary.json'; summary_path.write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    files=[model_path,standardizer_path,raw,fig_path,summary_path]; manifest={'schema':'aegisland.ornik.reference-manifest.v1','files':{f.name:{'sha256':sha256(f),'bytes':f.stat().st_size} for f in files},'simulation_only':True,'safety_acceptance':False}; (args.out/'result_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n'); print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
