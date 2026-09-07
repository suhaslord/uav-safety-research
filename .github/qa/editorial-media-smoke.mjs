import { chromium } from 'playwright';

const BASE = process.env.QA_BASE_URL || 'http://127.0.0.1:4173';
const viewports = [
  { name: 'desktop', width: 1440, height: 1000 },
  { name: 'tablet', width: 820, height: 1180 },
  { name: 'mobile', width: 390, height: 844, isMobile: true, hasTouch: true }
];
const keyRoutes = ['/', '/phases/', '/phases/phase1/', '/phases/phase11/', '/phases/phase22/'];
const expectedContext = 'Visual context — not AegisLand experimental evidence';
const results = [];
let failed = 0;
const add = (name, ok, details = {}) => {
  results.push({ name, ok, ...details });
  if (!ok) failed += 1;
};

const browser = await chromium.launch({ headless: true });
try {
  for (const viewport of viewports) {
    const context = await browser.newContext({
      viewport: { width: viewport.width, height: viewport.height },
      isMobile: !!viewport.isMobile,
      hasTouch: !!viewport.hasTouch,
      reducedMotion: 'reduce'
    });

    for (const route of keyRoutes) {
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', (error) => errors.push(String(error?.message || error)));
      page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()); });
      const response = await page.goto(`${BASE}${route}`, { waitUntil: 'networkidle', timeout: 60000 });
      add(`${viewport.name}-${route}-status`, !!response && response.status() < 400, { status: response?.status() || 0 });

      const state = await page.evaluate((contextLabel) => {
        const root = document.documentElement;
        const photos = [...document.querySelectorAll('[data-editorial-photo]')];
        const images = photos.map((figure) => figure.querySelector('img')).filter(Boolean);
        const frames = photos.map((figure) => figure.querySelector('.research-photo__frame')).filter(Boolean);
        return {
          overflow: root.scrollWidth - root.clientWidth,
          marker: root.dataset.editorialMedia || '',
          photoCount: photos.length,
          localSources: images.map((img) => img.getAttribute('src') || ''),
          imagesLoaded: images.every((img) => img.complete && img.naturalWidth > 0 && img.naturalHeight > 0),
          altText: images.map((img) => img.getAttribute('alt') || ''),
          captionCount: photos.filter((figure) => (figure.textContent || '').includes(contextLabel)).length,
          credits: photos.map((figure) => figure.querySelector('.research-photo__credit')?.textContent?.trim() || ''),
          sourceLinks: photos.map((figure) => figure.querySelector('.research-photo__credit a')?.href || ''),
          fallbackVisible: photos.some((figure) => figure.dataset.imageState === 'fallback' || !figure.querySelector('[data-image-fallback]')?.hidden),
          ratios: frames.map((frame) => {
            const rect = frame.getBoundingClientRect();
            return rect.height > 0 ? rect.width / rect.height : 0;
          }),
          remoteImageCount: [...document.images].filter((img) => /^https?:\/\//i.test(img.getAttribute('src') || '')).length
        };
      }, expectedContext);

      add(`${viewport.name}-${route}-no-overflow`, state.overflow <= 2, { overflow: state.overflow });
      add(`${viewport.name}-${route}-browser-clean`, errors.length === 0, { errors });

      if (route === '/') {
        add(`${viewport.name}-home-local-media-release`, state.marker === 'local-v1', { marker: state.marker });
        add(`${viewport.name}-home-exactly-two-editorial-photos`, state.photoCount === 2, { photoCount: state.photoCount });
        add(`${viewport.name}-home-local-image-sources`, state.localSources.length === 2 && state.localSources.every((src) => src.startsWith('/media/')), { sources: state.localSources });
        add(`${viewport.name}-home-no-remote-image-hotlinks`, state.remoteImageCount === 0, { remoteImageCount: state.remoteImageCount });
        add(`${viewport.name}-home-images-loaded`, state.imagesLoaded && !state.fallbackVisible, { imagesLoaded: state.imagesLoaded, fallbackVisible: state.fallbackVisible });
        add(`${viewport.name}-home-meaningful-alt`, state.altText.length === 2 && state.altText.every((alt) => alt.trim().length >= 24), { altText: state.altText });
        add(`${viewport.name}-home-context-labels`, state.captionCount === 2, { captionCount: state.captionCount });
        add(`${viewport.name}-home-credit-preserved`, state.credits.length === 2 && state.credits.every((credit) => /Don Richey \/ NASA Ames Research Center/i.test(credit) && /Public domain/i.test(credit)), { credits: state.credits });
        add(`${viewport.name}-home-source-links`, state.sourceLinks.length === 2 && state.sourceLinks.every((href) => href.startsWith('https://commons.wikimedia.org/wiki/File:Advanced_Capabilities_for_Emergency_Response_Operations')), { sourceLinks: state.sourceLinks });
        add(`${viewport.name}-home-consistent-aspect-ratio`, state.ratios.length === 2 && state.ratios.every((ratio) => Math.abs(ratio - (16 / 9)) < 0.03), { ratios: state.ratios });
      } else {
        add(`${viewport.name}-${route}-no-editorial-photo-duplication`, state.photoCount === 0, { photoCount: state.photoCount });
      }
      await page.close();
    }
    await context.close();
  }
} finally {
  await browser.close();
}

console.log(JSON.stringify({ base: BASE, passed: results.filter((result) => result.ok).length, failed, results }, null, 2));
if (failed) process.exitCode = 1;
