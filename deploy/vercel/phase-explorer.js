(() => {
  'use strict';
  const init = () => {
    const taxonomy = window.AEGIS_PHASE_TAXONOMY;
    if (!taxonomy || document.getElementById('phaseExplorer')) return;
    const frozen = window.AEGIS_FROZEN_LINEAGE?.bySlug || {};
    const slugs = Object.keys(taxonomy.bySlug);
    const current = location.pathname.match(/\/phases\/(phase\d+[a-z]*)\/?$/i)?.[1]?.toLowerCase();
    const label = slug => slug.replace(/^phase(\d+)(.*)$/, (_, number, suffix) => `Phase ${number}${suffix.toUpperCase()}`);
    const href = slug => `/phases/${slug}/`;
    const escape = text => String(text).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
    const status = slug => frozen[slug]?.verdict || ({phase4:'Naming gap',phase10r:'Failed holdout',phase11:'Mixed / failed overall'}[slug] || 'Historical record');
    const options = selected => slugs.map(slug => `<option value="${slug}" ${slug === selected ? 'selected' : ''}>${label(slug)} · ${escape(taxonomy.bySlug[slug].identity)}</option>`).join('');
    const dialog = document.createElement('dialog');
    dialog.id = 'phaseExplorer';
    dialog.className = 'phase-explorer';
    dialog.setAttribute('aria-labelledby', 'explorerTitle');
    dialog.innerHTML = `
      <div class="explorer-heading"><div><p>AEGISLAND RESEARCH</p><h2 id="explorerTitle">Find your next phase.</h2></div><button type="button" class="explorer-close" aria-label="Close phase browser">Close ×</button></div>
      <div class="explorer-modes" role="group" aria-label="Phase browser view"><button type="button" data-mode="browse" aria-pressed="true">Browse phases</button><button type="button" data-mode="compare" aria-pressed="false">Compare phases</button></div>
      <div id="explorerBrowse"><div class="explorer-search"><label for="phaseQuickSearch">Search all 26 records</label><input type="search" id="phaseQuickSearch" placeholder="Try Phase 10R, latency, or coverage" autocomplete="off"></div>
      <p class="explorer-count" role="status"></p><div class="explorer-groups"></div><p class="explorer-empty" hidden>No matching phases. Try a phase number or a shorter search.</p></div>
      <div id="explorerCompare" hidden><p class="compare-note">Compare the questions and recorded outcomes. Each phase tests different conditions; these results aren’t a ranking.</p>
      <div class="compare-selects"><label>First phase<select id="compareFirst" aria-label="First phase">${options(current || 'phase21')}</select></label><label>Second phase<select id="compareSecond" aria-label="Second phase">${options(current === 'phase22' ? 'phase21' : 'phase22')}</select></label></div><div class="compare-table-wrap"></div></div>
      <div class="explorer-footer"><span>26 records · every pass, failure, and naming gap</span><a href="/phases/">Open full archive →</a></div>`;
    const groups = dialog.querySelector('.explorer-groups');
    taxonomy.categories.forEach(category => {
      const section = document.createElement('section');
      section.className = 'explorer-group';
      section.innerHTML = `<h3>${escape(category.name)}</h3>`;
      slugs.filter(slug => taxonomy.bySlug[slug].category === category.id).forEach(slug => {
        const meta = taxonomy.bySlug[slug];
        const link = document.createElement('a');
        link.href = href(slug);
        link.className = 'explorer-phase';
        link.dataset.search = `${label(slug)} ${slug} ${meta.identity} ${meta.question} ${meta.signal} ${category.name}`.toLowerCase();
        if (current === slug) link.setAttribute('aria-current', 'page');
        link.innerHTML = `<span>${label(slug)} <small>${escape(status(slug))}</small></span><strong>${escape(meta.identity)}</strong><span class="explorer-arrow" aria-hidden="true">↗</span>`;
        section.append(link);
      });
      groups.append(section);
    });
    document.body.append(dialog);
    const search = dialog.querySelector('input');
    const filter = () => {
      const query = search.value.trim().toLowerCase();
      let count = 0;
      dialog.querySelectorAll('.explorer-phase').forEach(link => {
        link.hidden = !link.dataset.search.includes(query);
        if (!link.hidden) count++;
      });
      dialog.querySelectorAll('.explorer-group').forEach(group => { group.hidden = !group.querySelector('.explorer-phase:not([hidden])'); });
      dialog.querySelector('.explorer-count').textContent = `${count} of 26 phases`;
      dialog.querySelector('.explorer-empty').hidden = count !== 0;
    };
    search.addEventListener('input', filter);
    filter();
    const compare = () => {
      const pair = ['compareFirst','compareSecond'].map(id => dialog.querySelector(`#${id}`).value);
      const rows = [
        ['Research question', slug => taxonomy.bySlug[slug].question],
        ['Chapter', slug => taxonomy.categoryById[taxonomy.bySlug[slug].category].name],
        ['Recorded status', status],
        ['Focus', slug => taxonomy.bySlug[slug].signal],
        ['Reported finding', slug => frozen[slug]?.finding || 'Open the phase for its original findings and limitations.'],
      ];
      dialog.querySelector('.compare-table-wrap').innerHTML = `<table class="phase-compare"><caption>Phase comparison · simulation research</caption><thead><tr><th scope="col">Record</th>${pair.map(slug => `<th scope="col">${label(slug)}<a href="${href(slug)}">Read phase →</a></th>`).join('')}</tr></thead><tbody>${rows.map(([name, value]) => `<tr><th scope="row">${name}</th>${pair.map(slug => `<td>${escape(value(slug))}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
    };
    dialog.querySelectorAll('select').forEach(select => select.addEventListener('change', compare));
    compare();
    const setMode = mode => {
      dialog.querySelector('#explorerBrowse').hidden = mode !== 'browse';
      dialog.querySelector('#explorerCompare').hidden = mode !== 'compare';
      dialog.querySelectorAll('[data-mode]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.mode === mode)));
    };
    dialog.querySelectorAll('[data-mode]').forEach(button => button.addEventListener('click', () => setMode(button.dataset.mode)));
    let opener;
    const open = event => {
      opener = event.currentTarget;
      setMode('browse');
      search.value = '';
      filter();
      dialog.showModal();
      document.documentElement.classList.add('phase-explorer-open');
      search.focus();
    };
    dialog.querySelector('.explorer-close').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => { if (event.target === dialog) { const r = dialog.getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close(); } });
    dialog.addEventListener('close', () => { document.documentElement.classList.remove('phase-explorer-open'); opener?.focus(); });
    const header = document.querySelector('.site-header, .signature-nav, .top');
    if (header) {
      const button = document.createElement('button');
      button.className = 'phase-explorer-trigger';
      button.type = 'button';
      button.textContent = 'Browse phases';
      button.setAttribute('aria-haspopup', 'dialog');
      button.addEventListener('click', open);
      header.append(button);
    }
    if (current) {
      document.body.classList.add('phase-reading');
      const index = slugs.indexOf(current);
      const bar = document.createElement('nav');
      bar.className = 'phase-jumpbar';
      bar.setAttribute('aria-label', 'Phase switcher');
      bar.innerHTML = `<label for="phaseJump">${index + 1} / 26<select id="phaseJump" aria-label="Jump to phase">${options(current)}</select></label><div class="phase-jumpbar__links">${index ? `<a href="${href(slugs[index-1])}" aria-label="Previous phase: ${label(slugs[index-1])}">← Previous</a>` : ''}${index < slugs.length - 1 ? `<a href="${href(slugs[index+1])}" aria-label="Next phase: ${label(slugs[index+1])}">Next →</a>` : '<a href="/phases/">Full archive →</a>'}</div>`;
      bar.querySelector('select').addEventListener('change', event => { location.href = href(event.target.value); });
      header?.after(bar);
      // Keep the phase number visible even when legacy identity styling hides metadata.
      const kicker = document.querySelector('.phase-detail__hero .signature-kicker');
      if (kicker) kicker.textContent = `${label(current)} · ${frozen[current]?.stage || 'Frozen evidence record'}`;
    }
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, {once:true});
  else init();
})();
