(() => {
  'use strict';

  const getSlug = () => location.pathname.match(/\/phases\/(phase(?:\d+[a-z]?))\/?$/i)?.[1]?.toLowerCase() || '';

  const makeChip = (category, meta) => {
    const chip = document.createElement('div');
    chip.className = 'phase-identity-chip';
    chip.innerHTML = `<span>${category.name}</span><strong>${meta.identity}</strong>`;
    return chip;
  };

  const makeRoleCard = (meta) => {
    const card = document.createElement('div');
    card.className = 'phase-role-card';
    card.innerHTML = `
      <div class="phase-role-card__label"><span>Place in the program</span><strong>${meta.identity}</strong></div>
      <p class="phase-role-card__question" data-question-labeled="true"><span class="phase-role-card__question-label">Central question</span><span class="phase-role-card__question-text">${meta.question}</span></p>
      <div class="phase-role-card__signal"><span>Signal</span><strong>${meta.signal}</strong></div>`;
    return card;
  };

  const sentenceIdentity = (meta) => meta.identity.replace(/^The\s+/i, 'the ');

  const humanizeLegacyCopy = (slug, meta) => {
    const identity = sentenceIdentity(meta);
    const snapshot = document.getElementById('snapshotTitle');
    if (snapshot) snapshot.textContent = slug === 'phase4' ? 'Why the numbering gap matters.' : `Why ${identity} existed.`;

    const evidence = document.querySelector('.evidence-section .section-head h2');
    if (evidence) evidence.textContent = 'What the evidence showed.';

    const limits = document.querySelector('.limits-section .section-head h2');
    if (limits) limits.textContent = 'Where it still broke.';

    const changes = document.querySelector('#changes .section-head h2');
    if (changes) changes.textContent = 'What changed here.';

    const system = document.querySelector('.system-section .section-head h2');
    if (system) system.textContent = slug === 'phase4' ? 'How the gap is represented.' : `How ${identity} worked.`;

    const primary = document.querySelector('#phaseHero .actions .button.blue');
    if (primary) primary.textContent = 'Read the evidence';
    const secondary = document.querySelector('#phaseHero .actions .button.ash');
    if (secondary) secondary.textContent = 'Open source ↗';
  };

  const humanizeFrozenCopy = (meta) => {
    const identity = sentenceIdentity(meta);
    const panels = document.querySelectorAll('.phase-detail__body .phase-detail__panel');
    const findingTitle = panels[0]?.querySelector('h2');
    if (findingTitle) findingTitle.textContent = `What ${identity} tells us.`;
    const sourceTitle = panels[1]?.querySelector('h2');
    if (sourceTitle) sourceTitle.textContent = 'Locked source record';

    const frozenLabel = document.querySelector('.phase-detail__context .phase-detail__eyebrow');
    if (frozenLabel) frozenLabel.textContent = 'Why the record stays fixed';
  };

  const humanizePhase11Copy = () => {
    const primary = document.querySelector('body.phase11-polish .hero .button.primary, body.phase11-polish .hero .signature-button--primary');
    if (primary && /inspect|explore|case/i.test(primary.textContent)) primary.textContent = 'Read the result';
  };

  const normalizePhaseFlow = (slug) => {
    // Phase 10R used to jump out to a GitHub preregistration document even though
    // the archive now has a first-class Phase 11 page. Keep the research source
    // link intact elsewhere, but make the site progression stay inside the site.
    if (slug === 'phase10r') {
      const next = document.getElementById('nextPhase');
      if (next) {
        next.href = '/phases/phase11/';
        next.removeAttribute('target');
        next.removeAttribute('rel');
        next.innerHTML = '<span>Next research phase</span><strong>Phase 11 · Protected reliability</strong><i>→</i>';
      }
      if (!document.getElementById('phase10r-density-fix')) {
        const style = document.createElement('style');
        style.id = 'phase10r-density-fix';
        style.textContent = '@media(max-width:700px){body.archive-shell[data-phase="phase10r"] .section{padding-top:22px!important;padding-bottom:22px!important}body.archive-shell[data-phase="phase10r"] .section-head{margin-bottom:14px!important}body.archive-shell[data-phase="phase10r"] .metrics,body.archive-shell[data-phase="phase10r"] .metric-cards{margin-top:18px!important}}';
        document.head.appendChild(style);
      }
    }
  };

  const applyIdentity = () => {
    const taxonomy = window.AEGIS_PHASE_TAXONOMY;
    const slug = getSlug();
    const meta = taxonomy?.bySlug?.[slug];
    const category = meta && taxonomy?.categoryById?.[meta.category];
    if (!slug || !meta || !category) return;

    document.body.dataset.phase = slug;
    document.body.dataset.phaseCategory = category.id;

    // Categories organize the research, but the UI keeps one chromatic accent.
    document.documentElement.style.setProperty('--phase-accent', '#3e6ae1');
    document.documentElement.style.setProperty('--phase-tint', '#eef2ff');

    normalizePhaseFlow(slug);

    const legacyHero = document.querySelector('body.archive-shell #phaseHero');
    if (legacyHero) {
      const copy = legacyHero.querySelector('.hero-copy');
      if (copy && !copy.querySelector('.phase-identity-chip')) {
        copy.prepend(makeChip(category, meta));
        copy.appendChild(makeRoleCard(meta));
      }
      humanizeLegacyCopy(slug, meta);
      return;
    }

    const frozenHero = document.querySelector('.phase-detail__hero');
    if (frozenHero) {
      const copy = frozenHero.firstElementChild;
      if (copy && !copy.querySelector('.phase-identity-chip')) copy.prepend(makeChip(category, meta));
      if (!frozenHero.querySelector('.phase-role-card')) frozenHero.appendChild(makeRoleCard(meta));
      humanizeFrozenCopy(meta);
      return;
    }

    const phase11Copy = document.querySelector('body.phase11-polish .hero .hero-grid > div:first-child');
    if (phase11Copy && !phase11Copy.querySelector('.phase-identity-chip')) {
      phase11Copy.prepend(makeChip(category, meta));
      phase11Copy.appendChild(makeRoleCard(meta));
    }
    humanizePhase11Copy();
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => requestAnimationFrame(applyIdentity), { once: true });
  } else {
    requestAnimationFrame(applyIdentity);
  }
})();