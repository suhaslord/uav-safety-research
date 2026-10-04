const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { FRAME, CONDITIONS, validatePayload, visibleBoxes } = require('../deploy/vercel/home-evidence.js');
const original = () => JSON.parse(fs.readFileSync(require.resolve('../deploy/vercel/failure-atlas-data.json'), 'utf8'));

test('preview pairs authentic saved cases across the entire six-condition population', () => {
  const data = original(), maps = validatePayload(data);
  assert.equal(maps.baseline.size, 516); assert.equal(maps.phase23.size, 516);
  for (const condition of CONDITIONS) {
    const a = maps.baseline.get(`${FRAME}|${condition}`), b = maps.phase23.get(`${FRAME}|${condition}`);
    assert.deepEqual(a.gt, b.gt); assert.equal(a.id, b.id);
  }
  assert.equal(maps.baseline.get(`${FRAME}|occlusion`).pass, true);
  assert.equal(maps.phase23.get(`${FRAME}|occlusion`).pass, false);
});

test('missing measurements never become measured zero', () => {
  for (const name of ['tp', 'fp', 'fn', 'count', 'iou', 'score', 'pass']) {
    const data = original(); delete data.cases[0][name];
    assert.throws(() => validatePayload(data));
  }
});

test('duplicate, unpaired and mismatched annotation cases fail closed', () => {
  const duplicate = original(); duplicate.cases[1] = duplicate.cases[0]; assert.throws(() => validatePayload(duplicate));
  const incomplete = original(); incomplete.phase23.cases.pop(); assert.throws(() => validatePayload(incomplete));
  const annotation = original(); annotation.phase23.cases[0].gt[0][0] = 0; assert.throws(() => validatePayload(annotation));
});

test('nonfinite, boolean and contradictory counts cannot reach the comparison', () => {
  for (const bad of [NaN, Infinity, null, false, -1, 1.5]) {
    const data = original(); data.cases[0].tp = bad; assert.throws(() => validatePayload(data));
  }
  const data = original(); data.cases[0].pass = !data.cases[0].pass; assert.throws(() => validatePayload(data));
});

test('visual cap retains every matched prediction without changing the recorded count', () => {
  const matches = Array.from({length: 4}, () => [0,0,1,1,.005,.6,1]);
  const wrong = Array.from({length: 5}, () => [0,0,1,1,.1,.2,0]);
  const item = {boxes: [...wrong,...matches], count: 300};
  const visible = visibleBoxes(item);
  assert.equal(visible.filter(b => b[6]).length, 4);
  assert.equal(visible.filter(b => !b[6]).length, 2);
  assert.equal(item.count, 300); assert.equal(item.boxes.length, 9);
});
