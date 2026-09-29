import { chromium } from 'playwright';
import fsSync from 'node:fs';

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
const responsiveRoutes = ['/', '/model-vase/', '/phases/', '/phases/phase1/', '/phases/phase11/', '/phases/phase22/'];
const expectedContext = 'Visual context — not AegisLand experimental evidence';
const expectedPhaseRatio = (viewportName) => {
  if (viewportName === 'desktop') return 16 / 7;
  if (viewportName === 'tablet') return 2;
  return 16 / 9;
};
const results = [];
let failed = 0;
const add = (name, ok, details = {}) => {
  results.push({ name, ok, ...details });
  if (!ok) failed += 1;
};

const launchOptions = { headless: true };
if (process.platform === 'win32' && fsSync.existsSync('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe')) {
  launchOptions.executablePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
}
const browser = await chromium.launch(launchOptions);
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
      ? ['/', '/model-vase/', '/phases/', ...allPhaseRoutes]
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
      if (route === '/') {
        const images = page.locator('img');
        for (let index = 0; index < await images.count(); index += 1) {
          await images.nth(index).scrollIntoViewIfNeeded();
          await page.waitForFunction((imageIndex) => {
            const image = document.querySelectorAll('img')[imageIndex];
            return !!image && image.complete && image.naturalWidth > 0 && image.naturalHeight > 0;
          }, index, { timeout: 12000 }).catch(() => {});
        }
        const videoAssets = await page.locator('.home-field-media video').evaluateAll((videos) => videos.flatMap((video) => [
          ...[...video.querySelectorAll('source')].map((source) => ({ kind: 'clip', path: source.getAttribute('src') || '', type: source.type })),
          { kind: 'poster', path: video.getAttribute('poster') || '', type: 'image/jpeg' }
        ]));
        for (const [index, asset] of videoAssets.entries()) {
          const response = await page.request.get(new URL(asset.path, BASE).href);
          const bytes = await response.body();
          const contentType = response.headers()['content-type'] || '';
          add(`${viewport.name}-home-video-asset-${index + 1}`, response.ok() && contentType.includes(asset.type) && bytes.length > 1000, {
            kind: asset.kind, path: asset.path, status: response.status(), contentType, bytes: bytes.length
          });
        }
        await page.evaluate(() => window.scrollTo(0, 0));
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
          expectedRatios: photos.map((figure) => {
            if (figure.classList.contains('research-photo--hero')) { const r=document.querySelector('#top').getBoundingClientRect(); return r.width/r.height; }
            return figure.classList.contains('research-photo--inline') ? (innerWidth<=760 ? 4/3 : 2) : 16/9;
          }),
          ratios: frames.map((frame) => {
            const rect = frame.getBoundingClientRect();
            return rect.height > 0 ? rect.width / rect.height : 0;
          }),
          // This smoke test owns only editorial/context photography. Dataset evidence
          // can be sourced independently without weakening the local-media contract
          // for the NASA editorial figures themselves.
          remoteImageCount: images.filter((img) => /^https?:\/\//i.test(img.getAttribute('src') || '')).length,
          allHomeImages: [...document.querySelectorAll('main img')].map((img) => ({src:img.getAttribute('src')||'',alt:img.getAttribute('alt')||'',loaded:img.complete&&img.naturalWidth>0&&img.naturalHeight>0})),
          resultLayout: (() => {
            const section = document.querySelector('#status');
            if (!section) return null;
            const card = section.querySelector('.workspace-status-card');
            const measures = [...section.querySelectorAll('.workspace-measure')];
            const columns = measures.map((measure) => measure.getBoundingClientRect());
            const values = measures.map((measure) => measure.querySelector('strong')?.getBoundingClientRect());
            const overlaps = values.some((a, i) => values.slice(i + 1).some((b) => a && b && a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top));
            const valueClips = values.some((value, i) => value && (value.left < columns[i].left - 1 || value.right > columns[i].right + 1));
            return {containerDisplay:getComputedStyle(section).display,cardWidth:card?.getBoundingClientRect().width||0,measureCount:measures.length,overlaps,valueClips};
          })(),
          vaseHeroLoaded: (() => { const img=document.querySelector('.vase-hero__media img'); return !!img&&img.complete&&img.naturalWidth>0; })(),
          homeVideos: [...document.querySelectorAll('.home-field-media video')].map((video) => ({
            controls: video.controls,
            playsInline: video.playsInline,
            muted: video.muted,
            loop: video.loop,
            preload: video.getAttribute('preload') || '',
            autoplayWhenVisible: video.dataset.autoplay === 'visible',
            sources: [...video.querySelectorAll('source')].map((source) => source.getAttribute('src') || ''),
            poster: video.getAttribute('poster') || ''
          })),
          contextFigures: [...document.querySelectorAll('.home-field-media figure')].map((figure) => ({
            caption: figure.querySelector('figcaption')?.textContent || '',
            source: figure.querySelector('figcaption a')?.getAttribute('href') || ''
          }))
        };
      }, route === '/' ? 'NASA field image · context only' : expectedContext);

      add(`${viewport.name}-${route}-no-overflow`, state.overflow <= 2, { overflow: state.overflow });
      add(`${viewport.name}-${route}-browser-clean`, errors.length === 0, { errors });

      if (route === '/') {
        add(`${viewport.name}-home-local-media-release`, state.marker === 'local-v2', { marker: state.marker });
        add(`${viewport.name}-home-single-editorial-photo`, state.photoCount === 1, { photoCount: state.photoCount });
        add(`${viewport.name}-home-local-image-sources`, state.localSources.length === 1 && state.localSources.every((src) => src.startsWith('/media/')), { sources: state.localSources });
        add(`${viewport.name}-home-all-images-load`, state.allHomeImages.length === 6 && state.allHomeImages.every((image) => image.loaded && image.src.startsWith('/media/')), { images: state.allHomeImages });
        add(`${viewport.name}-home-no-remote-image-hotlinks`, state.remoteImageCount === 0, { remoteImageCount: state.remoteImageCount });
        add(`${viewport.name}-home-two-usable-video-controls`, state.homeVideos.length === 2 && state.homeVideos.every((video) => video.controls && video.playsInline), { videos: state.homeVideos });
        add(`${viewport.name}-home-two-autoplay-ready-clips`, state.homeVideos.length === 2 && state.homeVideos.every((video) => video.muted && video.loop && video.autoplayWhenVisible), { videos: state.homeVideos });
        add(`${viewport.name}-home-phase22-result-not-squeezed`, state.resultLayout?.containerDisplay === 'block' && state.resultLayout.measureCount === 3 && state.resultLayout.cardWidth >= 300 && !state.resultLayout.overlaps && !state.resultLayout.valueClips, { resultLayout: state.resultLayout });
        add(`${viewport.name}-home-two-local-video-sources`, state.homeVideos.length === 2 && state.homeVideos.every((video) => video.sources.some((source) => source.startsWith('/film/') && source.endsWith('.mp4')) && video.sources.some((source) => source.startsWith('/film/') && source.endsWith('.webm')) && video.poster.startsWith('/film/')), { videos: state.homeVideos });
        add(`${viewport.name}-home-context-media-credited`, state.contextFigures.length === 5 && state.contextFigures.every((figure) => /public-domain context/i.test(figure.caption) && figure.source.startsWith('https://')), { figures: state.contextFigures });
        add(`${viewport.name}-home-images-loaded`, state.imagesLoaded && !state.fallbackVisible, { imagesLoaded: state.imagesLoaded, fallbackVisible: state.fallbackVisible });
        add(`${viewport.name}-home-meaningful-alt`, state.altText.length === 1 && state.altText.every((alt) => alt.trim().length >= 24), { altText: state.altText });
        add(`${viewport.name}-home-context-labels`, state.captionCount === 1, { captionCount: state.captionCount });
        add(`${viewport.name}-home-credit-preserved`, state.credits.length === 1 && /Public domain/i.test(state.credits[0]) && /Don Richey/i.test(state.credits[0]), { credits: state.credits });
        add(`${viewport.name}-home-source-links`, state.sourceLinks.length === 1 && state.sourceLinks[0].startsWith('https://commons.wikimedia.org/wiki/File:'), { sourceLinks: state.sourceLinks });
        add(`${viewport.name}-home-consistent-aspect-ratio`, state.ratios.length === 1 && Math.abs(state.ratios[0] - state.expectedRatios[0]) < 0.03, { ratios: state.ratios });
      } else if (route === '/model-vase/') {
        await page.waitForFunction(() => {
          const image = document.querySelector('.vase-hero__media img');
          return !!image && image.complete && image.naturalWidth > 0;
        }, null, { timeout: 12000 }).catch(() => {});
        const imageLoaded = await page.locator('.vase-hero__media img').evaluate((image) => image.complete && image.naturalWidth > 0);
        add(`${viewport.name}-model-vase-hero-image-loads`, imageLoaded);
        const visionButton = page.locator('[data-evidence-button="vision"]');
        await visionButton.click();
        const visionVisible = await page.evaluate(() => {
          const button=document.querySelector('[data-evidence-button="vision"]');
          const vision=document.querySelector('[data-evidence-panel="vision"]');
          const simulation=document.querySelector('[data-evidence-panel="simulation"]');
          return button?.getAttribute('aria-pressed')==='true' && !!vision && !vision.hidden && !!simulation && simulation.hidden && /Published KIOS aggregates/.test(vision.innerText);
        });
        add(`${viewport.name}-model-vase-real-vision-switch`, visionVisible);
        await page.locator('[data-evidence-button="simulation"]').click();
        const simulationVisible = await page.evaluate(() => {
          const button=document.querySelector('[data-evidence-button="simulation"]');
          const vision=document.querySelector('[data-evidence-panel="vision"]');
          const simulation=document.querySelector('[data-evidence-panel="simulation"]');
          return button?.getAttribute('aria-pressed')==='true' && !!simulation && !simulation.hidden && !!vision && vision.hidden && /10,000 simulated episodes/.test(simulation.innerText);
        });
        add(`${viewport.name}-model-vase-simulation-switch`, simulationVisible);
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
        const targetRatio = expectedPhaseRatio(viewport.name);
        add(`${viewport.name}-${route}-phase-photo-ratio`, state.ratios.length === 1 && Math.abs(state.ratios[0] - targetRatio) < 0.03, { ratios: state.ratios, targetRatio });
        if (viewport.name === 'desktop' && state.localSources[0]) desktopPhaseSources.set(route, state.localSources[0]);
      }
      await page.close();
    }
    await context.close();
  }

  // The visual sweep above requests reduced motion. Verify automatic playback
  // separately under the normal preference, while leaving native controls intact.
  {
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: 'no-preference' });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', (error) => errors.push(String(error?.message || error)));
    page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()); });
    const response = await page.goto(`${BASE}/`, { waitUntil: 'domcontentloaded', timeout: 45000 });
    add('autoplay-home-status', !!response && response.status() < 400, { status: response?.status() || 0 });
    const clips = page.locator('.home-field-media video[data-autoplay="visible"]');
    add('autoplay-two-clips-present', await clips.count() === 2, { count: await clips.count() });
    const eagerlyLoaded = await clips.evaluateAll((videos) => videos.every((video) => video.preload === 'auto' && video.muted && video.loop));
    add('autoplay-clips-eagerly-preloaded', eagerlyLoaded);
    for (let index = 0; index < Math.min(await clips.count(), 2); index += 1) {
      const clip = clips.nth(index);
      await clip.scrollIntoViewIfNeeded();
      const started = await page.waitForFunction((clipIndex) => {
        const video = document.querySelectorAll('.home-field-media video[data-autoplay="visible"]')[clipIndex];
        return !!video && video.muted && !video.paused && video.currentTime > 0;
      }, index, { timeout: 12000 }).then(() => true).catch(() => false);
      const playbackState = await clip.evaluate((video) => {
        const rect = video.getBoundingClientRect();
        return {
          paused: video.paused,
          currentTime: video.currentTime,
          readyState: video.readyState,
          networkState: video.networkState,
          muted: video.muted,
          defaultMuted: video.defaultMuted,
          canPlayMp4: video.canPlayType('video/mp4; codecs="avc1.64001f"'),
          canPlayWebm: video.canPlayType('video/webm; codecs="vp9"'),
          currentSrc: video.currentSrc,
          error: video.error ? { code: video.error.code, message: video.error.message } : null,
          inViewport: rect.bottom > 0 && rect.top < innerHeight && rect.right > 0 && rect.left < innerWidth,
          visibility: getComputedStyle(video).visibility,
          reducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches,
          saveData: !!navigator.connection?.saveData
        };
      });
      const manualRetry = started ? null : await clip.evaluate(async (video) => {
        let timer;
        const result = await Promise.race([
          video.play().then(
            () => 'resolved',
            (error) => `${error?.name || 'Error'}: ${error?.message || error}`
          ),
          new Promise((resolve) => { timer = setTimeout(() => resolve('pending after 2500ms'), 2500); })
        ]);
        clearTimeout(timer);
        video.pause();
        return result;
      });
      add(`autoplay-visible-clip-${index + 1}-starts-muted`, started, { playbackState, manualRetry });
    }
    add('autoplay-browser-clean', errors.length === 0, { errors });
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
