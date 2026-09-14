(() => {
  'use strict';

  const boundary = {
    simulation_only: true,
    safety_acceptance: false,
    controller_tuning_allowed: false,
    statement: 'Every result on this page comes from synthetic simulation. It does not establish real-aircraft safety, certification, production readiness, equivalence to real sensors, a controller improvement, or permission to operate an aircraft.'
  };

  const phases = [
    {
      slug: 'phase12', label: 'Phase 12', title: 'Adaptive Normalized Conformal', verdict: 'PASS', stage: 'FINAL',
      summary: 'Phase 12 became the uncertainty reference for the latency experiments that followed.',
      finding: 'The final replication cleared the checks that had been locked beforehand. Later phases therefore used this result as the fixed uncertainty baseline instead of fitting a new one each time.',
      metrics: [
        ['Availability', '98.57%'], ['Lateral 95% coverage', '95.53%'], ['Altitude 95% coverage', '95.22%'], ['H4 lateral p95', '2.23035×']
      ],
      resultSha: 'e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991',
      note: 'Frozen result. No retuning.'
    },
    {
      slug: 'phase13a', label: 'Phase 13A', title: 'External-Validity Gauntlet', verdict: 'FAIL', stage: 'CLOSED',
      summary: 'The frozen model failed the external-validity test.',
      finding: 'This remains a failure. Better results later in the project do not retroactively turn Phase 13A into a partial success.',
      metrics: [['Verdict', 'FAIL'], ['Evidence state', 'Frozen']],
      note: 'Failure preserved.'
    },
    {
      slug: 'phase13b', label: 'Phase 13B', title: 'Paired Degradation Audit', verdict: 'FAIL', stage: 'CLOSED',
      summary: 'The paired-degradation confirmation did not meet its locked checks.',
      finding: 'The confirmation came back negative, and the archive keeps it that way. The attribution work that followed is easier to interpret because this miss is still visible.',
      metrics: [['Verdict', 'FAIL'], ['Evidence state', 'Frozen']],
      note: 'Failure preserved.'
    },
    {
      slug: 'phase13c', label: 'Phase 13C', title: 'Compound Interaction Attribution', verdict: 'PASS', stage: 'FINAL',
      summary: 'This controlled synthetic test asked which tested factor accounted for the most coverage loss in the hard context.',
      finding: 'Within the frozen hard domain-13 distribution, a fixed two-frame estimate delay contributed more to the compound lateral-coverage failure than bias or lateral drift. That statement is limited to this simulation setup; it is not a claim about physical causation.',
      metrics: [['Verdict', 'PASS'], ['Intervention', 'Frozen 2-frame latency'], ['Claim type', 'Synthetic attribution']],
      note: 'Final holdout passed.'
    },
    {
      slug: 'phase14', label: 'Phase 14', title: 'Uncertainty–Recoverability Bridge', verdict: 'FAIL', stage: 'DEVELOPMENT',
      summary: 'The proposed bridge from uncertainty to recoverability never produced an admitted transition.',
      finding: 'Development returned zero admitted transitions. That was enough to stop the idea there, so transfer, protected validation, and final evidence were never opened.',
      metrics: [['Admitted transitions', '0'], ['Frozen lateral a', '0.61027'], ['Verdict', 'FAIL']],
      note: 'Closed in development. Later roles were never exposed.'
    },
    {
      slug: 'phase15', label: 'Phase 15', title: 'Recoverability Feasibility Frontier', verdict: 'FAIL', stage: 'DEVELOPMENT',
      summary: 'The preregistered latency q90 infeasibility condition was not true in development.',
      finding: 'The latency q90 frontier fell inside the historical analysis range. The phase stopped before transfer rather than changing the rule after seeing where the result landed.',
      metrics: [['Verdict', 'FAIL'], ['Later roles', 'Unexposed']],
      note: 'The historical box is an analysis region, not a physical invariant set.'
    },
    {
      slug: 'phase16', label: 'Phase 16', title: 'Matched Latency Level Dynamics', verdict: 'FAIL', stage: 'DEVELOPMENT',
      summary: 'A two-frame-old estimate increased the error while the old Phase 12 uncertainty widths stayed fixed.',
      finding: 'The broader gate failed. Even so, the run answered a useful mechanism question: stale estimates raised lateral absolute error and made errors persist longer. It also falsified the preregistered idea that greater persistence had to reduce the frozen one-step q90 residuals.',
      metrics: [['Simple coverage Δ', '−2.86 pp'], ['Hard coverage Δ', '−9.70 pp'], ['Phase 12 width Δ', '0.0 m']],
      note: 'Negative verdict; the mechanism observation remains part of the record.'
    },
    {
      slug: 'phase17', label: 'Phase 17', title: 'Context-Conditional Coefficient Mismatch', verdict: 'FAIL', stage: 'DEVELOPMENT',
      summary: 'The simple context showed a clear mismatch, but two required checks still failed.',
      finding: 'The simple-context latency coefficient reduced the residuals. The hard-context transfer and proximity requirements did not both pass, so the phase closed as a failure.',
      metrics: [['Simple q90 improvement', '13.20%'], ['Hard q90 improvement', '0.21%'], ['Verdict', 'FAIL']],
      resultSha: '24aeed60003b3111c9d3dd24cee992f8bac539531d38923b9a205a1423e8d029',
      note: 'Transfer, protected, and final evidence stayed unexposed.'
    },
    {
      slug: 'phase18', label: 'Phase 18', title: 'Residual Advantage Confirmation', verdict: 'FAIL', stage: 'PROTECTED',
      summary: 'Development and transfer passed. Protected validation then missed two q90 checks.',
      finding: 'The RMSE result still looked favorable, but the locked protected q90 threshold and improvement-gap check failed. That ended the phase, and the final holdout was left closed.',
      metrics: [['Protected simple RMSE improvement', '5.90%'], ['Protected simple q90 improvement', '9.04%'], ['Verdict', 'FAIL']],
      resultSha: 'ad96ca1a5119fcd594a84fd72a04f8efcc377ba788383d90dda9ef7eecad4431',
      note: 'The q90 miss remains a failure.'
    },
    {
      slug: 'phase19', label: 'Phase 19', title: 'Distribution-Wide Residual Advantage', verdict: 'PASS', stage: 'FINAL',
      summary: 'A narrower question about the residuals held up across each fresh evidence split.',
      finding: 'In the simple context, the frozen latency coefficient repeatedly lowered one-step lateral residual RMSE and MAE relative to Phase 14. In the hard context, the difference was almost neutral. Latency still made the actual level error worse.',
      metrics: [['Final simple RMSE improvement', '8.94%'], ['Final simple MAE improvement', '14.64%'], ['Hard RMSE improvement', '0.34%'], ['Hard MAE improvement', '0.02%']],
      resultSha: '8c23b9b9c8c9fb2f9146bf739e52074f8709d2fe9a81c794e64fb43f360acebf',
      note: 'q90 stayed descriptive. This is not a claim that latency is beneficial.'
    },
    {
      slug: 'phase20', label: 'Phase 20', title: 'Five-Factor Shapley Attenuation', verdict: 'PASS', stage: 'FINAL',
      summary: 'Phase 20 split the loss of residual advantage from the simple context to the hard one across five predefined synthetic conditions.',
      finding: 'All 32 combinations were tested. Edge position, obliquity, dim lighting, blur/noise, and low contrast each contributed to the drop. These data do not support naming one factor as universally dominant.',
      metrics: [['Final RMSE attenuation', '14.77 pp'], ['Final MAE attenuation', '20.45 pp'], ['Shapley efficiency error', '0.0']],
      resultSha: 'f2a0cf4e1cf0765c3194025eb29072f9663f27e3cdd13b0594cde4643f33934e',
      note: 'Final PASS. All evidence roles closed.'
    },
    {
      slug: 'phase21', label: 'Phase 21', title: 'Orthogonal Context Spectrum', verdict: 'PASS', stage: 'FINAL',
      summary: 'Individual factors explained most of the context surface, with smaller interaction effects still present.',
      finding: 'Across fresh development, transfer, protected, and final cubes, all five predefined factors pointed toward attenuation in the balanced first-order RMSE and MAE effects. Interaction terms were smaller, but they were not zero.',
      metrics: [['Final RMSE first-order share', '88.44%'], ['Final MAE first-order share', '78.01%'], ['Stable factor direction', '5 / 5']],
      resultSha: 'bc85a746cf1b770fb4119feb3979789975ed5201065d94de47c6dcc3a051d9ee',
      note: 'Structural description only; not a physical-causality claim.'
    },
    {
      slug: 'phase22', label: 'Phase 22', title: 'Frozen Additive Context Transfer', verdict: 'PASS', stage: 'FINAL',
      summary: 'A frozen additive model predicted a fresh 32-cell context surface without another fit.',
      finding: 'The candidate passed development, transfer, protected validation, and the one-shot final holdout. Final cellwise R² was 0.8319 for the RMSE-advantage surface and 0.7744 for the MAE-advantage surface. Stable-sign accuracy on eligible cells was 100%.',
      metrics: [['Final RMSE R²', '0.8319'], ['Final MAE R²', '0.7744'], ['Stable-sign accuracy', '100%'], ['Locked gates', '10 / 10']],
      resultSha: '0ddc968b8bd48c2de6d904194b417854913389a8927cff0b15b96c6501f8294c',
      candidateSha: '62e75d7b39088c2e66f1cc6be4d180501b79632f2f6847af1fbe0bd96be17551',
      note: 'Frozen through Phase 22. This site does not imply a new scientific phase.'
    }
  ];

  const bySlug = Object.fromEntries(phases.map((phase) => [phase.slug, phase]));
  const counts = phases.reduce((acc, phase) => {
    acc[phase.verdict] = (acc[phase.verdict] || 0) + 1;
    return acc;
  }, {});

  window.AEGIS_FROZEN_LINEAGE = Object.freeze({
    frozenThrough: 'Phase 22',
    frozenScientificHead: '668d065714dde279857bc0e196f0ef7cc5e182ed',
    phase22FinalRun: '34043148327',
    phase22FinalArtifact: '9992317865',
    phase22FinalArtifactDigest: 'sha256:78fa8d0d5a0df2a59d2d65a3e30abb1e8c948c1f3b9b66a2cb262f00adb971cb',
    boundary: Object.freeze(boundary),
    phases: Object.freeze(phases.map(Object.freeze)),
    bySlug: Object.freeze(bySlug),
    counts: Object.freeze(counts)
  });
})();