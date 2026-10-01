#!/usr/bin/env python3
"""Authenticated geometry replay, separate Q95 follow-up freeze, gated execution."""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'src')]
import numpy as np
from PIL import Image
import run_phase25_occlusion_sweep as original
import run_phase22_representation_study as stage_a
from phase22_representation_transform import encode, atomic_write
from phase25_lib import Box, frame_metrics, iou_xyxy, sha256_file

OUT = ROOT / 'results/phase22_occlusion_v2'
RECOVERY = ROOT / 'results/phase22_occlusion_original_recovery'
ORIGINAL_RUNNER_SHA = '939b286418c66fa7a8ab39c6dc981b43324b5804f21f026ff1090a84e95c79a4'
STAGE_A_SHA = 'bd653fe22f90b2bf941909c5f96ceeeb9aab7f75dda0e58bbc9d7d785b4122bf'
STAGE_A_COMMIT = '3373aa8ed7138a4b09ff327aff2dc2640440509f'
RECOVERY_COMMIT = 'f090da03d20b2425c5addccb4d19117c8991bcc1'
TARGET_MASK_MANIFEST_SHA = '76f00fe7050e629a319b9b4d1fb65a0d45c6e9bd127f8f075b2d264d5a4d9554'
METHODS = ('scripts/run_phase22_occlusion_v2.py', 'scripts/run_phase25_occlusion_sweep.py',
           'scripts/run_phase22_representation_study.py', 'scripts/phase22_representation_transform.py',
           'scripts/phase25_lib.py', 'scripts/phase25_reconstruction_lock.py',
           'src/uav_safety/real_landing_dataset.py')


def write_json(path, value):
    stage_a.write_json(path, value)


def write_csv(path, rows, fields=None, compressed=False):
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=fields or list(rows[0]), lineterminator='\n')
    writer.writeheader(); writer.writerows(rows)
    content = buffer.getvalue().encode()
    if compressed:
        content = gzip.compress(content, mtime=0)
    atomic_write(path, content, hashlib.sha256(content).hexdigest())


def authenticate():
    if sha256_file(original.PROTOCOL) != original.PROTOCOL_SHA:
        raise ValueError('Actual original protocol unavailable or changed; no fallback')
    if sha256_file(ROOT / METHODS[1]) != ORIGINAL_RUNNER_SHA:
        raise ValueError('Recovered original runner changed')
    if original.DOSES != (0., .15, .30, .45, .60, .75):
        raise ValueError('Original authenticated dose array changed')
    provenance = json.loads((RECOVERY/'remote_provenance.json').read_text())
    if provenance['source_commit'] != RECOVERY_COMMIT:
        raise ValueError('Recovery source commit changed')
    for p, sha in provenance['file_sha256'].items():
        if sha256_file(ROOT/p) != sha:
            raise ValueError('Imported recovery bytes changed: '+p)
    return original.protected_rows()


def complete(rows, frames):
    expected = {(f['image'], i) for f in frames for i in range(len(original.DOSES))}
    keys = [(r['frame_id'], int(r['dose_index'])) for r in rows]
    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise ValueError('Duplicate or incomplete frame/dose population')


