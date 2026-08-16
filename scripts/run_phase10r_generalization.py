from __future__ import annotations
import json, math, os
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import numpy as np
import pandas as pd
from scripts.analyze_phase9_gazebo_camera_evidence import _detect_marker

W,H=160,120; FX=FY=145.; CX=(W-1)/2; CY=(H-1)/2; MARKER=.60
N=48; DEV_SEED=12345; VAL_SEED=271828; MIN_VISIBLE=.66
FAMILIES=range(5); OBLIQ=("nominal","difficult"); APPS=("nominal","low_exposure","blur_noise")
TARGETS=(.50,.68,.80,.90,.95)

@dataclass
class State:
    u:float|None=None; z:float|None=None; pu:float|None=None; pz:float|None=None
    hf:float|None=None; lspan:float|None=None; rspan:float|None=None; lres:float|None=None; rres:float|None=None

def cv2():
    import cv2 as c; return c

def ema(a,b): return float(b if a is None else .70*a+.30*b)

def traj(f,t):
    if f==0:q=math.sin(2*math.pi*t)
    elif f==1:q=-1+2*t
    elif f==2:q=1-2*t
    elif f==3:q=.9*math.sin(4*math.pi*t)
    else:q=math.sin(2*math.pi*t+.70)*(.55+.45*t)
    return q,2+.65*math.sin(math.pi*t)+.05*(f-2)

def quad(u,v,z,ob):
    h=FX*MARKER/z/2
    if ob=="nominal": return np.array([[u-h,v-h],[u+h,v-h],[u+h,v+h],[u-h,v+h]],np.float32)
    top=.58*h; bot=.92*h; sk=.13*h
    return np.array([[u-top+sk,v-h],[u+top+sk,v-h],[u+bot-sk,v+h],[u-bot-sk,v+h]],np.float32)

def area(p):
    p=np.asarray(p,float); x=p[:,0]; y=p[:,1]
    return float(abs(np.dot(x,np.roll(y,1))-np.dot(y,np.roll(x,1)))*.5)

def render(f,i,seed,ob,app):
    c=cv2(); off={"nominal":0,"low_exposure":7,"blur_noise":13}[app]+(31 if ob=="difficult" else 0)
    rng=np.random.default_rng(seed+f*100000+i*997+off); yy,xx=np.mgrid[0:H,0:W]
    im=np.clip(205+7*np.sin(xx/27)+5*np.cos(yy/19)+rng.normal(0,3,(H,W)),0,255).astype(np.uint8)
    t=i/(N-1); q,z=traj(f,t); u=CX+q*(W/2-3); v=CY+7*math.sin(2*math.pi*t+f*.3); p=quad(u,v,z,ob); present=4<=i<44
    if present:
        dic=c.aruco.getPredefinedDictionary(c.aruco.DICT_4X4_50); m=c.aruco.generateImageMarker(dic,0,96)
        src=np.array([[0,0],[95,0],[95,95],[0,95]],np.float32); M=c.getPerspectiveTransform(src,p)
        w=c.warpPerspective(m,M,(W,H),flags=c.INTER_LINEAR,borderValue=255); mask=c.warpPerspective(np.full_like(m,255),M,(W,H),flags=c.INTER_NEAREST,borderValue=0)
        im[mask>0]=w[mask>0]
    if app=="low_exposure": im=np.clip(im.astype(float)*.42+rng.normal(0,4,im.shape),0,255).astype(np.uint8)
    elif app=="blur_noise": im=c.GaussianBlur(im,(5,5),1.3); im=np.clip(im.astype(float)+rng.normal(0,9,im.shape),0,255).astype(np.uint8)
    inside=(p[:,0]>=0)&(p[:,0]<W)&(p[:,1]>=0)&(p[:,1]<H); partial=bool(present and not inside.all())
    x=(u-CX)*z/FX; margin=min(u,W-1-u,v,H-1-v)/(FX*MARKER/z/2)
    return im,dict(visible=present,u=u,v=v,x=x,z=z,partial=partial,margin=float(margin),proj_area=area(p))

