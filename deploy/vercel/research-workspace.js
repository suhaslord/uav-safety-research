(() => {
  'use strict';

  const samePath = (href) => {
    try {
      const target = new URL(href, location.href);
      const clean = (value) => value.replace(/\/+$/, '') || '/';
      return target.origin === location.origin && clean(target.pathname) === clean(location.pathname);
    } catch {
      return false;
    }
  };

  document.querySelectorAll('a[aria-current="page"]').forEach((link) => {
    if (!samePath(link.href)) link.removeAttribute('aria-current');
  });

  document.querySelectorAll('.mobile-menu-toggle').forEach((toggle) => {
    const sheetId = toggle.getAttribute('aria-controls');
    const sheet = sheetId ? document.getElementById(sheetId) : null;
    if (!sheet) return;

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

  document.querySelectorAll('[data-workspace-current]').forEach((link) => {
    if (samePath(link.href)) link.setAttribute('aria-current', 'page');
  });

  document.querySelectorAll('[data-editorial-photo]').forEach((figure) => {
    const image = figure.querySelector('img');
    const fallback = figure.querySelector('[data-image-fallback]');
    if (!image || !fallback) return;

    const showFallback = () => {
      if (!image.isConnected) return;
      image.remove();
      fallback.hidden = false;
      figure.dataset.imageState = 'fallback';
    };

    image.addEventListener('error', showFallback, { once: true });
    if (image.complete && image.naturalWidth === 0) showFallback();
  });
})();