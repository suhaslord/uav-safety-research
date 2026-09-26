(() => {
  'use strict';

  const DATASET = {
    name: 'KIOS Aerial Landing Pad, Unreal Engine Dataset (2024)',
    total: 422,
    train: 252,
    validation: 64,
    embargo: 20,
    test: 86,
    models: {
      phase23: {
        id: 'phase23',
        name: 'Phase 23 Robust YOLO11n',
        detail: '480px UAV domain-augmented detector (rotation, altitude scale, mosaic, random erasing, photometrics)'
      },
      baseline: {
        id: 'baseline',
        name: 'Detector baseline YOLO11n',
        detail: '320px standard baseline detector without aerial stress augmentations'
      }
    },
    conditions: {
      clean: {
        label: 'Clean',
        desc: 'Untouched protected real-image test split at approach altitude.',
        synthetic_src: '/media/perception/synthetic_clean.png',
        kios_src: '/media/perception/kios_clean.jpg',
        synthetic_note: '96×96 grayscale sensor · Centroid estimate: X +0.45m, Alt 2.5m (conf: 0.84)',
        kios_note: '1280×720 HD UAV camera · Ground truth (green) & Phase 23 detection (blue)',
        baseline: { precision: 0.796, recall: 0.384, map50: 0.427, map5095: 0.272 },
        phase23:  { precision: 0.717, recall: 0.593, map50: 0.555, map5095: 0.223 }
      },
      blur: {
        label: 'Blur',
        desc: 'High-frequency vibration and angular motion blur from UAV descent.',
        synthetic_src: '/media/perception/synthetic_blur.png',
        kios_src: '/media/perception/kios_blur.jpg',
        synthetic_note: '96×96 Gaussian blur kernel · Centroid estimate tracked (conf: 0.81)',
        kios_note: 'Deterministic UAV motion blur · Phase 23 mAP50 reaches 0.586 (+17.3 pp)',
        baseline: { precision: 0.844, recall: 0.378, map50: 0.413, map5095: 0.271 },
        phase23:  { precision: 0.777, recall: 0.570, map50: 0.586, map5095: 0.261 }
      },
      low_light: {
        label: 'Low light',
        desc: 'Severe underexposure, dusk lighting, and shadowed asphalt contrast.',
        synthetic_src: '/media/perception/synthetic_low_light.png',
        kios_src: '/media/perception/kios_low_light.jpg',
        synthetic_note: '96×96 attenuated intensity · Threshold estimator margin drops (conf: 0.64)',
        kios_note: 'Gamma & contrast reduction · Recall maintained at 44.2% (vs 37.2% baseline)',
        baseline: { precision: 0.787, recall: 0.372, map50: 0.417, map5095: 0.269 },
        phase23:  { precision: 0.635, recall: 0.442, map50: 0.424, map5095: 0.185 }
      },
      noise: {
        label: 'Noise',
        desc: 'Sensor ISO noise and downlink quantization artifacts.',
        synthetic_src: '/media/perception/synthetic_noise.png',
        kios_src: '/media/perception/kios_noise.jpg',
        synthetic_note: '96×96 additive Gaussian sensor noise · Centroid tracked (conf: 0.79)',
        kios_note: 'Severe additive pixel noise · Phase 23 mAP50 reaches 0.596 (vs 0.433 baseline)',
        baseline: { precision: 0.895, recall: 0.398, map50: 0.433, map5095: 0.262 },
        phase23:  { precision: 0.867, recall: 0.547, map50: 0.596, map5095: 0.236 }
      },
      occlusion: {
        label: 'Occlusion',
        desc: '55% synthetic central mask obstructing landing pad concentric markers.',
        synthetic_src: '/media/perception/synthetic_occlusion.png',
        kios_src: '/media/perception/kios_occlusion.jpg',
        synthetic_note: '96×96 partial occlusion · Centroid shifts to visible quadrant (conf: 0.85)',
        kios_note: 'Central occlusion mask · Both detector scores fall; controller response was not measured.',
        baseline: { precision: 0.622, recall: 0.326, map50: 0.348, map5095: 0.166 },
        phase23:  { precision: 0.301, recall: 0.244, map50: 0.138, map5095: 0.025 }
      },
      mixed: {
        label: 'Mixed',
        desc: 'Combined compound stress: blur + noise + low-light + partial occlusion.',
        synthetic_src: '/media/perception/synthetic_mixed.png',
        kios_src: '/media/perception/kios_mixed.jpg',
        synthetic_note: '96×96 compound degradation · Near failure boundary (conf: 0.54)',
        kios_note: 'Compound environmental stress · Both detector recall and mAP50 regressed',
        baseline: { precision: 0.597, recall: 0.186, map50: 0.185, map5095: 0.081 },
        phase23:  { precision: 0.487, recall: 0.081, map50: 0.129, map5095: 0.030 }
      }
    }
  };

  const pct = value => `${(value * 100).toFixed(1)}%`;
  const signed = value => `${value >= 0 ? '+' : ''}${(value * 100).toFixed(1)} pp`;
  const phase = () => document.body.dataset.phase || location.pathname.match(/phase\d+[a-z]*/i)?.[0]?.toLowerCase() || '';

  function ensureStyle() {
    if (document.getElementById('aegis-current-data-style')) return;
    const style = document.createElement('style');
    style.id = 'aegis-current-data-style';
    style.textContent = `
      .current-data-shell{display:grid;gap:28px;width:min(1440px,calc(100% - 64px));max-width:1440px;margin-inline:auto;min-width:0;box-sizing:border-box}
      .current-data-meta{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:22px;width:100%;max-width:100%;min-width:0}
      .current-data-pill{display:flex;align-items:center;min-height:48px;border:0;background:#f4f4f4;border-radius:4px;padding:10px 12px;font:600 12px/1.35 Arial,Helvetica,sans-serif;color:#3b3e42;min-width:0}
      .current-data-pill strong{color:#171a20;margin-right:4px}
      .current-data-note{margin:0;color:#5c5e62;font-size:14px;line-height:1.6}

      /* Visual Perception Inspector: Tesla clean cards */
      .perception-inspector{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:24px;margin-top:8px;width:100%;max-width:100%;min-width:0;box-sizing:border-box}
      .perception-card{background:#f4f4f4;border-radius:6px;padding:20px;display:flex;flex-direction:column;gap:12px;min-width:0;max-width:100%;box-sizing:border-box}
      .perception-card__header{display:flex;justify-content:space-between;align-items:baseline;gap:8px;flex-wrap:wrap}
      .perception-card__title{font-size:14px;font-weight:600;color:#171a20;letter-spacing:-.01em}
      .perception-card__badge{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;padding:3px 8px;border-radius:3px;background:#e3e5e8;color:#393c41}
      .perception-card__badge--robust{background:#3e6ae1;color:#fff}
      .perception-card__frame{position:relative;background:#0d0e11;border-radius:4px;overflow:hidden;border:1px solid #d0d2d5;aspect-ratio:16/9;display:flex;align-items:center;justify-content:center;width:100%;max-width:100%;min-width:0;box-sizing:border-box}
      .perception-card__frame--square{aspect-ratio:16/9;width:100%;max-width:none;margin:0 auto}
      .perception-card__frame img{width:100%;height:100%;object-fit:contain;display:block}
      .perception-card__caption{font-size:12px;line-height:1.45;color:#5c5e62}
      .perception-card__meta{font-size:11px;color:#808285;font-family:monospace;letter-spacing:-.02em;word-break:break-word}

      /* Interactive Controls & Results */
      .current-data-grid{display:grid;grid-template-columns:minmax(240px,.75fr) minmax(0,1.25fr);gap:24px;align-items:stretch;width:100%;max-width:100%;min-width:0}
      .current-data-controls,.current-data-results{border:0;border-radius:6px;background:#f4f4f4;padding:24px;min-width:0;max-width:100%;box-sizing:border-box}
      .current-data-controls{display:flex;flex-direction:column;gap:18px}
      .current-data-field{display:flex;flex-direction:column;gap:8px}
      .current-data-controls label{display:block;font-size:13px;font-weight:600;color:#3b3e42}
      .current-data-controls select{width:100%;min-height:44px;border:1px solid #c9cacc;border-radius:4px;background:#fff;padding:8px 36px 8px 11px;font:14px/1.3 Arial,Helvetica,sans-serif;color:#171a20;box-sizing:border-box}
      .current-data-controls select:focus-visible{outline:2px solid #3e6ae1;outline-offset:3px}

      /* Model Switcher Segmented Control */
      .model-switcher{display:grid;grid-template-columns:1fr 1fr;gap:4px;background:#e3e5e8;padding:3px;border-radius:4px}
      .model-switcher button{border:0;background:transparent;border-radius:3px;min-height:36px;font:600 12px Arial,Helvetica,sans-serif;color:#5c5e62;cursor:pointer;padding:6px 10px;transition:background .2s,color .2s}
      .model-switcher button.is-active{background:#fff;color:#171a20;box-shadow:0 1px 2px rgba(0,0,0,.08)}

      .current-data-results h3{margin:0 0 6px;font-size:24px;line-height:1.2;color:#171a20}
      .current-data-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:0;margin-top:20px;border-top:1px solid #d7d8da;border-bottom:1px solid #d7d8da;width:100%;max-width:100%;min-width:0}
      .current-data-metric{padding:16px 12px;min-width:0;text-align:center;border-right:1px solid #d7d8da}
      .current-data-metric:first-child{padding-left:0}
      .current-data-metric:last-child{border-right:0;padding-right:0}
      .current-data-metric span{display:block;color:#6b6d70;font-size:11px;line-height:1.3;margin-bottom:7px;text-transform:uppercase;letter-spacing:.06em}
      .current-data-metric strong{display:block;font-size:clamp(22px,2.4vw,32px);line-height:1;color:#171a20;font-weight:500}
      .current-data-delta{margin-top:16px;padding:12px 14px;background:#eef3ff;border-radius:4px;font-size:13px;line-height:1.55;color:#1e3a8a}
      .current-data-delta strong{font-weight:600}

      .current-data-table-wrap{display:block;width:100%;max-width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch}
      .current-data-table{width:100%;border-collapse:collapse;margin-top:4px;font-size:13px;background:#fff;border-top:1px solid #d7d8da;border-bottom:1px solid #d7d8da}
      .current-data-table th,.current-data-table td{padding:11px 12px;border-top:1px solid #ececee;text-align:right;white-space:nowrap}
      .current-data-table thead th{border-top:0;color:#5c5e62;font-size:11px;text-transform:uppercase;letter-spacing:.05em;font-weight:600}
      .current-data-table th:first-child,.current-data-table td:first-child{text-align:left}
      .current-data-table tr.is-active{background:#f3f6ff}
      .current-data-table tr.is-active td:first-child{box-shadow:inset 3px 0 0 #3e6ae1;font-weight:600}
      .current-data-table .gain-positive{color:#15803d;font-weight:600}

      .current-data-links{display:flex;gap:12px;flex-wrap:wrap;margin-top:auto;padding-top:12px}
      .current-data-links a{display:inline-flex;align-items:center;min-height:38px;padding:8px 12px;border-radius:4px;background:#fff;color:#171a20;font-size:13px;font-weight:600;text-decoration:none}
      .current-data-links a:hover{background:#e9e9e9}
      .phase24-callout{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:18px 28px;align-items:center;padding:22px 24px;border:1px solid #d8e1f2;border-left:3px solid #3e6ae1;border-radius:6px;background:#f8faff}
      .phase24-callout__eyebrow{grid-column:1/-1;color:#3e6ae1;font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase}
      .phase24-callout p{margin:0;color:#39404a;font-size:15px;line-height:1.55}
      .phase24-callout strong{color:#171a20}
      .phase24-callout a{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:0 16px;border-radius:4px;background:#171a20;color:#fff;font-size:13px;font-weight:650;text-decoration:none;white-space:nowrap}
      .phase24-callout a:hover{background:#3e6ae1}
      @media(max-width:640px){.phase24-callout{grid-template-columns:1fr;padding:18px}.phase24-callout__eyebrow{grid-column:auto}.phase24-callout a{justify-self:start}}

      @media(max-width:900px){
        .current-data-meta{grid-template-columns:repeat(2,minmax(0,1fr))}
        .current-data-shell{width:min(100% - 40px,1440px)}
        .perception-inspector{grid-template-columns:minmax(0,1fr)}
        .current-data-grid{grid-template-columns:minmax(0,1fr)}
        .current-data-results h3{font-size:22px}
      }
      @media(max-width:640px){
        .current-data-shell{gap:20px;width:calc(100% - 32px)}
        .perception-card__frame--square{width:100%}
        .current-data-meta{grid-template-columns:1fr;gap:8px}
        .current-data-pill{min-height:44px;font-size:11px}
        .perception-card{padding:16px}
        .current-data-controls,.current-data-results{padding:18px}
        .current-data-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}
        .current-data-metric{border-right:0;border-bottom:1px solid #d7d8da;padding:12px 6px}
        .current-data-metric:nth-child(odd){border-right:1px solid #d7d8da}
        .current-data-metric:nth-last-child(-n+2){border-bottom:0}
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
            <h2 id="lab-title">Live perception: Synthetic sensor vs. Real KIOS camera.</h2>
            <p>Compare the actual downward images the drone receives in simulation (Phases 1–22) against physical camera footage from the KIOS aerial landing benchmark and the Phase 23 robust detector.</p>
            <div class="current-data-meta">
              <span class="current-data-pill"><strong>422</strong> labeled real frames</span>
              <span class="current-data-pill"><strong>86</strong> protected test frames</span>
              <span class="current-data-pill"><strong>+20.9 pp</strong> Phase 23 clean recall change</span>
              <span class="current-data-pill"><strong>Temporal</strong> split + 5% embargo</span>
            </div>
          </div>
          <a class="lab-record" href="/phases/phase23/">Read Phase 23 →</a>
        </div>

        <!-- Visual Perception Inspector: Side-by-side drone camera feeds -->
        <div class="perception-inspector" aria-label="Drone visual perception comparison">
          <article class="perception-card">
            <div class="perception-card__header">
              <span class="perception-card__title">Synthetic simulator feed (Phases 1–22)</span>
              <span class="perception-card__badge">96×96 Grayscale</span>
            </div>
            <div class="perception-card__frame perception-card__frame--square">
              <img id="synthetic-feed-img" src="/media/perception/synthetic_clean.png" alt="Synthetic simulator downward camera feed with centroid estimator crosshair" width="384" height="384" loading="lazy">
            </div>
            <p class="perception-card__caption" id="synthetic-feed-caption">96×96 synthetic sensor abstraction with threshold centroid crosshair (+0.45m lateral offset, 2.5m altitude).</p>
            <span class="perception-card__meta" id="synthetic-feed-meta">Sensor: SyntheticLandingPadRenderer · Estimator: ThresholdPadEstimator</span>
          </article>

          <article class="perception-card">
            <div class="perception-card__header">
              <span class="perception-card__title">Real UAV downward camera (KIOS benchmark)</span>
              <span class="perception-card__badge perception-card__badge--robust">1280×720 HD RGB</span>
            </div>
            <div class="perception-card__frame">
              <img id="kios-feed-img" src="/media/perception/kios_clean.jpg" alt="Real drone downward camera frame from KIOS benchmark with landing pad bounding boxes" width="1280" height="720" loading="lazy">
            </div>
            <p class="perception-card__caption" id="kios-feed-caption">Real drone descent over asphalt terrain. Ground truth pad in green; Phase 23 robust YOLO11n detection in blue.</p>
            <span class="perception-card__meta" id="kios-feed-meta">Source: Zenodo 13682584 · Model: Phase 23 Robust (480px + UAV Augmentations)</span>
          </article>
        </div>

        <aside class="phase24-callout" aria-label="Phase 24 robustness audit">
          <span class="phase24-callout__eyebrow">Phase 24 · robustness frontier audit</span>
          <p><strong>The six-condition macro improves, but the hard tail gets worse.</strong> Phase 23 mAP50 rises by 3.4 percentage points on average; the equally weighted occlusion + mixed-stress average falls by 13.3 points. The report shows every condition.</p>
          <a href="/phases/phase24/">Open charts and results →</a>
        </aside>

        <div class="current-data-grid">
          <div class="current-data-controls">
            <div class="current-data-field">
              <label>Model evaluation</label>
              <div class="model-switcher" role="group" aria-label="Detector model selection">
                <button type="button" class="is-active" data-model="phase23">Phase 23 Robust</button>
                <button type="button" data-model="baseline">Detector baseline</button>
              </div>
            </div>

            <div class="current-data-field">
              <label for="current-data-condition">Test condition & camera stress</label>
              <select id="current-data-condition">
                ${Object.entries(DATASET.conditions).map(([key, value]) => `<option value="${key}">${value.label}</option>`).join('')}
              </select>
            </div>

            <p class="current-data-note" id="condition-description">Untouched protected real-image test split at approach altitude.</p>

            <div class="current-data-links">
              <a href="https://github.com/suhaslord/uav-safety-research/blob/main/results/phase23_robust_detector/summary.md" target="_blank" rel="noreferrer">Phase 23 result →</a>
              <a href="https://doi.org/10.5281/zenodo.13682584" target="_blank" rel="noreferrer">Dataset source →</a>
            </div>
          </div>

          <div class="current-data-results" aria-live="polite">
            <h3 id="current-data-title">Clean protected test</h3>
            <p class="current-data-note" id="current-data-model-detail">Evaluating Phase 23 Robust YOLO11n (480px with UAV augmentations).</p>
            <div class="current-data-metrics">
              <div class="current-data-metric"><span>Precision</span><strong id="metric-precision"></strong></div>
              <div class="current-data-metric"><span>Recall</span><strong id="metric-recall"></strong></div>
              <div class="current-data-metric"><span>mAP50</span><strong id="metric-map50"></strong></div>
              <div class="current-data-metric"><span>mAP50–95</span><strong id="metric-map5095"></strong></div>
            </div>
            <div class="current-data-delta" id="current-data-delta"></div>
          </div>
        </div>

        <div class="current-data-table-wrap">
          <table class="current-data-table" aria-label="KIOS real drone protected-test robustness comparison: Baseline vs Phase 23 Robust">
            <thead>
              <tr>
                <th>Condition</th>
                <th>Baseline Recall</th>
                <th>Phase 23 Recall</th>
                <th>Recall Gain</th>
                <th>Baseline mAP50</th>
                <th>Phase 23 mAP50</th>
                <th>mAP50 Delta</th>
              </tr>
            </thead>
            <tbody>
              ${Object.entries(DATASET.conditions).map(([key, value]) => {
                const rDelta = value.phase23.recall - value.baseline.recall;
                const mDelta = value.phase23.map50 - value.baseline.map50;
                const gainClass = rDelta > 0 ? 'gain-positive' : '';
                return `
                  <tr data-condition="${key}">
                    <td>${value.label}</td>
                    <td>${pct(value.baseline.recall)}</td>
                    <td><strong>${pct(value.phase23.recall)}</strong></td>
                    <td class="${gainClass}">${signed(rDelta)}</td>
                    <td>${value.baseline.map50.toFixed(3)}</td>
                    <td><strong>${value.phase23.map50.toFixed(3)}</strong></td>
                    <td class="${mDelta > 0 ? 'gain-positive' : ''}">${signed(mDelta)}</td>
                  </tr>
                `;
              }).join('')}
            </tbody>
          </table>
        </div>
      </div>`;

    const select = lab.querySelector('#current-data-condition');
    const modelButtons = lab.querySelectorAll('.model-switcher button');
    let activeModel = 'phase23';

    const update = () => {
      const key = select.value;
      const condition = DATASET.conditions[key];
      const modelMeta = DATASET.models[activeModel];
      const metrics = condition[activeModel];

      // Update Perception Images and captions
      lab.querySelector('#synthetic-feed-img').src = condition.synthetic_src;
      lab.querySelector('#synthetic-feed-caption').textContent = condition.synthetic_note;
      lab.querySelector('#kios-feed-img').src = condition.kios_src;
      lab.querySelector('#kios-feed-caption').textContent = condition.kios_note;
      lab.querySelector('#condition-description').textContent = condition.desc;

      // Update Metrics
      lab.querySelector('#current-data-title').textContent = `${condition.label} protected test`;
      lab.querySelector('#current-data-model-detail').textContent = `Evaluating ${modelMeta.name} — ${modelMeta.detail}.`;
      lab.querySelector('#metric-precision').textContent = pct(metrics.precision);
      lab.querySelector('#metric-recall').textContent = pct(metrics.recall);
      lab.querySelector('#metric-map50').textContent = pct(metrics.map50);
      lab.querySelector('#metric-map5095').textContent = pct(metrics.map5095);

      // Delta readout comparing Phase 23 vs Baseline
      const recallDelta = condition.phase23.recall - condition.baseline.recall;
      const mapDelta = condition.phase23.map50 - condition.baseline.map50;
      lab.querySelector('#current-data-delta').innerHTML = activeModel === 'phase23'
        ? `<strong>Phase 23 vs Baseline on ${condition.label}:</strong> Recall changed by ${signed(recallDelta)} (${pct(condition.phase23.recall)} vs ${pct(condition.baseline.recall)}). mAP50 changed by ${signed(mapDelta)}.`
        : `<strong>Baseline performance on ${condition.label}:</strong> Recall is ${pct(condition.baseline.recall)}, mAP50 is ${condition.baseline.map50.toFixed(3)}. Switch to Phase 23 to compare its metrics on this condition.`;

      // Active table row
      lab.querySelectorAll('tbody tr').forEach(tr => tr.classList.toggle('is-active', tr.dataset.condition === key));
    };

    select.addEventListener('change', update);
    modelButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        modelButtons.forEach(b => b.classList.remove('is-active'));
        btn.classList.add('is-active');
        activeModel = btn.dataset.model;
        update();
      });
    });

    update();
  }

  function updateGuide() {
    const intro = document.querySelector('.aegis-guide .guide-intro p');
    if (intro) intro.textContent = 'The active experiment uses the KIOS real-video landing-pad benchmark. Historical phase records remain frozen so past simulation evidence is not silently rewritten.';
    document.querySelectorAll('.aegis-guide .guide-more p').forEach(p => {
      if (/browser experiments create new examples/i.test(p.textContent)) {
        p.textContent = 'The published phase record stays fixed. The live panel below shows the current protected real-data benchmark and drone perception feeds instead of replacing the old evidence.';
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
