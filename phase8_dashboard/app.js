const EXPECTED_SCHEMA = 'aegisland.phase8.trace-comparison.v1';

const state = {
  bundle: null,
  status: 'all',
  family: 'all',
};

const statusRank = {
  mismatch: 0,
  watch: 1,
  insufficient: 2,
  close: 3,
};

const byId = (id) => document.getElementById(id);

function formatNumber(value, digits = 3) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits) : '—';
}

function setText(id, value) {
  byId(id).textContent = value ?? '—';
}

function meanFromMetric(metric, side) {
  if (metric.family === 'distribution') {
    return metric?.[side]?.mean;
  }
  return metric?.[`${side}_value`];
}

function updateEvidenceBanner(bundle) {
  const banner = byId('evidenceBanner');
  const fixture = bundle.external_evidence_status === 'fixture_non_authoritative';
  banner.className = fixture ? 'evidence-banner fixture' : 'evidence-banner external';
  banner.textContent = fixture
    ? 'NON-AUTHORITATIVE FIXTURE — pipeline validation only; this is not external-simulator evidence.'
    : `${String(bundle.external_evidence_status).replaceAll('_', ' ').toUpperCase()} — model resemblance diagnostic only, not a flight-safety pass/fail.`;
}

function renderMetadata(bundle) {
  const counts = bundle.status_counts || {};
  setText('diagnostic', bundle.overall_diagnostic);
  setText('closeCount', counts.close ?? 0);
  setText('watchCount', counts.watch ?? 0);
  setText('mismatchCount', counts.mismatch ?? 0);
  setText('insufficientCount', counts.insufficient ?? 0);
  setText('claimLevel', bundle.claim_level);
  setText('gitSha', bundle.git_sha || 'not stamped');
  setText('phase7Sha', bundle.phase7_audited_baseline_commit);
  setText('phase6bSha', bundle.historical_phase6b_frozen_commit);
  setText('externalSource', bundle.external_source);
  setText('externalStatus', bundle.external_evidence_status);
  setText('thresholdPolicy', bundle.threshold_policy);
  updateEvidenceBanner(bundle);
}

function filteredMetrics() {
  if (!state.bundle) return [];
  return [...(state.bundle.metrics || [])]
    .filter((metric) => state.status === 'all' || metric.status === state.status)
    .filter((metric) => state.family === 'all' || metric.family === state.family)
    .sort((a, b) => {
      const rankDelta = (statusRank[a.status] ?? 9) - (statusRank[b.status] ?? 9);
      return rankDelta || String(a.metric).localeCompare(String(b.metric));
    });
}

function renderMetrics() {
  const body = byId('metricRows');
  body.replaceChildren();
  const metrics = filteredMetrics();
  if (!metrics.length) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 7;
    cell.className = 'empty';
    cell.textContent = state.bundle ? 'No metrics match the active filters.' : 'Load a Phase 8 comparison bundle.';
    row.appendChild(cell);
    body.appendChild(row);
    return;
  }

  for (const metric of metrics) {
    const row = document.createElement('tr');

    const metricCell = document.createElement('td');
    metricCell.textContent = String(metric.metric || 'unknown').replaceAll('_', ' ');
    row.appendChild(metricCell);

    const statusCell = document.createElement('td');
    const badge = document.createElement('span');
    badge.className = `badge ${metric.status || 'unknown'}`;
    badge.textContent = metric.status || 'unknown';
    statusCell.appendChild(badge);
    row.appendChild(statusCell);

    const surrogateCell = document.createElement('td');
    surrogateCell.textContent = formatNumber(meanFromMetric(metric, 'surrogate'));
    row.appendChild(surrogateCell);

    const externalCell = document.createElement('td');
    externalCell.textContent = formatNumber(meanFromMetric(metric, 'external'));
    row.appendChild(externalCell);

    const ksCell = document.createElement('td');
    ksCell.textContent = formatNumber(metric.ks);
    row.appendChild(ksCell);

    const w1Cell = document.createElement('td');
    w1Cell.textContent = formatNumber(metric.normalized_wasserstein_1);
    row.appendChild(w1Cell);

    const deltaCell = document.createElement('td');
    deltaCell.textContent = formatNumber(metric.delta);
    row.appendChild(deltaCell);

    body.appendChild(row);
  }
}

function renderBundle(bundle) {
  if (!bundle || bundle.schema !== EXPECTED_SCHEMA) {
    throw new Error(`Unsupported bundle schema: ${bundle?.schema ?? 'missing'}`);
  }
  if (bundle.safety_acceptance !== false || bundle.controller_tuning_allowed !== false) {
    throw new Error('Phase 8 bundle violates the no-safety-acceptance/no-controller-tuning boundary.');
  }
  state.bundle = bundle;
  renderMetadata(bundle);
  renderMetrics();
}

async function handleFile(file) {
  const status = byId('loadStatus');
  try {
    status.textContent = `Reading ${file.name}…`;
    const text = await file.text();
    const bundle = JSON.parse(text);
    renderBundle(bundle);
    status.textContent = `Loaded ${file.name}`;
  } catch (error) {
    state.bundle = null;
    status.textContent = `Could not load bundle: ${error.message}`;
    renderMetrics();
  }
}

byId('bundleFile').addEventListener('change', (event) => {
  const [file] = event.target.files || [];
  if (file) handleFile(file);
});

byId('statusFilter').addEventListener('change', (event) => {
  state.status = event.target.value;
  renderMetrics();
});

byId('familyFilter').addEventListener('change', (event) => {
  state.family = event.target.value;
  renderMetrics();
});
