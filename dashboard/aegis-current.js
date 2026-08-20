(() => {
  const path = location.pathname.replace(/\/+$/, '') || '/';
  const phase11Href = '/phases/phase11/';

  function phase11RailStep() {
    const link = document.createElement('a');
    link.className = 'rail-step frontier';
    link.href = phase11Href;
    link.innerHTML = '<span>13</span><i></i><strong>Phase 11\nP14R</strong>';
    return link;
  }

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
    if (map && !map.querySelector(`a[href="${phase11Href}"]`)) {
      const era = document.createElement('section');
      era.className = 'era';
      era.id = 'phase11ArchiveEra';
      era.innerHTML = '<header><span>05</span><h2>Phase 11 P14R</h2></header><div class="track"><a class="phase-link frontier-link" href="/phases/phase11/"><span>Current research frontier</span><strong>High protected availability and uncertainty coverage, with one lateral tail-efficiency gate blocking confirmation.</strong><small>Study closed · mixed protected-validation result</small><i>→</i></a></div>';
      map.appendChild(era);
    }
    return;
  }

  if (!path.startsWith('/phases/phase') || path === '/phases/phase11') return;

  const rail = document.querySelector('#phaseRail,.phase-rail');
  if (rail && !rail.querySelector(`a[href="${phase11Href}"]`)) {
    rail.appendChild(phase11RailStep());
  }

  if (path === '/phases/phase10r') {
    const next = document.getElementById('nextPhase');
    if (next) {
      next.href = phase11Href;
      next.innerHTML = '<span>Next phase</span><strong>Phase 11 · P14R</strong><i>→</i>';
    }

    document.querySelectorAll('.frontier-badge span,.frontier-topline span').forEach((node) => {
      if (/latest|frontier/i.test(node.textContent || '')) node.textContent = 'Frozen predecessor';
    });
  }
})();
