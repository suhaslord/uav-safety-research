import { chromium } from 'playwright';

const BASE = process.env.QA_BASE_URL || 'http://127.0.0.1:4173';
const viewports = [
  { name: 'desktop', width: 1440, height: 1000 },
  { name: 'tablet', width: 820, height: 1180 },
  { name: 'mobile', width: 390, height: 844, isMobile: true, hasTouch: true }
];
const phaseSlugs = [
  'phase1', 'phase2', 'phase3', 'phase4', 'phase5', 'phase6', 'phase6b',
  'phase7', 'phase8', 'phase9', 'phase10', 'phase10r', 'phase11', 'phase12',
  'phase13a', 'phase13b', 'phase13c', 'phase14', 'phase15', 'phase16',
  'phase17', 'phase18', 'phase19', 'phase20', 'phase21', 'phase22'
];
const allPhaseRoutes = phaseSlugs.map((slug) => `/phases/${slug}/`);
const responsiveRoutes = ['/', '/phases/', '/phases/phase1/', '/phases/phase11/', '/phases/phase22/'];
const expectedContext = 'Visual context — not AegisLand experimental evidence';
const results = [];
let failed = 0;
const add = (name, ok, details = {}) => {
  results.push({ name, ok, ...details });
  if (!ok) failed += 1;
};

