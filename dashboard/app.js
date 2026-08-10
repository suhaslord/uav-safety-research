const state = {
  summary: [],
  paired: [],
  metadata: null,
};

const els = {
  bundleFile: document.getElementById('bundleFile'),
  summaryFile: document.getElementById('summaryFile'),
  pairedFile: document.getElementById('pairedFile'),
  bundleDropzone: document.getElementById('bundleDropzone'),
  summaryDropzone: document.getElementById('summaryDropzone'),
  pairedDropzone: document.getElementById('pairedDropzone'),
  condition: document.getElementById('conditionFilter'),
  fault: document.getElementById('faultFilter'),
  plant: document.getElementById('plantFilter'),
  reset: document.getElementById('resetButton'),
  analysisMode: document.getElementById('analysisMode'),
  loadedSource: document.getElementById('loadedSource'),
  success: document.getElementById('successMetric'),
  successCI: document.getElementById('successCI'),
  unsafe: document.getElementById('unsafeMetric'),
  unsafeCI: document.getElementById('unsafeCI'),
  abort: document.getElementById('abortMetric'),
  abortCI: document.getElementById('abortCI'),
  reference: document.getElementById('referenceMetric'),
  latency: document.getElementById('latencyMetric'),
  legacyUnsafe: document.getElementById('legacyUnsafe'),
  phase7Unsafe: document.getElementById('phase7Unsafe'),
  unsafeDelta: document.getElementById('unsafeDelta'),
  successDelta: document.getElementById('successDelta'),
  pairedStatus: document.getElementById('pairedStatus'),
  evidenceTitle: document.getElementById('evidenceTitle'),
  evidenceText: document.getElementById('evidenceText'),
  matrix: document.getElementById('matrix'),
  matrixPlantLabel: document.getElementById('matrixPlantLabel'),
  weaknessList: document.getElementById('weaknessList'),
  rankingPlantLabel: document.getElementById('rankingPlantLabel'),
  provenanceMeta: document.getElementById('provenanceMeta'),
};

function parseCsv(text) {
  const rows = [];
  let row = [];
  let value = '';
  let quoted = false;

  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    const next = text[i + 1];
    if (ch === '"' && quoted && next === '"') {
      value += '"';
      i += 1;
    } else if (ch === '"') {
      quoted = !quoted;
    } else if (ch === ',' && !quoted) {
      row.push(value);
      value = '';
    } else if ((ch === '\n' || ch === '\r') && !quoted) {
      if (ch === '\r' && next === '\n') i += 1;
      row.push(value);
      value = '';
      if (row.some(cell => cell.trim() !== '')) rows.push(row);
      row = [];
    } else {
      value += ch;
    }
  }
  if (value.length || row.length) {
    row.push(value);
    if (row.some(cell => cell.trim() !== '')) rows.push(row);
  }
  if (!rows.length) return [];

  const headers = rows[0].map(h => h.trim());
  return rows.slice(1).map(cells => Object.fromEntries(headers.map((h, i) => [h, (cells[i] ?? '').trim()])));
}