def aruco_corners(gray):
    c=cv2(); d=c.aruco.getPredefinedDictionary(c.aruco.DICT_4X4_50); det=c.aruco.ArucoDetector(d,c.aruco.DetectorParameters()); cs,ids,_=det.detectMarkers(gray)
    if ids is None:return None
    best=None
    for q,mid in zip(cs,ids.reshape(-1)):
        if int(mid)!=0:continue
        q=np.asarray(q,np.float32).reshape(4,2); a=area(q)
        if best is None or a>best[0]:best=(a,q)
    if best is None:return None
    q=best[1].reshape(-1,1,2).copy(); norm=c.normalize(gray,None,0,255,c.NORM_MINMAX)
    if not(np.any(q[:,:,0]<3) or np.any(q[:,:,0]>=W-3) or np.any(q[:,:,1]<3) or np.any(q[:,:,1]>=H-3)):
        try:c.cornerSubPix(norm,q,(4,4),(-1,-1),(c.TERM_CRITERIA_EPS+c.TERM_CRITERIA_MAX_ITER,30,.01))
        except c.error:pass
    return q.reshape(4,2)

def geom(q):
    q=np.asarray(q,float); u=float(q[:,0].mean()); v=float(q[:,1].mean()); hh=(np.linalg.norm(q[3]-q[0])+np.linalg.norm(q[2]-q[1]))/2
    z=FY*MARKER/max(float(hh),1); return u,v,float(z),float((u-CX)*z/FX),float(hh)

def components(gray):
    c=cv2(); eq=c.createCLAHE(2.0,(4,4)).apply(gray); _,b=c.threshold(eq,0,255,c.THRESH_BINARY_INV|c.THRESH_OTSU)
    b=c.morphologyEx(b,c.MORPH_CLOSE,c.getStructuringElement(c.MORPH_RECT,(5,5)),iterations=2); b=c.morphologyEx(b,c.MORPH_OPEN,np.ones((2,2),np.uint8),iterations=1)
    cs,_=c.findContours(b,c.RETR_EXTERNAL,c.CHAIN_APPROX_SIMPLE); out=[]
    for ct in cs:
        a=float(c.contourArea(ct)); x,y,w,h=c.boundingRect(ct)
        if a<45 or w<7 or h<7 or w>W*.8 or h>H*.8:continue
        fill=a/max(1,w*h); patch=gray[y:y+h,x:x+w]; contrast=float(np.percentile(patch,90)-np.percentile(patch,10)) if patch.size else 0
        if fill>=.18 and contrast>=30:out.append((a,x,y,w,h,fill,contrast))
    return sorted(out,reverse=True)

def best_comp(gray,ref):
    best=None; score=-1e9
    for a,x,y,w,h,fill,contrast in components(gray)[:10]:
        s=math.log(a+1)+2*fill-(abs(x+(w-1)/2-ref)/20 if ref is not None else 0)
        if s>score:score=s;best=(a,x,y,w,h,fill,contrast)
    return best

def candidate(gray,base,s):
    pred_u=s.u+(s.u-s.pu) if s.u is not None and s.pu is not None else s.u; pred_z=s.z+(s.z-s.pz) if s.z is not None and s.pz is not None else s.z
    q=aruco_corners(gray)
    if base is not None:
        if q is not None:u,v,z,x,hh=geom(q)
        else:
            u=float(base["center_x_px"]); v=float(base["center_y_px"]); cp=best_comp(gray,u)
            if cp: _,_,_,_,h,_,_=cp; z=FY*MARKER/max(4,(h-1)*(s.hf or 1))
            else:z=float(base["altitude_m"])
            x=(u-CX)*z/FX; hh=None
        bad=pred_z is not None and (abs(z-pred_z)>max(.32,.18*pred_z) or (pred_u is not None and abs(u-pred_u)>24))
        if not bad:
            cp=best_comp(gray,u); A=0.; contrast=float(np.std(gray))
            if q is not None and cp:
                A,x0,y0,w,h,_,contrast=cp; ch=max(1,h-1); le=float(x0); re=float(x0+w-1)
                if x0>2 and x0+w<W-2 and y0>2 and y0+h<H-2:
                    qmin=float(q[:,0].min()); qmax=float(q[:,0].max()); s.hf=ema(s.hf,hh/ch); s.lspan=ema(s.lspan,(u-qmin)*z); s.rspan=ema(s.rspan,(qmax-u)*z); s.lres=ema(s.lres,qmin-le); s.rres=ema(s.rres,qmax-re)
            if s.u is not None:s.pu,s.pz=s.u,s.z
            s.u,s.z=u,z
            return dict(u=u,v=v,x=x,z=z,source="known_aruco_refined" if q is not None else "phase9_center_regeometry",partial=False,contrast=contrast,support=A)
    cp=best_comp(gray,pred_u)
    if cp is None:return None
    A,x0,y0,w,h,_,contrast=cp; left=x0<=2; right=x0+w>=W-2; ch=max(1,h-1); cw=max(1,w-1)
    if s.u is None and (left or right):return None
    z=FY*MARKER/max(4,ch*(s.hf or 1)); le=float(x0); re=float(x0+w-1); u=None
    if not left and not right:u=(le+re)/2
    elif left and not right and s.rspan is not None and s.rres is not None:
        full=((s.lspan or 0)+s.rspan)/max(z,1e-9)
        if cw/max(full,1)>=MIN_VISIBLE:u=re+s.rres-s.rspan/z
    elif right and not left and s.lspan is not None and s.lres is not None:
        full=(s.lspan+(s.rspan or 0))/max(z,1e-9)
        if cw/max(full,1)>=MIN_VISIBLE:u=le+s.lres+s.lspan/z
    if u is None or (pred_u is not None and abs(u-pred_u)>18):return None
    if pred_z is not None and abs(z-pred_z)>.45:z=.8*z+.2*pred_z
    x=(u-CX)*z/FX
    if s.u is not None:s.pu,s.pz=s.u,s.z
    s.u,s.z=u,z
    return dict(u=u,v=y0+ch/2,x=x,z=z,source="partial_edge",partial=left or right,contrast=contrast,support=A)

