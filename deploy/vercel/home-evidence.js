(() => {
  'use strict';
  const FRAME = 'land_pad2__2475.jpg'; // Explicit illustrative regression, not a sample estimate.
  const CONDITIONS = ['clean', 'blur', 'low_light', 'noise', 'occlusion', 'mixed'];
  const NAMES = { clean: 'Clean', blur: 'Blur', low_light: 'Low light', noise: 'Noise', occlusion: 'Occlusion', mixed: 'Mixed' };
  const key = item => `${item.id}|${item.condition}`;
  const finiteUnit = x => typeof x === 'number' && Number.isFinite(x) && x >= 0 && x <= 1;
  function validRectangle(box) {
    return Array.isArray(box) && box.length >= 4 && box.slice(0, 4).every(finiteUnit) && box[0] <= box[2] && box[1] <= box[3];
  }
  function validatedCases(rows, ids) {
    if (!Array.isArray(rows) || rows.length !== 516) throw new Error('Incomplete saved case population');
    const result = new Map();
    for (const item of rows) {
      if (!ids.includes(item.id) || !CONDITIONS.includes(item.condition) || result.has(key(item))
        || ['tp', 'fp', 'fn', 'count'].some(name => !Number.isSafeInteger(item[name]) || item[name] < 0)
        || item.tp + item.fp !== item.count || typeof item.pass !== 'boolean'
        || !finiteUnit(item.iou) || !finiteUnit(item.score)
        || !Array.isArray(item.gt) || !item.gt.length || item.gt.some(box => !validRectangle(box))
        || item.tp + item.fn !== item.gt.length || item.pass !== (item.fn === 0)
        || !Array.isArray(item.boxes) || item.boxes.some(box => !validRectangle(box)
          || box.length !== 7 || !finiteUnit(box[4]) || !finiteUnit(box[5]) || ![0, 1].includes(box[6]))) {
        throw new Error('Invalid saved frame metrics');
      }
      result.set(key(item), item);
    }
    return result;
  }
  function validatePayload(data) {
    if (data.status !== 'paired_verified' || data.phase23?.status !== 'original_checkpoint_replay_verified'
      || !Array.isArray(data.frame_ids) || data.frame_ids.length !== 86 || new Set(data.frame_ids).size !== 86
      || data.frame_ids.some(id => !/^land_pad2?__\d+\.jpg$/.test(id))
      || JSON.stringify(data.conditions) !== JSON.stringify(CONDITIONS)) throw new Error('Saved record unavailable');
    const baseline = validatedCases(data.cases, data.frame_ids);
    const phase23 = validatedCases(data.phase23.cases, data.frame_ids);
    for (const [identity, item] of baseline) {
      if (JSON.stringify(item.gt) !== JSON.stringify(phase23.get(identity)?.gt)) throw new Error('Pair identity mismatch');
    }
    return { baseline, phase23 };
  }
  function visibleBoxes(item) {
    // These arrays are already a publication subset. Never remove matched predictions.
    return [...item.boxes.filter(box => box[6] === 1), ...item.boxes.filter(box => box[6] === 0).slice(0, 2)];
  }
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { FRAME, CONDITIONS, validatePayload, visibleBoxes };
    return;
  }
  const scriptBase = new URL('.', document.currentScript?.src || window.location.href);
  const root = document.getElementById('home-comparison');
  if (!root) return;
  const buttons = [...root.querySelectorAll('[data-home-condition]')];
  const note = document.getElementById('home-case-note');
  const showBoxes = document.getElementById('home-show-boxes');
  let tables, current = 'occlusion', generation = 0;
  function boxNode(box, type) {
    const node = document.createElement('span');
    node.className = `home-overlay-box ${type}`;
    Object.assign(node.style, { left: `${box[0] * 100}%`, top: `${box[1] * 100}%`, width: `${(box[2] - box[0]) * 100}%`, height: `${(box[3] - box[1]) * 100}%` });
    if (type !== 'gt') {
      node.title = `${type === 'tp' ? 'Matched' : 'Unmatched'} · score ${box[4].toFixed(3)} · IoU ${box[5].toFixed(3)}`;
      if (type === 'tp') { const label = document.createElement('em'); label.textContent = `IoU ${box[5].toFixed(2)}`; node.append(label); }
    }
    return node;
  }
  function draw() {
    const request = ++generation;
    for (const model of ['baseline', 'phase23']) {
      const item = tables[model].get(`${FRAME}|${current}`);
      const panel = root.querySelector(`[data-home-model="${model}"]`);
      const verdict = panel.querySelector('[data-home-verdict]');
      verdict.textContent = item.pass ? 'TARGET MATCHED' : 'TARGET MISSED';
      verdict.dataset.missed = String(!item.pass);
      panel.querySelectorAll('[data-home-metric]').forEach(node => { node.textContent = item[node.dataset.homeMetric]; });
      const camera = panel.querySelector('.home-camera');
      let image = camera.querySelector('img');
      // A fresh element isolates load/error callbacks from interrupted condition changes.
      const replacement = image.cloneNode(false);
      replacement.removeAttribute('src'); replacement.hidden = true;
      image.replaceWith(replacement); image = replacement;
      const layer = camera.querySelector('.home-boxes');
      layer.replaceChildren(); layer.hidden = true;
      for (const box of item.gt) layer.append(boxNode(box, 'gt'));
      for (const box of visibleBoxes(item)) layer.append(boxNode(box, box[6] ? 'tp' : 'fp'));
      const placeholder = camera.querySelector('.home-camera__placeholder');
      placeholder.hidden = false; placeholder.textContent = 'Loading source image…';
      image.alt = `${NAMES[current]} KIOS source frame ${FRAME}, with ${model === 'baseline' ? 'baseline' : 'Phase 23'} saved prediction overlays`;
      image.onload = () => { if (request !== generation) return; image.hidden = false; layer.hidden = !showBoxes.checked; placeholder.hidden = true; };
      image.onerror = () => { if (request !== generation) return; image.hidden = true; layer.hidden = true; placeholder.hidden = false; placeholder.textContent = 'Image unavailable. The measured table is retained; reload to retry.'; };
      image.src = new URL(`media/phase25/${current}/${FRAME}`, scriptBase).href;
    }
    buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.homeCondition === current)));
    note.textContent = `${FRAME.replace('.jpg', '')} · ${NAMES[current]} · saved original-model predictions at score ≥ 0.001, match IoU ≥ 0.50.`;
    root.dataset.loaded = 'true';
  }
  buttons.forEach(button => button.addEventListener('click', () => { current = button.dataset.homeCondition; draw(); }));
  showBoxes.addEventListener('change', () => {
    root.querySelectorAll('.home-camera').forEach(camera => {
      const image = camera.querySelector('img');
      camera.querySelector('.home-boxes').hidden = !showBoxes.checked || image.hidden;
    });
  });
  fetch(new URL('failure-atlas-data.json?v=3', scriptBase))
    .then(response => { if (!response.ok) throw new Error('Saved record unavailable'); return response.json(); })
    .then(data => { tables = validatePayload(data); draw(); buttons.forEach(button => { button.disabled = false; }); })
    .catch(() => {
      note.textContent = 'The saved comparison could not load. Open Failure Atlas or reload this page to retry.';
      root.querySelectorAll('[data-home-verdict]').forEach(node => { node.textContent = 'Record unavailable'; });
      root.querySelectorAll('.home-camera__placeholder').forEach(node => { node.textContent = 'Comparison unavailable'; });
    });

  const toggle = document.getElementById('mobileMenuToggle');
  const menu = document.getElementById('mobileMenuSheet');
  const close = menu.querySelector('.mobile-menu-close');
  function setMenu(open) {
    toggle.setAttribute('aria-expanded', String(open)); menu.setAttribute('aria-hidden', String(!open)); menu.inert = !open;
    menu.classList.toggle('open', open); document.body.classList.toggle('menu-open', open);
    if (open) close.focus(); else toggle.focus();
  }
  toggle.addEventListener('click', () => setMenu(toggle.getAttribute('aria-expanded') !== 'true'));
  close.addEventListener('click', () => setMenu(false));
  menu.querySelectorAll('a').forEach(link => link.addEventListener('click', () => setMenu(false)));
  document.addEventListener('keydown', event => {
    if (toggle.getAttribute('aria-expanded') !== 'true') return;
    if (event.key === 'Escape') { setMenu(false); return; }
    if (event.key === 'Tab') {
      const items = [...menu.querySelectorAll('button,a[href]')], first = items[0], last = items.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
  });
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const videos = [...document.querySelectorAll('video[data-autoplay="visible"]')];
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting && entry.intersectionRatio >= .4 && !reduced.matches) entry.target.play().catch(() => {});
      else entry.target.pause();
    }), { threshold: [0, .4] });
    videos.forEach(video => observer.observe(video));
  }
  reduced.addEventListener('change', () => { if (reduced.matches) videos.forEach(video => video.pause()); });
  const lineage = window.AEGIS_FROZEN_LINEAGE;
  if (lineage) for (const phase of lineage.phases) {
    const link = document.createElement('a'); link.className = 'home-lineage__node'; link.dataset.verdict = phase.verdict;
    link.href = new URL(`phases/${phase.slug}/`, scriptBase).href; link.textContent = phase.label.replace('Phase ', '');
    link.setAttribute('aria-label', `${phase.label}: ${phase.verdict} — ${phase.title}`);
    document.getElementById('homeLineage').append(link);
    const row = document.createElement('a'); row.className = 'evidence-item evidence-row'; row.dataset.verdict = phase.verdict; row.href = link.href;
    const label = document.createElement('span'); label.textContent = `${phase.label} · ${phase.stage}`;
    const title = document.createElement('strong'); title.textContent = `${phase.verdict} · ${phase.title}`; row.append(label, title);
    document.getElementById('evidenceSpine').append(row);
  }
})();
