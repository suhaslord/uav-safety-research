#!/usr/bin/env python3
"""Publication recovery of the unchanged Phase 22 sweep, not a new result run.

The earlier implementation freeze and generated inputs disappeared in a
workspace rollback. This source preserves the recorded rules and requires a
new implementation recovery freeze before preparing or evaluating anything.
Restored historical results do not substitute for that freeze or input checks.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.metadata as metadata
import io
import json
import math
import os
from pathlib import Path
import platform
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'src')]
from phase25_lib import Box, box_from_yolo, frame_metrics, iou_xyxy, sha256_file
from phase25_reconstruction_lock import load_lock, verify_archive

PROTOCOL = ROOT / 'docs/phase25_occlusion_sweep_protocol.md'
PROTECTED = ROOT / 'results/phase25_failure_atlas/protected_test_manifest.csv'
REFERENCE = ROOT / 'results/phase23_robust_detector/robustness_comparison.csv'
FREEZE = ROOT / 'docs/phase25_occlusion_publication_implementation_freeze.json'
INPUT_LOCK = ROOT / 'docs/phase25_occlusion_publication_input_lock.json'
PROTOCOL_SHA = 'e169e16ea40ca44ee60ca8b6074d054c33aeeaf1a3d24e55fa4cd3b8581882d7'
BUNDLE_SHA = '8d6eda7f8775ad899be7a8b6fbf9e6dea30678c1e28c0b687a88184ac592288b'
CHECKPOINT_SHA = '3a1801b192d624f8dcdda4bc5d9a9157309000df67a4c30d62368c37901feddd'
PRIOR_IMAGE_MANIFEST_SHA = 'eb2c4202dcd36f792f0a767986bdc3369e32b04d36360ee9fc7ac6db5f7ead28'
RELEASE_URL = 'https://github.com/suhaslord/uav-safety-research/releases/download/phase22-baseline-recovery/phase22_recovery_bundle.zip'
DOSES = (0., .15, .30, .45, .60, .75)
SETTINGS = dict(imgsz=320, conf=.001, iou=.7, max_det=300, batch=16, workers=2, device='cpu')
RUNTIME = {'python': '3.12.14', 'torch': '2.9.1', 'torchvision': '0.24.1', 'ultralytics': '8.4.152', 'numpy': '2.5.3', 'Pillow': '12.3.0', 'opencv-python': '4.11.0.86'}
METHODS = ('scripts/run_phase25_occlusion_sweep.py', 'scripts/phase25_lib.py', 'scripts/phase25_reconstruction_lock.py', 'src/uav_safety/real_landing_dataset.py', 'tests/test_phase25_occlusion_sweep_publication.py')


def atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f: f.write(content); f.flush(); os.fsync(f.fileno())
        os.replace(temp, path)
        if path.read_bytes() != content: raise ValueError('Incomplete persisted file')
    finally:
        if os.path.exists(temp): os.unlink(temp)


def write_json(path: Path, value) -> None:
    atomic_bytes(path, (json.dumps(value, indent=2, allow_nan=False) + '\n').encode())


def read_csv(path: Path) -> list[dict]:
    with path.open(newline='', encoding='utf-8') as f: return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fields=None, compressed=False) -> None:
    if not rows and not fields: raise ValueError('Empty table requires schema')
    b = io.StringIO(newline=''); w = csv.DictWriter(b, fieldnames=fields or list(rows[0]), lineterminator='\n')
    w.writeheader(); w.writerows(rows); raw = b.getvalue().encode()
    atomic_bytes(path, gzip.compress(raw, mtime=0) if compressed else raw)


def protected_rows() -> list[dict]:
    if sha256_file(PROTECTED) != '8605cf1cbf9e8769c0324bf066078f9964f232ac3128131c8bd0b689bb7b64b7': raise ValueError('Protected IDs changed')
    rows = read_csv(PROTECTED)
    if len(rows) != 86 or len({r['image'] for r in rows}) != 86: raise ValueError('Protected count changed')
    return rows


def inventory(folder: Path, rows: list[dict]) -> str:
    return hashlib.sha256(''.join(f"{r['image']}:{sha256_file(folder / r['image'])}\n" for r in rows).encode()).hexdigest()


def checked_runtime() -> dict:
    actual = {'python': platform.python_version(), **{n: metadata.version(n) for n in RUNTIME if n != 'python'}}
    if actual != RUNTIME: raise ValueError(f'Unpinned inference runtime: {actual}')
    return {'core': actual, 'packages': sorted((d.metadata['Name'].lower(), d.version) for d in metadata.distributions())}


def verify_release(bundle: Path) -> dict:
    if sha256_file(bundle) != BUNDLE_SHA: raise ValueError('Recovery bundle hash mismatch')
    with zipfile.ZipFile(bundle) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or not {'best.pt', 'recovery_manifest.json', 'summary.json', 'split_manifest.csv'}.issubset(names): raise ValueError('Missing recovery provenance')
        if any(Path(n).is_absolute() or '..' in Path(n).parts for n in names): raise ValueError('Unsafe release member')
        weights = z.read('best.pt')
        if hashlib.sha256(weights).hexdigest() != CHECKPOINT_SHA: raise ValueError('Wrong checkpoint hash')
        manifest = json.loads(z.read('recovery_manifest.json'))
        if manifest.get('phase') != 'phase22_baseline' or manifest.get('checkpoint_sha256') != CHECKPOINT_SHA: raise ValueError('Wrong model provenance')
        if manifest['protected_dataset']['manifest_sha256'] != sha256_file(PROTECTED): raise ValueError('Released split differs')
        expected = {'imgsz':320,'confidence_floor':.001,'nms_iou':.7,'max_det':300,'batch':16,'workers':2,'device':'cpu','split':'test'}
        if any(manifest['evaluation_settings'].get(k) != v for k,v in expected.items()): raise ValueError('Released settings differ')
        atomic_bytes(bundle.parent / 'best.pt', weights)
    return manifest


def freeze() -> None:
    if FREEZE.exists(): raise ValueError('Do not overwrite implementation freeze')
    if sha256_file(PROTOCOL) != PROTOCOL_SHA: raise ValueError('Original protocol changed')
    load_lock()
    inputs = (PROTECTED, REFERENCE, ROOT / 'docs/phase25_reconstruction_lock.json')
    write_json(FREEZE, {'status':'publication_recovered_implementation_original_protocol_unchanged', 'frozen_at_utc':datetime.now(timezone.utc).isoformat(), 'protocol_sha256':PROTOCOL_SHA, 'runtime':checked_runtime(), 'settings':SETTINGS, 'doses':DOSES, 'method_sha256':{p:sha256_file(ROOT/p) for p in METHODS}, 'input_sha256':{str(p.relative_to(ROOT)):sha256_file(p) for p in inputs}, 'note':'New implementation recovery freeze; does not recreate the lost earlier full runtime/method receipt.'})


def verify_freeze() -> dict:
    value = json.loads(FREEZE.read_text())
    if sha256_file(PROTOCOL) != PROTOCOL_SHA or value['protocol_sha256'] != PROTOCOL_SHA: raise ValueError('Protocol changed')
    for p, sha in {**value['method_sha256'], **value['input_sha256']}.items():
        if sha256_file(ROOT / p) != sha: raise ValueError(f'Frozen file changed: {p}')
    if json.loads(json.dumps(checked_runtime())) != value['runtime'] or value['settings'] != SETTINGS or value['doses'] != list(DOSES): raise ValueError('Frozen runtime/settings changed')
    return value


def truth(path: Path) -> list[Box]:
    boxes = []
    for line in path.read_text().splitlines():
        p = line.split()
        if len(p) != 5 or p[0] != '0': raise ValueError('Invalid target label')
        boxes.append(box_from_yolo(0, *map(float, p[1:])))
    if not boxes: raise ValueError('Empty target labels')
    return boxes


def mask_geometry(box: Box, width: int, height: int, dose: float) -> dict:
    if dose not in DOSES: raise ValueError('Unregistered dose')
    x0,y0 = max(0,math.floor(box.x0*width)),max(0,math.floor(box.y0*height))
    x1,y1 = min(width,math.ceil(box.x1*width)),min(height,math.ceil(box.y1*height))
    w,h = x1-x0,y1-y0
    if min(w,h) <= 0: raise ValueError('Zero-area target')
    mw,mh = (max(1,math.floor(w*math.sqrt(dose)+.5)),max(1,math.floor(h*math.sqrt(dose)+.5))) if dose else (0,0)
    mx,my = x0+(w-mw)//2,y0+(h-mh)//2
    return {'gt_x0':x0,'gt_y0':y0,'gt_x1':x1,'gt_y1':y1,'box_pixel_area':w*h,'mask_x0':mx,'mask_y0':my,'mask_x1':mx+mw,'mask_y1':my+mh,'mask_pixel_area':mw*mh,'achieved_mask_image_fraction':mw*mh/(width*height)}


def apply_mask(pixels, targets: list[Box], dose: float):
    import numpy as np
    height,width = pixels.shape[:2]; geometry = [mask_geometry(b,width,height,dose) for b in targets]
    union = np.zeros((height,width),dtype=bool)
    for g in geometry: union[g['mask_y0']:g['mask_y1'],g['mask_x0']:g['mask_x1']] = True
    result = pixels.copy(); result[union] = (127,127,127)
    for index,g in enumerate(geometry):
        hidden = int(union[g['gt_y0']:g['gt_y1'],g['gt_x0']:g['gt_x1']].sum())
        g.update(target_index=index,masked_box_pixels=hidden,achieved_target_box_mask_fraction=hidden/g['box_pixel_area'],visible_annotation_box_fraction=1-hidden/g['box_pixel_area'])
    return result,geometry


def prepare(args) -> None:
    import numpy as np
    import py7zr
    from PIL import Image
    from uav_safety.real_landing_dataset import read_yolo_boxes,write_single_class_yolo
    verify_freeze(); lock=load_lock(); verify_archive(args.archive,lock)
    if args.prepared.exists() or INPUT_LOCK.exists(): raise ValueError('Do not overwrite prepared inputs')
    rows=protected_rows();args.prepared.mkdir(parents=True);cases=[];masks=[]
    prefix='airisim_dataset2/Real_images_tight_labels/'
    with tempfile.TemporaryDirectory(prefix='phase25-source-') as temp:
        with py7zr.SevenZipFile(args.archive) as z:
            targets=[prefix+r[k] for r in rows for k in ('image','label')]
            if not set(targets).issubset(z.getnames()): raise ValueError('Archive members missing')
            z.extract(path=temp,targets=targets)
        source_dir=Path(temp)/prefix
        def prepare_one(row):
            source=args.prepared/'source/images/test'/row['image'];label=args.prepared/'source/labels/test'/row['label']
            atomic_bytes(source,(source_dir/row['image']).read_bytes());write_single_class_yolo(label,read_yolo_boxes(source_dir/row['label'],class_id=0))
            expected=lock['protected_test_files'][row['image']]
            if sha256_file(source)!=expected['image_sha256'] or sha256_file(label)!=expected['label_sha256']: raise ValueError('Source differs from frozen archive extraction')
            with Image.open(source) as image: pixels=np.asarray(image.convert('RGB')).copy()
            height,width=pixels.shape[:2];boxes=truth(label);local_cases=[];local_masks=[]
            for index,dose in enumerate(DOSES):
                filename=row['image'] if index==0 else Path(row['image']).stem+'.png'
                image_rel=f'dose_{index:02d}/images/test/{filename}';label_rel=f'dose_{index:02d}/labels/test/{row["label"]}'
                output,geometry=apply_mask(pixels,boxes,dose)
                if index==0: encoded=source.read_bytes()
                else:
                    buffer=io.BytesIO();Image.fromarray(output).save(buffer,format='PNG',compress_level=9);encoded=buffer.getvalue()
                atomic_bytes(args.prepared/image_rel,encoded)
                with Image.open(args.prepared/image_rel) as image: image.verify()
                with Image.open(args.prepared/image_rel) as image:
                    image.load()
                    if not np.array_equal(np.asarray(image.convert('RGB')),output): raise ValueError('Saved view changed pixels')
                atomic_bytes(args.prepared/label_rel,label.read_bytes())
                local_cases.append({'dose_index':index,'nominal_occluded_box_fraction':dose,'nominal_visible_box_fraction':1-dose,'frame_id':row['image'],'sequence':row['sequence'],'frame_index':row['frame_index'],'source_image_sha256':expected['image_sha256'],'source_label_sha256':expected['label_sha256'],'image_path':image_rel,'image_sha256':sha256_file(args.prepared/image_rel),'label_path':label_rel,'label_sha256':sha256_file(label),'width':width,'height':height,'target_count':len(boxes)})
                local_masks.extend({'frame_id':row['image'],'dose_index':index,**g} for g in geometry)
            return local_cases,local_masks
        with ThreadPoolExecutor(max_workers=4) as pool:
            for index,(c,m) in enumerate(pool.map(prepare_one,rows),1):
                cases.extend(c);masks.extend(m)
                if index%10==0 or index==86: print(f'Prepared {index}/86 frames',flush=True)
    write_csv(args.prepared/'dose_image_manifest.csv',cases);write_csv(args.prepared/'target_mask_manifest.csv',masks)
    if len(cases)!=516 or sha256_file(args.prepared/'dose_image_manifest.csv')!=PRIOR_IMAGE_MANIFEST_SHA: raise ValueError('Historical full image manifest mismatch; never refresh expected checksum')
    write_json(args.prepared/'prepared_manifest.json',{'case_count':len(cases),'target_case_count':len(masks),'archive_sha256':sha256_file(args.archive),'protocol_sha256':PROTOCOL_SHA,'table_sha256':{n:sha256_file(args.prepared/n) for n in ('dose_image_manifest.csv','target_mask_manifest.csv')}})
    write_json(INPUT_LOCK,{'prepared_manifest_sha256':sha256_file(args.prepared/'prepared_manifest.json'),'implementation_freeze_sha256':sha256_file(FREEZE)})


def verify_prepared(root: Path, archive: Path):
    import numpy as np
    from PIL import Image
    verify_freeze();lock=load_lock();verify_archive(archive,lock);record=json.loads(INPUT_LOCK.read_text())
    if sha256_file(root/'prepared_manifest.json')!=record['prepared_manifest_sha256'] or sha256_file(FREEZE)!=record['implementation_freeze_sha256']: raise ValueError('Input lock changed')
    manifest=json.loads((root/'prepared_manifest.json').read_text())
    for name,sha in manifest['table_sha256'].items():
        if sha256_file(root/name)!=sha: raise ValueError('Prepared table changed')
    if sha256_file(root/'dose_image_manifest.csv')!=PRIOR_IMAGE_MANIFEST_SHA: raise ValueError('Historical inventory mismatch')
    cases=read_csv(root/'dose_image_manifest.csv');masks=read_csv(root/'target_mask_manifest.csv')
    keys={(r['image'],str(i)) for r in protected_rows() for i in range(6)}
    if len(cases)!=len(keys) or {(c['frame_id'],c['dose_index']) for c in cases}!=keys: raise ValueError('Missing or duplicate cases')
    if {str(p.relative_to(root)) for p in root.glob('dose_*/images/test/*')}!={c['image_path'] for c in cases}: raise ValueError('Unexpected images')
    geometry={(m['frame_id'],m['dose_index'],m['target_index']):m for m in masks}
    if len(geometry)!=len(masks): raise ValueError('Duplicate target masks')
    target_count=0
    for row in protected_rows():
        source=root/'source/images/test'/row['image'];label=root/'source/labels/test'/row['label'];expected=lock['protected_test_files'][row['image']]
        if sha256_file(source)!=expected['image_sha256'] or sha256_file(label)!=expected['label_sha256']: raise ValueError('Source changed')
        with Image.open(source) as image: pixels=np.asarray(image.convert('RGB')).copy()
        targets=truth(label)
        for c in (c for c in cases if c['frame_id']==row['image']):
            index=int(c['dose_index']);p=root/c['image_path']
            if float(c['nominal_occluded_box_fraction'])!=DOSES[index] or int(c['target_count'])!=len(targets): raise ValueError('Incorrect case metadata')
            if sha256_file(p)!=c['image_sha256'] or sha256_file(root/c['label_path'])!=expected['label_sha256']: raise ValueError('Prepared bytes changed')
            if index==0 and p.read_bytes()!=source.read_bytes(): raise ValueError('Raw zero dose changed')
            expected_pixels,expected_geometry=apply_mask(pixels,targets,DOSES[index])
            with Image.open(p) as image: image.verify()
            with Image.open(p) as image:
                image.load()
                if not np.array_equal(np.asarray(image.convert('RGB')),expected_pixels): raise ValueError('Wrong frozen transform pixels')
            for g in expected_geometry:
                actual=geometry.get((row['image'],str(index),str(g['target_index'])))
                if actual is None or any(float(actual[k])!=float(v) for k,v in g.items()): raise ValueError('Wrong mask geometry')
            target_count+=len(targets)
    if len(masks)!=target_count: raise ValueError('Incomplete target masks')
    return cases,masks


def control_gate(actual: dict, reference: dict) -> dict:
    expected={'recall':float(reference['baseline_recall']),'map50':float(reference['baseline_map50'])}
    return {'actual':actual,'expected':expected,'delta':{k:actual[k]-expected[k] for k in expected},'tolerance':.001,'passed':all(math.isfinite(actual[k]) and 0<=actual[k]<=1 and abs(actual[k]-expected[k])<=.001 for k in expected)}


def evaluate(model, folder: Path, out: Path) -> dict:
    yaml=out/'data.yaml';atomic_bytes(yaml,(f'path: {folder.resolve()}\ntrain: images/test\nval: images/test\ntest: images/test\nnames:\n  0: landing_pad\n').encode())
    value=model.val(data=str(yaml),split='test',**SETTINGS,plots=False,verbose=False,project=str(out),name='validation',exist_ok=True)
    return {'precision':float(value.box.mp),'recall':float(value.box.mr),'map50':float(value.box.map50),'map50_95':float(value.box.map)}


def infer(args) -> bool:
    frozen=verify_freeze();cases,masks=verify_prepared(args.prepared,args.archive);release=verify_release(args.bundle)
    if args.out.exists(): raise ValueError('Do not overwrite run outputs')
    args.out.mkdir(parents=True)
    from ultralytics import YOLO
    model=YOLO(str(args.bundle.parent/'best.pt'))
    if model.names!={0:'landing_pad'}: raise ValueError('Incorrect class')
    record={'status':'running_zero_dose_gate','protocol_sha256':PROTOCOL_SHA,'bundle_sha256':BUNDLE_SHA,'checkpoint_sha256':CHECKPOINT_SHA,'release_url':RELEASE_URL,'release_provenance':release,'runtime':frozen['runtime'],'implementation_freeze_sha256':sha256_file(FREEZE),'input_lock_sha256':sha256_file(INPUT_LOCK),'settings':SETTINGS,'case_count':len(cases),'treatment_predictions_generated':False}
    write_json(args.out/'run_manifest.json',record)
    reference={r['condition']:r for r in read_csv(REFERENCE)}['clean']
    gate=control_gate(evaluate(model,args.prepared/'dose_00',args.out/'zero_dose_control'),reference);write_json(args.out/'zero_dose_gate.json',gate)
    if not gate['passed']:
        record.update(status='blocked_zero_dose_aggregate_reproduction_failed',zero_dose_gate=gate);write_json(args.out/'run_manifest.json',record)
        return False
    frames=[];boxes=[];targets=[];geometry={(g['frame_id'],g['dose_index'],g['target_index']):g for g in masks}
    for index in range(6):
        group=[c for c in cases if int(c['dose_index'])==index]
        results=model.predict(source=[str(args.prepared/c['image_path']) for c in group],**{k:v for k,v in SETTINGS.items() if k!='workers'},stream=True,verbose=False)
        for case,result in zip(group,results,strict=True):
            if Path(result.path).name!=Path(case['image_path']).name: raise ValueError('Prediction order changed')
            truth_boxes=truth(args.prepared/case['label_path']);predictions=[]
            if result.boxes is not None:
                for xyxy,cls,score in zip(result.boxes.xyxyn.cpu().numpy(),result.boxes.cls.cpu().numpy(),result.boxes.conf.cpu().numpy(),strict=True):
                    if not all(math.isfinite(float(v)) for v in (*xyxy,cls,score)) or cls!=int(cls) or not 0<=score<=1: raise ValueError('Invalid detector output')
                    coordinates=[max(0.,min(1.,float(v))) for v in xyxy]
                    if coordinates[2]<coordinates[0] or coordinates[3]<coordinates[1]: raise ValueError('Inverted prediction')
                    predictions.append(Box(int(cls),*coordinates,float(score)))
            metrics,matched=frame_metrics(truth_boxes,predictions,iou_threshold=.5)
            if metrics['tp']+metrics['fn']!=len(truth_boxes) or metrics['tp']+metrics['fp']!=len(predictions): raise ValueError('Counts do not reconcile')
            key={k:case[k] for k in ('frame_id','sequence','frame_index','dose_index')};frames.append({**key,**metrics});boxes.extend({**key,**b} for b in matched)
            for ti,target in enumerate(truth_boxes):
                candidates=[(iou_xyxy(target,b),float(b.confidence),pi) for pi,b in enumerate(predictions) if b.class_id==target.class_id]
                best=max(candidates,key=lambda t:(t[0],t[1],-t[2]),default=None);tp=next((b for b in matched if b['is_true_positive'] and b['matched_gt_index']==ti),None)
                targets.append({**key,'target_index':ti,**{k:geometry[(case['frame_id'],str(index),str(ti))][k] for k in ('achieved_target_box_mask_fraction','visible_annotation_box_fraction')},'detected':tp is not None,'best_iou':best[0] if best else 0.,'best_overlap_confidence':best[1] if best else None,'matched_tp_confidence_survivors_only':tp['confidence'] if tp else None})
    if len(frames)!=len(cases) or len(targets)!=len(masks): raise ValueError('Incomplete predictions')
    write_csv(args.out/'frame_condition_metrics.csv',frames);write_csv(args.out/'target_metrics.csv',targets)
    write_csv(args.out/'prediction_boxes.csv.gz',boxes,fields=['frame_id','sequence','frame_index','dose_index','prediction_index','class_id','x0','y0','x1','y1','confidence','matched_gt_index','match_iou','is_true_positive'],compressed=True)
    record.update(status='complete_predictions_analysis_pending',treatment_predictions_generated=True,zero_dose_gate=gate,output_sha256={n:sha256_file(args.out/n) for n in ('frame_condition_metrics.csv','target_metrics.csv','prediction_boxes.csv.gz')});write_json(args.out/'run_manifest.json',record)
    return True


def diagnose(args) -> None:
    from PIL import Image
    verify_freeze();verify_prepared(args.prepared,args.archive);verify_release(args.bundle)
    gate=json.loads((args.out/'zero_dose_gate.json').read_text());run=json.loads((args.out/'run_manifest.json').read_text())
    if gate['passed'] or run['treatment_predictions_generated']: raise ValueError('Diagnostic requires failed raw control')
    out=args.out.parent/'phase25_control_input_diagnostic_replay'
    if out.exists(): raise ValueError('Do not overwrite diagnostic')
    out.mkdir(parents=True);folder=args.prepared/'benchmark_clean';rows=protected_rows()
    for row in rows:
        b=io.BytesIO()
        with Image.open(args.prepared/'source/images/test'/row['image']) as image: image.convert('RGB').save(b,format='JPEG',quality=95)
        atomic_bytes(folder/'images/test'/row['image'],b.getvalue());atomic_bytes(folder/'labels/test'/row['label'],(args.prepared/'source/labels/test'/row['label']).read_bytes())
    digest=inventory(folder/'images/test',rows)
    if digest!=load_lock()['condition_image_inventory_sha256']['clean']: raise ValueError('Benchmark clean inventory mismatch')
    from ultralytics import YOLO
    actual=evaluate(YOLO(str(args.bundle.parent/'best.pt')),folder,out/'benchmark_clean_control')
    reference={r['condition']:r for r in read_csv(REFERENCE)}['clean']
    write_json(out/'diagnostic.json',{'status':'diagnostic_only_original_gate_remains_blocked','benchmark_clean_inventory_sha256':digest,'benchmark_clean_metrics':actual,'benchmark_clean_reconciliation':control_gate(actual,reference),'original_raw_zero_dose_gate':gate,'treatment_inference_authorized':False})


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('freeze','prepare','verify','infer','diagnose'))
    p.add_argument('--archive',type=Path,default=ROOT/'data/external/kios_landing_pad/airisim_dataset2.7z');p.add_argument('--bundle',type=Path,default=ROOT/'data/external/phase22_recovery_release/phase22_recovery_bundle.zip')
    p.add_argument('--prepared',type=Path,default=ROOT/'data/derived/phase25_occlusion_publication_replay');p.add_argument('--out',type=Path,default=ROOT/'results/phase25_occlusion_publication_replay')
    a=p.parse_args()
    if a.command=='freeze': freeze()
    elif a.command=='prepare': prepare(a)
    elif a.command=='verify':
        cases,masks=verify_prepared(a.prepared,a.archive);print(f'Verified {len(cases)} cases and {len(masks)} target masks')
    elif a.command=='infer':
        if not infer(a): raise SystemExit(2)
    else: diagnose(a)


if __name__=='__main__': main()