def run_split(name,seed,out,raw=True):
    rows=[]; root=out/"raw"/name; root.mkdir(parents=True,exist_ok=True)
    for app in APPS:
      for ob in OBLIQ:
       for f in FAMILIES:
        sid=f"{name}-f{f}-{ob}-{app}"; d=root/sid
        if raw:d.mkdir(parents=True,exist_ok=True)
        s=State()
        for i in range(N):
            gray,t=render(f,i,seed,ob,app); payload=gray.tobytes(); rel=f"raw/{name}/{sid}/frame_{i:04d}.raw"
            if raw:(d/f"frame_{i:04d}.raw").write_bytes(payload)
            b=_detect_marker(gray,MARKER,FX,FY,CX,CY); c=candidate(gray,b,s)
            r=dict(split=name,seed=seed,sequence_id=sid,family=f,obliquity=ob,appearance=app,frame_index=i,frame_path=rel,frame_sha256=sha256(payload).hexdigest(),truth_target_visible=t["visible"],truth_center_x_px=t["u"],truth_lateral_x_m=t["x"],truth_altitude_m=t["z"],truth_partial_edge=t["partial"],truth_edge_margin_ratio=t["margin"])
            r["difficult_truth_visible"]=bool(t["visible"] and (ob=="difficult" or app!="nominal" or t["partial"])); r["ambiguous_pose_truth"]=bool(t["visible"] and (ob=="difficult" or t["partial"])); r["clean_aruco_truth"]=bool(t["visible"] and ob=="nominal" and app=="nominal" and not t["partial"])
            if b:
                r.update(baseline_available=True,baseline_source=str(b.get("detector_kind") or "unknown"),baseline_center_abs_error_px=abs(float(b["center_x_px"])-t["u"]),baseline_lateral_abs_error_m=abs(float(b["lateral_x_m"])-t["x"]),baseline_altitude_abs_error_m=abs(float(b["altitude_m"])-t["z"]))
            else:r.update(baseline_available=False,baseline_source=None,baseline_center_abs_error_px=np.nan,baseline_lateral_abs_error_m=np.nan,baseline_altitude_abs_error_m=np.nan)
            if c:r.update(candidate_available=True,candidate_source=c["source"],candidate_center_abs_error_px=abs(c["u"]-t["u"]),candidate_lateral_abs_error_m=abs(c["x"]-t["x"]),candidate_altitude_abs_error_m=abs(c["z"]-t["z"]))
            else:r.update(candidate_available=False,candidate_source=None,candidate_center_abs_error_px=np.nan,candidate_lateral_abs_error_m=np.nan,candidate_altitude_abs_error_m=np.nan)
            rows.append(r)
    df=pd.DataFrame(rows); df.to_csv(out/f"{name}_frames.csv",index=False); return df