def build_views(source, work, q95=False):
    """No detector imports; recovered geometry and exact historical CSV schema."""
    frames = authenticate(); cases = []; masks = []
    for row in frames:
        raw = (source / 'images/test' / row['image']).read_bytes()
        label = (source / 'labels/test' / row['label']).read_bytes()
        expected = original.load_lock()['protected_test_files'][row['image']]
        if hashlib.sha256(raw).hexdigest() != expected['image_sha256'] or hashlib.sha256(label).hexdigest() != expected['label_sha256']:
            raise ValueError('Source bytes differ from historical source lock')
        canonical = encode(raw, 'HISTORICAL_Q95') if q95 else raw
        if q95 and canonical != encode(raw, 'HISTORICAL_Q95'):
            raise ValueError('Q95 transform nondeterministic')
        with Image.open(io.BytesIO(canonical)) as opened:
            pixels = np.asarray(opened.convert('RGB')).copy()
        height, width = pixels.shape[:2]
        targets = original.truth(source / 'labels/test' / row['label'])
        for index, dose in enumerate(original.DOSES):
            filename = row['image'] if index == 0 else Path(row['image']).stem + '.png'
            image_rel = f'dose_{index:02d}/images/test/{filename}'
            label_rel = f'dose_{index:02d}/labels/test/{row["label"]}'
            output, geometry = original.apply_mask(pixels, targets, dose)
            if index == 0:
                content = canonical
            else:
                buffer = io.BytesIO(); Image.fromarray(output).save(buffer, format='PNG', compress_level=9)
                content = buffer.getvalue()
            atomic_write(work / image_rel, content, hashlib.sha256(content).hexdigest(), image=True)
            atomic_write(work / label_rel, label, hashlib.sha256(label).hexdigest())
            with Image.open(work / image_rel) as opened:
                opened.load()
                if not np.array_equal(np.asarray(opened.convert('RGB')), output):
                    raise ValueError('Serialization changed treatment pixels')
            case = {'dose_index':index, 'nominal_occluded_box_fraction':dose,
                    'nominal_visible_box_fraction':1-dose, 'frame_id':row['image'],
                    'sequence':row['sequence'], 'frame_index':row['frame_index'],
                    'source_image_sha256':expected['image_sha256'], 'source_label_sha256':expected['label_sha256'],
                    'image_path':image_rel, 'image_sha256':sha256_file(work / image_rel),
                    'label_path':label_rel, 'label_sha256':hashlib.sha256(label).hexdigest(),
                    'width':width, 'height':height, 'target_count':len(targets)}
            if q95:
                mask_union = np.zeros((height,width), dtype=bool)
                for g in geometry:
                    mask_union[g['mask_y0']:g['mask_y1'],g['mask_x0']:g['mask_x1']] = True
                case.update(canonical_q95_sha256=hashlib.sha256(canonical).hexdigest(),
                    requested_dose=dose, session=row['sequence'],
                    achieved_image_mask_fraction=float(mask_union.mean()),
                    achieved_annotation_box_mask_fraction=sum(g['masked_box_pixels'] for g in geometry)/sum(g['box_pixel_area'] for g in geometry),
                    visible_annotation_box_fraction=sum(g['box_pixel_area']-g['masked_box_pixels'] for g in geometry)/sum(g['box_pixel_area'] for g in geometry))
            cases.append(case)
            masks.extend({'frame_id':row['image'], 'dose_index':index, **g} for g in geometry)
    complete(cases, frames)
    return cases, masks


