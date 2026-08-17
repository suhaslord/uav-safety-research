(() => {
  const q = (selector, root = document) => root.querySelector(selector);
  const qa = (selector, root = document) => [...root.querySelectorAll(selector)];
  const text = (selector, value, root = document) => {
    const node = q(selector, root);
    if (node) node.textContent = value;
    return node;
  };

  function ensureHomeStyles() {
    if (q('#phase11ConsistencyStyles')) return;
    const style = document.createElement('style');
    style.id = 'phase11ConsistencyStyles';
    style.textContent = `
      .hero-actions{justify-content:flex-start!important;align-items:center!important;gap:12px!important;margin-left:0!important;margin-right:0!important;width:100%!important}
      .hero-actions a{flex:0 0 auto!important;width:auto!important;min-width:164px!important;margin:0!important;padding-left:24px!important;padding-right:24px!important}
      .lineage-era-current .lineage-era-heading h3::after{content:'LATEST';display:inline-flex;margin-left:10px;padding:3px 6px;border:1px solid rgba(143,174,255,.45);border-radius:999px;color:#8faeff;font-size:8px;letter-spacing:.13em;vertical-align:middle}
      @media(max-width:560px){.hero-actions{display:grid!important;grid-template-columns:1fr!important}.hero-actions a{width:100%!important;min-width:0!important}}
    `;
    document.head.appendChild(style);
  }

  function makeLineageItem({index, eyebrow, title, copy, href, meta, action, secondaryHref, secondaryText}) {
    const li = document.createElement('li');
    li.innerHTML = `
      <a class="lineage-card-main" href="${href}" ${href.startsWith('http') ? 'target="_blank" rel="noreferrer"' : ''}>
        <span class="lineage-index">${index}</span>
        <div class="lineage-body">
          <p class="lineage-eyebrow">${eyebrow}</p>
          <h3>${title}</h3>
          <p>${copy}</p>
          <div class="lineage-meta"><span>${meta}</span><span class="lineage-open">${action}</span></div>
        </div>
      </a>
      ${secondaryHref ? `<div class="lineage-secondary"><a href="${secondaryHref}">${secondaryText}</a></div>` : ''}`;
    return li;
  }

  function patchHomeLineage() {
    const intro = q('#timeline .lineage-intro .lead');
    if (intro) {
      intro.textContent = 'The project history is deliberately inspectable: protocols, frozen benchmarks, external-simulator evidence, Phase 9 camera evidence, Phase 10 temporal perception, Phase 10R shift testing, and the current Phase 11 P14R study all remain linked to their record.';
    }

    const map = q('.lineage-map');
    if (map) {
      const eras = qa('.lineage-era', map);
      const cameraEra = eras[eras.length - 1];
      if (cameraEra && !cameraEra.dataset.phase11Historical) {
        cameraEra.dataset.phase11Historical = 'true';
        cameraEra.classList.remove('lineage-era-current');
        text('.lineage-era-heading h3', 'Camera + temporal perception', cameraEra);
        text('.lineage-era-heading p', 'Phase 9 camera evidence became historical; Phase 10 added temporal metric estimation and Phase 10R tested generalization under harder shift.', cameraEra);
        const phase9 = q('.lineage-era-list li', cameraEra);
        if (phase9) {
          text('.lineage-eyebrow', 'Historical camera evidence', phase9);
          const action = qa('.lineage-meta span', phase9).at(-1);
          if (action) action.textContent = 'View merged PR ↗';
        }
        const list = q('.lineage-era-list', cameraEra);
        if (list && !q('[data-lineage-phase="10"]', list)) {
          const p10 = makeLineageItem({
            index: '12',
            eyebrow: 'Frozen temporal metric study',
            title: 'Phase 10',
            copy: 'AegisT10 added causal temporal metric estimation and calibrated uncertainty; the frozen holdout preserved the mixed result instead of tuning it away.',
            href: '/phases/phase10/',
            meta: 'AegisT10',
            action: 'Open Phase 10 →'
          });
          p10.dataset.lineagePhase = '10';
          list.appendChild(p10);
          const p10r = makeLineageItem({
            index: '13',
            eyebrow: 'Distribution-shift revision',
            title: 'Phase 10R',
            copy: 'Phase 10R broadened challenge conditions and preserved the frozen shift result as the bridge into Phase 11 reliability work.',
            href: '/phases/phase10r/',
            meta: 'frozen shift evidence',
            action: 'Open Phase 10R →'
          });
          p10r.dataset.lineagePhase = '10r';
          list.appendChild(p10r);
        }
      }

      if (!q('#phase11LineageEra', map)) {
        const section = document.createElement('section');
        section.className = 'lineage-era lineage-era-current';
        section.id = 'phase11LineageEra';
        section.innerHTML = `
          <div class="lineage-era-heading"><span>05</span><h3>Current frontier</h3><p>Phase 11 P14R is the latest AegisLand model: high availability and robust uncertainty with one protected lateral tail-efficiency failure kept visible.</p></div>
          <ol class="lineage-era-list" style="--era-count:1"></ol>`;
        q('.lineage-era-list', section).appendChild(makeLineageItem({
          index: '14',
          eyebrow: 'Current model · mixed protected result',
          title: 'Phase 11 · P14R',
          copy: 'Every required seen-transfer gate passed. Protected validation reached 98.53% availability and about 96% 95%-coverage, but one locked H4 lateral tail-efficiency component failed, so final unseen confirmation was withheld.',
          href: '/phases/phase11/',
          meta: '98.53% availability',
          action: 'Open Phase 11 →'
        }));
        map.appendChild(section);
      }
      return;
    }

    const list = q('#timeline .lineage-list');
    if (list) {
      const last = qa(':scope > li', list).at(-1);
      if (last) {
        text('.lineage-eyebrow', 'Historical camera evidence', last);
        const action = qa('.lineage-meta span', last).at(-1);
        if (action) action.textContent = 'View merged PR ↗';
      }
    }
  }

  function patchHistoricalPhase9Sections() {
    const replacements = [
      ['#result .kicker', 'Historical evidence · Phase 9 camera trace'],
      ['#availability .kicker', 'Phase 9 archive · frame-level availability'],
      ['#telemetry .kicker', 'Phase 9 archive · derived trace views'],
      ['#geometry .kicker', 'Phase 9 archive · metric geometry'],
      ['#provenance .kicker', 'Phase 9 evidence provenance']
    ];
    replacements.forEach(([selector, value]) => text(selector, value));

    const resultLead = q('#result .lead');
    if (resultLead) resultLead.textContent = 'This preserved Phase 9 trace showed complete observation availability on projected-visible frames. It remains historical evidence; Phase 11 P14R is the current frontier.';

    const auditStatus = q('.source-audit-status');
    if (auditStatus) auditStatus.textContent = 'checked against archived Phase 9 artifact';

    const fig = q('.hero-media figcaption');
    if (fig) {
      const spans = qa('span', fig);
      if (spans[0]) spans[0].textContent = 'Historical Phase 9 camera target';
      if (spans[1]) spans[1].textContent = 'archived camera evidence · current model is Phase 11 P14R';
    }

    const status = q('#refreshStatus');
    if (status) {
      status.textContent = 'Phase 9 CI';
      status.title = 'Refresh archived Phase 9 CI status';
    }

    const normalizeStatus = () => {
      const label = q('#liveLabel');
      if (label) {
        label.textContent = label.textContent
          .replace('Current CI', 'Phase 9 archive CI')
          .replace('Audited evidence · checking current CI…', 'Archived Phase 9 evidence · checking CI…');
      }
      const meta = q('#liveMeta');
      if (meta) meta.textContent = meta.textContent.replace('Current UI/analysis CI:', 'Phase 9 archive UI/analysis CI:');
    };
    normalizeStatus();
    [q('#liveLabel'), q('#liveMeta')].filter(Boolean).forEach(node => {
      const observer = new MutationObserver(() => {
        observer.disconnect();
        normalizeStatus();
        observer.observe(node, {childList:true, characterData:true, subtree:true});
      });
      observer.observe(node, {childList:true, characterData:true, subtree:true});
    });
  }

  function patchHome() {
    ensureHomeStyles();
    document.title = 'AegisLand — Phase 11 · Current Frontier';
    const desc = q('meta[name="description"]');
    if (desc) desc.content = 'AegisLand Phase 11 P14R — the current AegisLand frontier, with high availability and robust uncertainty coverage under compound shift.';

    const headerPhase = q('.site-header .phase-link');
    if (headerPhase) {
      headerPhase.textContent = 'Phase 11';
      headerPhase.href = '/phases/phase11/';
    }

    text('main .hero .kicker', 'simulation-only research · current frontier: Phase 11');
    text('main .hero .hero-subtitle', 'P14R passed every required seen-transfer gate and preserved ~96% protected 95% coverage with 98.53% availability. One locked lateral tail-efficiency gate stopped final confirmation.');

    const actions = qa('main .hero .hero-actions a');
    if (actions[0]) { actions[0].textContent = 'Open Phase 11'; actions[0].href = '/phases/phase11/'; }
    if (actions[1]) { actions[1].textContent = 'Read final report'; actions[1].href = 'https://github.com/suhaslord/uav-safety-research/blob/main/docs/phase11_final_report.md'; }

    const meta = q('main .hero .hero-meta');
    if (meta) meta.innerHTML = '<span>Phase 11 · P14R</span><span>robust groupwise conformal envelope</span><span>current frontier · mixed protected result</span><span>safety acceptance: false</span>';

    const tele = q('main .hero .hero-telemetry');
    if (tele) tele.innerHTML = '<span><strong>98.53%</strong><small>protected availability</small></span><span><strong>96.17%</strong><small>lateral 95% coverage</small></span><span><strong>94.63%</strong><small>rescue recovery</small></span>';

    const heroFoot = q('.hero-foot');
    if (heroFoot) {
      const spans = qa('span', heroFoot);
      if (spans[0]) spans[0].textContent = 'Phase 11 · simulation-only · no safety acceptance';
    }

    const word = q('.site-header .wordmark');
    if (word && !q('.phase11-wordmark-icon', word)) {
      word.innerHTML = '<span class="phase11-wordmark-icon" style="width:28px;height:28px;border-radius:9px;background:#171a20;color:#fff;display:inline-grid;place-items:center;margin-right:9px;font-size:12px">A</span><span>AEGISLAND</span>';
    }

    const hero = q('main .hero');
    if (hero && !q('#phase11Victory')) {
      const win = document.createElement('section');
      win.id = 'phase11Victory';
      win.style.cssText = 'display:grid;grid-template-columns:minmax(0,1.2fr) minmax(280px,.8fr);gap:30px;align-items:end;padding:clamp(34px,6vw,72px) clamp(20px,5vw,72px);background:#171a20;color:#fff;border-bottom:1px solid #2b2e33';
      win.innerHTML = '<div><div style="font-size:10px;letter-spacing:.15em;text-transform:uppercase;color:#8faeff;margin-bottom:14px;font-weight:700">Phase 11 · P14R · current frontier</div><strong style="display:block;font-size:clamp(38px,5.8vw,82px);line-height:.92;letter-spacing:-.055em;max-width:900px">The strongest AegisLand model yet.</strong><p style="max-width:760px;color:#b7bbc2;line-height:1.6;margin:22px 0 0">Every required seen-transfer gate passed. Protected validation kept high coverage, high availability and honest rescue behavior; a single preregistered lateral tail-efficiency component still failed, so the final holdout stayed untouched.</p></div><div style="border-left:2px solid #2f6df6;padding-left:20px"><span style="font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:#9ca1aa">Protected result</span><strong style="display:block;font-size:42px;letter-spacing:-.045em;margin:8px 0">10 / 11</strong><small style="color:#b7bbc2">required gate families passed; H4 tail efficiency blocked final confirmation</small><div style="margin-top:22px"><a href="/phases/phase11/" style="color:#fff;text-decoration:none;font-size:12px;font-weight:700">Explore Phase 11 →</a></div></div>';
      hero.insertAdjacentElement('afterend', win);
    }

    if (hero && !q('#homeModelRail')) {
      const phases = ['1','2','3','4','5','6','6b','7','8','9','10','10r','11'];
      const rail = document.createElement('section');
      rail.id = 'homeModelRail';
      rail.style.cssText = 'background:#fff;border-top:1px solid rgba(23,26,32,.08);border-bottom:1px solid rgba(23,26,32,.08);padding:22px clamp(20px,5vw,72px);overflow-x:auto';
      rail.innerHTML = '<div style="display:flex;justify-content:space-between;gap:20px;margin-bottom:16px"><div><div style="font-size:10px;letter-spacing:.13em;color:#6b6d70;text-transform:uppercase">Research progression</div><strong style="font-size:13px">Every model stays reachable.</strong></div><a class="home-archive-link" href="/phases/" style="font-size:11px">Open full archive ↗</a></div><div class="home-rail-grid" style="display:grid;grid-template-columns:repeat(13,minmax(76px,1fr));min-width:1060px;gap:0">' + phases.map((p,i) => '<a class="home-rail-step ' + (p === '11' ? 'active' : '') + '" href="/phases/phase' + p + '/" style="text-align:center;font-size:10px;font-weight:' + (p === '11' ? '700' : '500') + '">' + String(i+1).padStart(2,'0') + '<br>Phase ' + (p === '10r' ? '10R' : p.toUpperCase()) + '</a>').join('') + '</div>';
      const anchor = q('#phase11Victory') || hero;
      anchor.insertAdjacentElement('afterend', rail);
    }

    const media = q('.hero-media');
    if (media) media.setAttribute('aria-label', 'Historical Phase 9 camera visualization retained beneath the current Phase 11 research summary');

    patchHistoricalPhase9Sections();
    patchHomeLineage();

    const mobilePhase = qa('.mobile-menu-secondary a').find(a => /Phase\s*7/i.test(a.textContent));
    if (mobilePhase) { mobilePhase.textContent = 'Phase 11'; mobilePhase.href = '/phases/phase11/'; }

    const mq = matchMedia('(max-width:820px)');
    const fix = () => {
      const win = q('#phase11Victory');
      if (win) win.style.gridTemplateColumns = mq.matches ? '1fr' : 'minmax(0,1.2fr) minmax(280px,.8fr)';
    };
    fix();
    mq.addEventListener?.('change', fix);
  }

  function ensureArchiveCard(track, href, label, title, status) {
    if (!track || q(`a[href="${href}"]`, track)) return;
    const a = document.createElement('a');
    a.className = 'phase-link';
    a.href = href;
    a.innerHTML = `<span>${label}</span><strong>${title}</strong><small>${status}</small><i>→</i>`;
    track.appendChild(a);
  }

  function patchArchive() {
    const top = q('.top-end .primary');
    if (top) { top.textContent = 'Phase 11'; top.href = '/phases/phase11/'; }

    const path = location.pathname.replace(/\/$/, '') || '/';
    const isIndex = path === '/phases';

    if (isIndex) {
      const big = q('.index-hero .big');
      if (big) big.textContent = 'From the first safety supervisor to PX4/Gazebo evidence, temporal metric perception, frozen Phase 10R shift testing, and Phase 11 P14R — the current AegisLand frontier. Positive results, mismatches, near-misses and failed gates all stay visible.';

      const map = q('#archiveMap');
      if (map) {
        const eras = qa('.era', map);
        const phase10Era = eras.find(era => q('a[href="/phases/phase10/"]', era));
        if (phase10Era) {
          text('header h2', 'Temporal perception + shift', phase10Era);
          ensureArchiveCard(q('.track', phase10Era), '/phases/phase10r/', 'Phase 10R · Generalization', 'Frozen distribution-shift revision preserved before the Phase 11 reliability program.', 'Frozen shift result · historical');
        }

        if (!q('#phase11ArchiveEra', map)) {
          const era = document.createElement('section');
          era.className = 'era';
          era.id = 'phase11ArchiveEra';
          era.innerHTML = '<header><span>05</span><h2>Current frontier · Phase 11</h2></header><div class="track"><a class="phase-link" href="/phases/phase11/"><span>Phase 11 · P14R</span><strong>Current AegisLand model: robust coverage, high availability, and one protected lateral tail-efficiency boundary.</strong><small>Study closed · mixed protected-validation result · no final unseen confirmation</small><i>→</i></a></div>';
          map.appendChild(era);
        }
      }
      return;
    }

    if (path === '/phases/phase10') {
      text('.hero-copy .kicker', 'Temporal metric perception · AegisLand research archive');
      text('#phaseOverviewVisual figcaption strong', 'Temporal metric perception');
      const next = q('#nextPhase');
      if (next) {
        next.href = '/phases/phase10r/';
        next.innerHTML = '<span>Next research step</span><strong>Phase 10R · Generalization</strong><i>→</i>';
      }
    }

    if (path === '/phases/phase10r') {
      const next = q('#nextPhase');
      if (next) {
        next.href = '/phases/phase11/';
        next.innerHTML = '<span>Current research frontier</span><strong>Phase 11 · P14R</strong><i>→</i>';
      }
    }

    const rail = q('#phaseRail,.phase-rail');
    if (rail) {
      if (!q('a[href="/phases/phase10r/"]', rail)) {
        const step = document.createElement('a');
        step.className = 'rail-step';
        step.href = '/phases/phase10r/';
        step.innerHTML = '<span>12</span><i></i><strong>Phase 10R\nGeneralization</strong>';
        rail.appendChild(step);
      }
      if (!q('a[href="/phases/phase11/"]', rail)) {
        const step = document.createElement('a');
        step.className = 'rail-step frontier';
        step.href = '/phases/phase11/';
        step.innerHTML = '<span>13</span><i></i><strong>Phase 11\nP14R</strong>';
        rail.appendChild(step);
      }
    }
  }

  const run = () => {
    if (location.pathname === '/' || !location.pathname.startsWith('/phases')) patchHome();
    else if (!location.pathname.startsWith('/phases/phase11')) patchArchive();
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => { run(); setTimeout(run, 120); }, {once:true});
  else { run(); setTimeout(run, 120); }
})();