def cq(v,q):
    a=np.sort(np.asarray(v,float)[np.isfinite(v)]); return float(a[min(len(a)-1,max(0,math.ceil((len(a)+1)*q)-1))])

def calibrate(df,sys):
    d=df[df[f"{sys}_available"]&df.truth_target_visible]; out={"fallback":{},"sources":{}}
    for src,g in [("fallback",d),*list(d.groupby(f"{sys}_source"))]:
        if src!="fallback" and len(g)<20:continue
        rec={}
        for ax in ("lateral","altitude"):rec[ax]={f"{q:.2f}":cq(g[f"{sys}_{ax}_abs_error_m"],q) for q in TARGETS}
        if src=="fallback":out["fallback"]=rec
        else:out["sources"][str(src)]=rec
    return out

def radius(cal,src,ax,q):return cal["sources"].get(str(src),cal["fallback"])[ax][f"{q:.2f}"]
def imp(b,c):return (b-c)/b if b>0 else 0

def summarize(dev,val,cc,bc):
    vis=val[val.truth_target_visible]; dif=val[val.difficult_truth_visible]; amb=val[val.ambiguous_pose_truth]; clean=val[val.clean_aruco_truth]; nv=val[~val.truth_target_visible]
    bm=1-dif.baseline_available.mean(); cm=1-dif.candidate_available.mean(); bcp=np.nanpercentile(dif.baseline_center_abs_error_px,95); ccp=np.nanpercentile(dif.candidate_center_abs_error_px,95)
    h1=dict(baseline_miss_rate=float(bm),candidate_miss_rate=float(cm),relative_miss_reduction=float(imp(bm,cm)),false_positive_rate=float(nv.candidate_available.mean()),baseline_center_p95_px=float(bcp),candidate_center_p95_px=float(ccp),center_p95_ratio=float(ccp/bcp))
    h2={}
    for ax in ("lateral","altitude"):
        b=amb[f"baseline_{ax}_abs_error_m"].dropna().to_numpy(); c=amb[f"candidate_{ax}_abs_error_m"].dropna().to_numpy(); cb=clean[f"baseline_{ax}_abs_error_m"].dropna().to_numpy(); ccx=clean[f"candidate_{ax}_abs_error_m"].dropna().to_numpy()
        h2[f"{ax}_mae_relative_improvement"]=float(imp(float(b.mean()),float(c.mean()))); h2[f"{ax}_p95_relative_improvement"]=float(imp(float(np.percentile(b,95)),float(np.percentile(c,95)))); h2[f"clean_{ax}_mae_regression"]=float((ccx.mean()-cb.mean())/cb.mean())
    h2["availability_drop"]=float(vis.baseline_available.mean()-vis.candidate_available.mean())
    cov={"lateral":{},"altitude":{}}; errs=[]; cr=vis[vis.candidate_available]
    for ax in cov:
      for q in TARGETS:
        x=np.mean([r[f"candidate_{ax}_abs_error_m"]<=radius(cc,r.candidate_source,ax,q) for _,r in cr.iterrows()]); cov[ax][f"{q:.2f}"]=float(x); errs.append(abs(x-q))
    paired=vis[vis.candidate_available&vis.baseline_available]; wr={}
    for ax in cov:
        cw=np.median([2*radius(cc,r.candidate_source,ax,.95) for _,r in paired.iterrows()]); bw=np.median([2*radius(bc,r.baseline_source,ax,.95) for _,r in paired.iterrows()]); wr[ax]=float(cw/bw)
    h3=dict(coverage=cov,mean_absolute_coverage_error=float(np.mean(errs)),paired_95_interval_width_ratio=wr)
    gates={"h1_miss_reduction_ge_40pct":h1["relative_miss_reduction"]>=.40,"h1_false_positive_rate_le_1pct":h1["false_positive_rate"]<=.01,"h1_center_p95_ratio_le_1_10":h1["center_p95_ratio"]<=1.10,"h2_lateral_mae_improvement_ge_40pct":h2["lateral_mae_relative_improvement"]>=.40,"h2_altitude_mae_improvement_ge_40pct":h2["altitude_mae_relative_improvement"]>=.40,"h2_lateral_p95_improvement_ge_30pct":h2["lateral_p95_relative_improvement"]>=.30,"h2_altitude_p95_improvement_ge_30pct":h2["altitude_p95_relative_improvement"]>=.30,"h2_clean_lateral_regression_le_10pct":h2["clean_lateral_mae_regression"]<=.10,"h2_clean_altitude_regression_le_10pct":h2["clean_altitude_mae_regression"]<=.10,"h2_visible_availability_drop_le_2pp":h2["availability_drop"]<=.02,"h3_mean_abs_coverage_error_le_5pp":h3["mean_absolute_coverage_error"]<=.05,"h3_lateral_95_coverage_90_to_98pct":.90<=cov["lateral"]["0.95"]<=.98,"h3_altitude_95_coverage_90_to_98pct":.90<=cov["altitude"]["0.95"]<=.98,"h3_lateral_width_ratio_le_1_20":wr["lateral"]<=1.20,"h3_altitude_width_ratio_le_1_20":wr["altitude"]<=1.20}
    return dict(schema="aegisland.phase10r.validation-result.v1",development_seed=DEV_SEED,validation_seed=VAL_SEED,truth_visible_frames_validation=int(len(vis)),h1=h1,h2=h2,h3=h3,gates=gates,all_preregistered_validation_gates_pass=all(gates.values()),evidence_role="phase10r_validation_seen_after_candidate_freeze",safety_acceptance=False,controller_tuning_allowed=False)