def recover(args):
    authenticate()
    stage_a.verify_population(args.source, args.weights, args.archive)
    cases, masks = build_views(args.source, args.work, False)
    write_csv(RECOVERY / 'dose_image_manifest.csv', cases)
    write_csv(RECOVERY / 'target_mask_manifest.csv', masks)
    write_csv(RECOVERY / 'source_labels.csv', [{'frame_id':r['image'],
        'label_sha256':sha256_file(args.source/'labels/test'/r['label']),
        'label_text':(args.source/'labels/test'/r['label']).read_text()} for r in authenticate()])
    observed = sha256_file(RECOVERY / 'dose_image_manifest.csv')
    if observed != original.PRIOR_IMAGE_MANIFEST_SHA:
        raise ValueError('Historical 516-case manifest mismatch; never refresh expected SHA')
    if sha256_file(RECOVERY / 'target_mask_manifest.csv') != TARGET_MASK_MANIFEST_SHA:
        raise ValueError('Historical target-mask manifest mismatch')
    write_json(RECOVERY / 'recovery.json', {
        'status':'PASS', 'protocol_path':str(original.PROTOCOL.relative_to(ROOT)),
        'protocol_sha256':original.PROTOCOL_SHA, 'recovered_runner_path':METHODS[1],
        'recovered_runner_sha256':ORIGINAL_RUNNER_SHA,
        'recovered_from':'codex/all-work-publication-2026-09-30', 'recovery_source_commit':RECOVERY_COMMIT,
        'authentication':'Protocol digest matches previously recorded full digest; geometry/PNG encoding reproduces previously recorded full 516-case manifest digest.',
        'receipt_limit':'The lost original implementation-freeze receipt was not recovered. Runner is the publication-recovery implementation, authenticated by complete historical manifest reproduction, not by an unavailable older source receipt.',
        'original_status':'INCONCLUSIVE — CLEAN GATE FAILED — NO TREATMENT INFERENCE RUN',
        'doses':original.DOSES, 'source_frames':86, 'case_count':len(cases), 'target_case_count':len(masks),
        'historical_manifest_sha256':observed, 'target_mask_manifest_sha256':sha256_file(RECOVERY / 'target_mask_manifest.csv'),
        'source_labels_sha256':sha256_file(RECOVERY / 'source_labels.csv'),
        'detector_inference_run':False, 'all_image_hashes_and_decodes_verified':True,
        'search_scope':{'worktrees':'all three local worktrees inspected; matching candidate found in aegisland-fix',
            'branches_stashes_reflogs':'local branches, reflogs and empty stash inventoried',
            'transcripts':'previous supplied Codex transcripts inspected; protocol prefix/suffix and historical recovery corroborated',
            'temporary_directories':'available /workspace and /tmp candidate paths searched',
            'windows_paths':'Requested C:\\Users\\suhas paths are not mounted in this Linux execution environment; no Windows drive access available'},
        'threshold_criterion':'None in authenticated original protocol; no threshold may be selected after outcomes.',
        'statistics':'Descriptive paired source-frame changes only; no significance tests or population confidence intervals.'})
    print('Historical geometry replay PASS:', observed, flush=True)


def reference():
    clean = {r['condition']:r for r in original.read_csv(original.REFERENCE)}['clean']
    return {'recall':float(clean['baseline_recall']), 'map50':float(clean['baseline_map50'])}


