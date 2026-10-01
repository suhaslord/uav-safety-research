"""Evidence authentication, inherited rules, and fail-closed v2 execution."""
from pathlib import Path
import hashlib
import io
import json
import sys
from types import SimpleNamespace
import numpy as np
from PIL import Image
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import run_phase22_occlusion_v2 as v2
from phase22_representation_transform import atomic_write, encode
from phase25_lib import Box


def test_authenticated_original_and_six_doses():
    assert len(v2.authenticate()) == 86
    assert v2.original.PROTOCOL_SHA == 'e169e16ea40ca44ee60ca8b6074d054c33aeeaf1a3d24e55fa4cd3b8581882d7'
    assert v2.original.DOSES == (0.,.15,.30,.45,.60,.75)
    assert v2.sha256_file(ROOT/v2.METHODS[1]) == v2.ORIGINAL_RUNNER_SHA


def test_no_fabricated_protocol_fallback(tmp_path,monkeypatch):
    p=tmp_path/'protocol.md';p.write_text('plausible replacement')
    monkeypatch.setattr(v2.original,'PROTOCOL',p)
    with pytest.raises(ValueError,match='no fallback'): v2.authenticate()


def test_method_authentication_cannot_be_skipped(monkeypatch):
    monkeypatch.setattr(v2,'ORIGINAL_RUNNER_SHA','0'*64)
    with pytest.raises(ValueError,match='runner changed'): v2.authenticate()


def test_original_geometry_replay_artifact():
    report=json.loads((v2.RECOVERY/'recovery.json').read_text())
    cases=v2.original.read_csv(v2.RECOVERY/'dose_image_manifest.csv')
    v2.complete(cases,v2.authenticate())
    assert len(cases)==516 and report['case_count']==516
    assert not report['detector_inference_run']
    assert report['historical_manifest_sha256']==v2.original.PRIOR_IMAGE_MANIFEST_SHA
    assert v2.sha256_file(v2.RECOVERY/'dose_image_manifest.csv')==v2.original.PRIOR_IMAGE_MANIFEST_SHA
    assert v2.sha256_file(v2.RECOVERY/'target_mask_manifest.csv')==report['target_mask_manifest_sha256']


def test_duplicate_frame_dose_rejected():
    frames=[{'image':'a.jpg'}];rows=[{'frame_id':'a.jpg','dose_index':i} for i in range(6)]
    v2.complete(rows,frames);rows[5]['dose_index']=4
    with pytest.raises(ValueError,match='Duplicate'): v2.complete(rows,frames)


def test_incomplete_population_rejected():
    with pytest.raises(ValueError,match='incomplete'): v2.complete([], [{'image':'a.jpg'}])


@pytest.mark.parametrize('delta,passed',[(0.,True),(.000999,True),(.001001,False),(float('nan'),False)])
def test_original_gate_tolerance(delta,passed):
    gate=v2.control_gate({'recall':.4,'map50':.5+delta},{'recall':.4,'map50':.5})
    assert (gate['status']=='PASS') is passed
    assert gate['tolerance']==.001


def test_failed_gate_prohibits_treatments():
    with pytest.raises(ValueError,match='prohibited'): v2.require_gates({'status':'FAIL','checks':{'map50':False}})


def test_run_failed_gate_never_builds_or_predicts(tmp_path,monkeypatch):
    monkeypatch.setattr(v2,'OUT',tmp_path/'out')
    monkeypatch.setattr(v2,'validate_freeze',lambda sha:({'zero_dose_gate':{'reference':{'recall':.4,'map50':.5},'tolerance':.001}},'f'*40))
    monkeypatch.setattr(v2.stage_a,'verify_population',lambda *a:[])
    monkeypatch.setattr(v2.stage_a,'runtime',lambda:{})
    monkeypatch.setattr(v2.stage_a,'evaluate',lambda *a:({'recall':.4,'map50':.502},[],[]))
    monkeypatch.setattr(v2.original,'inventory',lambda *a:v2.original.load_lock()['condition_image_inventory_sha256']['clean'])
    monkeypatch.setattr(v2,'build_views',lambda *a:pytest.fail('Treatment preparation after failed gate'))
    weights=tmp_path/'weights';weights.write_bytes(b'fixture')
    args=SimpleNamespace(source=tmp_path,canonical=tmp_path,weights=weights,archive=tmp_path,work=tmp_path,protocol_sha='fixture')
    v2.run(args)
    result=json.loads((v2.OUT/'run_outcome.json').read_text())
    assert result['status']=='BLOCKED_ZERO_DOSE_GATE_FAILED'
    assert result['treatment_inference_run'] is False


