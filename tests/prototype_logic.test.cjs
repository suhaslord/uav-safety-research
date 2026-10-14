'use strict';
const test=require('node:test'), assert=require('node:assert/strict'), fs=require('node:fs');
const {decide,validate,describe,boxValid}=require('../deploy/vercel/prototype.js');
const source=()=>JSON.parse(fs.readFileSync('deploy/vercel/prototype-cases.json','utf8'));

test('full authenticated 1032-row demo accepts previously used frames only',()=>{
  const d=validate(source());
  assert.equal(d.cases.size,1032);assert.equal(d.frames.length,86);
  assert.equal(d.payload.new_holdout,false);assert.equal(d.payload.threshold_selected,false);
});
test('runtime decision reads only finite score and cutoff; no labels',()=>{
  assert.equal(decide(0.9,0.5),true);
  assert.equal(decide(0.1,0.5),false);
  assert.equal(decide(0,0.05),false);
  assert.throws(()=>decide(NaN,0.5));
  assert.throws(()=>decide(0.5,0));
  assert.throws(()=>decide(true,0.5));
  assert.throws(()=>decide(0.5,Infinity));
  assert.equal(boxValid([0,0,1,1]),true);
  assert.equal(boxValid([0.4,0.4,0.1,0.2]),false);
});
test('retrospective wrong-and-coverage summaries do not invent a zero error rate',()=>{
  const d=validate(source());
  const rows=d.payload.cases.filter(c=>c.model==='phase23'&&c.condition==='occlusion');
  const s=describe(rows,.5);
  assert.equal(s.total,86);
  assert.equal(s.accepted,2);
  assert.equal(s.wrong,2);
  assert.equal(s.coverage,2/86);
  assert.equal(s.error,1);
  const no=describe([{score:0.1,top_correct:false}],.95);
  assert.equal(no.accepted,0);assert.equal(no.error,null);
});
test('tampered confidence, missing case, fake independence and swapped annotations are rejected',()=>{
  let d=source();d.cases[0].score=2;assert.throws(()=>validate(d));
  d=source();d.cases.pop();assert.throws(()=>validate(d));
  d=source();d.new_holdout=true;assert.throws(()=>validate(d));
  d=source();d.cases[0].truth_boxes[0][0]=0.4;assert.throws(()=>validate(d));
  d=source();d.cases[0].top_correct=!d.cases[0].top_correct;assert.throws(()=>validate(d));
});
