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
      /* Current-data surfaces use the same visual language as the original AegisLand site. */
      .current-data-shell{display:grid;gap:28px}
      .current-data-meta{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:22px}
      .current-data-pill{display:flex;align-items:center;min-height:48px;border:0;background:#f4f4f4;border-radius:4px;padding:10px 12px;font:600 12px/1.35 Arial,Helvetica,sans-serif;color:#3b3e42}
      .current-data-note{margin:0;color:#5c5e62;font-size:14px;line-height:1.6}
      .current-data-grid{display:grid;grid-template-columns:minmax(240px,.7fr) minmax(0,1.3fr);gap:24px;align-items:stretch}
      .current-data-controls,.current-data-results{border:0;border-radius:6px;background:#f4f4f4;padding:24px;min-width:0}
      .current-data-controls{display:flex;flex-direction:column}
      .current-data-controls label{display:block;font-size:13px;font-weight:600;margin-bottom:9px;color:#3b3e42}
      .current-data-controls select{width:100%;min-height:44px;border:1px solid #c9cacc;border-radius:4px;background:#fff;padding:8px 36px 8px 11px;font:14px/1.3 Arial,Helvetica,sans-serif;color:#171a20}
      .current-data-controls select:focus-visible{outline:2px solid #3e6ae1;outline-offset:3px}
      .current-data-results h3{margin:0 0 6px;font-size:24px;line-height:1.2;color:#171a20}
      .current-data-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:0;margin-top:22px;border-top:1px solid #d7d8da;border-bottom:1px solid #d7d8da}
      .current-data-metric{padding:16px 12px;min-width:0;text-align:center;border-right:1px solid #d7d8da}
      .current-data-metric:first-child{padding-left:0}
      .current-data-metric:last-child{border-right:0;padding-right:0}
      .current-data-metric span{display:block;color:#6b6d70;font-size:11px;line-height:1.3;margin-bottom:7px;text-transform:uppercase;letter-spacing:.06em}
      .current-data-metric strong{display:block;font-size:clamp(22px,2.4vw,34px);line-height:1;color:#171a20;font-weight:500}
      .current-data-delta{margin-top:18px;padding:0;font-size:13px;line-height:1.55;color:#4d5156}
      .current-data-table{width:100%;border-collapse:collapse;margin-top:0;font-size:13px;background:#fff;border-top:1px solid #d7d8da;border-bottom:1px solid #d7d8da}
      .current-data-table th,.current-data-table td{padding:11px 12px;border-top:1px solid #ececee;text-align:right;white-space:nowrap}
      .current-data-table thead th{border-top:0;color:#5c5e62;font-size:11px;text-transform:uppercase;letter-spacing:.05em;font-weight:600}
      .current-data-table th:first-child,.current-data-table td:first-child{text-align:left}
      .current-data-table tr.is-active{background:#f3f6ff}
      .current-data-table tr.is-active td:first-child{box-shadow:inset 3px 0 0 #3e6ae1;font-weight:600}
      .current-data-links{display:flex;gap:12px;flex-wrap:wrap;margin-top:auto;padding-top:24px}
      .current-data-links a{display:inline-flex;align-items:center;min-height:40px;padding:9px 12px;border-radius:4px;background:#fff;color:#171a20;font-size:13px;font-weight:600;text-decoration:none}
      .current-data-links a:hover{background:#e9e9e9}

      /* The old-vs-current evidence block should feel native, not like an embedded report. */
      .home-workspace #understanding{background:#fff!important}
      .home-workspace #understanding .section-head{margin-bottom:34px!important}
      .home-workspace #understanding .evidence-list{margin-bottom:36px!important}
      .home-workspace #understanding .research-photo{min-width:0!important;margin:0!important}
      .home-workspace #understanding .research-photo>div[style]{padding:22px!important;border:0!important;border-radius:6px!important;background:#f4f4f4!important;min-height:100%;box-sizing:border-box}
      .home-workspace #understanding .research-photo>div[style]>div:first-child{font-size:12px!important;letter-spacing:.055em!important;color:#5c5e62!important;margin-bottom:14px!important}
      .home-workspace #understanding .research-photo:first-of-type>div[style]>div:nth-child(2){gap:10px!important}
      .home-workspace #understanding .research-photo:first-of-type>div[style]>div:nth-child(2) img{width:100%!important;aspect-ratio:1/1!important;object-fit:cover!important;border:1px solid #d8d9db!important;border-radius:3px!important;background:#171a20!important}
      .home-workspace #understanding .research-photo:first-of-type>div[style]>div:nth-child(3){gap:10px!important;margin-top:8px!important;color:#5c5e62!important;font-size:10px!important;line-height:1.2!important}
      .home-workspace #understanding .research-photo:nth-of-type(2)>div[style]>div:nth-child(2){font-size:12px!important;color:#5c5e62!important;line-height:1.45!important;margin-bottom:14px!important}
      .home-workspace #understanding table{background:transparent!important}
      .home-workspace #understanding th{font-size:10px!important;text-transform:uppercase!important;letter-spacing:.05em!important;color:#686b70!important;font-weight:600!important}
      .home-workspace #understanding td,.home-workspace #understanding th{padding:9px 6px!important;border-color:#d8d9db!important}
      .home-workspace #understanding tbody tr:last-child{background:#eef3ff!important}
      .home-workspace #understanding .research-photo figcaption{display:flex!important;flex-direction:column!important;gap:3px!important;padding:12px 2px 0!important;margin:0!important;background:transparent!important;border:0!important;color:#5c5e62!important}
      .home-workspace #understanding .research-photo figcaption span{font-size:11px!important;line-height:1.45!important;color:#5c5e62!important}
      .home-workspace #understanding .research-photo figcaption .research-photo__context{font-weight:600!important;color:#31343a!important}
      .home-workspace #understanding .research-alert{margin-top:38px!important;margin-bottom:0!important}

      @media(max-width:900px){
        .current-data-meta{grid-template-columns:repeat(2,minmax(0,1fr))}
        .current-data-grid{grid-template-columns:1fr}
        .current-data-results h3{font-size:22px}
      }
      @media(max-width:640px){
        .current-data-shell{gap:22px}
        .current-data-meta{grid-template-columns:1fr 1fr;gap:8px}
        .current-data-pill{min-height:44px;font-size:11px}
        .current-data-controls,.current-data-results{padding:18px}
        .current-data-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}
        .current-data-metric{border-right:0;border-bottom:1px solid #d7d8da;padding:14px 8px}
        .current-data-metric:nth-child(odd){border-right:1px solid #d7d8da}
        .current-data-metric:nth-last-child(-n+2){border-bottom:0}
        .current-data-table{display:block;overflow-x:auto;-webkit-overflow-scrolling:touch}
        .home-workspace #understanding .research-photo>div[style]{padding:16px!important}
        .home-workspace #understanding .research-photo:first-of-type>div[style]>div:nth-child(2){grid-template-columns:repeat(3,minmax(0,1fr))!important}
        .home-workspace #understanding .research-photo:first-of-type>div[style]>div:nth-child(3){grid-template-columns:repeat(3,minmax(0,1fr))!important}
        .home-workspace #understanding .research-photo:first-of-type>div[style]>div:nth-child(3) span:nth-child(n+4){display:none!important}
      }
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
            <p>This live experiment panel uses the protected real-image benchmark. The archived ${slug.toUpperCase()} record above stays frozen and is not rewritten.</p>
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
            <label for="current-data-condition">Test condition</label>
            <select id="current-data-condition">
              ${Object.entries(DATASET.conditions).map(([key, value]) => `<option value="${key}">${value.label}</option>`).join('')}
            </select>
            <div class="current-data-links">
              <a href="https://github.com/suhaslord/uav-safety-research/blob/main/results/real_detector/summary.md" target="_blank" rel="noreferrer">Full result →</a>
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
    if (intro) intro.textContent = 'The active experiment uses the KIOS real-video landing-pad benchmark. Historical phase records remain frozen so the old simulation evidence is not silently rewritten.';
    document.querySelectorAll('.aegis-guide .guide-more p').forEach(p => {
      if (/browser experiments create new examples/i.test(p.textContent)) {
        p.textContent = 'The published phase record stays fixed. The live panel below shows the current protected real-data benchmark instead of replacing the old evidence.';
      }
    });
  }

  function apply() {
    ensureStyle();
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
