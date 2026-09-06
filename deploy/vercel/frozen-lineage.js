(() => {
  'use strict';

  const boundary = {
    simulation_only: true,
    safety_acceptance: false,
    controller_tuning_allowed: false,
    statement: 'Frozen synthetic simulation evidence only. This does not establish physical-flight safety, certification, production readiness, real-sensor equivalence, controller improvement, or operational safety.'
  };

  const phases = [
    {
      slug: 'phase12', label: 'Phase 12', title: 'Adaptive Normalized Conformal', verdict: 'PASS', stage: 'FINAL',
      summary: 'This became the frozen uncertainty baseline used by the later latency studies.',
      finding: 'The final replication cleared its locked gates, so Phase 12 became the fixed uncertainty reference for everything that followed.',
      metrics: [
        ['Availability', '98.57%'], ['Lateral 95% coverage', '95.53%'], ['Altitude 95% coverage', '95.22%'], ['H4 lateral p95', '2.23035×']
      ],
      resultSha: 'e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991',
      note: 'Frozen result. No retuning.'
    },
    {
      slug: 'phase13a', label: 'Phase 13A', title: 'External-Validity Gauntlet', verdict: 'FAIL', stage: 'CLOSED',
      summary: 'The frozen model did not pass the external-validity test.',
      finding: 'That failure stays exactly where it belongs in the record. It is not relabeled as a partial success because later phases worked better.',
      metrics: [['Verdict', 'FAIL'], ['Evidence state', 'Frozen']],
      note: 'Failure preserved.'
    },
    {
      slug: 'phase13b', label: 'Phase 13B', title: 'Paired Degradation Audit', verdict: 'FAIL', stage: 'CLOSED',
      summary: 'The paired degradation confirmation missed its locked gates.',
      finding: 'The result stayed negative. Later attribution work only makes sense if the archive keeps the earlier failure visible.',
      metrics: [['Verdict', 'FAIL'], ['Evidence state', 'Frozen']],
      note: 'Failure preserved.'
    },
    {
      slug: 'phase13c', label: 'Phase 13C', title: 'Compound Interaction Attribution', verdict: 'PASS', stage: 'FINAL',
      summary: 'A controlled synthetic decomposition asked which factor contributed most to the hard-context coverage failure.',
      finding: 'On the frozen hard domain-13 distribution, fixed two-frame estimate latency contributed more to the compound lateral-coverage failure than bias or lateral drift. That is a result about this synthetic setup, not a physical-causality claim.',
      metrics: [['Verdict', 'PASS'], ['Intervention', 'Frozen 2-frame latency'], ['Claim type', 'Synthetic attribution']],
      note: 'Final holdout passed.'
    },
    {
      slug: 'phase14', label: 'Phase 14', title: 'Uncertainty–Recoverability Bridge', verdict: 'FAIL', stage: 'DEVELOPMENT',
      summary: 'The proposed uncertainty-to-recoverability bridge admitted no usable transitions.',
      finding: 'Development produced zero admitted transitions, so the idea failed before transfer, protected validation, or final evidence was opened.',
      metrics: [['Admitted transitions', '0'], ['Frozen lateral a', '0.61027'], ['Verdict', 'FAIL']],
      note: 'Closed in development. Later roles were never exposed.'
    },
    {
      slug: 'phase15', label: 'Phase 15', title: 'Recoverability Feasibility Frontier', verdict: 'FAIL', stage: 'DEVELOPMENT',
      summary: 'The preregistered latency q90 infeasibility condition did not hold.',
      finding: 'The latency q90 frontier landed inside the historical analysis box, so the phase stopped before transfer instead of changing the rule after seeing the result.',
      metrics: [['Verdict', 'FAIL'], ['Later roles', 'Unexposed']],
      note: 'The historical box is an analysis region, not a physical invariant set.'
    },
    {
      slug: 'phase16', label: 'Phase 16', title: 'Matched Latency Level Dynamics', verdict: 'FAIL', stage: 'DEVELOPMENT',
      summary: 'Two-frame staleness made the estimate worse while the old Phase 12 interval widths stayed the same.',
      finding: 'The phase failed its broader gate, but one result was still useful: stale estimates increased lateral absolute error and persistence. The preregistered idea that greater persistence had to reduce frozen one-step q90 residuals was falsified.',
      metrics: [['Simple coverage Δ', '−2.86 pp'], ['Hard coverage Δ', '−9.70 pp'], ['Phase 12 width Δ', '0.0 m']],
      note: 'Negative verdict; the mechanism observation remains part of the record.'
    },
    {
      slug: 'phase17', label: 'Phase 17', title: 'Context-Conditional Coefficient Mismatch', verdict: 'FAIL', stage: 'DEVELOPMENT',
      summary: 'The simple context showed a clear mismatch, but two locked gates still failed.',
      finding: 'The simple-context latency coefficient showed a real residual advantage. The hard-context transfer and proximity requirements did not both pass, so the phase closed as a failure.',
      metrics: [['Simple q90 improvement', '13.20%'], ['Hard q90 improvement', '0.21%'], ['Verdict', 'FAIL']],
      resultSha: '24aeed60003b3111c9d3dd24cee992f8bac539531d38923b9a205a1423e8d029',
      note: 'Transfer, protected, and final evidence stayed unexposed.'
    },
    {
      slug: 'phase18', label: 'Phase 18', title: 'Residual Advantage Confirmation', verdict: 'FAIL', stage: 'PROTECTED',
      summary: 'Development and transfer passed, then protected validation missed two q90 gates.',
      finding: 'The RMSE result still looked promising, but the locked protected q90 threshold and improvement-gap gate failed. That ended the phase and permanently blocked the final holdout.',
      metrics: [['Protected simple RMSE improvement', '5.90%'], ['Protected simple q90 improvement', '9.04%'], ['Verdict', 'FAIL']],
      resultSha: 'ad96ca1a5119fcd594a84fd72a04f8efcc377ba788383d90dda9ef7eecad4431',
      note: 'The q90 miss remains a failure.'
    },
    {
      slug: 'phase19', label: 'Phase 19', title: 'Distribution-Wide Residual Advantage', verdict: 'PASS', stage: 'FINAL',
      summary: 'A narrower residual question held up across every fresh evidence role.',
      finding: 'In the simple context, the frozen latency coefficient repeatedly reduced one-step lateral residual RMSE and MAE relative to Phase 14. In the hard context it was roughly neutral. Absolute level error still worsened under latency.',
      metrics: [['Final simple RMSE improvement', '8.94%'], ['Final simple MAE improvement', '14.64%'], ['Hard RMSE improvement', '0.34%'], ['Hard MAE improvement', '0.02%']],
      resultSha: '8c23b9b9c8c9fb2f9146bf739e52074f8709d2fe9a81c794e64fb43f360acebf',
      note: 'q90 stayed descriptive. This is not a claim that latency is beneficial.'
    },
    {
      slug: 'phase20', label: 'Phase 20', title: 'Five-Factor Shapley Attenuation', verdict: 'PASS', stage: 'FINAL',
      summary: 'The simple-to-hard loss of residual advantage was split across five predefined synthetic modifiers.',
      finding: 'All 32 factorial contexts were evaluated. Edge, obliquity, dim lighting, blur/noise, and low contrast all contributed to attenuation; the evidence does not support one factor as universally dominant.',
      metrics: [['Final RMSE attenuation', '14.77 pp'], ['Final MAE attenuation', '20.45 pp'], ['Shapley efficiency error', '0.0']],
      resultSha: 'f2a0cf4e1cf0765c3194025eb29072f9663f27e3cdd13b0594cde4643f33934e',
      note: 'Final PASS. All evidence roles closed.'
    },
    {
      slug: 'phase21', label: 'Phase 21', title: 'Orthogonal Context Spectrum', verdict: 'PASS', stage: 'FINAL',
      summary: 'The context surface turned out to be mostly first-order, with smaller interaction terms still present.',
      finding: 'Across fresh development, transfer, protected, and final cubes, all five predefined factors pointed toward attenuation in the balanced first-order effects for RMSE and MAE. Interaction structure was still non-zero.',
      metrics: [['Final RMSE first-order share', '88.44%'], ['Final MAE first-order share', '78.01%'], ['Stable factor direction', '5 / 5']],
      resultSha: 'bc85a746cf1b770fb4119feb3979789975ed5201065d94de47c6dcc3a051d9ee',
      note: 'Structural description only; not a physical-causality claim.'
    },
    {
      slug: 'phase22', label: 'Phase 22', title: 'Frozen Additive Context Transfer', verdict: 'PASS', stage: 'FINAL',
      summary: 'A simple frozen additive model predicted fresh 32-cell context surfaces without being refit.',
      finding: 'The candidate cleared development, transfer, protected validation, and the one-shot final holdout. Final cellwise R² was 0.8319 for the RMSE-advantage surface and 0.7744 for the MAE-advantage surface, with 100% stable-sign accuracy on eligible cells.',
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
