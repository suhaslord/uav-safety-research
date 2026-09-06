(() => {
  'use strict';

  const boundary = {
    simulation_only: true,
    safety_acceptance: false,
    controller_tuning_allowed: false,
    statement: 'Synthetic, frozen simulation evidence only. No physical-flight safety, certification, production-readiness, real-sensor-equivalence, controller-improvement, or operational-safety claim.'
  };

  const phases = [
    {
      slug: 'phase12', label: 'Phase 12', title: 'Adaptive Normalized Conformal', verdict: 'PASS', stage: 'FINAL',
      summary: 'Frozen conformal uncertainty baseline that anchors every later comparison.',
      finding: 'Final frozen replication passed its preregistered evidence gates and became the immutable uncertainty reference for the later latency studies.',
      metrics: [
        ['Availability', '98.57%'], ['Lateral 95% coverage', '95.53%'], ['Altitude 95% coverage', '95.22%'], ['H4 lateral p95', '2.23035×']
      ],
      resultSha: 'e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991',
      note: 'Frozen. Do not tune or reopen.'
    },
    {
      slug: 'phase13a', label: 'Phase 13A', title: 'External-Validity Gauntlet', verdict: 'FAIL', stage: 'CLOSED',
      summary: 'The frozen model did not clear the external-validity gauntlet.',
      finding: 'The failure remains part of the evidence record and is not rewritten as a partial success.',
      metrics: [['Verdict', 'FAIL'], ['Evidence state', 'Frozen']],
      note: 'Failure preserved exactly.'
    },
    {
      slug: 'phase13b', label: 'Phase 13B', title: 'Paired Degradation Audit', verdict: 'FAIL', stage: 'CLOSED',
      summary: 'Paired degradation confirmation failed its locked scientific gates.',
      finding: 'The negative result stays visible because later attribution work depends on remembering what did not generalize.',
      metrics: [['Verdict', 'FAIL'], ['Evidence state', 'Frozen']],
      note: 'Failure preserved exactly.'
    },
    {
      slug: 'phase13c', label: 'Phase 13C', title: 'Compound Interaction Attribution', verdict: 'PASS', stage: 'FINAL',
      summary: 'A controlled compound decomposition isolated the strongest synthetic contributor to the hard-context coverage failure.',
      finding: 'On the frozen hard domain-13 synthetic distribution, fixed two-frame estimate latency was the dominant contributor to compound lateral-coverage failure; bias and lateral drift were smaller. This is not a physical-causality claim.',
      metrics: [['Verdict', 'PASS'], ['Intervention', 'Frozen 2-frame latency'], ['Claim type', 'Synthetic attribution']],
      note: 'Passed through final holdout.'
    },
    {
      slug: 'phase14', label: 'Phase 14', title: 'Uncertainty–Recoverability Bridge', verdict: 'FAIL', stage: 'DEVELOPMENT',
      summary: 'The direct uncertainty-halfwidth to bounded-disturbance bridge was structurally vacuous.',
      finding: 'Development produced zero admitted transitions for the proposed bridge, so transfer, protected, and final evidence stayed unexposed.',
      metrics: [['Admitted transitions', '0'], ['Frozen lateral a', '0.61027'], ['Verdict', 'FAIL']],
      note: 'Closed without exposing later roles.'
    },
    {
      slug: 'phase15', label: 'Phase 15', title: 'Recoverability Feasibility Frontier', verdict: 'FAIL', stage: 'DEVELOPMENT',
      summary: 'The preregistered latency q90 infeasibility condition did not hold.',
      finding: 'The latency q90 frontier unexpectedly fell inside the historical analysis box, so the lineage stopped before transfer.',
      metrics: [['Verdict', 'FAIL'], ['Later roles', 'Unexposed']],
      note: 'Historical box is an analysis region, not a physical invariant set.'
    },
    {
      slug: 'phase16', label: 'Phase 16', title: 'Matched Latency Level Dynamics', verdict: 'FAIL', stage: 'DEVELOPMENT',
      summary: 'Pure two-frame staleness worsened level error while leaving Phase 12 interval widths unchanged.',
      finding: 'The useful mechanism result survived even though the phase failed: stale estimates increased lateral absolute error and persistence, while the claim that more persistence must reduce frozen one-step q90 residuals was falsified.',
      metrics: [['Simple coverage Δ', '−2.86 pp'], ['Hard coverage Δ', '−9.70 pp'], ['Phase 12 width Δ', '0.0 m']],
      note: 'Negative gate verdict; mechanism observation preserved.'
    },
    {
      slug: 'phase17', label: 'Phase 17', title: 'Context-Conditional Coefficient Mismatch', verdict: 'FAIL', stage: 'DEVELOPMENT',
      summary: 'Context-specific mismatch substantially replicated, but two locked gates failed.',
      finding: 'Simple-context latency dynamics showed a clear coefficient mismatch and residual advantage; hard-context coefficient transfer/proximity requirements did not both clear.',
      metrics: [['Simple q90 improvement', '13.20%'], ['Hard q90 improvement', '0.21%'], ['Verdict', 'FAIL']],
      resultSha: '24aeed60003b3111c9d3dd24cee992f8bac539531d38923b9a205a1423e8d029',
      note: 'Transfer, protected, and final stayed unexposed.'
    },
    {
      slug: 'phase18', label: 'Phase 18', title: 'Residual Advantage Confirmation', verdict: 'FAIL', stage: 'PROTECTED',
      summary: 'Development and transfer passed; protected validation missed two q90 gates.',
      finding: 'Distribution-wide RMSE evidence remained encouraging, but the preregistered protected q90 threshold and improvement-gap gate failed. Final was permanently prohibited.',
      metrics: [['Protected simple RMSE improvement', '5.90%'], ['Protected simple q90 improvement', '9.04%'], ['Verdict', 'FAIL']],
      resultSha: 'ad96ca1a5119fcd594a84fd72a04f8efcc377ba788383d90dda9ef7eecad4431',
      note: 'q90 failure remains a failure.'
    },
    {
      slug: 'phase19', label: 'Phase 19', title: 'Distribution-Wide Residual Advantage', verdict: 'PASS', stage: 'FINAL',
      summary: 'The narrower distribution-wide residual question survived every fresh evidence role.',
      finding: 'The frozen simple-context latency coefficient repeatedly reduced one-step lateral residual RMSE and MAE relative to Phase 14, while the hard-context coefficient stayed approximately neutral. Absolute level error still worsened under latency.',
      metrics: [['Final simple RMSE improvement', '8.94%'], ['Final simple MAE improvement', '14.64%'], ['Hard RMSE improvement', '0.34%'], ['Hard MAE improvement', '0.02%']],
      resultSha: '8c23b9b9c8c9fb2f9146bf739e52074f8709d2fe9a81c794e64fb43f360acebf',
      note: 'q90 remained descriptive; no latency-benefit claim.'
    },
    {
      slug: 'phase20', label: 'Phase 20', title: 'Five-Factor Shapley Attenuation', verdict: 'PASS', stage: 'FINAL',
      summary: 'The simple→hard loss of residual advantage was exactly decomposed across five predefined synthetic modifiers.',
      finding: 'All 32 factorial contexts were evaluated with exact Shapley efficiency. Attenuation was distributed across edge, oblique, dim, blur/noise, and low contrast; no single factor is established as universally dominant.',
      metrics: [['Final RMSE attenuation', '14.77 pp'], ['Final MAE attenuation', '20.45 pp'], ['Shapley efficiency error', '0.0']],
      resultSha: 'f2a0cf4e1cf0765c3194025eb29072f9663f27e3cdd13b0594cde4643f33934e',
      note: 'Full final PASS; all roles closed.'
    },
    {
      slug: 'phase21', label: 'Phase 21', title: 'Orthogonal Context Spectrum', verdict: 'PASS', stage: 'FINAL',
      summary: 'An exact Walsh–Hadamard decomposition showed the context surface was predominantly first-order.',
      finding: 'Across fresh development, transfer, protected, and final cubes, every predefined factor’s balanced first-order effect pointed toward attenuation on RMSE and MAE while interaction structure remained non-zero.',
      metrics: [['Final RMSE first-order share', '88.44%'], ['Final MAE first-order share', '78.01%'], ['Stable factor direction', '5 / 5']],
      resultSha: 'bc85a746cf1b770fb4119feb3979789975ed5201065d94de47c6dcc3a051d9ee',
      note: 'Descriptive structural decomposition; not physical causality.'
    },
    {
      slug: 'phase22', label: 'Phase 22', title: 'Frozen Additive Context Transfer', verdict: 'PASS', stage: 'FINAL',
      summary: 'A frozen additive main-effects model predicted fresh 32-cell context surfaces without refitting.',
      finding: 'The frozen additive candidate cleared development, transfer, protected validation, and the one-shot final holdout. Final cellwise R² was 0.8322 for the RMSE-advantage surface and 0.7738 for the MAE-advantage surface, with 100% stable-sign accuracy on eligible cells.',
      metrics: [['Final RMSE R²', '0.8322'], ['Final MAE R²', '0.7738'], ['RMSE prediction MAE', '0.01056'], ['MAE prediction MAE', '0.01679'], ['Stable-sign accuracy', '100%']],
      resultSha: '0ddc968b8bd48c2de6d904194b417854913389a8927cff0b15b96c6501f8294c',
      candidateSha: '62e75d7b39088c2e66f1cc6be4d180501b79632f2f6847af1fbe0bd96be17551',
      note: 'Frozen through Phase 22. No new scientific phase is implied by this site.'
    }
  ];

  const bySlug = Object.fromEntries(phases.map((phase) => [phase.slug, phase]));
  const counts = phases.reduce((acc, phase) => {
    acc[phase.verdict] = (acc[phase.verdict] || 0) + 1;
    return acc;
  }, {});

  window.AEGIS_FROZEN_LINEAGE = Object.freeze({
    frozenThrough: 'Phase 22',
    frozenScientificHead: '668d065f4312e33e2d21ca7a7ee76d4d6d5617b3',
    phase22FinalRun: '34043148327',
    phase22FinalArtifact: '9992317865',
    phase22FinalArtifactDigest: 'sha256:78fa8eb98cd72c8a32969a463b44e12e2ef38aad7e5af64a968cab9ada6871cb',
    boundary: Object.freeze(boundary),
    phases: Object.freeze(phases.map(Object.freeze)),
    bySlug: Object.freeze(bySlug),
    counts: Object.freeze(counts)
  });
})();