function num(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function pct(value, digits = 1) {
  const n = num(value);
  return n === null ? '—' : `${(100 * n).toFixed(digits)}%`;
}

function pp(value, digits = 1) {
  const n = num(value);
  if (n === null) return '—';
  const sign = n > 0 ? '+' : '';
  return `${sign}${n.toFixed(digits)} pp`;
}

function ci(low, high) {
  if (num(low) === null || num(high) === null) return '95% CI unavailable';
  return `95% CI ${pct(low)} – ${pct(high)}`;
}

function human(value) {
  return String(value ?? '').replaceAll('_', ' ');
}

function unique(key) {
  return [...new Set(state.summary.map(r => r[key]).filter(Boolean))].sort();
}

function fillSelect(select, values) {
  select.innerHTML = '';
  for (const value of values) {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = human(value);
    select.appendChild(option);
  }
  select.disabled = values.length === 0;
}

function currentRow(plantOverride = null) {
  const plant = plantOverride ?? els.plant.value;
  return state.summary.find(r =>
    r.condition === els.condition.value &&
    r.fault_scenario === els.fault.value &&
    r.plant_model === plant
  ) ?? null;
}

function validateSummary(rows) {
  const required = ['condition', 'fault_scenario', 'plant_model', 'success_rate', 'unsafe_touchdown_rate'];
  if (!Array.isArray(rows) || !rows.length) throw new Error('The result summary contains no rows.');
  const missing = required.filter(k => !(k in rows[0]));
  if (missing.length) throw new Error(`Result summary is missing: ${missing.join(', ')}`);
}

function setLoaded(fileName) {
  const conditions = unique('condition').length;
  const faults = unique('fault_scenario').length;
  const plants = unique('plant_model').length;
  els.analysisMode.textContent = `${conditions} conditions · ${faults} faults · ${plants} plants`;
  els.loadedSource.textContent = `${fileName} · ${state.summary.length} aggregate cells loaded`;
  renderProvenance();
}

function renderProvenance() {
  if (!state.metadata) {
    els.provenanceMeta.textContent = 'CSV mode · no run metadata loaded.';
    return;
  }
  const m = state.metadata;
  const seed = m.episode_seed ?? 'unknown';
  const role = human(m.run_role ?? 'unknown');
  const count = m.episodes_per_condition_fault_plant ?? 'unknown';
  const seedStatus = human(m.episode_seed_status ?? 'unknown');
  const sha = String(m.git_sha ?? 'unknown');
  const shortSha = sha === 'unknown' ? sha : sha.slice(0, 12);
  els.provenanceMeta.textContent = `Run role: ${role} · commit ${shortSha} · episode seed ${seed} (${seedStatus}) · ${count} episodes per condition/fault/plant cell.`;
}

function initializeFilters() {
  fillSelect(els.condition, unique('condition'));
  fillSelect(els.fault, unique('fault_scenario'));
  fillSelect(els.plant, unique('plant_model'));
  els.reset.disabled = false;
  render();
}

function renderMetrics(row) {
  if (!row) {
    [els.success, els.unsafe, els.abort, els.reference].forEach(el => { el.textContent = '—'; });
    els.successCI.textContent = '95% CI';
    els.unsafeCI.textContent = '95% CI';
    els.abortCI.textContent = '95% CI';
    els.latency.textContent = 'Transport —';
    return;
  }
  els.success.textContent = pct(row.success_rate);
  els.successCI.textContent = ci(row.success_ci_low, row.success_ci_high);
  els.unsafe.textContent = pct(row.unsafe_touchdown_rate);
  els.unsafeCI.textContent = ci(row.unsafe_ci_low, row.unsafe_ci_high);
  els.abort.textContent = pct(row.abort_rate);
  els.abortCI.textContent = ci(row.abort_ci_low, row.abort_ci_high);
  els.reference.textContent = pct(row.mean_reference_available_rate);

  const delivery = num(row.mean_reference_delivery_rate);
  const configured = num(row.mean_reference_latency_steps);
  const delivered = num(row.mean_delivered_transport_latency_steps);
  const age = num(row.mean_reference_age_steps);
  const parts = [];
  if (delivery !== null) parts.push(`delivery ${pct(delivery)}`);
  if (configured !== null) parts.push(`configured ${configured.toFixed(2)} steps`);
  if (delivered !== null) parts.push(`delivered ${delivered.toFixed(2)}`);
  if (age !== null) parts.push(`state age ${age.toFixed(2)}`);
  els.latency.textContent = parts.length ? parts.join(' · ') : 'Transport diagnostics unavailable';
}

function findPairedRow() {
  return state.paired.find(r => r.condition === els.condition.value && r.fault_scenario === els.fault.value) ?? null;
}

function renderComparison() {
  const legacy = currentRow('legacy');
  const stronger = currentRow('phase7');
  els.legacyUnsafe.textContent = legacy ? pct(legacy.unsafe_touchdown_rate) : '—';
  els.phase7Unsafe.textContent = stronger ? pct(stronger.unsafe_touchdown_rate) : '—';

  const paired = findPairedRow();
  if (paired) {
    els.unsafeDelta.textContent = pp(paired.phase7_minus_legacy_unsafe_pp);
    els.successDelta.textContent = `Δ success ${pp(paired.phase7_minus_legacy_success_pp)}`;
    els.pairedStatus.textContent = `${paired.paired_episodes || 'paired'} paired episodes`;
  } else if (legacy && stronger) {
    const unsafe = 100 * (num(stronger.unsafe_touchdown_rate) - num(legacy.unsafe_touchdown_rate));
    const success = 100 * (num(stronger.success_rate) - num(legacy.success_rate));
    els.unsafeDelta.textContent = pp(unsafe);
    els.successDelta.textContent = `Δ success ${pp(success)}`;
    els.pairedStatus.textContent = 'Aggregate comparison';
  } else {
    els.unsafeDelta.textContent = '—';
    els.successDelta.textContent = 'Δ success —';
    els.pairedStatus.textContent = 'Comparison unavailable';
  }
}

function renderEvidence() {
  const selected = currentRow();
  const legacy = currentRow('legacy');
  const stronger = currentRow('phase7');
  if (!selected) {
    els.evidenceTitle.textContent = 'No matching result';
    els.evidenceText.textContent = 'The selected condition/fault/plant combination is not present in this bundle.';
    return;
  }

  const unsafe = num(selected.unsafe_touchdown_rate) ?? 0;
  const fault = human(els.fault.value);
  const plant = els.plant.value;
  const delta = legacy && stronger
    ? 100 * ((num(stronger.unsafe_touchdown_rate) ?? 0) - (num(legacy.unsafe_touchdown_rate) ?? 0))
    : null;

  if (fault === 'shared lateral bias' && unsafe > 0) {
    els.evidenceTitle.textContent = 'Common-mode bias is a visible weakness';
    els.evidenceText.textContent = `Unsafe touchdown is ${pct(unsafe)} for this cell. Because the fault moves both sensing streams in the same direction, estimator agreement is no longer strong evidence of correctness. Treat this as external-validity evidence, not a parameter-tuning target.`;
  } else if (delta !== null && Math.abs(delta) >= 10) {
    els.evidenceTitle.textContent = 'Plant choice materially changes the outcome';
    els.evidenceText.textContent = `For this condition/fault pair, the stronger plant changes unsafe touchdown by ${pp(delta)} versus the legacy plant. That association suggests plant-model sensitivity is large enough to report separately from sensing/fault robustness.`;
  } else if (unsafe === 0) {
    els.evidenceTitle.textContent = 'No unsafe touchdown observed in this cell';
    els.evidenceText.textContent = `This development bundle observed 0% unsafe touchdown for ${fault} on the ${plant} plant. That is not evidence of zero real risk; use the confidence interval, sample count, and additional seed families before making a stronger claim.`;
  } else {
    els.evidenceTitle.textContent = 'Failure remains under distribution shift';
    els.evidenceText.textContent = `Unsafe touchdown is ${pct(unsafe)} for ${fault} on the ${plant} plant. Keep the failure visible and compare it against paired plant effects before attributing it to sensing or dynamics.`;
  }
}

function heatColor(rate) {
  const r = Math.max(0, Math.min(1, num(rate) ?? 0));
  if (r === 0) return 'rgba(125, 226, 173, 0.10)';
  const alpha = 0.12 + 0.58 * r;
  return `rgba(255, 125, 133, ${alpha.toFixed(3)})`;
}

function renderMatrix() {
  if (!state.summary.length) return;
  const plant = els.plant.value;
  const conditions = unique('condition');
  const faults = unique('fault_scenario');
  els.matrixPlantLabel.textContent = `${human(plant)} plant`;

  const table = document.createElement('table');
  table.className = 'matrix-table';
  const thead = document.createElement('thead');
  const headRow = document.createElement('tr');
  headRow.appendChild(document.createElement('th'));
  faults.forEach(fault => {
    const th = document.createElement('th');
    th.textContent = human(fault);
    headRow.appendChild(th);
  });
  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  conditions.forEach(condition => {
    const tr = document.createElement('tr');
    const label = document.createElement('th');
    label.textContent = human(condition);
    tr.appendChild(label);
    faults.forEach(fault => {
      const row = state.summary.find(r => r.condition === condition && r.fault_scenario === fault && r.plant_model === plant);
      const td = document.createElement('td');
      const rate = row ? row.unsafe_touchdown_rate : null;
      td.textContent = row ? pct(rate) : '—';
      td.style.background = row ? heatColor(rate) : 'rgba(255,255,255,.025)';
      td.title = `${condition} · ${fault} · ${plant}`;
      td.addEventListener('click', () => {
        els.condition.value = condition;
        els.fault.value = fault;
        render();
        window.scrollTo({ top: document.querySelector('.controls').offsetTop - 20, behavior: 'smooth' });
      });
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);

  els.matrix.className = 'matrix';
  els.matrix.innerHTML = '';
  els.matrix.appendChild(table);
}

function renderWeaknesses() {
  if (!state.summary.length) return;
  const plant = els.plant.value;
  els.rankingPlantLabel.textContent = `${human(plant)} plant`;

  const rows = state.summary
    .filter(row => row.plant_model === plant)
    .slice()
    .sort((a, b) => {
      const unsafeDiff = (num(b.unsafe_touchdown_rate) ?? -1) - (num(a.unsafe_touchdown_rate) ?? -1);
      if (unsafeDiff !== 0) return unsafeDiff;
      const successDiff = (num(a.success_rate) ?? 1) - (num(b.success_rate) ?? 1);
      if (successDiff !== 0) return successDiff;
      return `${a.condition}/${a.fault_scenario}`.localeCompare(`${b.condition}/${b.fault_scenario}`);
    })
    .slice(0, 6);

  els.weaknessList.className = 'weakness-list';
  els.weaknessList.innerHTML = '';
  rows.forEach(row => {
    const card = document.createElement('div');
    card.className = 'weakness-row';
    card.tabIndex = 0;
    card.setAttribute('role', 'button');
    card.setAttribute('aria-label', `Inspect ${human(row.condition)} ${human(row.fault_scenario)}`);

    const label = document.createElement('div');
    label.className = 'weakness-label';
    const title = document.createElement('strong');
    title.textContent = `${human(row.condition)} · ${human(row.fault_scenario)}`;
    const note = document.createElement('span');
    note.textContent = `n=${row.episodes ?? '—'} · success ${pct(row.success_rate)} · abort ${pct(row.abort_rate)}`;
    label.append(title, note);

    const rate = document.createElement('div');
    rate.className = 'weakness-rate';
    const strong = document.createElement('strong');
    strong.textContent = pct(row.unsafe_touchdown_rate);
    const interval = document.createElement('span');
    interval.textContent = ci(row.unsafe_ci_low, row.unsafe_ci_high);
    rate.append(strong, interval);

    const selectCell = () => {
      els.condition.value = row.condition;
      els.fault.value = row.fault_scenario;
      render();
      window.scrollTo({ top: document.querySelector('.controls').offsetTop - 20, behavior: 'smooth' });
    };
    card.addEventListener('click', selectCell);
    card.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        selectCell();
      }
    });

    card.append(label, rate);
    els.weaknessList.appendChild(card);
  });
}

function render() {
  renderMetrics(currentRow());
  renderComparison();
  renderEvidence();
  renderMatrix();
  renderWeaknesses();
  renderProvenance();
}

async function loadBundle(file) {
  try {
    const payload = JSON.parse(await file.text());
    if (payload.schema !== 'aegisland.phase7.dashboard-bundle.v1') {
      throw new Error('Unsupported dashboard bundle schema.');
    }
    validateSummary(payload.summary);
    state.summary = payload.summary;
    state.paired = Array.isArray(payload.paired_plant_effects) ? payload.paired_plant_effects : [];
    state.metadata = payload.metadata ?? null;
    setLoaded(file.name);
    initializeFilters();
  } catch (error) {
    alert(error.message || 'Could not load dashboard_bundle.json');
  }
}

async function loadSummary(file) {
  try {
    const rows = parseCsv(await file.text());
    validateSummary(rows);
    state.summary = rows;
    state.metadata = null;
    setLoaded(file.name);
    initializeFilters();
  } catch (error) {
    alert(error.message || 'Could not load summary.csv');
  }
}

async function loadPaired(file) {
  try {
    state.paired = parseCsv(await file.text());
    renderComparison();
  } catch (error) {
    alert(error.message || 'Could not load paired_plant_effects.csv');
  }
}

function attachDropzone(zone, input, handler) {
  input.addEventListener('change', () => {
    if (input.files?.[0]) handler(input.files[0]);
  });
  ['dragenter', 'dragover'].forEach(type => zone.addEventListener(type, event => {
    event.preventDefault();
    zone.classList.add('dragging');
  }));
  ['dragleave', 'drop'].forEach(type => zone.addEventListener(type, event => {
    event.preventDefault();
    zone.classList.remove('dragging');
  }));
  zone.addEventListener('drop', event => {
    const file = event.dataTransfer?.files?.[0];
    if (file) handler(file);
  });
}

attachDropzone(els.bundleDropzone, els.bundleFile, loadBundle);
attachDropzone(els.summaryDropzone, els.summaryFile, loadSummary);
attachDropzone(els.pairedDropzone, els.pairedFile, loadPaired);
[els.condition, els.fault, els.plant].forEach(select => select.addEventListener('change', render));
els.reset.addEventListener('click', () => {
  els.condition.selectedIndex = 0;
  els.fault.selectedIndex = 0;
  els.plant.selectedIndex = 0;
  render();
});
