/* Offline reliability prototype: frozen Phase 25 records only, not flight control. */
(() => {
  'use strict';
  const CONDITIONS = ['clean','blur','low_light','noise','occlusion','mixed'];
  const MODELS = ['baseline','phase23'];
  const ID = /^land_pad2?__\d+\.jpg$/;
  const name = (c) => c.model + '|' + c.condition + '|' + c.frame;

  function boxValid(b,degenerate=false) {
    return Array.isArray(b) && b.length===4
      && b.every(x => typeof x==='number' && Number.isFinite(x) && x>=0 && x<=1)
      && (degenerate ? b[2]>=b[0] && b[3]>=b[1] : b[2]>b[0] && b[3]>b[1]);
  }
  function decide(score,cutoff) {
    if (typeof score!=='number' || !Number.isFinite(score) || score<0 || score>1
      || typeof cutoff!=='number' || !Number.isFinite(cutoff) || cutoff<=0 || cutoff>1)
      throw new Error('Invalid score/cutoff');
    return score>=cutoff; // no ground truth is read by this runtime decision
  }
  function validate(payload) {
    if (!payload || payload.schema!=='aegisland.phase25.retrospective-demo.v1'
      || payload.status!=='previously_tested_demo_only'
      || payload.new_holdout!==false || payload.threshold_selected!==false
      || payload.flight_safety_validated!==false || payload.source_frames!==86
      || payload.source_videos!==2 || payload.cases_total!==1032
      || payload.any_correct_top_wrong_count!==135
      || JSON.stringify(payload.models)!==JSON.stringify(MODELS)
      || JSON.stringify(payload.conditions)!==JSON.stringify(CONDITIONS)
      || !payload.source_sha256 || Object.keys(payload.source_sha256).length!==4
      || !Array.isArray(payload.cases) || payload.cases.length!==1032)
      throw new Error('Unverified retrospective record');
    const cases=new Map(), groups=new Map(), truth=new Map();
    let mismatches=0;
    for (const c of payload.cases) {
      const k=name(c), q=c.condition+'|'+c.frame, group=c.model+'|'+c.condition;
      if (!MODELS.includes(c.model) || !CONDITIONS.includes(c.condition) || !ID.test(c.frame)
        || !['land_pad','land_pad2'].includes(c.sequence)
        || c.sequence!==c.frame.split('__')[0]
        || typeof c.score!=='number' || !Number.isFinite(c.score) || c.score<0 || c.score>1
        || typeof c.top_correct!=='boolean' || typeof c.any_match_success!=='boolean'
        || typeof c.top_iou!=='number' || !Number.isFinite(c.top_iou) || c.top_iou<0 || c.top_iou>1
        || !Array.isArray(c.truth_boxes) || !c.truth_boxes.length || !c.truth_boxes.every(b=>boxValid(b))
        || (c.top_box!==null && (!boxValid(c.top_box,true) || !Number.isInteger(c.top_index) || c.top_index<0))
        || (c.top_box===null && (c.top_index!==null || c.score!==0 || c.top_correct || c.top_iou!==0))
        || c.top_correct!==(c.top_box!==null && c.top_iou>=0.5) || cases.has(k))
        throw new Error('Contradictory or missing saved case');
      const gt=JSON.stringify(c.truth_boxes);
      if (truth.has(q) && truth.get(q)!==gt) throw new Error('Model annotations disagree');
      truth.set(q,gt);
      cases.set(k,c);
      if (!groups.has(group)) groups.set(group,new Set());
      groups.get(group).add(c.frame);
      mismatches += Number(c.any_match_success && !c.top_correct);
    }
    if (mismatches!==135 || groups.size!==12 || [...groups.values()].some(v=>v.size!==86))
      throw new Error('Unexpected original data inventory');
    const ref=[...groups.get('baseline|clean')].sort().join('|');
    for (const group of groups.values()) if ([...group].sort().join('|')!==ref)
      throw new Error('Different source frames between models/conditions');
    function counts(model,condition) {
      const rows=payload.cases.filter(c=>c.model===model&&c.condition===condition);
      return [rows.filter(c=>c.any_match_success).length,rows.filter(c=>c.top_correct).length];
    }
    if (counts('phase23','occlusion').join(',')!=='43,23'
      || counts('phase23','mixed').join(',')!=='44,22')
      throw new Error('Published top-confidence audit does not reconcile');
    return {cases,groups,frames:[...groups.get('baseline|clean')].sort(),payload};
  }
  function describe(rows,cutoff) {
    if (!rows.length) throw new Error('Empty selected group');
    const accepted=rows.filter(c=>decide(c.score,cutoff));
    const wrong=accepted.filter(c=>!c.top_correct).length;
    return {total:rows.length, accepted:accepted.length, wrong,
      alwaysWrong:rows.filter(c=>!c.top_correct).length,
      coverage:accepted.length/rows.length,
      error:accepted.length?wrong/accepted.length:null};
  }
  if (typeof module!=='undefined' && module.exports) {
    module.exports={CONDITIONS,MODELS,boxValid,decide,validate,describe};
    return;
  }
  if (typeof document==='undefined') return;
  const app=document.getElementById('prototype-app');
  if (!app) return;
  const lookup={};
  for (const id of ['prototype-status','model-select','condition-select','cutoff','cutoff-value',
    'frame-select','frame-label','sequence-label','prototype-image','frame-image','image-message',
    'predicted-overlay','truth-overlay','decision','decision-explainer','confidence-score',
    'localization-result','iou-score','accepted-count','accepted-total','coverage-rate',
    'wrong-count','wrong-rate','baseline-errors','previous-frame','next-frame'])
    lookup[id]=document.getElementById(id);
  let data=null, frame='', imageRequest=0;
  const percent=n=>n===null?'—':(100*n).toFixed(1)+'%';
  function place(el,b) {
    el.style.left=(b[0]*100)+'%';el.style.top=(b[1]*100)+'%';
    el.style.width=((b[2]-b[0])*100)+'%';el.style.height=((b[3]-b[1])*100)+'%';
  }
  function drawImage(record) {
    const request=++imageRequest, root=lookup['frame-image'];
    const image=lookup['prototype-image'].cloneNode(false);
    lookup['prototype-image'].replaceWith(image);
    lookup['prototype-image']=image;
    const selected=lookup['predicted-overlay'],truth=lookup['truth-overlay'];
    root.querySelectorAll('.truth-extra').forEach(n=>n.remove());
    selected.hidden=true;truth.hidden=true;image.hidden=true;
    lookup['image-message'].hidden=false;
    lookup['image-message'].textContent='Loading recorded frame…';
    image.alt='Saved '+record.condition.replace('_',' ')+' KIOS frame '+record.frame+
      ', top-ranked detector box and original landing-pad annotation';
    image.onload=()=>{
      if(request!==imageRequest)return;
      root.style.aspectRatio=image.naturalWidth+'/'+image.naturalHeight;
      image.hidden=false;lookup['image-message'].hidden=true;
      if(record.top_box){place(selected,record.top_box);selected.hidden=false;}
      record.truth_boxes.forEach((b,i)=>{
        const node=i===0?truth:truth.cloneNode(true);
        if(i){node.removeAttribute('id');node.classList.add('truth-extra');root.append(node);}
        place(node,b);node.hidden=false;
      });
    };
    image.onerror=()=>{
      if(request!==imageRequest)return;
      image.hidden=true;selected.hidden=true;truth.hidden=true;
      lookup['image-message'].hidden=false;
      lookup['image-message'].textContent='Archived image unavailable. Saved measurements remain visible.';
    };
    image.src='/media/phase25/'+record.condition+'/'+record.frame;
  }
  function fail() {
    app.hidden=true;lookup['prototype-status'].hidden=false;
    lookup['prototype-status'].textContent='The archived prototype data could not be verified or loaded. See Failure Atlas for the preserved research record.';
  }
  function render(refreshImage=true) {
    if (!data)return;
    const model=lookup['model-select'].value, condition=lookup['condition-select'].value;
    const cutoff=Number(lookup.cutoff.value);
    const record=data.cases.get(model+'|'+condition+'|'+frame);
    if(!record){fail();return;}
    const accepted=decide(record.score,cutoff);
    lookup['cutoff-value'].textContent=cutoff.toFixed(2);
    lookup.decision.replaceChildren();
    const chip=document.createElement('span');
    chip.className=accepted?'accepted':'abstained';
    chip.textContent=accepted?'ACCEPT':'ABSTAIN';
    lookup.decision.append(chip);
    lookup['decision-explainer'].textContent=accepted
      ? 'The saved top detection passes this illustrative confidence cutoff.'
      : 'The detector score is below the cutoff, so the prediction is withheld.';
    lookup['confidence-score'].textContent=record.top_box?record.score.toFixed(4):'0.0000 · no detection';
    lookup['localization-result'].textContent=!record.top_box?'No top box':record.top_correct?'Yes':'No';
    lookup['iou-score'].textContent=record.top_box?record.top_iou.toFixed(3):'—';
    lookup['frame-label'].textContent=record.frame;
    lookup['sequence-label'].textContent=record.sequence==='land_pad2'?'Video 2':'Video 1';
    lookup['frame-select'].value=frame;
    const rows=data.payload.cases.filter(c=>c.model===model&&c.condition===condition);
    const result=describe(rows,cutoff);
    lookup['accepted-count'].textContent=String(result.accepted);
    lookup['accepted-total'].textContent='of '+result.total+' frames';
    lookup['coverage-rate'].textContent=percent(result.coverage);
    lookup['wrong-count'].textContent=String(result.wrong);
    lookup['wrong-rate'].textContent=result.error===null
      ? 'None accepted · rate undefined' : percent(result.error)+' of accepted';
    lookup['baseline-errors'].textContent=result.alwaysWrong+' / '+result.total;
    if(refreshImage)drawImage(record);
  }
  function step(delta) {
    const i=data.frames.indexOf(frame);
    frame=data.frames[(i+delta+data.frames.length)%data.frames.length];
    render();
  }
  const url=new URL('prototype-cases.json?v=1',document.currentScript?.src||location.href);
  fetch(url).then(r=>{if(!r.ok)throw Error('missing');return r.json();})
    .then(payload=>{
      data=validate(payload);frame=data.frames[0];
      lookup['frame-select'].replaceChildren();
      data.frames.forEach(id=>{
        const option=document.createElement('option');
        option.value=id;option.textContent=id.replace('.jpg','');
        lookup['frame-select'].append(option);
      });
      lookup['model-select'].addEventListener('change',()=>render());
      lookup['condition-select'].addEventListener('change',()=>render());
      lookup.cutoff.addEventListener('input',()=>render(false));
      lookup['frame-select'].addEventListener('change',()=>{
        const v=lookup['frame-select'].value;
        if(data.frames.includes(v)){frame=v;render();}
      });
      lookup['previous-frame'].addEventListener('click',()=>step(-1));
      lookup['next-frame'].addEventListener('click',()=>step(1));
      lookup['prototype-status'].hidden=true;app.hidden=false;
      render();
    }).catch(fail);
})();
