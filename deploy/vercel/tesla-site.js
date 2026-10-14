/* THESIS: Extend the approved image-led homepage across AegisLand without altering research.
   OWN-WORLD: White navigation and content, full-bleed credited NASA photography,
   centered neutral sans-serif headings, blue and white rectangular actions.
   STORY: Read the original findings, inspect their limits, operate the preserved
   prototype and explorer, and follow the original source records.
   FIRST VIEWPORT: Reports and phases open over context photographs; the image
   explorer keeps its measured preview and compact tool introduction on white.
   FORM: Extend the user-approved Tesla reference, inherited seed 8f1be4a2;
   Read and Operate adapt the approved homepage grammar without a new direction.
   FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, and DESIGN.md */
(() => {
  'use strict';
  if (document.body.classList.contains('home-evidence-led')) return;
  const body = document.body;
  body.classList.add('tesla-site');
  body.dataset.sitePresentation = 'tesla';
  body.dataset.siteMode = /\/(prototype|failure-atlas)\/?$/.test(location.pathname) ? 'operate' : 'read';

  const assetBase = new URL('.', document.currentScript?.src || location.href);
  const updateViewport = () => body.style.setProperty('--site-viewport-width', `${document.documentElement.clientWidth}px`);
  updateViewport();
  window.addEventListener('resize', updateViewport, { passive: true });

  const header = body.querySelector('header');
  if (header) {
    header.dataset.teslaHeader = '';
    // Keep the existing navigation handlers; supply a native menu only where absent.
    if (!header.querySelector('.mobile-menu-toggle, details, .menu-toggle')) {
      const links = [...header.querySelectorAll('nav a[href]')];
      if (links.length) {
        const menu = document.createElement('details');
        menu.className = 'tesla-page-menu';
        const summary = document.createElement('summary');
        summary.textContent = 'Menu';
        const nav = document.createElement('nav');
        nav.setAttribute('aria-label', 'Mobile page navigation');
        for (const link of links) {
          const copy = link.cloneNode(true);
          copy.removeAttribute('id');
          nav.append(copy);
        }
        menu.append(summary, nav);
        header.append(menu);
        nav.addEventListener('click', event => {
          if (event.target.closest('a')) menu.open = false;
        });
        menu.addEventListener('keydown', event => {
          if (event.key === 'Escape') { menu.open = false; summary.focus(); }
        });
        window.matchMedia('(min-width: 981px)').addEventListener('change', event => {
          if (event.matches) menu.open = false;
        });
      }
    }
  }

  const visuals = {
    flight: ['acero-uav-flight.jpg', 'ACD24-0180-035'],
    landing: ['acero-uav-landing.jpg', 'ACD24-0180-037'],
    ground: ['acero-ground-control.jpg', 'ACD24-0180-009'],
    preflight: ['stereo-uav-preflight.jpg', 'NHQ202105050002'],
    audit: ['phase04-context.jpg', 'ACD24-0180-012']
  };
  const pathname = location.pathname;
  const scene = /fdi/.test(pathname) ? visuals.ground
    : /reproduce/.test(pathname) ? visuals.preflight
    : /phase24|confidence-audit/.test(pathname) ? visuals.audit
    : /model-vase|phase23/.test(pathname) ? visuals.landing : visuals.flight;

  const mount = () => {
    const answerLabel = body.querySelector('.vase-answer__label');
    const answerHeading = body.querySelector('.vase-answer__copy h2');
    if (answerLabel && answerHeading && answerLabel.parentElement !== answerHeading.parentElement) {
      answerLabel.dataset.teslaSupporting = '';
      answerHeading.after(answerLabel);
    }
    for (const label of body.querySelectorAll('.eyebrow, .kicker, .report-kicker, .signature-kicker, .fdi-eyebrow, .workspace-context, .phase-detail__eyebrow, .vase-card-meta')) {
      const heading = label.parentElement.querySelector(':scope > :is(h1, h2, h3)');
      if (heading && (label.compareDocumentPosition(heading) & Node.DOCUMENT_POSITION_FOLLOWING)) {
        label.dataset.teslaSupporting = '';
        heading.after(label);
      }
    }
    const hero = body.querySelector('#phaseHero, .phase-detail__hero, .archive-hero, .vase-hero, .report-hero, .fdi-hero, .proof-intro, main > .intro, main > .hero');
    if (!hero) return;
    const tool = /\/failure-atlas\/?$/.test(pathname);
    const firstMount = !hero.dataset.teslaHero;
    if (firstMount) hero.dataset.teslaHero = tool ? 'tool' : 'photo';
    const phasePhoto = body.querySelector('.phase-editorial-photo');
    if (phasePhoto) {
      phasePhoto.classList.add('tesla-hero-media');
      if (phasePhoto.parentElement !== hero) hero.append(phasePhoto);
      hero.style.removeProperty('--site-hero-image');
      hero.querySelector('.tesla-hero-credit')?.remove();
    } else if (firstMount && !tool && !hero.querySelector('.vase-hero__media')) {
      hero.style.setProperty('--site-hero-image', `url("${new URL(`media/${scene[0]}`, assetBase).href}")`);
      const caption = document.createElement('p');
      caption.className = 'tesla-hero-credit';
      caption.append('NASA photograph · research context, not AegisLand experiment data. ');
      const source = document.createElement('a');
      source.href = `https://images.nasa.gov/details/${scene[1]}`;
      source.textContent = 'Source';
      caption.append(source);
      hero.append(caption);
    }
    const explanation = body.querySelector('#understand-aegis');
    if (explanation && hero.nextElementSibling !== explanation) hero.after(explanation);
    const back = body.querySelector('.phase-detail__back');
    if (back && back.parentElement !== hero) hero.prepend(back);
    updateViewport();
  };
  let queued = false;
  const scheduleMount = () => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => { queued = false; mount(); });
  };
  const main = body.querySelector('main');
  if (main && (body.classList.contains('archive-shell') || body.classList.contains('phase11-polish') || main.querySelector('#phaseContent'))) {
    new MutationObserver(scheduleMount).observe(main, { childList: true, subtree: true });
  }
  // Phase rendering and its existing context-photo mount finish in the same frame.
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', scheduleMount, { once: true });
  else scheduleMount();
})();
