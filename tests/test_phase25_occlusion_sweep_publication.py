"""Fail-closed checks for the publication recovery, without running detectors."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import zipfile
import numpy as np
from PIL import Image
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import run_phase25_occlusion_sweep as sweep
from phase25_lib import Box


def test_original_protocol_bytes():
    assert sweep.sha256_file(sweep.PROTOCOL)==sweep.PROTOCOL_SHA


def test_empty_prediction_schema_and_lf(tmp_path):
    p=tmp_path/'empty.csv.gz';sweep.write_csv(p,[],fields=['frame_id','confidence'],compressed=True)
    assert gzip.decompress(p.read_bytes())==b'frame_id,confidence\n'


@pytest.mark.parametrize('score,passed',[(.700999,True),(.701001,False),(float('nan'),False)])
def test_fixed_finite_metric_gate(score,passed):
    result=sweep.control_gate({'recall':.4,'map50':score},{'baseline_recall':.4,'baseline_map50':.7})
    assert result['passed'] is passed and result['tolerance']==.001


def test_wrong_release_rejected(tmp_path):
    p=tmp_path/'wrong.zip';p.write_bytes(b'arbitrary weights')
    with pytest.raises(ValueError,match='bundle hash mismatch'): sweep.verify_release(p)


def test_missing_release_provenance_rejected(tmp_path,monkeypatch):
    p=tmp_path/'missing.zip'
    with zipfile.ZipFile(p,'w') as z: z.writestr('best.pt',b'candidate')
    monkeypatch.setattr(sweep,'BUNDLE_SHA',sweep.sha256_file(p))
    with pytest.raises(ValueError,match='provenance'): sweep.verify_release(p)


def test_unpinned_runtime_rejected(monkeypatch):
    monkeypatch.setattr(sweep.platform,'python_version',lambda:sweep.RUNTIME['python'])
    monkeypatch.setattr(sweep.metadata,'version',lambda n:'wrong' if n=='ultralytics' else sweep.RUNTIME[n])
    with pytest.raises(ValueError,match='Unpinned inference runtime'): sweep.checked_runtime()


def test_gate_failure_never_predicts(tmp_path,monkeypatch):
    for n in ('freeze.json','input.json'): (tmp_path/n).write_text('{}')
    monkeypatch.setattr(sweep,'FREEZE',tmp_path/'freeze.json');monkeypatch.setattr(sweep,'INPUT_LOCK',tmp_path/'input.json')
    monkeypatch.setattr(sweep,'verify_freeze',lambda:{'runtime':{}});monkeypatch.setattr(sweep,'verify_prepared',lambda *a:([{}],[]));monkeypatch.setattr(sweep,'verify_release',lambda *a:{})
    model=SimpleNamespace(names={0:'landing_pad'},predict=lambda *a,**k:pytest.fail('Treatment prediction ran'))
    monkeypatch.setitem(sys.modules,'ultralytics',SimpleNamespace(YOLO=lambda *a:model))
    ref={r['condition']:r for r in sweep.read_csv(sweep.REFERENCE)}['clean']
    monkeypatch.setattr(sweep,'evaluate',lambda *a:{'recall':float(ref['baseline_recall']),'map50':float(ref['baseline_map50'])+.002})
    args=SimpleNamespace(prepared=tmp_path/'prepared',archive=tmp_path/'archive',bundle=tmp_path/'bundle',out=tmp_path/'out')
    assert sweep.infer(args) is False
    value=json.loads((args.out/'run_manifest.json').read_text())
    assert value['treatment_predictions_generated'] is False
    assert not (args.out/'prediction_boxes.csv.gz').exists()


def test_mask_rounding_and_unchanged_zero():
    g=sweep.mask_geometry(Box(0,.1,.1,.9,.9),100,100,.15)
    assert (g['mask_x0'],g['mask_x1'])==(34,65)
    source=np.zeros((100,100,3),dtype=np.uint8);out,rows=sweep.apply_mask(source,[Box(0,.1,.1,.9,.9)],0.)
    assert np.array_equal(out,source) and rows[0]['visible_annotation_box_fraction']==1.


def test_nested_doses_only_change_mask():
    source=np.full((31,43,3),42,dtype=np.uint8);previous=np.zeros((31,43),dtype=bool)
    for dose in sweep.DOSES:
        out,rows=sweep.apply_mask(source,[Box(0,.15,.12,.75,.8)],dose);changed=np.any(out!=source,axis=2)
        assert np.all(changed[previous]) and np.all(out[changed]==127)
        assert changed.sum()==rows[0]['mask_pixel_area'];previous=changed


def test_overlapping_masks_use_union():
    out,rows=sweep.apply_mask(np.zeros((20,20,3),dtype=np.uint8),[Box(0,.1,.1,.7,.7),Box(0,.3,.3,.9,.9)],.6)
    for g in rows:
        hidden=np.any(out!=0,axis=2)[g['gt_y0']:g['gt_y1'],g['gt_x0']:g['gt_x1']].sum()
        assert g['masked_box_pixels']==hidden
        assert g['visible_annotation_box_fraction']==1-hidden/g['box_pixel_area']


def test_unregistered_dose_rejected():
    with pytest.raises(ValueError,match='Unregistered'): sweep.mask_geometry(Box(0,0.,0.,1.,1.),20,20,.2)


def fixture_inputs(tmp_path,monkeypatch):
    root=tmp_path/'prepared';label=b'0 0.5 0.5 0.5 0.5\n';boxes=[Box(0,.25,.25,.75,.75)]
    b=io.BytesIO();Image.fromarray(np.full((18,22,3),42,dtype=np.uint8)).save(b,format='JPEG');source=b.getvalue()
    sweep.atomic_bytes(root/'source/images/test/frame.jpg',source);sweep.atomic_bytes(root/'source/labels/test/frame.txt',label)
    with Image.open(io.BytesIO(source)) as image: pixels=np.asarray(image.convert('RGB')).copy()
    cases=[];masks=[]
    for i,dose in enumerate(sweep.DOSES):
        image_rel=f'dose_{i:02d}/images/test/frame.'+('jpg' if i==0 else 'png');label_rel=f'dose_{i:02d}/labels/test/frame.txt'
        out,geometry=sweep.apply_mask(pixels,boxes,dose);b=io.BytesIO();Image.fromarray(out).save(b,format='PNG')
        sweep.atomic_bytes(root/image_rel,source if i==0 else b.getvalue());sweep.atomic_bytes(root/label_rel,label)
        cases.append({'frame_id':'frame.jpg','dose_index':i,'nominal_occluded_box_fraction':dose,'target_count':1,'image_path':image_rel,'label_path':label_rel,'image_sha256':sweep.sha256_file(root/image_rel)})
        masks.extend({'frame_id':'frame.jpg','dose_index':i,**g} for g in geometry)
    monkeypatch.setattr(sweep,'protected_rows',lambda:[{'image':'frame.jpg','label':'frame.txt'}]);monkeypatch.setattr(sweep,'verify_freeze',lambda:{});monkeypatch.setattr(sweep,'verify_archive',lambda *a:None)
    monkeypatch.setattr(sweep,'load_lock',lambda:{'protected_test_files':{'frame.jpg':{'image_sha256':hashlib.sha256(source).hexdigest(),'label_sha256':hashlib.sha256(label).hexdigest()}}})
    freeze=tmp_path/'freeze.json';freeze.write_text('{}');monkeypatch.setattr(sweep,'FREEZE',freeze);monkeypatch.setattr(sweep,'INPUT_LOCK',tmp_path/'input.json')
    def seal():
        sweep.write_csv(root/'dose_image_manifest.csv',cases);sweep.write_csv(root/'target_mask_manifest.csv',masks)
        monkeypatch.setattr(sweep,'PRIOR_IMAGE_MANIFEST_SHA',sweep.sha256_file(root/'dose_image_manifest.csv'))
        sweep.write_json(root/'prepared_manifest.json',{'table_sha256':{n:sweep.sha256_file(root/n) for n in ('dose_image_manifest.csv','target_mask_manifest.csv')}})
        sweep.write_json(sweep.INPUT_LOCK,{'prepared_manifest_sha256':sweep.sha256_file(root/'prepared_manifest.json'),'implementation_freeze_sha256':sweep.sha256_file(freeze)})
    seal();return root,cases,masks,seal


def test_truncated_image_rejected(tmp_path,monkeypatch):
    root,cases,_,seal=fixture_inputs(tmp_path,monkeypatch)
    assert len(sweep.verify_prepared(root,tmp_path/'archive')[0])==6
    (root/cases[3]['image_path']).write_bytes(b'truncated')
    with pytest.raises(ValueError,match='Prepared bytes changed'): sweep.verify_prepared(root,tmp_path/'archive')


def test_rehashed_wrong_pixels_rejected(tmp_path,monkeypatch):
    root,cases,_,seal=fixture_inputs(tmp_path,monkeypatch);p=root/cases[4]['image_path']
    Image.fromarray(np.zeros((18,22,3),dtype=np.uint8)).save(p);cases[4]['image_sha256']=sweep.sha256_file(p);seal()
    with pytest.raises(ValueError,match='Wrong frozen transform pixels'): sweep.verify_prepared(root,tmp_path/'archive')


def test_duplicate_case_rejected(tmp_path,monkeypatch):
    root,cases,_,seal=fixture_inputs(tmp_path,monkeypatch);cases[2]['dose_index']=1;seal()
    with pytest.raises(ValueError,match='duplicate cases'): sweep.verify_prepared(root,tmp_path/'archive')


def test_mask_geometry_mismatch_rejected(tmp_path,monkeypatch):
    root,_,masks,seal=fixture_inputs(tmp_path,monkeypatch);masks[3]['mask_x0']+=1;seal()
    with pytest.raises(ValueError,match='Wrong mask geometry'): sweep.verify_prepared(root,tmp_path/'archive')


def test_historical_manifest_cannot_be_refreshed(tmp_path,monkeypatch):
    root,_,_,_=fixture_inputs(tmp_path,monkeypatch);monkeypatch.setattr(sweep,'PRIOR_IMAGE_MANIFEST_SHA','0'*64)
    with pytest.raises(ValueError,match='Historical inventory mismatch'): sweep.verify_prepared(root,tmp_path/'archive')


def test_inventory_preserves_manifest_order(tmp_path):
    (tmp_path/'z.jpg').write_bytes(b'z');(tmp_path/'a.jpg').write_bytes(b'a')
    assert sweep.inventory(tmp_path,[{'image':'z.jpg'},{'image':'a.jpg'}])!=sweep.inventory(tmp_path,[{'image':'a.jpg'},{'image':'z.jpg'}])