def freeze(args):
    authenticate()
    recovery = json.loads((RECOVERY / 'recovery.json').read_text())
    if recovery['status'] != 'PASS' or recovery['historical_manifest_sha256'] != original.PRIOR_IMAGE_MANIFEST_SHA:
        raise ValueError('Historical geometry replay not authenticated')
    if sha256_file(ROOT / 'results/phase22_input_representation/protocol.json') != STAGE_A_SHA:
        raise ValueError('Stage A protocol changed')
    gate = json.loads((ROOT / 'results/phase22_input_representation/stage_a_gate.json').read_text())
    if gate['status'] != 'PASS' or not all(gate['checks'].values()):
        raise ValueError('Stage A gate must pass')
    stage_a.verify_population(args.source, args.weights, args.archive)
    protocol = {'study':'Phase 22 Controlled Occlusion Sweep v2 — Historical Q95 Representation',
        'separate_versioned_followup':True, 'schema_version':1,
        'original_protocol_path':str(original.PROTOCOL.relative_to(ROOT)), 'original_protocol_sha256':original.PROTOCOL_SHA,
        'recovery_source_branch':'codex/all-work-publication-2026-09-30','recovery_source_commit':RECOVERY_COMMIT,
        'remote_recovery_file_sha256':json.loads((RECOVERY/'remote_provenance.json').read_text())['file_sha256'],
        'original_runner_path':METHODS[1], 'original_runner_sha256':ORIGINAL_RUNNER_SHA,
        'original_implementation_receipt':'Lost earlier freeze receipt unavailable; recovered publication implementation authenticated by exact historical manifest replay.',
        'historical_geometry_manifest_sha256':original.PRIOR_IMAGE_MANIFEST_SHA,
        'historical_target_mask_manifest_sha256':TARGET_MASK_MANIFEST_SHA,
        'recovery_receipt_sha256':sha256_file(RECOVERY / 'recovery.json'),
        'stage_a_protocol_sha256':STAGE_A_SHA, 'stage_a_result_commit':STAGE_A_COMMIT,
        'stage_a_gate_sha256':sha256_file(ROOT / 'results/phase22_input_representation/stage_a_gate.json'),
        'checkpoint_release':original.RELEASE_URL, 'checkpoint_sha256':original.CHECKPOINT_SHA,
        'release_bundle_sha256':original.BUNDLE_SHA,
        'source_manifest_sha256':sha256_file(original.PROTECTED), 'source_archive_sha256':sha256_file(args.archive),
        'q95_transformation':'Pillow open original JPEG, convert RGB, save JPEG quality=95 with remaining Pillow defaults; decode canonical JPEG. Exact Stage A historical Q95 transform.',
        'q95_transform_implementation_sha256':sha256_file(ROOT / 'scripts/phase22_representation_transform.py'),
        'representation_chain':['SOURCE ORIGINAL JPEG','decode RGB','historical JPEG Q95 canonicalization','decode canonical Q95 pixels','original centered occlusion transform','lossless PNG treatment serialization (compress_level=9)'],
        'zero_dose_serialization':'Exact canonical Q95 JPEG bytes retained unchanged; nonzero doses PNG only; no lossy post-mask encoding.',
        'dose_array':original.DOSES, 'mask_geometry':'For each GT: floor top-left, ceil exclusive bottom-right, clip; scale each dimension sqrt(dose); round-half-up, minimum 1 for positive dose; floor centered offset; union RGB(127,127,127) masks. Achieved box fraction counts union inside every GT.',
        'settings':stage_a.SETTINGS, 'runtime':stage_a.runtime(),
        'zero_dose_gate':{'metrics':['recall','map50'], 'reference':reference(), 'reference_path':str(original.REFERENCE.relative_to(ROOT)), 'reference_sha256':sha256_file(original.REFERENCE), 'tolerance':.001},
        'matching_rules':'Same-class descending-confidence one-to-one IoU >= 0.50; unmatched predictions FP, unmatched targets FN.',
        'success_criterion':'All targets matched (FN=0); no false-positive restriction; confidence floor 0.001.',
        'primary_outcome':'Object recall by achieved visible annotation-box fraction.',
        'target_best_overlap':'Best same-class IoU over all predictions, zero if none; confidence of that prediction null if none. Ties: higher confidence then stable prediction index.',
        'frame_confidence':'Mean best-overlap confidence across targets; not maximum confidence of unrelated detections; survivor-only matched confidence separate.',
        'prediction_execution':'Recovered original runner model.predict per dose with original SETTINGS except workers; official model.val for zero-dose aggregate gate only. Original scoring execution preserved.',
        'statistics':{'unit':'source frame paired across six doses', 'source_frames':86, 'sessions':2,
            'plan':'Per-dose descriptive counts/means, paired changes from zero and adjacent-dose transitions. No significance tests or population confidence intervals.',
            'random_seed':None, 'randomness':'No random sampling, randomized masks, bootstrap or stochastic analysis in original plan; deterministic order.'},
        'threshold_criterion':None, 'threshold_result_policy':'NOT APPLICABLE — original protocol contains no preregistered threshold criterion; do not choose one after inspecting outcomes.',
        'output_schema':{'original':['frame_condition_metrics.csv','target_metrics.csv','prediction_boxes.csv.gz'],
            'extended_frame_fields':['frame_id','session','frame_index','dose_index','requested_dose','achieved_image_mask_fraction','achieved_annotation_box_mask_fraction','visible_annotation_box_fraction','source_sha256','canonical_q95_sha256','treatment_sha256','pred_count','best_iou','best_confidence','tp','fp','fn','frame_success'],
            'additional':['dose_image_manifest.csv','target_mask_manifest.csv','dose_response.csv','paired_transitions.csv','paired_frame_changes.csv','zero_dose_gate.json','analysis.json','run_manifest.json']},
        'failure_rules':'Missing original hash/method authentication, changed freeze/runtime/settings/source/model/Q95 hashes, failed Stage A or zero-dose gate, duplicate/missing cases or corrupt images: STOP, no treatment inference. Never overwrite earlier artifacts.',
        'limitations':['Exploratory retrospective evidence; these protected frames were previously inspected.', 'Two temporally dependent sequences; 516 cases are repeated views of 86 sources, not 516 independent samples.', 'Box visibility proxy, not physical pad surface visibility.', 'Single centered opaque synthetic intervention and fixed static detector; no general flight safety claim.', 'Detector confidence is a model score, not landing-safety probability.', 'Aggregate gate recall uses evaluator operating point; primary frame/target recall uses frozen confidence floor.'],
        'method_sha256':{p:sha256_file(ROOT / p) for p in METHODS}}
    write_json(OUT / 'protocol.json', protocol)
    print('V2 protocol SHA:', sha256_file(OUT / 'protocol.json'), flush=True)


