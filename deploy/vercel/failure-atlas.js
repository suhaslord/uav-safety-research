(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const names = {clean:'Clean', blur:'Blur', low_light:'Low light', noise:'Noise', occlusion:'Occlusion', mixed:'Mixed'};
  const els = Object.fromEntries(['frame-title','frame-sequence','frame-range','prev-frame','next-frame','view-mode','conditions','show-gt','show-baseline','local-files','image-note','comparison','baseline-verdict','baseline-scene','frame-image','box-layer','scene-index','baseline-metrics','case-label','case-features','filter-condition','filter-outcome','filter-confidence','small-target','match-count','matrix','scatter','point-detail','show-wrong','scatter-count','evidence-dialog','close-evidence'].map(id=>[id,$(id)]));
  let data, byKey, index=0, condition='clean', smallLimit=0, wrongOnly=false, plotPoints=[], localImages=new Map();
  const key=(id,c)=>`${id}|${c}`;
  const value=(x,d=2)=>Number(x).toFixed(d);
  const caseNow=()=>byKey.get(key(data.frame_ids[index],condition));
  const positions=(box)=>({left:`${box[0]*100}%`,top:`${box[1]*100}%`,width:`${Math.max(0,(box[2]-box[0])*100)}%`,height:`${Math.max(0,(box[3]-box[1])*100)}%`});
  function drawCase(){
    const item=caseNow();if(!item)return;
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
    els['case-features'].textContent=`Target area ${(item.size*100).toFixed(3)}% · Brightness ${value(item.brightness)} · Sharpness ${value(item.sharpness,4)} · ${item.count} detections at score ≥ 0.001`;
    els['scene-index'].textContent=`${item.id} / ${names[condition]}`;
    const local=localImages.get(key(item.id,condition));
    const published=item.id==='land_pad2__2100.jpg';
    const image=local|| (published?`/media/perception/kios_${condition}.jpg`:null);
    els['frame-image'].hidden=!image;
    if(image){els['frame-image'].src=image;els['frame-image'].alt=`${names[condition]} view of ${item.id}${local?' loaded locally':' from a previously published annotated example'}`;}
    else{els['frame-image'].removeAttribute('src');els['frame-image'].alt='';}
    els['image-note'].textContent=local?'Local image loaded only in this browser. The measured boxes and scores come from the frozen run.':published?'This published example has its original blue annotation baked into the image. Toggles control the measured overlays; the blue source mark remains visible.':'The archive imagery stays off this site. Box coordinates are measured; load your own verified images in this browser to see overlays. Select images for the active condition.';
    els['box-layer'].replaceChildren();
    if(els['show-gt'].checked)for(const box of item.gt) addBox(box,'gt','GT');
    if(els['show-baseline'].checked){
      // Always draw matched targets, even when their score falls below the display floor.
      const visible=item.boxes.slice(0,60);
      for(const box of item.boxes)if(box[6]&&!visible.includes(box))visible.push(box);
      for(const box of visible) addBox(box,box[6]?'tp':'fp',`${box[6]?'TP':'FP'} ${value(box[4])}`);
    }
    els['baseline-scene'].title=`${item.count} predictions; ${item.omitted} below display score 0.01. Matching uses every box ≥ 0.001.`;
    els['conditions'].querySelectorAll('button').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.condition===condition)));
    els['matrix'].querySelectorAll('button.selected').forEach(button=>button.classList.remove('selected'));
    els['matrix'].querySelector(`[data-frame="${index}"][data-condition="${condition}"]`)?.classList.add('selected');
  }
  function addBox(box,type,label){
    const node=document.createElement('span');node.className=`overlay-box ${type}`;
    Object.assign(node.style,positions(box));node.title=`${label}${type!=='gt'?` · IoU ${value(box[5])}`:''}`;
    if(type!=='gt'){const tag=document.createElement('em');tag.textContent=label;node.append(tag);}
    els['box-layer'].append(node);
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
        ctx.beginPath();ctx.arc(x,y,wrongOnly?4:2.7,0,Math.PI*2);ctx.fillStyle=tp?'#15877299':'#b6582c8a';ctx.fill();plotPoints.push({x,y,item,box});
      }
    }
    els['scatter-count'].textContent=`${plotPoints.length.toLocaleString()} displayed baseline boxes${wrongOnly?' with score ≥ 0.70 and false-positive status':''}. Display includes scores ≥ 0.01 and any matched boxes below. All ${data.prediction_rows.toLocaleString()} predictions remain in the complete table; no threshold is selected from these reused frames.`;
  }
  function init(payload){
    if(payload.status!=='baseline_only'||payload.phase23!==null||payload.frame_ids.length!==86||payload.cases.length!==516)throw Error('Atlas data contract failed');
    data=payload;byKey=new Map(data.cases.map(item=>[key(item.id,item.condition),item]));
    index=Math.max(0,data.frame_ids.indexOf('land_pad2__2100.jpg')); // Existing published illustration.
    const sizes=data.frame_ids.map(id=>byKey.get(key(id,'clean')).size).sort((a,b)=>a-b);smallLimit=sizes[Math.ceil(sizes.length*.25)-1];
    for(const c of data.conditions){const button=document.createElement('button');button.type='button';button.dataset.condition=c;button.textContent=names[c];button.addEventListener('click',()=>{condition=c;drawCase()});els['conditions'].append(button);const option=document.createElement('option');option.value=c;option.textContent=names[c];els['filter-condition'].append(option);}
    els['frame-range'].addEventListener('input',event=>{index=Number(event.target.value);drawCase()});
    els['prev-frame'].addEventListener('click',()=>{index=(index+85)%86;drawCase()});els['next-frame'].addEventListener('click',()=>{index=(index+1)%86;drawCase()});
    els['view-mode'].addEventListener('click',()=>{const side=els['comparison'].classList.toggle('stacked');els['view-mode'].setAttribute('aria-pressed',String(!side));els['view-mode'].textContent=side?'Stacked view':'Side by side';});
    for(const id of ['show-gt','show-baseline'])els[id].addEventListener('change',drawCase);
    for(const id of ['filter-condition','filter-outcome','filter-confidence','small-target'])els[id].addEventListener('change',drawMatrix);
    els['show-wrong'].addEventListener('click',()=>{wrongOnly=!wrongOnly;els['show-wrong'].setAttribute('aria-pressed',String(wrongOnly));drawScatter();});
    els['local-files'].addEventListener('change',event=>{
      for(const file of event.target.files){if(!file.type.startsWith('image/')||!data.frame_ids.includes(file.name))continue;
        const k=key(file.name,condition);const old=localImages.get(k);if(old)URL.revokeObjectURL(old);localImages.set(k,URL.createObjectURL(file));
      }drawCase();event.target.value='';
    });
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
  fetch('/failure-atlas-data.json').then(response=>{if(!response.ok)throw Error(`HTTP ${response.status}`);return response.json()}).then(init).catch(error=>{els['image-note'].textContent=`Frame data could not load. Read the Phase 25 method or try again. (${error.message})`;});
})();
