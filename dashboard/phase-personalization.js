(() => {
  'use strict';

  const getSlug = () => location.pathname.match(/\/phases\/(phase(?:\d+[a-z]?))\/?$/i)?.[1]?.toLowerCase() || '';

  const makeChip = (category, meta) => {
    const chip = document.createElement('div');
    chip.className = 'phase-identity-chip';
    chip.innerHTML = `<span>${category.name}</span><strong>· ${meta.identity}</strong>`;
    return chip;
  };

  const makeRoleCard = (meta) => {
    const card = document.createElement('div');
    card.className = 'phase-role-card';
    card.innerHTML = `
      <div class="phase-role-card__label"><span>Phase role</span><strong>${meta.identity}</strong></div>
      <p class="phase-role-card__question">${meta.question}</p>
      <div class="phase-role-card__signal"><span>Core signal</span><strong>${meta.signal}</strong></div>`;
    return card;
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

    const legacyHero = document.querySelector('body.archive-shell #phaseHero');
    if (legacyHero) {
      const copy = legacyHero.querySelector('.hero-copy');
      if (copy && !copy.querySelector('.phase-identity-chip')) {
        copy.prepend(makeChip(category, meta));
        copy.appendChild(makeRoleCard(meta));
      }
      return;
    }

    const frozenHero = document.querySelector('.phase-detail__hero');
    if (frozenHero) {
      const copy = frozenHero.firstElementChild;
      if (copy && !copy.querySelector('.phase-identity-chip')) copy.prepend(makeChip(category, meta));
      if (!frozenHero.querySelector('.phase-role-card')) frozenHero.appendChild(makeRoleCard(meta));
      return;
    }

    const phase11Copy = document.querySelector('body.phase11-polish .hero .hero-grid > div:first-child');
    if (phase11Copy && !phase11Copy.querySelector('.phase-identity-chip')) {
      phase11Copy.prepend(makeChip(category, meta));
      phase11Copy.appendChild(makeRoleCard(meta));
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => requestAnimationFrame(applyIdentity), { once: true });
  } else {
    requestAnimationFrame(applyIdentity);
  }
})();
