#!/usr/bin/env python3
"""Replay all saved v2 matches, frame/target outcomes and paired analysis offline."""
from collections import defaultdict
import csv
import gzip
import hashlib
import io
import json
import subprocess
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import run_phase22_occlusion_v2 as v2
from phase25_lib import Box, box_from_yolo, sha256_file


def rows(path, compressed=False):
    if compressed:
        return list(csv.DictReader(io.StringIO(gzip.decompress(path.read_bytes()).decode())))
    return v2.original.read_csv(path)


def typed(row):
    return {k: True if v=='True' else False if v=='False' else None if v=='' else
            int(v) if k in ('dose_index','target_index','prediction_index','matched_gt_index','class_id','tp','fp','fn','gt_count','detection_count','pred_count','frame_index') else
            float(v) if k in ('x0','y0','x1','y1','confidence','match_iou','best_iou','best_confidence','best_confidence_any','best_confidence_tp',
                'best_overlap_confidence','matched_tp_confidence_survivors_only','matched_tp_iou_survivors_only','requested_dose','achieved_image_mask_fraction',
                'achieved_annotation_box_mask_fraction','visible_annotation_box_fraction','achieved_target_box_mask_fraction') else v
            for k,v in row.items()}


def verify_artifact_freeze(output):
    """Offline byte/provenance check; never require the inference runtime in CI."""
    outcome=json.loads((output/'run_outcome.json').read_text())
    protocol=json.loads((output/'protocol.json').read_text())
    if sha256_file(output/'protocol.json')!=outcome['protocol_sha256']:
        raise ValueError('Frozen protocol SHA changed')
    v2.authenticate()
    resolved={}
    for p,sha in {**protocol['method_sha256'],**protocol['remote_recovery_file_sha256']}.items():
        path=ROOT/p
        if sha256_file(path)!=sha:
            path=output/'frozen_methods'/p
            if not path.exists() or sha256_file(path)!=sha:
                raise ValueError('Frozen method/provenance changed: '+p)
        resolved[p]=path
    if sha256_file(v2.RECOVERY/'recovery.json')!=protocol['recovery_receipt_sha256']:
        raise ValueError('Frozen recovery receipt changed')
    commit=outcome['freeze_commit']
    available=subprocess.run(['git','cat-file','-e',commit+'^{commit}'],cwd=ROOT,capture_output=True).returncode==0
    if available:
        for p in ('results/phase22_occlusion_v2/protocol.json',*v2.METHODS):
            blob=subprocess.check_output(['git','show',commit+':'+p],cwd=ROOT)
            expected=outcome['protocol_sha256'] if p=='results/phase22_occlusion_v2/protocol.json' else protocol['method_sha256'][p]
            if hashlib.sha256(blob).hexdigest()!=expected:
                raise ValueError('Implementation differs from actual freeze commit')
    return protocol,commit,available


def verify(output):
    outcome=json.loads((output/'run_outcome.json').read_text())
    if outcome['status']!='COMPLETE' or not outcome['treatment_inference_run']:
        raise ValueError('V2 treatments not complete')
    protocol,freeze_commit,history_verified=verify_artifact_freeze(output)
    if outcome['freeze_commit']!=freeze_commit:
        raise ValueError('Freeze commit provenance changed')
    for name,sha in outcome['output_sha256'].items():
        if sha256_file(output/name)!=sha:
            raise ValueError('Artifact hash changed: '+name)
    gate=json.loads((output/'zero_dose_gate.json').read_text())
    if v2.control_gate(gate['actual'],protocol['zero_dose_gate']['reference'],protocol['zero_dose_gate']['tolerance'])!=gate:
        raise ValueError('Recorded gate does not replay')
    v2.require_gates(gate)
    cases=[typed(c) for c in rows(output/'dose_image_manifest.csv')]
    saved_frames=[typed(r) for r in rows(output/'frame_condition_metrics.csv')]
    saved_targets=[typed(r) for r in rows(output/'target_metrics.csv')]
    masks=[typed(r) for r in rows(output/'target_mask_manifest.csv')]
    v2.complete(cases,v2.authenticate());v2.complete(saved_frames,v2.authenticate())
    by_case={(c['frame_id'],c['dose_index']):c for c in cases}
    geometry={(m['frame_id'],m['dose_index'],m['target_index']):m for m in masks}
    if len(geometry)!=len(masks): raise ValueError('Duplicate target masks')
    groups=defaultdict(list)
    for raw in rows(output/'prediction_boxes.csv.gz',True):
        row=typed(raw);groups[row['frame_id'],row['dose_index']].append(row)
    if not set(groups).issubset(by_case): raise ValueError('Unknown frame/dose predictions')
    recovery=json.loads((v2.RECOVERY/'recovery.json').read_text())
    if sha256_file(v2.RECOVERY/'source_labels.csv')!=recovery['source_labels_sha256']:
        raise ValueError('Frozen replay label table changed')
    labels={r['frame_id']:r for r in rows(v2.RECOVERY/'source_labels.csv')}
    reconstructed_frames=[];reconstructed_targets=[]
    for saved in saved_frames:
        key=saved['frame_id'],saved['dose_index'];case=by_case[key];raw=groups[key]
        if [r['prediction_index'] for r in raw]!=list(range(len(raw))):
            raise ValueError('Duplicate/noncontiguous prediction indices')
        boxes=[Box(r['class_id'],*(r[k] for k in ('x0','y0','x1','y1','confidence'))) for r in raw]
        label=labels[saved['frame_id']]['label_text']
        if hashlib.sha256(label.encode()).hexdigest()!=case['label_sha256']:
            raise ValueError('Replay label hash changed')
        truth=[box_from_yolo(int(p[0]),*map(float,p[1:])) for line in label.splitlines() if (p:=line.split())]
        frame,target,matched=v2.score_case(case,truth,boxes,geometry)
        if frame!=saved: raise ValueError('Frame metrics do not replay: '+str(key))
        if matched!=raw: raise ValueError('Raw prediction matches do not replay: '+str(key))
        reconstructed_frames.append(frame);reconstructed_targets.extend(target)
    if reconstructed_targets!=saved_targets: raise ValueError('Target metrics do not replay')
    analysis,doses,transitions,paired=v2.analyze(reconstructed_frames,reconstructed_targets)
    if analysis!=json.loads((output/'analysis.json').read_text()): raise ValueError('Paired analysis does not replay')
    for name,expected in [('dose_response.csv',doses),('paired_transitions.csv',transitions),('paired_frame_changes.csv',paired)]:
        # Compare exact canonical CSV bytes, preserving explicit null/boolean schema.
        b=io.StringIO(newline='');w=csv.DictWriter(b,fieldnames=list(expected[0]),lineterminator='\n');w.writeheader();w.writerows(expected)
        if b.getvalue().encode()!=(output/name).read_bytes(): raise ValueError('Analysis table does not replay: '+name)
    return {'status':'PASS','frame_rows_replayed':len(saved_frames),'target_rows_replayed':len(saved_targets),
        'prediction_rows_replayed':sum(map(len,groups.values())),'source_frames':analysis['source_frames'],
        'freeze_commit':freeze_commit,'freeze_commit_locally_verified':history_verified,
        'source_frame_paired_analysis_replayed':True,'detector_inference_run':False,
        'scope':'Saved artifact hashes/boxes/matches/outcomes/paired descriptive statistics and recorded clean gate; independent detector rerun and input replay require original source/runner.'}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=v2.OUT)
    args=p.parse_args()
    print(json.dumps(verify(args.out),indent=2))
