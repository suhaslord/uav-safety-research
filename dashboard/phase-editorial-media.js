(() => {
  'use strict';

  const getSlug = () => location.pathname.match(/\/phases\/(phase(?:\d+[a-z]?))\/?$/i)?.[1]?.toLowerCase() || '';

  const buildFigure = (visual, label) => {
    const figure = document.createElement('figure');
    figure.className = 'phase-editorial-photo';
    figure.dataset.editorialPhoto = '';

    const frame = document.createElement('div');
    frame.className = 'phase-editorial-photo__frame';

    const image = document.createElement('img');
    image.src = `/media/${visual.file}`;
    image.alt = visual.alt;
    image.width = 1280;
    image.height = 720;
    image.loading = 'eager';
    image.decoding = 'async';

    const fallback = document.createElement('div');
    fallback.className = 'phase-editorial-photo__fallback';
    fallback.hidden = true;
    fallback.setAttribute('role', 'status');
    fallback.textContent = 'Context photograph unavailable. The AegisLand evidence record is unchanged.';

    image.addEventListener('error', () => {
      image.hidden = true;
      fallback.hidden = false;
      figure.dataset.imageState = 'fallback';
    }, { once: true });

    frame.append(image, fallback);

    const caption = document.createElement('figcaption');

    const context = document.createElement('span');
    context.className = 'phase-editorial-photo__context';
    context.textContent = label;

    const why = document.createElement('span');
    why.className = 'phase-editorial-photo__why';
    why.textContent = visual.context;

    const credit = document.createElement('span');
    credit.className = 'phase-editorial-photo__credit';
    credit.append(`${visual.credit} · ${visual.license} · `);

    const source = document.createElement('a');
    source.href = visual.source;
    source.target = '_blank';
    source.rel = 'noreferrer';
    source.textContent = 'Source';
    credit.appendChild(source);

    caption.append(context, why, credit);
    figure.append(frame, caption);
    return figure;
  };

  const mount = () => {
    const slug = getSlug();
    const manifest = window.AEGIS_PHASE_VISUALS;
    const visual = manifest?.bySlug?.[slug];
    if (!slug || !visual || document.querySelector('.phase-editorial-photo')) return;

    const hero = document.querySelector('#phaseHero, .phase-detail__hero, body.phase11-polish .hero');
    if (!hero) return;

    const figure = buildFigure(visual, manifest.contextLabel);
    hero.insertAdjacentElement('afterend', figure);
    document.body.dataset.phaseVisual = visual.file;
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => requestAnimationFrame(mount), { once: true });
  } else {
    requestAnimationFrame(mount);
  }
})();
