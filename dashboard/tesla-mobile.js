(() => {
  const header = document.querySelector('.top');
  if (!header) return;
  document.body.classList.add('archive-shell');
  if (document.querySelector('.archive-menu-toggle')) return;

  const toggle = document.createElement('button');
  toggle.className = 'archive-menu-toggle';
  toggle.type = 'button';
  toggle.textContent = 'Menu';
  toggle.setAttribute('aria-expanded', 'false');
  toggle.setAttribute('aria-controls', 'archiveMobileMenu');
  toggle.setAttribute('aria-label', 'Open navigation');
  header.appendChild(toggle);

  const sheet = document.createElement('aside');
  sheet.id = 'archiveMobileMenu';
  sheet.className = 'archive-menu-sheet';
  sheet.setAttribute('aria-hidden', 'true');
  sheet.innerHTML = `
    <div class="archive-menu-sheet-head">
      <strong>AEGISLAND</strong>
      <button class="archive-menu-close" type="button" aria-label="Close navigation">Close</button>
    </div>
    <nav class="archive-menu-links" aria-label="Mobile navigation"></nav>
    <div class="archive-menu-meta">
      <a href="https://github.com/suhaslord/uav-safety-research" target="_blank" rel="noreferrer">GitHub ↗</a>
      <a href="https://www.linkedin.com/in/suhas-beemineni-1984763b8/" target="_blank" rel="noreferrer">LinkedIn ↗</a>
    </div>`;
  document.body.appendChild(sheet);

  const links = sheet.querySelector('.archive-menu-links');
  const isPhase = Boolean(document.getElementById('phaseHero'));
  const isArchive = Boolean(document.querySelector('.index-hero'));

  const add = (label, href, primary = false) => {
    if (!href || links.querySelector(`a[href="${CSS.escape(href)}"]`)) return;
    const a = document.createElement('a');
    a.textContent = label;
    a.href = href;
    if (primary) a.className = 'primary';
    links.appendChild(a);
  };

  if (isPhase) {
    add('Overview', '#snapshot');
    add('System', '#system');
    add('Evidence', '#evidence');
    add('Limits', '#limits');
    add('Finding', '#finding');
    add('All phases', '/phases/', true);
  } else if (isArchive) {
    add('Research lineage', '#archiveMap');
    add('Main cockpit', '/');
    add('Phase 10', '/phases/phase10/', true);
  } else {
    document.querySelectorAll('.nav a').forEach(a => add(a.textContent.trim(), a.getAttribute('href')));
    add('Research archive', '/phases/', true);
  }

  let returnFocus = null;
  const closeButton = sheet.querySelector('.archive-menu-close');
  const focusables = () => [...sheet.querySelectorAll('a[href],button:not([disabled])')];

  const setOpen = open => {
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
    sheet.setAttribute('aria-hidden', String(!open));
    sheet.classList.toggle('open', open);
    document.body.classList.toggle('archive-menu-open', open);
    if (open) {
      returnFocus = document.activeElement;
      requestAnimationFrame(() => closeButton.focus());
    } else if (returnFocus instanceof HTMLElement) {
      returnFocus.focus({preventScroll:true});
    }
  };

  toggle.addEventListener('click', () => setOpen(!sheet.classList.contains('open')));
  closeButton.addEventListener('click', () => setOpen(false));
  links.addEventListener('click', e => {
    if (e.target.closest('a')) setOpen(false);
  });

  document.addEventListener('keydown', e => {
    if (!sheet.classList.contains('open')) return;
    if (e.key === 'Escape') {
      e.preventDefault();
      setOpen(false);
      return;
    }
    if (e.key !== 'Tab') return;
    const items = focusables();
    if (!items.length) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  });

  const desktop = matchMedia('(min-width: 768px)');
  const onDesktop = event => { if (event.matches) setOpen(false); };
  if (desktop.addEventListener) desktop.addEventListener('change', onDesktop);
  else desktop.addListener(onDesktop);
})();
