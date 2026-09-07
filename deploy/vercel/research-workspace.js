(() => {
  'use strict';

  const ensureConvergenceStyles = () => {
    if (document.querySelector('link[data-aegis-final-convergence]')) return;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = '/final-convergence.css?v=1';
    link.dataset.aegisFinalConvergence = '';
    link.addEventListener('load', () => { document.documentElement.dataset.finalConvergence = 'ready'; }, { once: true });
    document.head.appendChild(link);
  };
  ensureConvergenceStyles();

  const samePath = (href) => {
    try {
      const target = new URL(href, location.href);
      const clean = (value) => value.replace(/\/+$/, '') || '/';
      return target.origin === location.origin && clean(target.pathname) === clean(location.pathname);
    } catch {
      return false;
    }
  };

  const phaseLabel = (slug) => {
    if (!slug) return '';
    const match = slug.match(/^phase(\d+)([a-z]+)?$/i);
    if (!match) return slug;
    return `Phase ${match[1]}${match[2] ? match[2].toUpperCase() : ''}`;
  };

  const phaseOrder = [
    'phase1','phase2','phase3','phase4','phase5','phase6','phase6b','phase7','phase8','phase9','phase10','phase10r','phase11','phase12','phase13a','phase13b','phase13c','phase14','phase15','phase16','phase17','phase18','phase19','phase20','phase21','phase22'
  ];

  const currentSlug = () => document.body.dataset.phase || location.pathname.match(/\/phases\/(phase\d+[a-z]*)\/?$/i)?.[1]?.toLowerCase() || '';

  const normalizeThemeColor = () => {
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', '#ffffff');
  };

  const normalizeCurrentLinks = () => {
    document.querySelectorAll('a[aria-current="page"]').forEach((link) => {
      if (!samePath(link.href)) link.removeAttribute('aria-current');
    });
    document.querySelectorAll('[data-workspace-current]').forEach((link) => {
      if (samePath(link.href)) link.setAttribute('aria-current', 'page');
    });
  };

  const manageMobileMenus = () => {
    document.querySelectorAll('.mobile-menu-toggle').forEach((toggle) => {
      const sheetId = toggle.getAttribute('aria-controls');
      const sheet = sheetId ? document.getElementById(sheetId) : null;
      if (!sheet || toggle.dataset.focusManaged === 'true') return;
      toggle.dataset.focusManaged = 'true';

      const close = sheet.querySelector('.mobile-menu-close');
      let returnFocus = toggle;
      const focusables = () => [...sheet.querySelectorAll('a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])')]
        .filter((element) => !element.hasAttribute('hidden') && element.getAttribute('aria-hidden') !== 'true');

      const focusInside = () => {
        const items = focusables();
        (close || items[0] || sheet).focus?.();
      };

      const observer = new MutationObserver(() => {
        const open = sheet.getAttribute('aria-hidden') === 'false';
        if (open) {
          returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : toggle;
          sheet.setAttribute('data-focus-managed', 'true');
          requestAnimationFrame(focusInside);
        } else if (sheet.hasAttribute('data-focus-managed')) {
          sheet.removeAttribute('data-focus-managed');
          requestAnimationFrame(() => returnFocus?.focus?.());
        }
      });
      observer.observe(sheet, { attributes: true, attributeFilter: ['aria-hidden'] });

      sheet.addEventListener('keydown', (event) => {
        if (event.key !== 'Tab' || sheet.getAttribute('aria-hidden') !== 'false') return;
        const items = focusables();
        if (!items.length) return;
        const first = items[0];
        const last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      });
    });
  };

  const normalizeEditorialFallbacks = () => {
    document.querySelectorAll('[data-editorial-photo]').forEach((figure) => {
      const image = figure.querySelector('img');
      const fallback = figure.querySelector('[data-image-fallback]');
      if (!image || !fallback || image.dataset.fallbackManaged === 'true') return;
      image.dataset.fallbackManaged = 'true';
      const showFallback = () => {
        if (!image.isConnected) return;
        image.remove();
        fallback.hidden = false;
        figure.dataset.imageState = 'fallback';
      };
      image.addEventListener('error', showFallback, { once: true });
      if (image.complete && image.naturalWidth === 0) showFallback();
    });
  };

  const labelRoleQuestion = () => {
    document.querySelectorAll('.phase-role-card__question').forEach((question) => {
      if (question.dataset.questionLabeled === 'true') return;
      const text = question.textContent.trim();
      question.textContent = '';
      const label = document.createElement('span');
      label.className = 'phase-role-card__question-label';
      label.textContent = 'Central question';
      const value = document.createElement('span');
      value.className = 'phase-role-card__question-text';
      value.textContent = text;
      question.append(label, value);
      question.dataset.questionLabeled = 'true';
    });
  };

  const normalizePhaseNavigation = () => {
    if (!location.pathname.startsWith('/phases/')) return;

    if (document.body.classList.contains('archive-shell')) {
      const nav = document.querySelector('.top .nav');
      if (nav) nav.innerHTML = '<a href="#snapshot">Overview</a><a href="#finding">Finding</a><a href="#evidence">Evidence</a><a href="#limits">Limits</a><a href="#changes">Method</a>';
      return;
    }

    if (document.body.classList.contains('phase11-polish')) {
      const nav = document.querySelector('.site-nav');
      if (nav) nav.innerHTML = '<a href="#result">Overview</a><a href="#evidence">Evidence</a><a href="#boundary">Limits</a><a href="#method">Method</a><a href="#provenance">Provenance</a>';
      return;
    }

    const hero = document.querySelector('.phase-detail__hero');
    if (!hero) return;
    hero.id = 'overview';
    const panels = document.querySelectorAll('.phase-detail__body .phase-detail__panel');
    if (panels[0]) panels[0].id = 'finding';
    if (panels[1]) panels[1].id = 'evidence';
    const context = document.querySelector('.phase-detail__context');
    if (context) context.id = 'limits';
    const nav = document.querySelector('.signature-nav__links');
    if (nav) nav.innerHTML = '<a href="#overview">Overview</a><a href="#finding">Finding</a><a href="#evidence">Evidence</a><a href="#limits">Limits</a><a href="/phases/">Archive</a><a href="https://github.com/suhaslord/uav-safety-research" target="_blank" rel="noreferrer">GitHub ↗</a>';
  };

  const addLegacyProgressDisclosure = () => {
    if (!document.body.classList.contains('archive-shell')) return;
    const section = document.querySelector('.phase-rail-section');
    if (!section || section.querySelector('.phase-progress-compact')) return;
    const slug = currentSlug();
    const index = phaseOrder.indexOf(slug);
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'phase-progress-compact';
    button.setAttribute('aria-expanded', 'false');
    button.innerHTML = `<span>${phaseLabel(slug)} · early research sequence</span><strong>View timeline</strong>`;
    button.addEventListener('click', () => {
      const open = !section.classList.contains('is-open');
      section.classList.toggle('is-open', open);
      button.setAttribute('aria-expanded', String(open));
    });
    if (index >= 0) button.dataset.phaseIndex = String(index + 1);
    section.prepend(button);
  };

  const addUnifiedPhaseNav = () => {
    const slug = currentSlug();
    const index = phaseOrder.indexOf(slug);
    if (index < 0 || document.querySelector('.phase-unified-nav')) return;

    const prev = phaseOrder[index - 1];
    const next = phaseOrder[index + 1];
    const nav = document.createElement('nav');
    nav.className = 'phase-unified-nav';
    nav.setAttribute('aria-label', 'Adjacent research phases');

    const prevLink = document.createElement('a');
    prevLink.className = 'phase-unified-nav__prev';
    prevLink.href = prev ? `/phases/${prev}/` : '/';
    prevLink.textContent = prev ? `← ${phaseLabel(prev)}` : '← Research home';

    const archiveLink = document.createElement('a');
    archiveLink.className = 'phase-unified-nav__archive';
    archiveLink.href = '/phases/';
    archiveLink.textContent = 'All phases';

    const nextLink = document.createElement('a');
    nextLink.className = 'phase-unified-nav__next';
    nextLink.href = next ? `/phases/${next}/` : '/';
    nextLink.textContent = next ? `${phaseLabel(next)} →` : 'Research home →';

    nav.append(prevLink, archiveLink, nextLink);
    const footer = document.querySelector('footer');
    if (footer) footer.before(nav);
    else document.querySelector('main')?.insertAdjacentElement('afterend', nav);
  };

  const makeArchiveRowsClickable = () => {
    if (!document.body.classList.contains('archive-workspace')) return;
    document.querySelectorAll('.archive-card.phase-personalized').forEach((card) => {
      if (card.dataset.rowClick === 'true') return;
      const target = card.querySelector('a.archive-card__open, a[href^="/phases/"]');
      if (!target) return;
      card.dataset.rowClick = 'true';
      card.addEventListener('click', (event) => {
        if (event.target.closest('a,button,input,select,textarea')) return;
        location.href = target.href;
      });
    });
  };

  const normalizePhaseSurface = () => {
    normalizeThemeColor();
    normalizeCurrentLinks();
    labelRoleQuestion();
    normalizePhaseNavigation();
    addLegacyProgressDisclosure();
    addUnifiedPhaseNav();
    makeArchiveRowsClickable();
    normalizeEditorialFallbacks();
  };

  normalizeThemeColor();
  normalizeCurrentLinks();
  manageMobileMenus();
  normalizeEditorialFallbacks();

  requestAnimationFrame(() => {
    normalizePhaseSurface();
    requestAnimationFrame(normalizePhaseSurface);
  });
})();