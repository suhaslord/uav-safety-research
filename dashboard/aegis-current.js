(() => {
  const applyCurrentFrontier = () => {
    const path = location.pathname.replace(/\/+$/, '') || '/';
    const phase11Href = '/phases/phase11/';
    const phase12Href = '/phases/phase12/';

    const replaceLeafText = (root, replacements) => {
      if (!root) return;
      root.querySelectorAll('*').forEach((node) => {
        if (node.children.length) return;
        const value = (node.textContent || '').trim();
        if (Object.prototype.hasOwnProperty.call(replacements, value)) node.textContent = replacements[value];
      });
    };

    const railStep = (href, index, label, frontier = false) => {
      const link = document.createElement('a');
      link.className = frontier ? 'rail-step frontier' : 'rail-step';
      link.href = href;
      link.innerHTML = `<span>${index}</span><i></i><strong>${label}</strong>`;
      return link;
    };

    if (path === '/phases') {
      const tabletStyle = document.createElement('style');
      tabletStyle.textContent = `
        @media (min-width:768px) and (max-width:900px) {
          body.archive-shell .map { padding-left:28px; padding-right:28px; }
          body.archive-shell .era { grid-template-columns:170px minmax(0,1fr); gap:28px; }
          body.archive-shell .track { min-width:0; }
          body.archive-shell .phase-link { grid-template-columns:120px minmax(0,1fr) 132px 24px; gap:16px; }
          body.archive-shell .phase-link > span,
          body.archive-shell .phase-link strong,
          body.archive-shell .phase-link small { min-width:0; overflow-wrap:anywhere; }
        }
      `;
      document.head.appendChild(tabletStyle);

      const top = document.querySelector('.top-end .primary');
      if (top) {
        top.textContent = 'Phase 12';
        top.href = phase12Href;
      }

      const intro = document.querySelector('.index-hero .big');
      if (intro) {
        intro.textContent = 'From the first safety supervisor through PX4/Gazebo evidence, the failed Phase 11 protected boundary, and the frozen Phase 12 final replication. Positive results, mismatches, near-misses, and failed gates all stay visible.';
      }

      const map = document.getElementById('archiveMap');
      if (map) {
        const staleFrontier = [...map.querySelectorAll('.era')].find((era) => {
          if (era.id === 'phase11ArchiveEra' || era.id === 'phase12ArchiveEra') return false;
          return (era.querySelector('h2')?.textContent || '').trim().toLowerCase() === 'current frontier';
        });
        if (staleFrontier) {
          const heading = staleFrontier.querySelector('h2');
          if (heading) heading.textContent = 'Frozen predecessor';
          staleFrontier.querySelectorAll('.frontier-link').forEach((link) => link.classList.remove('frontier-link'));
          replaceLeafText(staleFrontier, {
            'CURRENT FRONTIER': 'FROZEN PREDECESSOR',
            'Current frontier': 'Frozen predecessor',
            'Latest published frontier · mixed / failed overall · frozen without retuning': 'Frozen predecessor · mixed / failed overall · frozen without retuning'
          });
        }

        if (!map.querySelector(`a[href="${phase11Href}"]`)) {
          const era11 = document.createElement('section');
          era11.className = 'era';
          era11.id = 'phase11ArchiveEra';
          era11.innerHTML = '<header><span>05</span><h2>Phase 11 P14R</h2></header><div class="track"><a class="phase-link" href="/phases/phase11/"><span>Frozen predecessor</span><strong>High protected availability and coverage, with the locked lateral tail-efficiency gate still failing.</strong><small>Study closed · protected H4 failure preserved</small><i>→</i></a></div>';
          map.appendChild(era11);
        }

        if (!map.querySelector(`a[href="${phase12Href}"]`)) {
          const era12 = document.createElement('section');
          era12.className = 'era';
          era12.id = 'phase12ArchiveEra';
          era12.innerHTML = '<header><span>06</span><h2>Phase 12 Iteration 3</h2></header><div class="track"><a class="phase-link frontier-link" href="/phases/phase12/"><span>Current research frontier</span><strong>Innovation-conditioned continuity uncertainty passed development, transfer, protected validation, and final unseen replication without retuning.</strong><small>Lineage closed · simulation-only final replication PASS</small><i>→</i></a></div>';
          map.appendChild(era12);
        }
      }
      return;
    }

    if (!path.startsWith('/phases/phase') || path === '/phases/phase11' || path === '/phases/phase12') return;

    const rail = document.querySelector('#phaseRail,.phase-rail');
    if (rail) {
      if (!rail.querySelector(`a[href="${phase11Href}"]`)) rail.appendChild(railStep(phase11Href, '13', 'Phase 11\nP14R'));
      if (!rail.querySelector(`a[href="${phase12Href}"]`)) rail.appendChild(railStep(phase12Href, '14', 'Phase 12\nI3', true));
    }

    if (path === '/phases/phase10r') {
      const hero = document.getElementById('phaseHero');
      replaceLeafText(hero, {
        'Latest published frontier': 'Frozen predecessor',
        'Latest published frontier · frozen': 'Frozen predecessor · archived',
        'Latest published frontier · AegisLand research archive': 'Frozen predecessor · AegisLand research archive',
        'LATEST FRONTIER': 'FROZEN PREDECESSOR'
      });

      const next = document.getElementById('nextPhase');
      if (next) {
        next.href = phase11Href;
        next.removeAttribute('target');
        next.removeAttribute('rel');
        next.innerHTML = '<span>Next phase</span><strong>Phase 11 · P14R</strong><i>→</i>';
      }
    }

    if (path === '/phases/phase10') replaceLeafText(document.getElementById('nextPhase'), { 'Latest published frontier': 'Next phase' });
  };

  const scheduleCurrentFrontier = () => requestAnimationFrame(() => requestAnimationFrame(applyCurrentFrontier));
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', scheduleCurrentFrontier, { once: true });
  else scheduleCurrentFrontier();
})();