const browser = await chromium.launch({ headless: true });
const desktopPhaseSources = new Map();
try {
  for (const viewport of viewports) {
    const context = await browser.newContext({
      viewport: { width: viewport.width, height: viewport.height },
      isMobile: !!viewport.isMobile,
      hasTouch: !!viewport.hasTouch,
      reducedMotion: 'reduce'
    });

    const routes = viewport.name === 'desktop'
      ? ['/', '/phases/', ...allPhaseRoutes]
      : responsiveRoutes;

    for (const route of routes) {
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', (error) => errors.push(String(error?.message || error)));
      page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()); });
      const response = await page.goto(`${BASE}${route}`, { waitUntil: 'networkidle', timeout: 60000 });
      add(`${viewport.name}-${route}-status`, !!response && response.status() < 400, { status: response?.status() || 0 });

      const figures = page.locator('[data-editorial-photo]');
      const count = await figures.count();
      for (let index = 0; index < count; index += 1) {
        await figures.nth(index).scrollIntoViewIfNeeded();
        await page.waitForFunction((photoIndex) => {
          const figure = document.querySelectorAll('[data-editorial-photo]')[photoIndex];
          if (!figure) return false;
          const image = figure.querySelector('img');
          return figure.dataset.imageState === 'fallback' || !image || (image.complete && image.naturalWidth > 0 && image.naturalHeight > 0);
        }, index, { timeout: 12000 }).catch(() => {});
      }

      const state = await page.evaluate((contextLabel) => {
        const root = document.documentElement;
        const photos = [...document.querySelectorAll('[data-editorial-photo]')];
        const images = photos.map((figure) => figure.querySelector('img')).filter(Boolean);
        const frameFor = (figure) => figure.querySelector('.research-photo__frame, .phase-editorial-photo__frame');
        const creditFor = (figure) => figure.querySelector('.research-photo__credit, .phase-editorial-photo__credit');
        const frames = photos.map(frameFor).filter(Boolean);
        return {
          overflow: root.scrollWidth - root.clientWidth,
          marker: root.dataset.editorialMedia || '',
          photoCount: photos.length,
          localSources: images.map((img) => img.getAttribute('src') || ''),
          imagesLoaded: images.length === photos.length && images.every((img) => img.complete && img.naturalWidth > 0 && img.naturalHeight > 0),
          altText: images.map((img) => img.getAttribute('alt') || ''),
          captionCount: photos.filter((figure) => (figure.textContent || '').includes(contextLabel)).length,
          credits: photos.map((figure) => creditFor(figure)?.textContent?.trim() || ''),
          sourceLinks: photos.map((figure) => creditFor(figure)?.querySelector('a')?.href || ''),
          fallbackVisible: photos.some((figure) => figure.dataset.imageState === 'fallback' || [...figure.querySelectorAll('[data-image-fallback], .phase-editorial-photo__fallback')].some((node) => !node.hidden)),
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
        add(`${viewport.name}-home-local-media-release`, state.marker === 'local-v2', { marker: state.marker });
        add(`${viewport.name}-home-four-editorial-photos`, state.photoCount === 4, { photoCount: state.photoCount });
        add(`${viewport.name}-home-local-image-sources`, state.localSources.length === 4 && state.localSources.every((src) => src.startsWith('/media/')), { sources: state.localSources });
        add(`${viewport.name}-home-no-remote-image-hotlinks`, state.remoteImageCount === 0, { remoteImageCount: state.remoteImageCount });
        add(`${viewport.name}-home-images-loaded`, state.imagesLoaded && !state.fallbackVisible, { imagesLoaded: state.imagesLoaded, fallbackVisible: state.fallbackVisible });
        add(`${viewport.name}-home-meaningful-alt`, state.altText.length === 4 && state.altText.every((alt) => alt.trim().length >= 24), { altText: state.altText });
        add(`${viewport.name}-home-context-labels`, state.captionCount === 4, { captionCount: state.captionCount });
        add(`${viewport.name}-home-credit-preserved`, state.credits.length === 4 && state.credits.every((credit) => /Public domain/i.test(credit) && /(Don Richey|Joel Kowsky)/i.test(credit)), { credits: state.credits });
        add(`${viewport.name}-home-source-links`, state.sourceLinks.length === 4 && state.sourceLinks.every((href) => href.startsWith('https://commons.wikimedia.org/wiki/File:')), { sourceLinks: state.sourceLinks });
        add(`${viewport.name}-home-consistent-aspect-ratio`, state.ratios.length === 4 && state.ratios.every((ratio) => Math.abs(ratio - (16 / 9)) < 0.03), { ratios: state.ratios });
      } else if (route === '/phases/') {
        add(`${viewport.name}-archive-no-editorial-photo-duplication`, state.photoCount === 0, { photoCount: state.photoCount });
      } else {
        add(`${viewport.name}-${route}-one-phase-photo`, state.photoCount === 1, { photoCount: state.photoCount });
        add(`${viewport.name}-${route}-phase-photo-local`, state.localSources.length === 1 && state.localSources[0].startsWith('/media/'), { sources: state.localSources });
        add(`${viewport.name}-${route}-phase-photo-loaded`, state.imagesLoaded && !state.fallbackVisible, { imagesLoaded: state.imagesLoaded, fallbackVisible: state.fallbackVisible });
        add(`${viewport.name}-${route}-phase-photo-alt`, state.altText.length === 1 && state.altText[0].trim().length >= 24, { altText: state.altText });
        add(`${viewport.name}-${route}-phase-photo-context`, state.captionCount === 1, { captionCount: state.captionCount });
        add(`${viewport.name}-${route}-phase-photo-credit`, state.credits.length === 1 && /Public domain/i.test(state.credits[0]) && /(Don Richey|Joel Kowsky)/i.test(state.credits[0]), { credits: state.credits });
        add(`${viewport.name}-${route}-phase-photo-source`, state.sourceLinks.length === 1 && state.sourceLinks[0].startsWith('https://commons.wikimedia.org/wiki/File:'), { sourceLinks: state.sourceLinks });
        add(`${viewport.name}-${route}-phase-photo-ratio`, state.ratios.length === 1 && Math.abs(state.ratios[0] - (16 / 9)) < 0.03, { ratios: state.ratios });
        if (viewport.name === 'desktop' && state.localSources[0]) desktopPhaseSources.set(route, state.localSources[0]);
      }
      await page.close();
    }
    await context.close();
  }

  add('desktop-all-26-phase-photos-observed', desktopPhaseSources.size === 26, { count: desktopPhaseSources.size });
  const uniqueSources = new Set(desktopPhaseSources.values());
  add('desktop-all-26-phase-photos-unique', uniqueSources.size === 26, { count: uniqueSources.size, sources: [...uniqueSources] });
} finally {
  await browser.close();
}

console.log(JSON.stringify({ base: BASE, passed: results.filter((result) => result.ok).length, failed, results }, null, 2));
if (failed) process.exitCode = 1;
