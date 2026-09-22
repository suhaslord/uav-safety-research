export const VERSION = 'aegis-lab-2026-09-v2';
export const STORAGE_KEY = 'aegisland.saved-experiments.v2';
export function validateSetup(raw, fields, catalog) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw) || !Object.hasOwn(catalog,raw.phase) || raw.phase==='phase4') throw Error('Choose a runnable research phase.');
  const clean={phase:raw.phase};
  for (const [key,value] of Object.entries(raw)) {
    if(key==='phase')continue;
    if(key==='condition'){if(!['clean','blur','low_light','occlusion','mixed'].includes(value))throw Error('Unsupported camera condition.');clean[key]=value;continue;}
    if(!Object.hasOwn(fields,key))throw Error('Unknown setting: '+key);
    const [, ,min,max]=fields[key];
    if(typeof value!=='number'||!Number.isFinite(value)||value<min||value>max||(['seed','samples','episodes','lag'].includes(key)&&!Number.isInteger(value)))throw Error('Invalid setting: '+key);
    clean[key]=value;
  }
  if(['phase6','phase6b'].includes(clean.phase)&&clean.samples>128)throw Error('Camera experiments allow at most 128 frames.');
  return clean;
}
export function setupLink(origin, setup) {
  const url=new URL('/',origin);url.hash='experiment-lab';url.searchParams.set('setup',JSON.stringify(setup));return url.href;
}
export function readSetup(search, fields, catalog) {
  const text=new URLSearchParams(search).get('setup');
  if(text===null)return null;
  if(text.length>5000)throw Error('This setup link is too large.');
  return validateSetup(JSON.parse(text),fields,catalog);
}
const shortString=x=>typeof x==='string'&&x.length<=2000;
export function validateResult(raw,fields,catalog) {
  if(!raw||raw.schema!=='aegisland.browser-experiment.v1'||raw.exploratory!==true||raw.simulation_only!==true||raw.frozen_evidence_modified!==false)throw Error('Unsupported saved result.');
  const inputs=validateSetup(raw.inputs,fields,catalog);
  if(inputs.phase!==raw.phase||!shortString(raw.title)||!shortString(raw.runtime)||!shortString(raw.x_label)||!shortString(raw.y_label)||!shortString(raw.note)||!shortString(raw.source_commit))throw Error('Invalid saved result.');
  if(!Array.isArray(raw.metrics)||raw.metrics.length>16||raw.metrics.some(m=>!shortString(m.label)||!shortString(m.unit)||(m.value!==null&&(typeof m.value!=='number'||!Number.isFinite(m.value)))))throw Error('Invalid saved metrics.');
  if(!Array.isArray(raw.series)||raw.series.length>8||raw.series.some(s=>!shortString(s.label)||!Array.isArray(s.values)||s.values.length>5000||s.values.some(v=>v!==null&&(typeof v!=='number'||!Number.isFinite(v)))))throw Error('Invalid saved series.');
  if(!Array.isArray(raw.rows)||raw.rows.length>1024||raw.rows.some(r=>!r||typeof r!=='object'||Object.keys(r).length>32||Object.entries(r).some(([k,v])=>!shortString(k)||!(v===null||typeof v==='boolean'||(typeof v==='number'&&Number.isFinite(v))||shortString(v)))))throw Error('Invalid saved rows.');
  // Persist only fields consumed by comparison and downloads. Camera bitmaps are unnecessary.
  return {schema:raw.schema,phase:raw.phase,inputs,metrics:raw.metrics,series:raw.series.map(s=>({label:s.label,values:s.values})),rows:raw.rows,note:raw.note,title:String(raw.title||''),x_label:raw.x_label,y_label:raw.y_label,source_commit:raw.source_commit,exploratory:true,simulation_only:true,frozen_evidence_modified:false,runtime:raw.runtime};
}
export function restore(text,fields,catalog,keyFor) {
  if(!text)return {};
  if(text.length>4000000)throw Error('Saved runs exceed the storage limit.');
  const parsed=JSON.parse(text);if(parsed.version!==VERSION)throw Error('Saved runs use an older experiment version.');
  if(!Array.isArray(parsed.runs)||parsed.runs.length>24)throw Error('Too many saved runs.');
  const stacks={};const ids=new Set();
  for(const entry of parsed.runs){if(!Number.isSafeInteger(entry.id)||entry.id<1||ids.has(entry.id))throw Error('Invalid saved run ID.');ids.add(entry.id);const data=validateResult(entry.data,fields,catalog),key=keyFor(data);const list=stacks[key]||=[];if(list.length>=4)throw Error('Too many runs in a comparison.');list.push({id:entry.id,data});}
  return stacks;
}
export function serialize(stacks,fields,catalog) {
  const runs=Object.values(stacks).flat().map(r=>({id:r.id,data:validateResult(r.data,fields,catalog)}));
  if(runs.length>24)throw Error('Remove a saved run before saving more than 24 runs.');
  const text=JSON.stringify({version:VERSION,runs});if(text.length>4000000)throw Error('Browser storage is full. Export or remove some saved runs.');return text;
}
export function takeaway(current, previous) {
  const m=current.metrics.find(m=>/RMSE|Empirical coverage|successful landings|First-order variance|Endpoint attenuation/i.test(m.label)&&m.value!==null)||current.metrics.find(m=>m.value!==null);
  if(!m)return 'No usable measurements were returned. Try another setting.';
  const f=n=>Number(n.toPrecision(4)).toString();
  const old=previous?.metrics.find(x=>x.label===m.label&&x.unit===m.unit&&x.value!==null);
  const changes=previous?Object.keys(current.inputs).filter(k=>current.inputs[k]!==previous.inputs[k]):[];
  let text=`${m.label}: ${f(m.value)}${m.unit?' '+m.unit:''}.`;
  if(old){const delta=m.value-old.value;text+=` ${delta===0?'Unchanged':`${delta>0?'Up':'Down'} ${f(Math.abs(delta))}${m.unit==='%'?' percentage points':m.unit?' '+m.unit:''}`} from the previous comparable run.`;text+=changes.length?` Changed settings: ${changes.join(', ')}.`:' The input settings are identical.';}
  else text+=' Run another scenario to measure a change.';
  return text+' This synthetic example does not establish real-flight safety or change the published results.';
}
