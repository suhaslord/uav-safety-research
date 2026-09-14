(() => {
  'use strict';

  const boundary = {
    simulation_only: true,
    safety_acceptance: false,
    controller_tuning_allowed: false,
    statement: 'These are frozen results from synthetic simulations. They do not show that a real aircraft is safe, certified, production-ready, equivalent to real sensors, improved by controller tuning, or safe to operate.'
  };

  const phases = [
    {
      slug: 'phase12', label: 'Phase 12', title: 'Adaptive Normalized Conformal', verdict: 'PASS', stage: 'FINAL',
      summary: 'This became the fixed uncertainty baseline for the latency studies that came next.',
      finding: 'The final replication passed its locked checks, so Phase 12 became the uncertainty reference used by the later phases.',
      metrics: [
        ['Availability', '98.57%'], ['Lateral 95% coverage', '95.53%'], ['Altitude 95% coverage', '95.22%'], ['H4 lateral p95', '2.23035×']
      ],
      resultSha: 'e2372ca597cdd983f098f1a45524c077798114c59a62bf9faccefd17b67a4991',
      note: 'Frozen result. No retuning.'
    },
    {
      slug: 'phase13a', label: 'Phase 13A', title: 'External-Validity Gauntlet', verdict: 'FAIL', stage: 'CLOSED',
      summary: 'The frozen model did not pass the external-validity test.',
      finding: 'The failure stays in the record as a failure. Later phases doing better does not turn this result into a partial success.',
      metrics: [['Verdict', 'FAIL'], ['Evidence state', 'Frozen']],
      note: 'Failure preserved.'
    },
    {
      slug: 'phase13b', label: 'Phase 13B', title: 'Paired Degradation Audit', verdict: 'FAIL', stage: 'CLOSED',
      summary: 'The paired-degradation confirmation missed its locked checks.',
      finding: 'This result stayed negative. The later attribution work only means something if this earlier failure remains visible.',
      metrics: [['Verdict', 'FAIL'], ['Evidence state', 'Frozen']],
      note: 'Failure preserved.'
    },
    {
      slug: 'phase13c', label: 'Phase 13C', title: 'Compound Interaction Attribution', verdict: 'PASS', stage: 'FINAL',
      summary: 'A controlled synthetic test asked which factor contributed most to the coverage failure in the hard context.',
      finding: 'In the frozen hard domain-13 distribution, a fixed two-frame estimate delay contributed more to the compound lateral-coverage failure than bias or lateral drift. That result applies to this synthetic setup; it is not a claim about physical causation.',
      metrics: [['Verdict', 'PASS'], ['Intervention', 'Frozen 2-frame latency'], ['Claim type', 'Synthetic attribution']],
      note: 'Final holdout passed.'
    },
    {
      slug: 'phase14', label: 'Phase 14', title: 'Uncertainty–Recoverability Bridge', verdict: 'FAIL', stage: 'DEVELOPMENT',
      summary: 'The proposed link between uncertainty and recoverability produced no usable transitions.',
      finding: 'Development produced zero admitted transitions, so the idea stopped there. Transfer, protected validation, and final evidence were never opened.',
      metrics: [['Admitted transitions', '0'], ['Frozen lateral a', '0.61027'], ['Verdict', 'FAIL']],
      note: 'Closed in development. Later roles were never exposed.'
    },
    {
      slug: 'phase15', label: 'Phase 15', title: 'Recoverability Feasibility Frontier', verdict: 'FAIL', stage: 'DEVELOPMENT',
      summary: 'The preregistered latency q90 infeasibility condition did not hold.',
      finding: 'The latency q90 frontier landed inside the historical analysis range, so the phase stopped before transfer instead of changing the rule after seeing the answer.',
      metrics: [['Verdict', 'FAIL'], ['Later roles', 'Unexposed']],
      note: 'The historical box is an analysis region, not a physical invariant set.'
    },
    {
      slug: 'phase16', label: 'Phase 16', title: 'Matched Latency Level Dynamics', verdict: 'FAIL', stage: 'DEVELOPMENT',
      summary: 'Making the estimate two frames old increased the error while the old Phase 12 uncertainty widths stayed the same.',
      finding: 'The phase failed its broader gate, but it still showed something useful: stale estimates increased lateral absolute error and made errors persist longer. The preregistered idea that more persistence had to lower the frozen one-step q90 residuals was falsified.',
      metrics: [['Simple coverage Δ', '−2.86 pp'], ['Hard coverage Δ', '−9.70 pp'], ['Phase 12 width Δ', '0.0 m']],
      note: 'Negative verdict; the mechanism observation remains part of the record.'
    },
    {
      slug: 'phase17', label: 'Phase 17', title: 'Context-Conditional Coefficient Mismatch', verdict: 'FAIL', stage: 'DEVELOPMENT',
      summary: 'The simple context showed a clear mismatch, but two locked checks still failed.',
      finding: 'The simple-context latency coefficient gave a real residual advantage. The hard-context transfer and proximity requirements did not both pass, so the phase closed as a failure.',
      metrics: [['Simple q90 improvement', '13.20%'], ['Hard q90 improvement', '0.21%'], ['Verdict', 'FAIL']],
      resultSha: '24aeed60003b3111c9d3dd24cee992f8bac539531d38923b9a205a1423e8d029',
      note: 'Transfer, protected, and final evidence stayed unexposed.'
    },
    {
      slug: 'phase18', label: 'Phase 18', title: 'Residual Advantage Confirmation', verdict: 'FAIL', stage: 'PROTECTED',
      summary: 'Development and transfer passed, but protected validation missed two q90 checks.',
      finding: 'The RMSE result still looked promising, but the locked protected q90 threshold and improvement-gap check failed. That ended the phase, so the final holdout stayed closed.',
      metrics: [['Protected simple RMSE improvement', '5.90%'], ['Protected simple q90 improvement', '9.04%'], ['Verdict', 'FAIL']],
      resultSha: 'ad96ca1a5119fcd594a84fd72a04f8efcc377ba788383d90dda9ef7eecad4431',
      note: 'The q90 miss remains a failure.'
    },
    {
      slug: 'phase19', label: 'Phase 19', title: 'Distribution-Wide Residual Advantage', verdict: 'PASS', stage: 'FINAL',
      summary: 'A narrower question about the residuals held up across every fresh evidence split.',
      finding: 'In the simple context, the frozen latency coefficient repeatedly reduced one-step lateral residual RMSE and MAE compared with Phase 14. In the hard context, the difference was close to neutral. The actual level error still became worse with latency.',
      metrics: [['Final simple RMSE improvement', '8.94%'], ['Final simple MAE improvement', '14.64%'], ['Hard RMSE improvement', '0.34%'], ['Hard MAE improvement', '0.02%']],
      resultSha: '8c23b9b9c8c9fb2f9146bf739e52074f8709d2fe9a81c794e64fb43f360acebf',
      note: 'q90 stayed descriptive. This is not a claim that latency is beneficial.'
    },
    {
      slug: 'phase20', label: 'Phase 20', title: 'Five-Factor Shapley Attenuation', verdict: 'PASS', stage: 'FINAL',
      summary: 'The drop in residual advantage from the simple context to the hard one was split across five predefined synthetic conditions.',
      finding: 'All 32 combinations were tested. Edge position, obliquity, dim lighting, blur/noise, and low contrast all contributed to the drop; the evidence does not support one factor as universally dominant.',
      metrics: [['Final RMSE attenuation', '14.77 pp'], ['Final MAE attenuation', '20.45 pp'], ['Shapley efficiency error', '0.0']],
      resultSha: 'f2a0cf4e1cf0765c3194025eb29072f9663f27e3cdd13b0594cde4643f33934e',
      note: 'Final PASS. All evidence roles closed.'
    },
    {
      slug: 'phase21', label: 'Phase 21', title: 'Orthogonal Context Spectrum', verdict: 'PASS', stage: 'FINAL',
      summary: 'Most of the context surface came from individual factors, although smaller interaction effects were still present.',
      finding: 'Across fresh development, transfer, protected, and final cubes, all five predefined factors pointed toward attenuation in the balanced first-order RMSE and MAE effects. The interactions were smaller, but not zero.',
      metrics: [['Final RMSE first-order share', '88.44%'], ['Final MAE first-order share', '78.01%'], ['Stable factor direction', '5 / 5']],
      resultSha: 'bc85a746cf1b770fb4119feb3979789975ed5201065d94de47c6dcc3a051d9ee',
      note: 'Structural description only; not a physical-causality claim.'
    },
    {
      slug: 'phase22', label: 'Phase 22', title: 'Frozen Additive Context Transfer', verdict: 'PASS', stage: 'FINAL',
      summary: 'A simple frozen additive model predicted a fresh 32-cell context surface without being refit.',
      finding: 'The candidate passed development, transfer, protected validation, and the one-shot final holdout. Final cellwise R² was 0.8319 for the RMSE-advantage surface and 0.7744 for the MAE-advantage surface, with 100% stable-sign accuracy on eligible cells.',
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