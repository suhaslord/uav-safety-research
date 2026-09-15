(() => {
  'use strict';

  const DATASET = {
    name: 'KIOS Aerial Landing Pad, Unreal Engine Dataset (2024)',
    total: 422,
    train: 252,
    validation: 64,
    embargo: 20,
    test: 86,
    model: 'YOLO11n',
    conditions: {
      clean:      { label: 'Clean',      precision: 0.796, recall: 0.384, map50: 0.427, map5095: 0.272 },
      blur:       { label: 'Blur',       precision: 0.844, recall: 0.378, map50: 0.413, map5095: 0.271 },
      low_light:  { label: 'Low light',  precision: 0.787, recall: 0.372, map50: 0.417, map5095: 0.269 },
      noise:      { label: 'Noise',      precision: 0.895, recall: 0.398, map50: 0.433, map5095: 0.262 },
      occlusion:  { label: 'Occlusion',  precision: 0.622, recall: 0.326, map50: 0.348, map5095: 0.166 },
      mixed:      { label: 'Mixed',      precision: 0.597, recall: 0.186, map50: 0.185, map5095: 0.081 }
    }
  };

  const pct = value => `${(value * 100).toFixed(1)}%`;
  const signed = value => `${value >= 0 ? '+' : ''}${(value * 100).toFixed(1)} pp`;
  const phase = () => document.body.dataset.phase || location.pathname.match(/phase\d+[a-z]*/i)?.[0]?.toLowerCase() || 'phase1';

  function ensureStyle() {
    if (document.getElementById('aegis-current-data-style')) return;
    const style = document.createElement('style');
    style.id = 'aegis-current-data-style';
    style.textContent = `
      .current-data-shell{display:grid;gap:24px}
      .current-data-meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
      .current-data-pill{border:1px solid #d9dde3;background:#f7f8fa;border-radius:999px;padding:7px 11px;font:600 12px/1.2 Arial,Helvetica,sans-serif;color:#30343a}
      .current-data-note{margin:0;color:#5f646b;font-size:14px;line-height:1.55}
      .current-data-grid{display:grid;grid-template-columns:minmax(220px,.72fr) minmax(0,1.28fr);gap:22px;align-items:start}
      .current-data-controls,.current-data-results{border:1px solid #e0e2e5;border-radius:8px;background:#fff;padding:22px}
      .current-data-controls label{display:block;font-weight:700;margin-bottom:8px}
      .current-data-controls select{width:100%;min-height:44px;border:1px solid #cfd3d8;border-radius:5px;background:#fff;padding:8px 10px;font:inherit}
      .current-data-results h3{margin:0 0 6px}
      .current-data-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:16px}
      .current-data-metric{border-top:1px solid #e6e7e9;padding-top:10px}
      .current-data-metric span{display:block;color:#6b7077;font-size:12px;margin-bottom:4px}
      .current-data-metric strong{font-size:20px}
      .current-data-delta{margin-top:14px;padding:12px 14px;background:#f5f7fa;border-radius:5px;font-size:13px;line-height:1.5}
      .current-data-table{width:100%;border-collapse:collapse;margin-top:18px;font-size:13px}
      .current-data-table th,.current-data-table td{padding:8px 10px;border-top:1px solid #eceef0;text-align:right}
      .current-data-table th:first-child,.current-data-table td:first-child{text-align:left}
      .current-data-table tr.is-active{background:#f1f5ff}
      .current-data-links{display:flex;gap:16px;flex-wrap:wrap;margin-top:18px}
      .current-data-links a{font-weight:700}
      @media(max-width:760px){.current-data-grid{grid-template-columns:1fr}.current-data-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}}
    `;
    document.head.appendChild(style);
  }

  function renderLab(lab) {
    ensureStyle();
    const slug = phase();
    lab.dataset.currentDataset = 'kios-real-video';
    lab.innerHTML = `
      <div class="lab-shell current-data-shell">
        <div class="lab-heading">
          <div>
            <h2 id="lab-title">Current experiment: real KIOS landing images.</h2>
            <p>This live experiment panel now uses the protected real-image benchmark instead of generating a fresh synthetic example in the browser. The archived ${slug.toUpperCase()} record above stays frozen and is not rewritten.</p>
            <div class="current-data-meta">
              <span class="current-data-pill">422 labeled real frames</span>
              <span class="current-data-pill">86 protected test frames</span>
              <span class="current-data-pill">Temporal split + 5% embargo</span>
              <span class="current-data-pill">YOLO11n baseline</span>
            </div>
          </div>
          <a class="lab-record" href="/phases/${slug}/">Read ${slug.replace('phase','Phase ').toUpperCase()} →</a>
        </div>

        <p class="current-data-note">The same 86 protected test frames are evaluated clean and under deterministic blur, low-light, noise, occlusion, and mixed stress. None of those stress variants was used for training this baseline.</p>

        <div class="current-data-grid">
          <div class="current-data-controls">
            <label for="current-data-condition">Current test condition</label>
            <select id="current-data-condition">
              ${Object.entries(DATASET.conditions).map(([key, value]) => `<option value="${key}">${value.label}</option>`).join('')}
            </select>
            <div class="current-data-links">
              <a href="https://github.com/suhaslord/uav-safety-research/blob/main/results/real_detector/summary.md" target="_blank" rel="noreferrer">Full detector result →</a>
              <a href="https://doi.org/10.5281/zenodo.13682584" target="_blank" rel="noreferrer">Dataset source →</a>
            </div>
          </div>

          <div class="current-data-results" aria-live="polite">
            <h3 id="current-data-title">Clean protected test</h3>
            <p class="current-data-note" id="current-data-explainer"></p>
            <div class="current-data-metrics">
              <div class="current-data-metric"><span>Precision</span><strong id="metric-precision"></strong></div>
              <div class="current-data-metric"><span>Recall</span><strong id="metric-recall"></strong></div>
              <div class="current-data-metric"><span>mAP50</span><strong id="metric-map50"></strong></div>
              <div class="current-data-metric"><span>mAP50–95</span><strong id="metric-map5095"></strong></div>
            </div>
            <div class="current-data-delta" id="current-data-delta"></div>
          </div>
        </div>

        <table class="current-data-table" aria-label="Current KIOS protected-test robustness results">
          <thead><tr><th>Condition</th><th>Precision</th><th>Recall</th><th>mAP50</th><th>mAP50–95</th></tr></thead>
          <tbody>${Object.entries(DATASET.conditions).map(([key, value]) => `<tr data-condition="${key}"><td>${value.label}</td><td>${value.precision.toFixed(3)}</td><td>${value.recall.toFixed(3)}</td><td>${value.map50.toFixed(3)}</td><td>${value.map5095.toFixed(3)}</td></tr>`).join('')}</tbody>
        </table>
      </div>`;

    const select = lab.querySelector('#current-data-condition');
    const clean = DATASET.conditions.clean;
    const update = () => {
      const key = select.value;
      const row = DATASET.conditions[key];
      lab.querySelector('#current-data-title').textContent = `${row.label} protected test`;
      lab.querySelector('#metric-precision').textContent = pct(row.precision);
      lab.querySelector('#metric-recall').textContent = pct(row.recall);
      lab.querySelector('#metric-map50').textContent = pct(row.map50);
      lab.querySelector('#metric-map5095').textContent = pct(row.map5095);
      lab.querySelector('#current-data-explainer').textContent = key === 'clean'
        ? 'Baseline evaluation on the untouched protected real-image split.'
        : `The same protected real frames after the preregistered ${row.label.toLowerCase()} stress transformation.`;
      const delta = row.map50 - clean.map50;
      lab.querySelector('#current-data-delta').textContent = key === 'clean'
        ? 'Reference condition. Mixed degradation is the largest current failure mode.'
        : `mAP50 change versus clean: ${signed(delta)} (${((delta / clean.map50) * 100).toFixed(1)}% relative).`;
      lab.querySelectorAll('tbody tr').forEach(tr => tr.classList.toggle('is-active', tr.dataset.condition === key));
    };
    select.addEventListener('change', update);
    update();
  }

  function updateGuide() {
    const intro = document.querySelector('.aegis-guide .guide-intro p');
    if (intro) intro.textContent = 'The active experiment now uses the KIOS real-video landing-pad benchmark. Historical phase records remain frozen so the old simulation evidence is not silently rewritten.';
    document.querySelectorAll('.aegis-guide .guide-more p').forEach(p => {
      if (/browser experiments create new examples/i.test(p.textContent)) {
        p.textContent = 'The published phase record stays fixed. The live panel below shows the current protected real-data benchmark instead of replacing the old evidence.';
      }
    });
  }

  function apply() {
    updateGuide();
    const lab = document.getElementById('experiment-lab');
    if (!lab || lab.dataset.currentDataset === 'kios-real-video') return false;
    renderLab(lab);
    return true;
  }

  if (!apply()) {
    const observer = new MutationObserver(() => {
      if (apply()) observer.disconnect();
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });
    setTimeout(() => observer.disconnect(), 15000);
  }
})();