def validate_freeze(expected_sha):
    path = OUT / 'protocol.json'
    if sha256_file(path) != expected_sha:
        raise ValueError('V2 protocol SHA changed')
    protocol = json.loads(path.read_text())
    authenticate()
    if protocol['dose_array'] != list(original.DOSES) or protocol['settings'] != stage_a.SETTINGS or protocol['runtime'] != stage_a.runtime():
        raise ValueError('Frozen V2 runtime/settings/doses changed')
    for p, sha in protocol['method_sha256'].items():
        if sha256_file(ROOT / p) != sha:
            raise ValueError('Frozen V2 method changed: ' + p)
    for p, sha in protocol['remote_recovery_file_sha256'].items():
        if sha256_file(ROOT/p) != sha:
            raise ValueError('Remote original provenance changed: '+p)
    for p, sha in [(original.REFERENCE, protocol['zero_dose_gate']['reference_sha256']),
                   (RECOVERY / 'recovery.json', protocol['recovery_receipt_sha256']),
                   (ROOT / 'results/phase22_input_representation/stage_a_gate.json', protocol['stage_a_gate_sha256'])]:
        if sha256_file(p) != sha:
            raise ValueError('Frozen evidence changed')
    # Require exact protocol AND implementation committed before running the detector.
    freeze_commit = subprocess.check_output(['git','log','-1','--format=%H','--','results/phase22_occlusion_v2/protocol.json'], cwd=ROOT, text=True).strip()
    if not freeze_commit:
        raise ValueError('V2 must be committed before inference')
    for p in ('results/phase22_occlusion_v2/protocol.json', *METHODS):
        blob = subprocess.check_output(['git','show',f'{freeze_commit}:{p}'], cwd=ROOT)
        if hashlib.sha256(blob).hexdigest() != sha256_file(ROOT / p):
            raise ValueError('V2 implementation not committed at freeze')
    return protocol, freeze_commit


def control_gate(actual, expected, tolerance=.001):
    checks = {k:math.isfinite(actual[k]) and 0 <= actual[k] <= 1 and abs(actual[k]-v) <= tolerance for k,v in expected.items()}
    return {'status':'PASS' if all(checks.values()) else 'FAIL', 'checks':checks,
            'actual':actual, 'expected':expected, 'delta':{k:actual[k]-v for k,v in expected.items()}, 'tolerance':tolerance}


def require_gates(gate):
    stage = json.loads((ROOT / 'results/phase22_input_representation/stage_a_gate.json').read_text())
    stage_a.require_treatment_gates(stage, gate)


def verify_cases(source, work, cases, masks):
    expected_cases, expected_masks = build_views(source, work, True)
    if expected_cases != cases or expected_masks != masks:
        raise ValueError('V2 manifest or mask geometry changed')
    complete(cases, authenticate())
    expected_paths = {c['image_path'] for c in cases}
    if {str(p.relative_to(work)) for p in work.glob('dose_*/images/test/*')} != expected_paths:
        raise ValueError('Unexpected or missing treatment images')


