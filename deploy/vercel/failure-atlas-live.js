(() => {
  'use strict';

  // failure-atlas.html and failure-atlas.js are sealed research artifacts. The
  // live route layers presentation corrections over the unchanged frozen code.
  const comparison = document.getElementById('comparison');
  const normalizeLocalLabels = () => {
    for (const id of ['frame-image', 'phase23-frame-image']) {
      const image = document.getElementById(id);
      if (!image?.getAttribute('src')?.startsWith('blob:')) continue;
      const alt = image.alt.replace(/^Verified reconstructed /, '').replace(/ loaded from a local file$/, '');
      if (!alt.startsWith('Local, unverified ')) image.alt = `Local, unverified ${alt}`;
    }
    const image = document.getElementById('phase23-frame-image');
    const badge = document.getElementById('phase23-image-badge');
    if (image?.getAttribute('src')?.startsWith('blob:') && badge?.textContent === 'Same reconstructed input · measured predictions') {
      badge.textContent = 'Local image · unverified · measured predictions unchanged';
    }
  };
  if (comparison) {
    new MutationObserver(normalizeLocalLabels).observe(comparison, {
      subtree: true, childList: true, attributes: true, attributeFilter: ['src', 'alt']
    });
  }

  const frozen = document.createElement('script');
  frozen.src = '/failure-atlas-frozen.js?v=8';
  frozen.addEventListener('error', () => {
    const note = document.getElementById('image-note');
    if (note) note.textContent = 'The frame explorer could not load. Reload the page to retry; the linked result tables remain available.';
  }, { once: true });
  document.head.appendChild(frozen);
})();