def test_q95_determinism_and_lossless_masking(tmp_path):
    pixels=np.arange(39*53*3,dtype=np.uint8).reshape(39,53,3)
    b=io.BytesIO();Image.fromarray(pixels).save(b,format='JPEG',quality=88)
    q95=encode(b.getvalue(),'HISTORICAL_Q95')
    assert q95==encode(b.getvalue(),'HISTORICAL_Q95')
    with Image.open(io.BytesIO(q95)) as image: canonical=np.asarray(image.convert('RGB')).copy()
    masked,_=v2.original.apply_mask(canonical,[Box(0,.1,.1,.9,.9)],.45)
    b=io.BytesIO();Image.fromarray(masked).save(b,format='PNG',compress_level=9)
    atomic_write(tmp_path/'mask.png',b.getvalue(),hashlib.sha256(b.getvalue()).hexdigest(),image=True)
    with Image.open(tmp_path/'mask.png') as image: assert np.array_equal(np.asarray(image),masked)


def test_atomic_corruption_and_overwrite_rejected(tmp_path):
    content=b'invalid image';sha=hashlib.sha256(content).hexdigest()
    with pytest.raises(Exception): atomic_write(tmp_path/'a.png',content,sha,image=True)
    assert not (tmp_path/'a.png').exists()
    atomic_write(tmp_path/'a.txt',b'a',hashlib.sha256(b'a').hexdigest())
    with pytest.raises(ValueError,match='overwrite'): atomic_write(tmp_path/'a.txt',b'b',hashlib.sha256(b'b').hexdigest())


def test_target_best_overlap_confidence_not_unrelated_max():
    case={'frame_id':'a.jpg','sequence':'s','frame_index':0,'dose_index':0,'session':'s','requested_dose':0.,
        'achieved_image_mask_fraction':0.,'achieved_annotation_box_mask_fraction':0.,'visible_annotation_box_fraction':1.,
        'source_image_sha256':'a','canonical_q95_sha256':'b','image_sha256':'c'}
    geometry={('a.jpg',0,0):{'achieved_target_box_mask_fraction':0.,'visible_annotation_box_fraction':1.}}
    truth=[Box(0,.1,.1,.4,.4)]
    predictions=[Box(0,.6,.6,.9,.9,.99),Box(0,.1,.1,.4,.4,.2)]
    frame,targets,_=v2.score_case(case,truth,predictions,geometry)
    assert frame['best_confidence']==.2 and frame['best_confidence_any']==.99
    assert frame['frame_success'] and frame['fp']==1
    assert targets[0]['best_iou']==1.


def test_descriptive_analysis_uses_paired_sources_without_invented_seed(monkeypatch):
    monkeypatch.setattr(v2,'authenticate',lambda:[{'image':'a'},{'image':'b'}])
    frames=[];targets=[]
    for index,dose in enumerate(v2.original.DOSES):
        for f in ('a','b'):
            success=f=='a' and index==0
            frames.append({'frame_id':f,'dose_index':index,'session':'s','frame_success':success,
                'tp':int(success),'fp':0,'fn':int(not success),'best_iou':float(success),'best_confidence':.5})
            targets.append({'frame_id':f,'dose_index':index,'visible_annotation_box_fraction':1-dose,
                'best_iou':float(success),'best_overlap_confidence':.5,'matched_tp_iou_survivors_only':1. if success else None,'matched_tp_confidence_survivors_only':.5 if success else None})
    result,doses,transitions,paired=v2.analyze(frames,targets)
    assert result['source_frames']==2 and result['repeated_cases']==12
    assert result['random_seed'] is None and 'NOT APPLICABLE' in result['threshold_result']
    assert all(r['source_frames']==2 for r in doses+transitions)
    assert len(paired)==10 and transitions[-1]['regressed']==0
    assert v2.analyze(list(reversed(frames)),targets)==(result,doses,transitions,paired)


def test_v2_freeze_committed_before_inference():
    path=v2.OUT/'protocol.json'
    if not path.exists(): pytest.skip('Pre-freeze preparation')
    protocol,commit=v2.validate_freeze(v2.sha256_file(path))
    assert len(commit)==40 and protocol['dose_array']==list(v2.original.DOSES)
    assert protocol['statistics']['random_seed'] is None
    assert protocol['threshold_criterion'] is None


def test_actual_v2_artifact_replay():
    outcome=v2.OUT/'run_outcome.json'
    if not outcome.exists(): pytest.skip('Pre-execution freeze')
    from verify_phase22_occlusion_v2 import verify
    result=verify(v2.OUT)
    assert result['status']=='PASS' and result['frame_rows_replayed']==516