def score_case(case, targets, predictions, geometry):
    metrics, boxes = frame_metrics(targets, predictions, iou_threshold=.5)
    key = {k:case[k] for k in ('frame_id','sequence','frame_index','dose_index')}
    target_rows = []
    for ti, target in enumerate(targets):
        candidates = [(iou_xyxy(target,b), float(b.confidence), pi) for pi,b in enumerate(predictions) if b.class_id == target.class_id]
        best = max(candidates, key=lambda t:(t[0],t[1],-t[2]), default=None)
        tp = next((b for b in boxes if b['is_true_positive'] and b['matched_gt_index'] == ti), None)
        g = geometry[(case['frame_id'],int(case['dose_index']),ti)]
        target_rows.append({**key, 'target_index':ti,
            **{k:g[k] for k in ('achieved_target_box_mask_fraction','visible_annotation_box_fraction')},
            'detected':tp is not None, 'best_iou':best[0] if best else 0.,
            'best_overlap_confidence':best[1] if best else None,
            'matched_tp_iou_survivors_only':tp['match_iou'] if tp else None,
            'matched_tp_confidence_survivors_only':tp['confidence'] if tp else None})
    mean = lambda values: float(np.mean(values)) if values else None
    frame = {**key, **metrics, 'session':case['session'], 'requested_dose':case['requested_dose'],
        **{k:case[k] for k in ('achieved_image_mask_fraction','achieved_annotation_box_mask_fraction','visible_annotation_box_fraction')},
        'source_sha256':case['source_image_sha256'], 'canonical_q95_sha256':case['canonical_q95_sha256'],
        'treatment_sha256':case['image_sha256'], 'pred_count':len(predictions),
        'best_iou':mean([t['best_iou'] for t in target_rows]),
        'best_confidence':mean([t['best_overlap_confidence'] for t in target_rows if t['best_overlap_confidence'] is not None])}
    if frame['tp'] + frame['fn'] != len(targets) or frame['tp'] + frame['fp'] != len(predictions):
        raise ValueError('Frame counts do not reconcile')
    return frame, target_rows, [{**key, **b} for b in boxes]


