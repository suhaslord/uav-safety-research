#!/usr/bin/env python3
"""Build the public detector follow-up page from finalized verified evidence."""
import html
import csv
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
RESULTS=ROOT/'results/phase22_occlusion_v2'
SITE=ROOT/'deploy/vercel'


def build():
    outcome=json.loads((RESULTS/'run_outcome.json').read_text())
    replay=json.loads((RESULTS/'artifact_replay.json').read_text())
    if outcome['status']!='COMPLETE' or replay['status']!='PASS':
        raise ValueError('Only finalized verified v2 results may be published')
    analysis=json.loads((RESULTS/'analysis.json').read_text())
    protocol=json.loads((RESULTS/'protocol.json').read_text())
    stage_a=json.loads((ROOT/'results/phase22_input_representation/stage_a_gate.json').read_text())
    if stage_a['status']!='PASS': raise ValueError('Stage A not verified')
    doses=analysis['dose_response']; first,last=doses[0],doses[-1]
    with (ROOT/'results/phase22_input_representation/frame_metrics.csv').open(newline='') as f:
        q95_val_success=sum(r['success']=='True' for r in csv.DictReader(f) if r['representation']=='HISTORICAL_Q95')
    pct=lambda v:f'{100*v:.1f}%'
    table=''.join(f'<tr><td>{pct(r["requested_dose"])}</td><td>{pct(r["achieved_visible_annotation_box_fraction_mean"])}</td><td>{r["tp"]}/86 · {pct(r["object_recall"])}</td><td>{r["frame_success_count"]}/86</td><td>{r["false_positives_per_frame"]:.2f}</td><td>{r["target_best_iou_mean"]:.3f}</td><td>{r["best_overlap_confidence_mean"]:.3f}</td></tr>' for r in doses)
    base='https://github.com/suhaslord/uav-safety-research'
    prefix=(SITE/'reproduce.html').read_text().split('  <main>')[0]
    prefix=prefix.replace('Reproduce the evidence — AegisLand','Phase 22 detector follow-ups — AegisLand').replace('https://aegisland-research-cockpit.vercel.app/reproduce/','https://aegisland-research-cockpit.vercel.app/phase22-detector-study/').replace('Verify the Phase 25 Failure Atlas evidence and see which AegisLand claims are still pending.','Verify the separate original failed control, Q95 representation study, and occlusion v2 detector follow-up.')
    prefix=prefix.replace('</head>','<style>.dose-figure{margin:30px 0}.dose-figure img{display:block;width:100%;height:auto}.dose-figure figcaption{font-size:13px;color:#526771;line-height:1.6}.study-hash{overflow-wrap:anywhere}.study-table{overflow:auto}</style></head>')
    content=f'''  <main id="evidence">
    <section class="proof-intro"><span class="kicker">PHASE 22 / SEPARATE DETECTOR FOLLOW-UPS</span><h1>Representation first. Occlusion second.</h1><p>The exact recovered detector was evaluated on 86 protected frames from two videos. These retrospective detector studies have their own records; the frozen Phase 22 simulation verdict remains separate.</p>
    <div class="proof-grid" aria-label="Three separate experimental records"><article><span>ORIGINAL RAW-SOURCE SWEEP</span><strong>INCONCLUSIVE</strong><p>Clean gate FAILED: raw mAP50 0.423908 versus historical 0.426627, beyond tolerance 0.001. No nonzero treatment inference ran.</p></article><article><span>STAGE A / REPRESENTATION</span><strong>PASS</strong><p>Q95 reproduced all four historical clean metrics. 86 × five representations = 430 cases. Raw and Q95 had zero binary success transitions; raw and lossless PNG predictions were identical.</p></article><article><span>SEPARATE OCCLUSION V2</span><strong>COMPLETE · CLEAN GATE PASS</strong><p>86 × six frozen centered-mask doses = 516 cases. Masks use Q95 canonical pixels; nonzero treatments are lossless PNGs. This result does not change the original failed sweep.</p></article></div></section>
    <section class="proof-section"><span class="kicker">DESCRIPTIVE DOSE RESPONSE</span><h2>{first['tp']} to {last['tp']} detected targets across the grid.</h2><p>Object recall changed from {pct(first['object_recall'])} at zero dose to {pct(last['object_recall'])} at nominal 75% occlusion. Best target IoU changed from {first['target_best_iou_mean']:.3f} to {last['target_best_iou_mean']:.3f}; best-overlap confidence from {first['best_overlap_confidence_mean']:.3f} to {last['best_overlap_confidence_mean']:.3f}. Each dose contains the same 86 source frames.</p>
    <figure class="dose-figure"><img src="/media/phase22-occlusion-v2.png" alt="Four descriptive curves showing object recall, all-target frame success, best target IoU, and best-overlap confidence against achieved visible annotation-box fraction."><figcaption>Annotation-box visibility is a pixel proxy. Lines connect the six frozen interventions; they do not identify a population or safety threshold.</figcaption></figure>
    <div class="study-table"><table class="proof-table"><thead><tr><th>Requested occlusion</th><th>Mean box visibility</th><th>Object recall</th><th>Frame success</th><th>FP/frame</th><th>Best IoU</th><th>Best-overlap confidence</th></tr></thead><tbody>{table}</tbody></table></div><p>Frame success requires all targets to match and permits false positives. This recall uses the frozen confidence floor 0.001 and IoU ≥ 0.50. Aggregate clean-gate recall uses the official evaluator's operating point and is a different measure.</p><p>V2 retains the original runner's per-dose prediction path; Stage A exported a validation pass. Zero-dose frame success is {first['tp']}/86 in v2 and {q95_val_success}/86 in Stage A's Q95 validation pass. These different execution passes retain their original preprocessing defaults; this count difference is not an additional representation transition.</p></section>
    <section class="proof-section proof-muted"><span class="kicker">EVIDENCE BOUNDARY</span><h2>86 paired sources. Two dependent videos.</h2><p>516 cases are repeated views of 86 source frames. The original plan supports descriptive paired changes from dose zero and adjacent-dose transitions, with no population significance tests or confidence intervals. No preregistered threshold criterion exists: threshold finding is NOT APPLICABLE.</p><p>Best-overlap confidence is the score of the prediction with greatest target overlap. Matched-TP IoU and confidence are survivor-only summaries in the downloadable tables. Confidence is a model score, not a probability of a safe landing. Annotation-box visibility is not measured physical pad surface visibility. Previously inspected frames and this single synthetic intervention do not establish flight safety or independent-session generalization.</p></section>
    <section class="proof-section"><span class="kicker">PROVENANCE / REPLAY</span><h2>Check the frozen records.</h2><p class="study-hash">Recovery source: <a href="{base}/commit/{protocol['recovery_source_commit']}">{protocol['recovery_source_commit']}</a>. Only its ten research files were imported; the old website branch was not merged.</p><p class="study-hash">Original protocol SHA:<br><code>{protocol['original_protocol_sha256']}</code></p><p class="study-hash">Separate v2 protocol SHA:<br><code>{outcome['protocol_sha256']}</code></p><p>The lost original implementation/runtime receipt remains unavailable. The recovered publication runner reproduces both complete historical geometry manifests. V2 records its own Stage A CPU runtime and fresh clean gate.</p><div class="proof-links"><a href="{base}/tree/main/results/phase22_occlusion_v2">All v2 tables and raw boxes ↗</a><a href="{base}/blob/main/docs/phase22_occlusion_v2.md">Reproduction instructions ↗</a><a href="{base}/tree/main/results/phase22_input_representation">Stage A evidence ↗</a><a href="{base}/blob/main/results/phase25_occlusion_sweep_recovered/summary.md">Original failed sweep ↗</a><a href="/phases/phase22/">Separate simulation record →</a></div></section>
    </main><footer><span>AegisLand · retrospective detector evidence</span><a href="/">Research home</a></footer></body></html>'''
    (SITE/'phase22-detector-study.html').write_text(prefix+content)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(2,2,figsize=(10,6.4),constrained_layout=True)
    x=[r['achieved_visible_annotation_box_fraction_mean'] for r in doses]
    for ax,(key,title) in zip(axes.flat,[('object_recall','Object recall'),('frame_success_fraction','All-target frame success'),('target_best_iou_mean','Best target IoU'),('best_overlap_confidence_mean','Best-overlap confidence')]):
        ax.plot(x,[r[key] for r in doses],'-o',color='#176eb7',linewidth=2,markersize=5)
        ax.set(xlabel='Achieved visible annotation-box fraction',ylabel=title,xlim=(.2,1.04),ylim=(0,1));ax.grid(alpha=.15)
    fig.suptitle('Phase 22 occlusion v2 · 86 paired sources · descriptive evidence',fontsize=13)
    fig.savefig(RESULTS/'dose_response.png',dpi=180);plt.close(fig)
    shutil.copyfile(RESULTS/'dose_response.png',SITE/'media/phase22-occlusion-v2.png')
    print('Built finalized Phase 22 detector evidence page and dose-response figure.')


if __name__=='__main__': build()