def dump(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+"\n")
def fh(p):return sha256(p.read_bytes()).hexdigest()

def main():
    import argparse; a=argparse.ArgumentParser(); a.add_argument("--out",type=Path,required=True); a.add_argument("--no-raw",action="store_true"); z=a.parse_args(); z.out.mkdir(parents=True,exist_ok=True)
    dev=run_split("development",DEV_SEED,z.out,not a.no_raw); cc=calibrate(dev,"candidate"); bc=calibrate(dev,"baseline"); dump(z.out/"candidate_uncertainty_calibration.json",cc); dump(z.out/"baseline_uncertainty_calibration.json",bc)
    freeze=dict(schema="aegisland.phase10r.candidate-freeze.v1",git_sha=os.getenv("GITHUB_SHA","local-smoke"),development_seed_seen=DEV_SEED,validation_seed_unseen_at_candidate_selection=VAL_SEED,partial_min_visible_fraction=MIN_VISIBLE,historical_phase10_holdout_used_for_selection=False,safety_acceptance=False,controller_tuning_allowed=False); dump(z.out/"candidate_freeze.json",freeze)
    val=run_split("validation",VAL_SEED,z.out,not a.no_raw); result=summarize(dev,val,cc,bc); result["candidate_freeze"]=freeze; dump(z.out/"validation_result.json",result)
    h1,h2,h3=result["h1"],result["h2"],result["h3"]; summary=f"# Phase 10R trajectory-held-out validation\n\n- all preregistered validation gates passed: **{result['all_preregistered_validation_gates_pass']}**\n- difficult miss rate: Phase 9 `{100*h1['baseline_miss_rate']:.2f}%` → Phase 10R `{100*h1['candidate_miss_rate']:.2f}%`\n- relative miss reduction: **{100*h1['relative_miss_reduction']:.1f}%**\n- lateral / altitude MAE improvement: **{100*h2['lateral_mae_relative_improvement']:.1f}% / {100*h2['altitude_mae_relative_improvement']:.1f}%**\n- lateral / altitude p95 improvement: **{100*h2['lateral_p95_relative_improvement']:.1f}% / {100*h2['altitude_p95_relative_improvement']:.1f}%**\n- mean absolute coverage error: **{100*h3['mean_absolute_coverage_error']:.2f} pp**\n- 95% coverage: **{100*h3['coverage']['lateral']['0.95']:.1f}% lateral / {100*h3['coverage']['altitude']['0.95']:.1f}% altitude**\n\nSimulation-only development/validation evidence. This is not the new frozen holdout and is not a physical-flight safety acceptance.\n"; (z.out/"summary.md").write_text(summary)
    names=["development_frames.csv","validation_frames.csv","candidate_uncertainty_calibration.json","baseline_uncertainty_calibration.json","candidate_freeze.json","validation_result.json","summary.md"]; dump(z.out/"result_manifest.json",{"schema":"aegisland.phase10r.generalization.v1","files":{n:{"sha256":fh(z.out/n),"bytes":(z.out/n).stat().st_size} for n in names}}); print(summary)
if __name__=="__main__":main()