def analyze(frames, targets):
    complete(frames, authenticate())
    by_key = {(r['frame_id'],int(r['dose_index'])):r for r in frames}
    ids = sorted({r['frame_id'] for r in frames})
    dose_rows = []; transitions = []; paired = []
    mean = lambda rows, k: float(np.mean([r[k] for r in rows if r[k] is not None])) if any(r[k] is not None for r in rows) else None
    for index, dose in enumerate(original.DOSES):
        group = [by_key[f,index] for f in ids]
        tg = [t for t in targets if int(t['dose_index']) == index]
        tp, fp, fn = (sum(r[k] for r in group) for k in ('tp','fp','fn'))
        dose_rows.append({'dose_index':index, 'requested_dose':dose, 'source_frames':len(group),
            'achieved_visible_annotation_box_fraction_mean':mean(tg,'visible_annotation_box_fraction'),
            'achieved_visible_annotation_box_fraction_min':min(t['visible_annotation_box_fraction'] for t in tg),
            'achieved_visible_annotation_box_fraction_max':max(t['visible_annotation_box_fraction'] for t in tg),
            'tp':tp,'fp':fp,'fn':fn,'object_recall':tp/(tp+fn),
            'frame_success_count':sum(r['frame_success'] for r in group),
            'frame_success_fraction':mean(group,'frame_success'), 'false_positives_per_frame':fp/len(group),
            'target_best_iou_mean':mean(tg,'best_iou'), 'best_overlap_confidence_mean':mean(tg,'best_overlap_confidence'),
            'matched_tp_iou_survivors_only_mean':mean(tg,'matched_tp_iou_survivors_only'),
            'matched_tp_confidence_survivors_only_mean':mean(tg,'matched_tp_confidence_survivors_only'),
            'matched_tp_confidence_survivor_count':sum(t['matched_tp_confidence_survivors_only'] is not None for t in tg)})
        if index:
            for left_index in sorted({0,index-1}):
                counts = Counter()
                for f in ids:
                    a,b = by_key[f,left_index], by_key[f,index]
                    counts['both_pass' if a['frame_success'] and b['frame_success'] else 'regressed' if a['frame_success'] else 'recovered' if b['frame_success'] else 'both_fail'] += 1
                transitions.append({'from_dose_index':left_index,'to_dose_index':index,'source_frames':len(ids),
                    **{k:counts[k] for k in ('both_pass','regressed','recovered','both_fail')}})
            for f in ids:
                a,b = by_key[f,0], by_key[f,index]
                paired.append({'frame_id':f,'session':b['session'],'dose_index':index,
                    **{k+'_minus_zero':b[k]-a[k] if b[k] is not None and a[k] is not None else None
                       for k in ('frame_success','tp','fp','fn','best_iou','best_confidence')}})
    analysis = {'status':'COMPLETE', 'source_frames':len(ids), 'repeated_cases':len(frames), 'source_sessions':2,
        'statistical_unit':'source frame paired across doses', 'statistical_plan':'Original descriptive plan; no significance tests or population confidence intervals.',
        'threshold_result':'NOT APPLICABLE — no preregistered threshold criterion in original protocol.',
        'random_seed':None, 'deterministic_analysis':True, 'dose_response':dose_rows,
        'zero_to_maximum':{'object_recall_change':dose_rows[-1]['object_recall']-dose_rows[0]['object_recall'],
            'best_iou_mean_change':dose_rows[-1]['target_best_iou_mean']-dose_rows[0]['target_best_iou_mean'],
            'best_overlap_confidence_mean_change':dose_rows[-1]['best_overlap_confidence_mean']-dose_rows[0]['best_overlap_confidence_mean']}}
    return analysis, dose_rows, transitions, paired


