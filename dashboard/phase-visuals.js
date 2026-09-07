(() => {
  'use strict';

  const commonsFile = (title) => `https://commons.wikimedia.org/wiki/File:${encodeURIComponent(title).replace(/%20/g, '_')}`;
  const aceroTitle = (id) => `Advanced Capabilities for Emergency Response Operations (ACERO) (${id}).jpg`;
  const stereoTitle = (id) => `STEReO Field Testing (${id}).jpg`;

  const donRichey = 'Photo: Don Richey / NASA Ames Research Center';
  const joelKowsky = 'Photo: Joel Kowsky / NASA';

  const acero = (file, id, alt, context) => Object.freeze({
    file,
    alt,
    context,
    credit: donRichey,
    license: 'Public domain',
    source: commonsFile(aceroTitle(id))
  });

  const stereo = (file, id, alt, context) => Object.freeze({
    file,
    alt,
    context,
    credit: joelKowsky,
    license: 'Public domain',
    source: commonsFile(stereoTitle(id))
  });

  const bySlug = {
    phase1: acero('phase01-context.jpg', 'ACD24-0180-005', 'L3Harris FVR90 unmanned aerial vehicle lifting off during a NASA Ames ACERO field test.', 'Context: supervised launch and active safety gating.'),
    phase2: acero('phase02-context.jpg', 'ACD24-0180-034', 'Alta-X unmanned aerial vehicle with a camera payload in flight during a NASA Ames ACERO field test.', 'Context: sustained flight where one noisy instant should not dominate.'),
    phase3: acero('acero-ground-control.jpg', 'ACD24-0180-009', 'Ground-control operators monitoring an unmanned aircraft flight during a NASA Ames ACERO field test.', 'Context: independent monitoring around a single flight.'),
    phase4: acero('phase04-context.jpg', 'ACD24-0180-012', 'Ground-control personnel monitoring an unmanned aircraft flight during a NASA Ames ACERO field test.', 'Context: recorded operations and traceable provenance.'),
    phase5: acero('phase05-context.jpg', 'ACD24-0180-001', 'NASA Ames ACERO field-test scene from unmanned aircraft operations at Monterey Bay Academy Airport.', 'Context: field testing under real operational stress.'),
    phase6: acero('acero-uav-flight.jpg', 'ACD24-0180-035', 'Alta-X unmanned aerial vehicle with a camera payload in flight during a NASA Ames ACERO field test.', 'Context: camera-equipped UAV perception in flight.'),
    phase6b: acero('phase06b-context.jpg', 'ACD24-0180-036', 'Alta-X unmanned aerial vehicle with a camera payload being guided toward a landing pad during a NASA Ames ACERO field test.', 'Context: camera perception during terminal landing.'),
    phase7: stereo('phase07-context.jpg', 'NHQ202105050027', 'FreeFly Systems Alta X drone in flight during NASA STEReO field testing near Redding, California.', 'Context: moving from internal assumptions toward field conditions.'),
    phase8: stereo('phase08-context.jpg', 'NHQ202105050015', 'NASA STEReO software engineer working at a research laptop during simulated drone operations.', 'Context: human-in-the-loop simulated drone operations.'),
    phase9: acero('acero-uav-landing.jpg', 'ACD24-0180-037', 'Alta-X unmanned aerial vehicle with a camera payload being guided down to a landing pad during a NASA Ames ACERO field test.', 'Context: camera geometry close to the landing surface.'),
    phase10: stereo('phase10-context.jpg', 'NHQ202105050020', 'NASA STEReO autonomy researchers during simulated drone operations near Redding, California.', 'Context: temporal estimation supported by monitored operations.'),
    phase10r: stereo('phase10r-context.jpg', 'NHQ202105050025', 'FreeFly Systems Alta X drone in flight during NASA STEReO field testing near Redding, California.', 'Context: a UAV exposed to a different field environment.'),
    phase11: stereo('stereo-uav-preflight.jpg', 'NHQ202105050002', 'NASA STEReO pilot performing pre-flight checks on a FreeFly Systems Alta X drone.', 'Context: pre-flight checks before protected validation.'),
    phase12: acero('phase12-context.jpg', 'ACD24-0180-016', 'NASA Ames ACERO field-test photograph from unmanned aircraft operations at Monterey Bay Academy Airport.', 'Context: establishing a repeatable uncertainty baseline.'),
    phase13a: stereo('phase13a-context.jpg', 'NHQ202105050026', 'FreeFly Systems Alta X drone in flight during NASA STEReO field testing near Redding, California.', 'Context: external-validity pressure in field operations.'),
    phase13b: acero('phase13b-context.jpg', 'ACD24-0180-022', 'NASA Ames ACERO field-test photograph from unmanned aircraft operations at Monterey Bay Academy Airport.', 'Context: paired degradation under repeated test conditions.'),
    phase13c: acero('phase13c-context.jpg', 'ACD24-0180-023', 'NASA Ames ACERO field-test photograph from unmanned aircraft operations at Monterey Bay Academy Airport.', 'Context: isolating which test factor matters most.'),
    phase14: acero('phase14-context.jpg', 'ACD24-0180-021', 'A SuperVolo XL unmanned aerial vehicle being prepared for flight during a NASA Ames ACERO field test.', 'Context: preparing another bounded test attempt.'),
    phase15: acero('phase15-context.jpg', 'ACD24-0180-002', 'NASA Ames ACERO field-test photograph from unmanned aircraft operations at Monterey Bay Academy Airport.', 'Context: testing whether the proposed operating frontier is feasible.'),
    phase16: acero('phase16-context.jpg', 'ACD24-0180-003', 'NASA Ames ACERO field-test photograph from unmanned aircraft operations at Monterey Bay Academy Airport.', 'Context: latency and stale information during active operations.'),
    phase17: acero('phase17-context.jpg', 'ACD24-0180-004', 'NASA Ames ACERO field-test photograph from unmanned aircraft operations at Monterey Bay Academy Airport.', 'Context: context-dependent model behavior across operating conditions.'),
    phase18: acero('phase18-context.jpg', 'ACD24-0180-038', 'Alta-X unmanned aerial vehicle on a landing pad during a NASA Ames ACERO field test at sunset.', 'Context: a protected confirmation attempt near the landing boundary.'),
    phase19: acero('phase19-context.jpg', 'ACD24-0180-006', 'NASA Ames ACERO field-test photograph from unmanned aircraft operations at Monterey Bay Academy Airport.', 'Context: narrowing the claim to repeatable residual behavior.'),
    phase20: acero('phase20-context.jpg', 'ACD24-0180-029', 'NASA Ames ACERO field-test photograph from unmanned aircraft operations at Monterey Bay Academy Airport.', 'Context: decomposing a complex field context into simpler factors.'),
    phase21: acero('phase21-context.jpg', 'ACD24-0180-033', 'NASA Ames ACERO field-test photograph from unmanned aircraft operations at Monterey Bay Academy Airport.', 'Context: studying structure across multiple operating contexts.'),
    phase22: stereo('phase22-context.jpg', 'NHQ202105050014', 'NASA STEReO test operators at a workstation during simulated drone operations.', 'Context: a final locked transfer reviewed without refitting.')
  };

  window.AEGIS_PHASE_VISUALS = Object.freeze({
    bySlug: Object.freeze(bySlug),
    contextLabel: 'Visual context — not AegisLand experimental evidence'
  });
})();
