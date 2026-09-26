(() => {
  'use strict';

  // Bind the route immediately, before the legacy renderer's DOMContentLoaded handler.
  // This makes Phase 10R render as its own native record instead of falling through
  // the older phase1–phase10 route matcher and visually masquerading as Phase 10.
  const routeMatch = location.pathname.match(/\/phases\/(phase(?:1|2|3|4|5|6|6b|7|8|9|10r?|11|12|13a|13b|13c|14|15|16|17|18|19|20|21|22|23|24))\/?$/i);
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

  // Shared exploratory runner. Frozen records remain unchanged. The live panel is
  // immediately replaced by current-data.js with the protected KIOS real-image benchmark.
  if (!document.querySelector('script[data-aegis-experiment-lab]')) {
    const style = document.createElement('link');
    style.rel = 'stylesheet'; style.href = '/lab/lab.css?v=5';
    document.head.appendChild(style);
    const runner = document.createElement('script');
    runner.src = '/lab/lab.js?v=8'; runner.dataset.aegisExperimentLab = '';
    document.head.appendChild(runner);
  }
  if (!document.querySelector('script[data-aegis-current-data]')) {
    const current = document.createElement('script');
    current.src = '/lab/current-data.js?v=2'; current.dataset.aegisCurrentData = '';
    document.head.appendChild(current);
  }

  const categories = [
    {
      id: 'safety-architecture',
      label: '01 · Safety architecture',
      name: 'Safety architecture',
      range: 'Phase 1 → Phase 4',
      description: 'A separate check, then an independent estimate. Phase 4 remains a numbering gap.',
      accent: '#3e6ae1',
      tint: '#eef3ff'
    },
    {
      id: 'perception-robustness',
      label: '02 · Perception + robustness',
      name: 'Perception + robustness',
      range: 'Phase 5 → Phase 6B',
      description: 'Images replace abstract measurements. Confidence splits by geometry.',
      accent: '#4d6f9d',
      tint: '#f0f4f8'
    },
    {
      id: 'external-validation',
      label: '03 · External validation',
      name: 'External validation',
      range: 'Phase 7 → Phase 10R',
      description: 'Harder simulation meets PX4/Gazebo. The mismatches remain.',
      accent: '#416b78',
      tint: '#eef5f6'
    },
    {
      id: 'reliability-calibration',
      label: '04 · Reliability + calibration',
      name: 'Reliability + calibration',
      range: 'Phase 11 → Phase 13C',
      description: 'Tougher validation exposes both useful coverage and failed checks.',
      accent: '#5a6484',
      tint: '#f1f2f7'
    },
    {
      id: 'latency-dynamics',
      label: '05 · Latency + error dynamics',
      name: 'Latency + error dynamics',
      range: 'Phase 14 → Phase 19',
      description: 'Stale estimates worsen error. Residual patterns answer a narrower question.',
      accent: '#596f63',
      tint: '#f1f5f2'
    },
    {
      id: 'context-transfer',
      label: '06 · Context structure + transfer',
      name: 'Context structure + transfer',
      range: 'Phase 20 → Phase 22',
      description: 'Five context factors, their interactions, and a frozen transfer test.',
      accent: '#365f8d',
      tint: '#eef4fa'
    },
    {
      id: 'real-camera-robustness',
      label: '07 · Real-camera robustness',
      name: 'Real-camera robustness',
      range: 'Phase 23 → Phase 24',
      description: 'A protected KIOS detector comparison, followed by a descriptive audit of its published condition aggregates. Average gains and severe-stress regressions stay visible together.',
      accent: '#3e6ae1',
      tint: '#eef3ff'
    }
  ];

  const bySlug = {
    phase1: { category: 'safety-architecture', identity: 'First safety supervisor', question: 'Can a separate confidence check stop a risky touchdown?', signal: 'HOLD / ABORT' },
    phase2: { category: 'safety-architecture', identity: 'Risk over time', question: 'What changes if one bad frame is not enough to trigger an escalation?', signal: 'Temporal risk' },
    phase3: { category: 'safety-architecture', identity: 'Independent reference', question: 'Can a second estimate expose bias that vision cannot see by itself?', signal: 'Disagreement' },
    phase4: { category: 'safety-architecture', identity: 'The numbering gap', question: 'How should the archive handle a phase that was never run?', signal: 'No invented result' },

    phase5: { category: 'perception-robustness', identity: 'Broader stress + pixels', question: 'Does V3 survive a wider stress test, and what breaks when measurements start coming from images?', signal: 'Robustness' },
    phase6: { category: 'perception-robustness', identity: 'Image-driven loop', question: 'Can a full simulated landing run on measurements extracted from image sequences?', signal: 'Pixels → control' },
    phase6b: { category: 'perception-robustness', identity: 'Split confidence', question: 'What if lateral position is usable while altitude is not?', signal: 'Component confidence' },

    phase7: { category: 'external-validation', identity: 'Harder simulator', question: 'Which earlier results depended on convenient timing, sensing, or dynamics?', signal: 'Latency + faults' },
    phase8: { category: 'external-validation', identity: 'PX4/Gazebo comparison', question: 'Where do the internal traces agree with PX4/Gazebo, and where do they not?', signal: 'Trace mismatch' },
    phase9: { category: 'external-validation', identity: 'Camera-frame geometry', question: 'How accurate is the metric estimate when it starts from Gazebo camera frames?', signal: 'PnP geometry' },
    phase10: { category: 'external-validation', identity: 'Stateful metric estimator', question: 'Can recent state protect a good track when fallback camera geometry is ambiguous?', signal: 'Causal tracking' },
    phase10r: { category: 'external-validation', identity: 'Shifted holdout', question: 'Do the average gains survive a holdout where both appearance and geometry move?', signal: 'Tail + coverage' },

    phase11: { category: 'reliability-calibration', identity: 'Protected reliability check', question: 'Can availability improve without covering up an uncertainty problem?', signal: 'Protected gates' },
    phase12: { category: 'reliability-calibration', identity: 'Frozen uncertainty reference', question: 'Is normalized conformal uncertainty stable enough to freeze as the baseline?', signal: 'Coverage' },
    phase13a: { category: 'reliability-calibration', identity: 'External-validity challenge', question: 'Does that frozen uncertainty result survive a harder validation setting?', signal: 'FAIL preserved' },
    phase13b: { category: 'reliability-calibration', identity: 'Paired degradation check', question: 'Do the locked claims survive when degradations are paired?', signal: 'FAIL preserved' },
    phase13c: { category: 'reliability-calibration', identity: 'Failure attribution', question: 'Within the frozen synthetic setup, which tested factor contributes most to the coverage loss?', signal: 'Latency attribution' },

    phase14: { category: 'latency-dynamics', identity: 'Recoverability bridge attempt', question: 'Can uncertainty width support a useful recoverability bound?', signal: '0 admitted' },
    phase15: { category: 'latency-dynamics', identity: 'Frontier feasibility check', question: 'Does the preregistered latency frontier actually fall outside the historical analysis range?', signal: 'Frontier test' },
    phase16: { category: 'latency-dynamics', identity: 'Stale-estimate experiment', question: 'How much does a two-frame delay change the error level itself?', signal: 'Level error' },
    phase17: { category: 'latency-dynamics', identity: 'Context mismatch', question: 'Does the useful latency coefficient carry from the simple context into the hard one?', signal: 'Context mismatch' },
    phase18: { category: 'latency-dynamics', identity: 'Protected residual check', question: 'Does the residual improvement still clear the protected q90 requirements?', signal: 'Protected FAIL' },
    phase19: { category: 'latency-dynamics', identity: 'Residual distribution test', question: 'Does the narrower residual effect repeat across RMSE and MAE on fresh splits?', signal: 'RMSE / MAE' },

    phase20: { category: 'context-transfer', identity: 'Five-factor breakdown', question: 'How is the simple-to-hard drop distributed across the five predefined conditions?', signal: 'Shapley' },
    phase21: { category: 'context-transfer', identity: 'Main effects vs. interactions', question: 'How much of the context surface comes from individual factors, and how much from interactions?', signal: 'Walsh–Hadamard' },
    phase22: { category: 'context-transfer', identity: 'Frozen additive transfer', question: 'Can the model predict a new context cube without being fit again?', signal: '10 / 10 gates' },
    phase23: { category: 'real-camera-robustness', identity: 'Robust KIOS detector', question: 'Does a higher-resolution, augmented detector improve protected camera results across stress conditions?', signal: 'Clean recall gain · severe-stress loss' },
    phase24: { category: 'real-camera-robustness', identity: 'Robustness frontier audit', question: 'Does the Phase 23 average gain hold up under the hardest camera stress?', signal: '4 / 6 mAP50 gains · tail loss preserved' }
  };

  const categoryById = Object.fromEntries(categories.map(category => [category.id, category]));

  window.AEGIS_PHASE_TAXONOMY = Object.freeze({
    categories: Object.freeze(categories.map(Object.freeze)),
    bySlug: Object.freeze(Object.fromEntries(Object.entries(bySlug).map(([key, value]) => [key, Object.freeze(value)]))),
    categoryById: Object.freeze(categoryById)
  });
})();
