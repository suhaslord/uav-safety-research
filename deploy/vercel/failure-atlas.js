(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const names = {clean:'Clean', blur:'Blur', low_light:'Low light', noise:'Noise', occlusion:'Occlusion', mixed:'Mixed'};
  const els = Object.fromEntries(['frame-title','frame-sequence','frame-range','prev-frame','next-frame','view-mode','conditions','show-gt','show-baseline','local-files','local-folder','image-note','comparison','baseline-verdict','baseline-scene','frame-image','scene-placeholder','box-layer','scene-index','baseline-metrics','show-phase23','phase23-verdict','phase23-metrics','phase23-box-layer','phase23-scene','phase23-frame-image','phase23-image-placeholder','phase23-image-badge','phase23-aggregate-condition','phase23-map50','phase23-recall','case-label','case-features','filter-condition','filter-outcome','filter-confidence','small-target','match-count','matrix','scatter','point-detail','show-wrong','scatter-count','evidence-dialog','close-evidence'].map(id=>[id,$(id)]));
  let data, byKey, phase23ByKey, index=0, condition='clean', smallLimit=0, wrongOnly=false, plotPoints=[], localImages=new Map(), imageRequest=0;
  const key=(id,c)=>`${id}|${c}`;
  const value=(x,d=2)=>Number(x).toFixed(d);
  const caseNow=()=>byKey.get(key(data.frame_ids[index],condition));
  const positions=(box)=>({left:`${box[0]*100}%`,top:`${box[1]*100}%`,width:`${Math.max(0,(box[2]-box[0])*100)}%`,height:`${Math.max(0,(box[3]-box[1])*100)}%`});
  function imageNote(item,image,local){
    const loaded=localImages.size;
    const countText=loaded?` ${loaded} local frame-condition image${loaded===1?' is':'s are'} loaded.`:'';
    if(local)return `Local source image loaded for this frame. Images stay in this browser; image hashes are not checked here.${countText}`;
    if(image)return `Verified ${names[condition].toLowerCase()} frame image loaded for ${item.id}. ${countText}`;
    return `The verified image for ${item.id} under ${names[condition]} could not be loaded. Reload this view to retry.${countText}`;
  }
  function showImageFailure(source,request){
    if(request!==imageRequest||els['frame-image'].getAttribute('src')!==source)return;
    els['frame-image'].hidden=true;els['box-layer'].hidden=true;els['scene-index'].hidden=true;
    els['scene-placeholder'].hidden=false;
    els['scene-placeholder'].textContent='This frame image could not be decoded. Reload the page to retry.';
    els['image-note'].textContent='Image failed to load. The measured results remain available; reload the page to retry.';
  }
  function syncPhase23Image(source,item){
    const scene=els['phase23-scene'],placeholder=els['phase23-image-placeholder'],badge=els['phase23-image-badge'];
    scene.classList.toggle('has-image',Boolean(source));
    placeholder.hidden=Boolean(source);
    badge.textContent=source?'Same reconstructed input · measured predictions':'Source image unavailable · measured table retained';
    placeholder.textContent=`Loading verified ${names[condition].toLowerCase()} source image for ${item.id}…`;
    let frameImage=els['phase23-frame-image'];
    frameImage.hidden=!source;
    els['phase23-box-layer'].hidden=!source;
    if(!source){frameImage.removeAttribute('src');frameImage.alt='';return;}
    if(frameImage.getAttribute('src')!==source){
      const replacement=frameImage.cloneNode(false);replacement.removeAttribute('src');
      frameImage.replaceWith(replacement);els['phase23-frame-image']=replacement;frameImage=replacement;
    }
    frameImage.alt=`${names[condition]} source image for ${item.id}; Phase 23 measured outcomes are available in the linked paired frame tables`;
    frameImage.onerror=()=>{
      if(frameImage.getAttribute('src')!==source)return;
      frameImage.hidden=true;els['phase23-box-layer'].hidden=true;scene.classList.remove('has-image');placeholder.hidden=false;
      placeholder.textContent='This source image could not be decoded. Reload the page to retry; paired frame outcomes remain available in the linked tables.';
      badge.textContent='Image unavailable · measured table retained';
    };
    if(frameImage.getAttribute('src')!==source)frameImage.src=source;
    else if(frameImage.complete&&frameImage.naturalWidth===0)frameImage.onerror();
  }
  function drawCase(){
    const item=caseNow();if(!item)return;
    const robust=phase23ByKey.get(key(item.id,condition));
    els['phase23-verdict'].textContent=robust.pass?'TARGET MATCHED':'TARGET MISSED';
    els['phase23-verdict'].classList.toggle('failed',!robust.pass);
    els['phase23-metrics'].replaceChildren();
    for(const [label,number] of [['TP',robust.tp],['FP',robust.fp],['FN',robust.fn],['BEST IoU',value(robust.iou)],['TOP SCORE',value(robust.score)]]){
      const span=document.createElement('span');span.textContent=label;const b=document.createElement('b');b.textContent=number;span.append(b);els['phase23-metrics'].append(span);
    }
    els['phase23-box-layer'].replaceChildren();
    if(els['show-gt'].checked)for(const box of robust.gt)addBox(box,'gt','GT',true,'phase23-box-layer');
    if(els['show-phase23'].checked){
      const visible=[...robust.boxes.slice(0,12)];
      for(const box of robust.boxes)if(box[6]&&!visible.includes(box))visible.push(box);
      for(const box of visible)addBox(box,box[6]?'tp':'fp',`${box[6]?'TP':'FP'} ${value(box[4])}`,Boolean(box[6]),'phase23-box-layer');
    }
    els['phase23-scene'].title=`${robust.count} Phase 23 predictions scored at 0.001 or above; display is a subset, all predictions determine the metrics.`;
    els['frame-title'].textContent=`FRAME ${String(index+1).padStart(3,'0')} / 086`;
    els['frame-sequence'].textContent=`${item.id.replace('.jpg','')} · ${names[condition].toUpperCase()}`;
    els['frame-range'].value=index;
    els['baseline-verdict'].textContent=item.pass?'TARGET MATCHED':'TARGET MISSED';
    els['baseline-verdict'].classList.toggle('failed',!item.pass);
    els['baseline-metrics'].replaceChildren();
    for(const [label,number] of [['TP',item.tp],['FP',item.fp],['FN',item.fn],['BEST IoU',value(item.iou)],['TOP SCORE',value(item.score)]]){
      const span=document.createElement('span');span.textContent=label;const b=document.createElement('b');b.textContent=number;span.append(b);els['baseline-metrics'].append(span);
    }
    els['case-label'].textContent=item.pass?'BASELINE TARGET MATCHED':'BASELINE TARGET MISSED';
    els['case-label'].classList.toggle('pass',item.pass);
    els['scene-index'].textContent=`${item.id} / ${names[condition]}`;
    const aggregate=data.phase23_condition_aggregates[condition];
    els['phase23-aggregate-condition'].textContent=names[condition];
    els['phase23-map50'].textContent=`${(aggregate.map50*100).toFixed(1)}%`;
    els['phase23-recall'].textContent=`${(aggregate.recall*100).toFixed(1)}%`;
    const local=localImages.get(key(item.id,condition));
    const image=local||`/media/phase25/${condition}/${item.id}`;
    syncPhase23Image(image,item);
    els['frame-image'].hidden=!image;
    els['scene-placeholder'].hidden=Boolean(image);
    els['box-layer'].hidden=!image;els['scene-index'].hidden=!image;
    const request=++imageRequest;
    if(image){
      els['scene-placeholder'].textContent='Loading verified frame image…';
      let frameImage=els['frame-image'];
      if(frameImage.getAttribute('src')!==image){
        const replacement=frameImage.cloneNode(false);replacement.removeAttribute('src');
        frameImage.replaceWith(replacement);els['frame-image']=replacement;frameImage=replacement;
      }
      frameImage.alt=`Verified reconstructed ${names[condition].toLowerCase()} view of ${item.id}${local?' loaded from a local file':''}`;
      frameImage.onerror=()=>showImageFailure(image,request);
      if(frameImage.getAttribute('src')!==image)frameImage.src=image;
      else if(frameImage.complete&&frameImage.naturalWidth===0)showImageFailure(image,request);
    }else{els['frame-image'].removeAttribute('src');els['frame-image'].alt='';els['scene-placeholder'].textContent='Loading verified frame image…';}
    els['image-note'].textContent=imageNote(item,image,Boolean(local));
    els['box-layer'].replaceChildren();
    if(els['show-gt'].checked)for(const box of item.gt) addBox(box,'gt','GT');
    const visible=[];
    if(els['show-baseline'].checked){
      visible.push(...item.boxes.slice(0,12));
      for(const box of item.boxes)if(box[6]&&!visible.includes(box))visible.push(box);
      // Keep the view legible while preserving every matched target; metrics still use all predictions.
      let falsePositiveLabels=0;
      for(const box of visible){
        const truePositive=Boolean(box[6]);
        const showLabel=truePositive||falsePositiveLabels<4;
        if(!truePositive)falsePositiveLabels++;
        addBox(box,truePositive?'tp':'fp',`${truePositive?'TP':'FP'} ${value(box[4])}`,showLabel);
      }
    }
    els['baseline-scene'].title=`${item.count} predictions scored at 0.001 or above; ${visible.length} boxes are drawn. Metrics use every prediction.`;
    els['case-features'].textContent=`Target area ${(item.size*100).toFixed(3)}% · Brightness ${value(item.brightness)} · Sharpness ${value(item.sharpness,4)} · ${item.count} detections; ${visible.length} shown, all counted.`;
    els['conditions'].querySelectorAll('button').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.condition===condition)));
    els['matrix'].querySelectorAll('button.selected').forEach(button=>button.classList.remove('selected'));
    els['matrix'].querySelector(`[data-frame="${index}"][data-condition="${condition}"]`)?.classList.add('selected');
  }
  function addBox(box,type,label,showLabel=true,layer='box-layer'){
    const node=document.createElement('span');node.className=`overlay-box ${type}`;
    Object.assign(node.style,positions(box));node.title=`${label}${type!=='gt'?` · IoU ${value(box[5])}`:''}`;
    if(type!=='gt'&&showLabel){const tag=document.createElement('em');tag.textContent=label;node.append(tag);}
    els[layer].append(node);
  }
  function matches(item){
    const c=els['filter-condition'].value,o=els['filter-outcome'].value,f=Number(els['filter-confidence'].value);
    return (c==='all'||item.condition===c) && (o==='all'||o==='miss'&&item.fn>0||o==='false-positive'&&item.fp>0||o==='pass'&&item.pass)
      && (!f||item.boxes.some(box=>box[4]>=f)) && (!els['small-target'].checked||item.size<=smallLimit);
  }
  function drawMatrix(){
    els['matrix'].replaceChildren();let count=0;
    const fragment=document.createDocumentFragment();
    data.frame_ids.forEach((frame,i)=>data.conditions.forEach(c=>{
      const item=byKey.get(key(frame,c)),pass=matches(item);
      if(pass)count++;
      const button=document.createElement('button');button.type='button';button.className=`${item.pass?'matched':'missed'}${pass?'':' dimmed'}`;
      button.dataset.frame=i;button.dataset.condition=c;button.title=`Frame ${i+1}, ${names[c]}: ${item.pass?'target matched':'target missed'}; ${item.fp} false positives${pass?'':' (filtered out)'}`;
      button.setAttribute('aria-label',button.title);button.textContent=String(i+1).padStart(2,'0');
      button.addEventListener('click',()=>{index=i;condition=c;drawCase();document.getElementById('explorer').scrollIntoView({behavior:'smooth'});});fragment.append(button);
    }));
    els['matrix'].append(fragment);els['match-count'].textContent=`${count} / 516 matching views`;drawCase();drawScatter();
  }
  function drawScatter(){
    const canvas=els['scatter'],ctx=canvas.getContext('2d');if(!ctx)return;
    const width=canvas.clientWidth,height=canvas.clientHeight,dpr=window.devicePixelRatio||1;
    if(canvas.width!==Math.floor(width*dpr)||canvas.height!==Math.floor(height*dpr)){canvas.width=Math.floor(width*dpr);canvas.height=Math.floor(height*dpr);}
    ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,width,height);
    const left=42,right=16,top=15,bottom=30,w=width-left-right,h=height-top-bottom;
    ctx.strokeStyle='#dce5e7';ctx.fillStyle='#65777c';ctx.lineWidth=1;ctx.font='11px DM Sans, sans-serif';
    for(let i=0;i<=4;i++){const x=left+w*i/4,y=top+h*i/4;ctx.beginPath();ctx.moveTo(x,top);ctx.lineTo(x,top+h);ctx.moveTo(left,y);ctx.lineTo(left+w,y);ctx.stroke();ctx.fillText(value(i/4),x-10,top+h+18);ctx.fillText(value(1-i/4),4,y+4);}
    plotPoints=[];
    for(const item of data.cases){if(!matches(item))continue;
      for(const box of item.boxes){const [,,, ,score,iou,tp]=box;
        if(wrongOnly && (score<.7||tp))continue;
        const x=left+Math.min(1,score)*w,y=top+(1-Math.min(1,iou))*h;
        ctx.beginPath();ctx.arc(x,y,wrongOnly?4:2.7,0,Math.PI*2);ctx.fillStyle=tp?'#2f6a4599':'#b3261e8a';ctx.fill();plotPoints.push({x,y,item,box});
      }
    }
    els['scatter-count'].textContent=`${plotPoints.length.toLocaleString()} displayed baseline boxes${wrongOnly?' with score ≥ 0.70 and false-positive status':''}. Display includes scores ≥ 0.01 and any matched boxes below. All ${data.prediction_rows.toLocaleString()} predictions remain in the complete table; no threshold is selected from these reused frames.`;
  }
  function conditionFromPath(file){
    const segments=(file.webkitRelativePath||'').split(/[\\/]+/).filter(Boolean).slice(0,-1).reverse();
    for(const raw of segments){
      let part=raw.toLowerCase().replace(/[ -]+/g,'_');
      part=part.replace(/^kios_/,'').replace(/^condition_/,'').replace(/^stress_/,'');
      if(data.conditions.includes(part))return part;
    }
    return null;
  }
  function acceptImages(files,folderMode){
    const frameNames=new Map(data.frame_ids.map(id=>[id.toLowerCase(),id]));
    const imageExtensions=/\.(?:avif|bmp|gif|jpe?g|png|tiff?|webp)$/i;
    let accepted=0,replaced=0,skipped=0;
    for(const file of files){
      const frame=frameNames.get(file.name.toLowerCase());
      if((!file.type||!file.type.startsWith('image/'))&&!imageExtensions.test(file.name)){skipped++;continue;}
      if(!frame){skipped++;continue;}
      const fileCondition=folderMode?conditionFromPath(file):condition;
      if(!fileCondition){skipped++;continue;}
      const k=key(frame,fileCondition),old=localImages.get(k);
      if(old){URL.revokeObjectURL(old);replaced++;}
      localImages.set(k,URL.createObjectURL(file));accepted++;
    }
    drawCase();
    const perCondition=data.conditions.map(c=>[c,[...localImages.keys()].filter(k=>k.endsWith(`|${c}`)).length]).filter(([,n])=>n>0);
    const distribution=perCondition.map(([c,n])=>`${names[c]} ${n}`).join(' · ');
    els['image-note'].textContent=accepted
      ?`Loaded ${accepted} image view${accepted===1?'':'s'}${distribution?`: ${distribution}`:''}. ${replaced?`${replaced} replaced. `:''}${skipped?`${skipped} skipped (filename or condition folder did not match). `:''}Files stay in this browser; hashes are not checked here.`
      :`No matching images loaded. Use original frame filenames${folderMode?' inside condition-named folders':''}. ${skipped?`${skipped} file${skipped===1?' was':'s were'} skipped. `:''}Files are not sent anywhere.`;
  }
  function init(payload){
    if(payload.status!=='paired_verified'||payload.phase23?.status!=='original_checkpoint_replay_verified'||payload.phase23.cases.length!==516||payload.frame_ids.length!==86||payload.cases.length!==516
      ||!payload.phase23_condition_aggregates||Object.keys(payload.phase23_condition_aggregates).length!==6
      ||payload.conditions.some(c=>!payload.phase23_condition_aggregates[c]||!Number.isFinite(payload.phase23_condition_aggregates[c].map50)||!Number.isFinite(payload.phase23_condition_aggregates[c].recall)))throw Error('Atlas data contract failed');
    data=payload;byKey=new Map(data.cases.map(item=>[key(item.id,item.condition),item]));
    phase23ByKey=new Map(data.phase23.cases.map(item=>[key(item.id,item.condition),item]));
    if(phase23ByKey.size!==516||[...byKey.keys()].some(k=>!phase23ByKey.has(k)))throw Error('Phase 23 case identity mismatch');
    index=0;
    const sizes=data.frame_ids.map(id=>byKey.get(key(id,'clean')).size).sort((a,b)=>a-b);smallLimit=sizes[Math.ceil(sizes.length*.25)-1];
    for(const c of data.conditions){const button=document.createElement('button');button.type='button';button.dataset.condition=c;button.textContent=names[c];button.addEventListener('click',()=>{condition=c;drawCase()});els['conditions'].append(button);const option=document.createElement('option');option.value=c;option.textContent=names[c];els['filter-condition'].append(option);}
    els['frame-range'].addEventListener('input',event=>{index=Number(event.target.value);drawCase()});
    els['prev-frame'].addEventListener('click',()=>{index=(index+85)%86;drawCase()});els['next-frame'].addEventListener('click',()=>{index=(index+1)%86;drawCase()});
    els['view-mode'].addEventListener('click',()=>{const side=els['comparison'].classList.toggle('stacked');els['view-mode'].setAttribute('aria-pressed',String(!side));els['view-mode'].textContent=side?'Stacked view':'Side by side';});
    for(const id of ['show-gt','show-baseline','show-phase23'])els[id].addEventListener('change',drawCase);
    for(const id of ['filter-condition','filter-outcome','filter-confidence','small-target'])els[id].addEventListener('change',drawMatrix);
    els['show-wrong'].addEventListener('click',()=>{wrongOnly=!wrongOnly;els['show-wrong'].setAttribute('aria-pressed',String(wrongOnly));drawScatter();});
    els['local-files'].addEventListener('change',event=>{acceptImages(event.target.files,false);event.target.value='';});
    els['local-folder'].addEventListener('change',event=>{acceptImages(event.target.files,true);event.target.value='';});
    window.addEventListener('pagehide',()=>{for(const url of localImages.values())URL.revokeObjectURL(url)});
    els['scatter'].addEventListener('pointermove',event=>{const bounds=els['scatter'].getBoundingClientRect();const x=event.clientX-bounds.left,y=event.clientY-bounds.top;let closest=null,distance=110;
      for(const point of plotPoints){const d=(point.x-x)**2+(point.y-y)**2;if(d<distance){closest=point;distance=d;}}
      if(closest){const p=closest;els['point-detail'].textContent=`Frame ${data.frame_ids.indexOf(p.item.id)+1} · ${names[p.item.condition]} · score ${value(p.box[4])} · IoU ${value(p.box[5])} · ${p.box[6]?'TRUE POSITIVE':'FALSE POSITIVE'}. Click to inspect.`;els['scatter'].dataset.hover='1';els['scatter']._nearest=closest;}
      else{els['point-detail'].textContent='Hover a point or select a case to inspect its score and IoU.';els['scatter']._nearest=null;}
    });
    els['scatter'].addEventListener('click',()=>{const p=els['scatter']._nearest;if(!p)return;index=data.frame_ids.indexOf(p.item.id);condition=p.item.condition;drawCase();document.getElementById('explorer').scrollIntoView({behavior:'smooth'});});
    window.addEventListener('resize',drawScatter);
    document.querySelectorAll('[data-open-evidence]').forEach(button=>button.addEventListener('click',()=>els['evidence-dialog'].showModal()));els['close-evidence'].addEventListener('click',()=>els['evidence-dialog'].close());
    drawMatrix();
  }
  fetch('/failure-atlas-data.json?v=3').then(response=>{if(!response.ok)throw Error(`HTTP ${response.status}`);return response.json()}).then(init).catch(error=>{els['image-note'].textContent=`Frame data could not load. Read the Phase 25 method or try again. (${error.message})`;});
})();
