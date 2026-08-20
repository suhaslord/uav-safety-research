(() => {
  const applyCurrentFrontier = () => {
    const path = location.pathname.replace(/\/+$/, '') || '/';
    const phase11Href = '/phases/phase11/';

    const replaceLeafText = (root, replacements) => {
      if (!root) return;
      root.querySelectorAll('*').forEach((node) => {
        if (node.children.length) return;
        const value = (node.textContent || '').trim();
        if (Object.prototype.hasOwnProperty.call(replacements, value)) {
          node.textContent = replacements[value];
        }
      });
    };

    const phase11RailStep = () => {
      const link = document.createElement('a');
      link.className = 'rail-step frontier';
      link.href = phase11Href;
      link.innerHTML = '<span>13</span><i></i><strong>Phase 11\nP14R</strong>';
      return link;
    };

    if (path === '/phases') {
      const top = document.querySelector('.top-end .primary');
      if (top) {
        top.textContent = 'Phase 11';
        top.href = phase11Href;
      }

      const intro = document.querySelector('.index-hero .big');
      if (intro) {
        intro.textContent = 'From the first safety supervisor through PX4/Gazebo evidence, the frozen Phase 10R holdout, and Phase 11 P14R. Positive results, mismatches, near-misses, and failed gates all stay visible.';
      }

      const map = document.getElementById('archiveMap');
      if (map) {
        const staleFrontier = [...map.querySelectorAll('.era')].find((era) => {
          if (era.id === 'phase11ArchiveEra') return false;
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
          const era = document.createElement('section');
          era.className = 'era';
          era.id = 'phase11ArchiveEra';
          era.innerHTML = '<header><span>05</span><h2>Phase 11 P14R</h2></header><div class="track"><a class="phase-link frontier-link" href="/phases/phase11/"><span>Current research frontier</span><strong>High protected availability and uncertainty coverage, with one lateral tail-efficiency gate blocking confirmation.</strong><small>Study closed · mixed protected-validation result</small><i>→</i></a></div>';
          map.appendChild(era);
        }
      }
      return;
    }

    if (!path.startsWith('/phases/phase') || path === '/phases/phase11') return;

    const rail = document.querySelector('#phaseRail,.phase-rail');
    if (rail && !rail.querySelector(`a[href="${phase11Href}"]`)) {
      rail.appendChild(phase11RailStep());
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
        next.innerHTML = '<span>Next phase</span><strong>Phase 11 · P14R</strong><i>→</i>';
      }
    }

    if (path === '/phases/phase10') {
      replaceLeafText(document.getElementById('nextPhase'), { 'Latest published frontier': 'Next phase' });
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyCurrentFrontier, { once: true });
  } else {
    applyCurrentFrontier();
  }
})();