def run(args):
    protocol, freeze_commit = validate_freeze(args.protocol_sha)
    frames = stage_a.verify_population(args.source, args.weights, args.archive)
    if (OUT / 'run_manifest.json').exists():
        raise ValueError('Use a new version; never overwrite prior execution')
    # Verify all canonical Q95 bytes before the control; Stage A outputs remain untouched.
    for row in frames:
        expected = encode((args.source/'images/test'/row['image']).read_bytes(), 'HISTORICAL_Q95')
        if (args.canonical/'images/test'/row['image']).read_bytes() != expected:
            raise ValueError('Q95 canonical image changed')
        if (args.canonical/'labels/test'/row['label']).read_bytes() != (args.source/'labels/test'/row['label']).read_bytes():
            raise ValueError('Canonical labels changed')
    digest = original.inventory(args.canonical/'images/test', frames)
    if digest != original.load_lock()['condition_image_inventory_sha256']['clean']:
        raise ValueError('Historical Q95 canonical inventory differs')
    record = {'status':'PREFLIGHT_RECEIPT', 'outcome_record':'run_outcome.json', 'protocol_sha256':args.protocol_sha,
        'freeze_commit':freeze_commit, 'stage_a_result_commit':STAGE_A_COMMIT,
        'checkpoint_sha256':sha256_file(args.weights), 'q95_inventory_sha256':digest,
        'runtime':stage_a.runtime(), 'settings':stage_a.SETTINGS,
        'source_frames':86, 'expected_cases':516, 'treatment_inference_run':False}
    write_json(OUT / 'run_manifest.json', record)
    actual, _, _ = stage_a.evaluate(args.weights, args.canonical, frames, 'HISTORICAL_Q95')
    gate = control_gate(actual, protocol['zero_dose_gate']['reference'], protocol['zero_dose_gate']['tolerance'])
    write_json(OUT / 'zero_dose_gate.json', gate)
    if gate['status'] != 'PASS':
        write_json(OUT / 'run_outcome.json', {'status':'BLOCKED_ZERO_DOSE_GATE_FAILED','treatment_inference_run':False})
        return
    require_gates(gate)
    cases, masks = build_views(args.source, args.work, True)
    verify_cases(args.source, args.work, cases, masks)
    write_csv(OUT / 'dose_image_manifest.csv', cases); write_csv(OUT / 'target_mask_manifest.csv', masks)
    geometry = {(g['frame_id'],int(g['dose_index']),int(g['target_index'])):g for g in masks}
    from ultralytics import YOLO
    model = YOLO(str(args.weights))
    if model.names != {0:'landing_pad'}:
        raise ValueError('Checkpoint class differs')
    outcome_frames=[]; outcome_targets=[]; outcome_boxes=[]
    for index in range(6):
        require_gates(gate)
        group = [c for c in cases if c['dose_index'] == index]
        results = model.predict(source=[str(args.work/c['image_path']) for c in group],
            **{k:v for k,v in original.SETTINGS.items() if k != 'workers'}, stream=True, verbose=False)
        for case, result in zip(group, results, strict=True):
            if Path(result.path).name != Path(case['image_path']).name:
                raise ValueError('Prediction frame order changed')
            predictions=[]
            if result.boxes is not None:
                for coords, cls, score in zip(result.boxes.xyxyn.cpu().numpy(),result.boxes.cls.cpu().numpy(),result.boxes.conf.cpu().numpy(),strict=True):
                    if not all(math.isfinite(float(v)) for v in (*coords,cls,score)) or cls != int(cls) or not 0 <= score <= 1:
                        raise ValueError('Invalid raw prediction')
                    xyxy = [max(0.,min(1.,float(v))) for v in coords]
                    if xyxy[0] > xyxy[2] or xyxy[1] > xyxy[3]:
                        raise ValueError('Inverted raw prediction')
                    predictions.append(Box(int(cls),*xyxy,float(score)))
            truth = original.truth(args.work/case['label_path'])
            frame, target, boxes = score_case(case, truth, predictions, geometry)
            outcome_frames.append(frame); outcome_targets.extend(target); outcome_boxes.extend(boxes)
        print(f'Completed dose {index}: {len(group)} source frames', flush=True)
    complete(outcome_frames, frames)
    if len(outcome_targets) != len(masks):
        raise ValueError('Target population incomplete')
    write_csv(OUT / 'frame_condition_metrics.csv', outcome_frames)
    write_csv(OUT / 'target_metrics.csv', outcome_targets)
    write_csv(OUT / 'prediction_boxes.csv.gz', outcome_boxes, fields=['frame_id','sequence','frame_index','dose_index','prediction_index','class_id','x0','y0','x1','y1','confidence','matched_gt_index','match_iou','is_true_positive'], compressed=True)
    analysis, doses, transitions, paired = analyze(outcome_frames, outcome_targets)
    write_json(OUT / 'analysis.json', analysis); write_csv(OUT / 'dose_response.csv', doses)
    write_csv(OUT / 'paired_transitions.csv', transitions); write_csv(OUT / 'paired_frame_changes.csv', paired)
    outputs = [p for p in OUT.iterdir() if p.is_file() and p.name not in ('run_manifest.json','run_outcome.json')]
    write_json(OUT / 'run_outcome.json', {**record, 'status':'COMPLETE', 'treatment_inference_run':True,
        'frame_case_count':len(outcome_frames), 'target_case_count':len(outcome_targets), 'prediction_count':len(outcome_boxes),
        'output_sha256':{p.name:sha256_file(p) for p in sorted(outputs)}, 'zero_dose_gate':gate})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('recover','freeze','run'))
    p.add_argument('--source',type=Path,required=True);p.add_argument('--weights',type=Path,required=True)
    p.add_argument('--archive',type=Path,required=True);p.add_argument('--work',type=Path,required=True)
    p.add_argument('--canonical',type=Path);p.add_argument('--protocol-sha')
    args=p.parse_args()
    {'recover':recover,'freeze':freeze,'run':run}[args.command](args)


if __name__ == '__main__':
    main()
