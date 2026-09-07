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

  const categories = [
    {
      id: 'safety-architecture',
      label: '01 · Safety architecture',
      name: 'Safety architecture',
      range: 'Phase 1 → Phase 4',
      description: 'The early system: supervision, temporal behavior, independent evidence, and the provenance gap.',
      accent: '#3e6ae1',
      tint: '#eef3ff'
    },
    {
      id: 'perception-robustness',
      label: '02 · Perception + robustness',
      name: 'Perception + robustness',
      range: 'Phase 5 → Phase 6B',
      description: 'Move from abstract state errors to pixels, confidence, tracking, and component-selective perception.',
      accent: '#4d6f9d',
      tint: '#f0f4f8'
    },
    {
      id: 'external-validation',
      label: '03 · External validation',
      name: 'External validation',
      range: 'Phase 7 → Phase 10R',
      description: 'Make the assumptions harder, compare against PX4/Gazebo, and test camera geometry under shift.',
      accent: '#416b78',
      tint: '#eef5f6'
    },
    {
      id: 'reliability-calibration',
      label: '04 · Reliability + calibration',
      name: 'Reliability + calibration',
      range: 'Phase 11 → Phase 13C',
      description: 'Protect availability and uncertainty honesty, then stress whether those claims survive harder domains.',
      accent: '#5a6484',
      tint: '#f1f2f7'
    },
    {
      id: 'latency-dynamics',
      label: '05 · Latency + error dynamics',
      name: 'Latency + error dynamics',
      range: 'Phase 14 → Phase 19',
      description: 'Separate stale level error from short-horizon residual structure and keep failed mechanisms visible.',
      accent: '#596f63',
      tint: '#f1f5f2'
    },
    {
      id: 'context-transfer',
      label: '06 · Context structure + transfer',
      name: 'Context structure + transfer',
      range: 'Phase 20 → Phase 22',
      description: 'Decompose the synthetic context surface, identify its structure, and test frozen transfer without refitting.',
      accent: '#365f8d',
      tint: '#eef4fa'
    }
  ];

  const bySlug = {
    phase1: { category: 'safety-architecture', identity: 'The safety gate', question: 'Can confidence stop an unsafe action before touchdown?', signal: 'HOLD / ABORT' },
    phase2: { category: 'safety-architecture', identity: 'The stabilizer', question: 'Can the supervisor stop panicking over one bad frame?', signal: 'Temporal risk' },
    phase3: { category: 'safety-architecture', identity: 'The independent referee', question: 'What changes when vision gets a second opinion?', signal: 'Disagreement' },
    phase4: { category: 'safety-architecture', identity: 'The provenance break', question: 'What should the archive do when a numbered phase never existed?', signal: 'No invented result' },

    phase5: { category: 'perception-robustness', identity: 'The stress lab', question: 'Does the architecture survive stronger stress and the first move to pixels?', signal: 'Robustness' },
    phase6: { category: 'perception-robustness', identity: 'The pixel loop', question: 'Can image-derived measurements drive the full landing loop?', signal: 'Pixels → control' },
    phase6b: { category: 'perception-robustness', identity: 'The selective fusion layer', question: 'What if lateral position is trustworthy but altitude is not?', signal: 'Component confidence' },

    phase7: { category: 'external-validation', identity: 'The realism stress test', question: 'How much of the result depends on a forgiving simulator?', signal: 'Latency + faults' },
    phase8: { category: 'external-validation', identity: 'The simulator mirror', question: 'Does the internal simulator actually resemble PX4/Gazebo?', signal: 'Trace mismatch' },
    phase9: { category: 'external-validation', identity: 'The camera geometry test', question: 'What happens when the estimator sees genuine Gazebo camera frames?', signal: 'PnP geometry' },
    phase10: { category: 'external-validation', identity: 'The temporal estimator', question: 'Can temporal state protect metric perception from ambiguous geometry?', signal: 'Causal tracking' },
    phase10r: { category: 'external-validation', identity: 'The shift holdout', question: 'Do strong mean gains still hold when geometry and appearance shift together?', signal: 'Tail + coverage' },

    phase11: { category: 'reliability-calibration', identity: 'The protected reliability pass', question: 'Can availability recover without hiding uncertainty failures?', signal: 'Protected gates' },
    phase12: { category: 'reliability-calibration', identity: 'The uncertainty baseline', question: 'Can normalized conformal uncertainty become a stable frozen reference?', signal: 'Coverage' },
    phase13a: { category: 'reliability-calibration', identity: 'The validity gauntlet', question: 'Does the frozen uncertainty story survive an external-validity challenge?', signal: 'FAIL preserved' },
    phase13b: { category: 'reliability-calibration', identity: 'The paired degradation audit', question: 'Do the locked claims replicate under paired degradation?', signal: 'FAIL preserved' },
    phase13c: { category: 'reliability-calibration', identity: 'The attribution test', question: 'Which frozen synthetic factor contributes most to the coverage failure?', signal: 'Latency attribution' },

    phase14: { category: 'latency-dynamics', identity: 'The bridge attempt', question: 'Can uncertainty width be turned into a useful recoverability bound?', signal: '0 admitted' },
    phase15: { category: 'latency-dynamics', identity: 'The feasibility frontier', question: 'Is the preregistered latency frontier actually outside the historical box?', signal: 'Frontier test' },
    phase16: { category: 'latency-dynamics', identity: 'The staleness mechanism', question: 'What does pure two-frame staleness do to level error?', signal: 'Level error' },
    phase17: { category: 'latency-dynamics', identity: 'The coefficient mismatch test', question: 'Does the useful coefficient change with context?', signal: 'Context mismatch' },
    phase18: { category: 'latency-dynamics', identity: 'The protected confirmation', question: 'Does the residual advantage survive protected q90 gates?', signal: 'Protected FAIL' },
    phase19: { category: 'latency-dynamics', identity: 'The residual effect', question: 'Does the narrower distribution-wide residual advantage replicate?', signal: 'RMSE / MAE' },

    phase20: { category: 'context-transfer', identity: 'The factor decomposition', question: 'Which predefined modifiers explain the simple-to-hard attenuation?', signal: 'Shapley' },
    phase21: { category: 'context-transfer', identity: 'The context spectrum', question: 'Is the context surface mostly first-order or interaction-driven?', signal: 'Walsh–Hadamard' },
    phase22: { category: 'context-transfer', identity: 'The frozen transfer model', question: 'Can a simple additive model predict a fresh context cube without refitting?', signal: '10 / 10 gates' }
  };

  const categoryById = Object.fromEntries(categories.map(category => [category.id, category]));

  window.AEGIS_PHASE_TAXONOMY = Object.freeze({
    categories: Object.freeze(categories.map(Object.freeze)),
    bySlug: Object.freeze(Object.fromEntries(Object.entries(bySlug).map(([key, value]) => [key, Object.freeze(value)]))),
    categoryById: Object.freeze(categoryById)
  });
})();
