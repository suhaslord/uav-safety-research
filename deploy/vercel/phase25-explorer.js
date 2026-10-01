(() => {
  const appBase = new URL('.', document.currentScript?.src || window.location.href);
  const appAsset = (path) => new URL(String(path).replace(/^\/+/, ''), appBase).pathname;
  const rootSlash = String.fromCharCode(47);
  const expected = ['clean', 'blur', 'low_light', 'noise', 'occlusion', 'mixed'];
  const explorers = [...document.querySelectorAll('[data-phase25-explorer]')];
  if (!explorers.length) return;

  const percent = (value) => `${(value * 100).toFixed(1)}%`;
  const signedPoints = (value) => `${value >= 0 ? '+' : '−'}${Math.abs(value * 100).toFixed(1)} points`;

  function setCondition(root, conditions, current) {
    const chosen = conditions.find((item) => item.key === current);
    const photo = root.querySelector('[data-atlas-image]');
    const caption = root.querySelector('[data-atlas-caption]');
    const delta = root.querySelector('[data-atlas-delta]');
    if (photo) {
      photo.src = appAsset(chosen.illustration);
      photo.alt = `Illustrative KIOS pad frame under ${chosen.title.toLowerCase()} stress, with its source annotation drawn in blue`;
    }
    if (caption) caption.textContent = chosen.title;
    if (delta) {
      const difference = chosen.robust_map50 - chosen.baseline_map50;
      delta.textContent = `${signedPoints(difference)} mAP50 on the published Phase 23 test set`;
      delta.dataset.direction = difference < 0 ? 'regressed' : 'improved';
    }
    root.querySelectorAll('[data-atlas-condition]').forEach((button) => {
      button.setAttribute('aria-pressed', String(button.dataset.atlasCondition === current));
    });
  }

  function addConditions(root, conditions) {
    const controls = root.querySelector('[data-atlas-controls]');
    if (!controls) return;
    controls.replaceChildren();
    for (const item of conditions) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'atlas-condition-button';
      button.dataset.atlasCondition = item.key;
      button.textContent = item.title;
      button.addEventListener('click', () => setCondition(root, conditions, item.key));
      controls.append(button);
    }
    setCondition(root, conditions, 'occlusion');
  }

  function addChart(root, conditions) {
    const chart = root.querySelector('[data-atlas-chart]');
    if (!chart) return;
    chart.replaceChildren();
    for (const item of conditions) {
      const row = document.createElement('div');
      row.className = 'atlas-chart-row';
      row.setAttribute('aria-label', `${item.title}: baseline mAP50 ${percent(item.baseline_map50)}, Phase 23 mAP50 ${percent(item.robust_map50)}`);
      const label = document.createElement('span');
      label.textContent = item.title;
      const bars = document.createElement('div');
      bars.className = 'atlas-chart-bars';
      bars.setAttribute('aria-hidden', 'true');
      for (const [key, title, className] of [
        ['baseline_map50', 'Baseline', 'atlas-chart-bar--baseline'],
        ['robust_map50', 'Phase 23', 'atlas-chart-bar--robust'],
      ]) {
        const track = document.createElement('div');
        track.className = 'atlas-chart-track';
        const bar = document.createElement('span');
        bar.className = `atlas-chart-bar ${className}`;
        bar.style.width = percent(item[key]);
        track.append(bar);
        track.title = `${item.title}: ${title} mAP50 ${percent(item[key])}`;
        bars.append(track);
      }
      const values = document.createElement('span');
      values.className = 'atlas-chart-values';
      values.textContent = `${Math.round(item.baseline_map50 * 100)}% / ${Math.round(item.robust_map50 * 100)}%`;
      row.append(label, bars, values);
      chart.append(row);
    }
    chart.setAttribute('aria-label', 'Published Phase 23 mAP50 by condition, baseline then robust detector');
  }

  fetch(new URL('phase25-explorer-data.json', appBase))
    .then((response) => {
      if (!response.ok) throw new Error('Condition data unavailable');
      return response.json();
    })
    .then((data) => {
      if (data.schema_version !== 1 || data.status !== 'published_aggregates_only'
        || data.conditions?.length !== expected.length
        || data.conditions.some((item, i) => item.key !== expected[i]
          || item.illustration !== `${rootSlash}media/perception/kios_${item.key}.jpg`
          || ['baseline_map50', 'robust_map50', 'baseline_recall', 'robust_recall']
            .some((key) => !Number.isFinite(item[key]) || item[key] < 0 || item[key] > 1))) {
        throw new Error('Condition data failed validation');
      }
      for (const root of explorers) {
        addConditions(root, data.conditions);
        addChart(root, data.conditions);
      }
    })
    .catch(() => {
      for (const root of explorers) {
        const note = root.querySelector('[data-atlas-error]');
        if (note) note.hidden = false;
      }
    });
})();
// Deployment sync 2026-09-30: no behavior change.
