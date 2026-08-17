(() => {
  const q = (s, root = document) => root.querySelector(s);
  const qa = (s, root = document) => [...root.querySelectorAll(s)];

  function fixLineage() {
    const map = q('.lineage-map');
    if (!map) return;

    const eras = qa('.lineage-era', map);
    const historical = eras.find(era => era.id !== 'phase11LineageEra' && /Phase 9/i.test(era.textContent));
    if (historical) {
      historical.classList.remove('lineage-era-current');
      historical.dataset.phase11Historical = 'true';
      const h = q('.lineage-era-heading h3', historical);
      const p = q('.lineage-era-heading p', historical);
      if (h) h.textContent = 'Camera + temporal perception';
      if (p) p.textContent = 'Phase 9 camera evidence became historical; Phase 10 added temporal metric estimation and Phase 10R tested generalization under harder shift.';
      const phase9 = qa('.lineage-era-list li', historical).find(li => /Phase 9/i.test(li.textContent));
      if (phase9) {
        const eyebrow = q('.lineage-eyebrow', phase9);
        if (eyebrow) eyebrow.textContent = 'Historical camera evidence';
        const meta = qa('.lineage-meta span', phase9);
        if (meta.length) meta[meta.length - 1].textContent = 'View merged PR ↗';
      }
    }

    const current = q('#phase11LineageEra', map);
    if (current) {
      current.classList.add('lineage-era-current');
      current.classList.remove('phase11Historical');
      delete current.dataset.phase11Historical;
      const h = q('.lineage-era-heading h3', current);
      const p = q('.lineage-era-heading p', current);
      if (h) h.textContent = 'Current frontier';
      if (p) p.textContent = 'Phase 11 P14R is the current AegisLand model: high availability and robust uncertainty with one protected lateral tail-efficiency failure kept visible.';
      const card = q('.lineage-era-list li', current);
      if (card) {
        const eyebrow = q('.lineage-eyebrow', card);
        if (eyebrow) eyebrow.textContent = 'Current model · mixed protected result';
      }
    }
  }

  function fixMobile() {
    const old = qa('.mobile-menu-secondary a').find(a => /Phase\s*7/i.test(a.textContent));
    if (old) { old.textContent = 'Phase 11'; old.href = '/phases/phase11/'; }
  }

  function fix() {
    if (location.pathname === '/') {
      fixLineage();
      fixMobile();
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fix, {once:true});
  [250, 800].forEach(ms => setTimeout(fix, ms));
})();
