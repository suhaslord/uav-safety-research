(() => {
  'use strict';

  // Bind the route immediately, before the legacy renderer's DOMContentLoaded handler.
  // This makes Phase 10R render as its own native record instead of falling through
  // the older phase1–phase10 route matcher and visually masquerading as Phase 10.
  const routeMatch = location.pathname.match(/\/phases\/(phase(?:1|2|3|4|5|6|6b|7|8|9|10r?|11|12|13a|13b|13c|14|15|16|17|18|19|20|21|22))\/?$/i);
  if (routeMatch) document.body.dataset.phase = routeMatch[1].toLowerCase();

  // Every archive/detail template already loads this taxonomy before its phase runtime.
  // Attach the final shared visual guardrail here so legacy, Phase 11, frozen detail,
  // and the archive all receive the same interaction/readability layer.
  if (!document.querySelector('link[data-aegis-phase-ui-consistency]')) {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = '/phase-ui-consistency.css?v=1';
    link.dataset.aegisPhaseUiConsistency = '';
    document.head.appendChild(link);
  }

  // Older phase templates still carry the pre-redesign dark theme-color meta tag.
  // Keep mobile browser chrome consistent with the actual light workspace without
  // touching any scientific page content.
  const themeColor = document.querySelector('meta[name="theme-color"]');
  if (themeColor) themeColor.setAttribute('content', '#ffffff');

  // Shared exploratory runner. Frozen records remain unchanged.
  if (!document.querySelector('script[data-aegis-experiment-lab]')) {
    const style = document.createElement('link');
    style.rel = 'stylesheet'; style.href = '/lab/lab.css?v=5';
    document.head.appendChild(style);
    const runner = document.createElement('script');
    runner.src = '/lab/lab.js?v=5'; runner.dataset.aegisExperimentLab = '';
    document.head.appendChild(runner);
  }

  const categories = [
    {
      id: 'safety-architecture',
      label: '01 · Safety architecture',
      name: 'Safety architecture',
      range: 'Phase 1 → Phase 4',
      description: 'The project starts here: add a safety layer, make it less reactive, bring in independent evidence, and keep the real gap in the research record.',
      accent: '#3e6ae1',
      tint: '#eef3ff'
    },
    {
      id: 'perception-robustness',
      label: '02 · Perception + robustness',
      name: 'Perception + robustness',
      range: 'Phase 5 → Phase 6B',
      description: 'Move from abstract error signals to actual image-based estimates, then test how confidence, tracking, and partial uncertainty behave.',
      accent: '#4d6f9d',
      tint: '#f0f4f8'
    },
    {
      id: 'external-validation',
      label: '03 · External validation',
      name: 'External validation',
      range: 'Phase 7 → Phase 10R',
      description: 'Make the simulation harder, compare it with PX4 and Gazebo, and see what breaks when camera geometry and conditions shift.',
      accent: '#416b78',
      tint: '#eef5f6'
    },
    {
      id: 'reliability-calibration',
      label: '04 · Reliability + calibration',
      name: 'Reliability + calibration',
      range: 'Phase 11 → Phase 13C',
      description: 'Ask whether the system can stay useful without becoming overconfident, then test whether those uncertainty claims hold in harder conditions.',
      accent: '#5a6484',
      tint: '#f1f2f7'
    },
    {
      id: 'latency-dynamics',
      label: '05 · Latency + error dynamics',
      name: 'Latency + error dynamics',
      range: 'Phase 14 → Phase 19',
      description: 'Separate the damage caused by stale estimates from the short-term patterns left in the residuals, while keeping failed ideas in the record.',
      accent: '#596f63',
      tint: '#f1f5f2'
    },
    {
      id: 'context-transfer',
      label: '06 · Context structure + transfer',
      name: 'Context structure + transfer',
      range: 'Phase 20 → Phase 22',
      description: 'Break down which synthetic conditions matter, study how those effects combine, and test whether a frozen model carries over without being refit.',
      accent: '#365f8d',
      tint: '#eef4fa'
    }
  ];

  const bySlug = {
    phase1: { category: 'safety-architecture', identity: 'The safety gate', question: 'Can a confidence check stop an unsafe action before touchdown?', signal: 'HOLD / ABORT' },
    phase2: { category: 'safety-architecture', identity: 'The stabilizer', question: 'Can the supervisor avoid overreacting to one bad frame?', signal: 'Temporal risk' },
    phase3: { category: 'safety-architecture', identity: 'The second opinion', question: 'What changes when vision gets an independent second estimate?', signal: 'Disagreement' },
    phase4: { category: 'safety-architecture', identity: 'The missing phase', question: 'What should the archive show when a numbered experiment never existed?', signal: 'No invented result' },

    phase5: { category: 'perception-robustness', identity: 'The stress test', question: 'Does the design still hold up under stronger stress and the first move to pixels?', signal: 'Robustness' },
    phase6: { category: 'perception-robustness', identity: 'The image loop', question: 'Can image-based measurements drive the full simulated landing loop?', signal: 'Pixels → control' },
    phase6b: { category: 'perception-robustness', identity: 'The selective confidence layer', question: 'What if lateral position looks reliable but altitude does not?', signal: 'Component confidence' },

    phase7: { category: 'external-validation', identity: 'The realism stress test', question: 'How much of the result depends on an overly forgiving simulator?', signal: 'Latency + faults' },
    phase8: { category: 'external-validation', identity: 'The simulator comparison', question: 'How closely does the internal simulator match PX4 and Gazebo?', signal: 'Trace mismatch' },
    phase9: { category: 'external-validation', identity: 'The camera geometry test', question: 'What happens when the estimator uses real Gazebo camera frames?', signal: 'PnP geometry' },
    phase10: { category: 'external-validation', identity: 'The temporal estimator', question: 'Can recent state protect metric perception when the camera geometry is ambiguous?', signal: 'Causal tracking' },
    phase10r: { category: 'external-validation', identity: 'The shifted holdout', question: 'Do the strong average gains survive when geometry and appearance both change?', signal: 'Tail + coverage' },

    phase11: { category: 'reliability-calibration', identity: 'The protected reliability test', question: 'Can availability recover without hiding uncertainty problems?', signal: 'Protected gates' },
    phase12: { category: 'reliability-calibration', identity: 'The uncertainty baseline', question: 'Can normalized conformal uncertainty serve as a stable frozen reference?', signal: 'Coverage' },
    phase13a: { category: 'reliability-calibration', identity: 'The validity stress test', question: 'Does the frozen uncertainty result survive a harder external-validity challenge?', signal: 'FAIL preserved' },
    phase13b: { category: 'reliability-calibration', identity: 'The paired degradation test', question: 'Do the locked claims still hold under paired degradation?', signal: 'FAIL preserved' },
    phase13c: { category: 'reliability-calibration', identity: 'The attribution test', question: 'Which frozen synthetic factor contributes most to the coverage failure?', signal: 'Latency attribution' },

    phase14: { category: 'latency-dynamics', identity: 'The bridge attempt', question: 'Can uncertainty width be turned into a useful recoverability bound?', signal: '0 admitted' },
    phase15: { category: 'latency-dynamics', identity: 'The feasibility check', question: 'Is the preregistered latency frontier actually outside the historical range?', signal: 'Frontier test' },
    phase16: { category: 'latency-dynamics', identity: 'The staleness test', question: 'What does a two-frame-old estimate do to the actual error level?', signal: 'Level error' },
    phase17: { category: 'latency-dynamics', identity: 'The coefficient mismatch test', question: 'Does the useful coefficient change when the context changes?', signal: 'Context mismatch' },
    phase18: { category: 'latency-dynamics', identity: 'The protected confirmation', question: 'Does the residual advantage survive the protected q90 checks?', signal: 'Protected FAIL' },
    phase19: { category: 'latency-dynamics', identity: 'The residual effect', question: 'Does the narrower residual advantage repeat across the full error distribution?', signal: 'RMSE / MAE' },

    phase20: { category: 'context-transfer', identity: 'The factor breakdown', question: 'Which predefined conditions explain the drop from simple to hard contexts?', signal: 'Shapley' },
    phase21: { category: 'context-transfer', identity: 'The context spectrum', question: 'Is the context surface mostly driven by individual factors or their interactions?', signal: 'Walsh–Hadamard' },
    phase22: { category: 'context-transfer', identity: 'The frozen transfer model', question: 'Can a simple additive model predict a fresh context cube without being refit?', signal: '10 / 10 gates' }
  };

  const categoryById = Object.fromEntries(categories.map(category => [category.id, category]));

  window.AEGIS_PHASE_TAXONOMY = Object.freeze({
    categories: Object.freeze(categories.map(Object.freeze)),
    bySlug: Object.freeze(Object.fromEntries(Object.entries(bySlug).map(([key, value]) => [key, Object.freeze(value)]))),
    categoryById: Object.freeze(categoryById)
  });
})();