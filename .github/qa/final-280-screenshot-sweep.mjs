import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';

const BASE = process.env.QA_BASE_URL || 'https://aegisland-research-cockpit.vercel.app';
const ROOT = path.join('qa-artifacts', 'final-280-sweep');
const SCREENSHOTS = path.join(ROOT, 'screenshots');

const phaseSlugs = [
  'phase1','phase2','phase3','phase4','phase5','phase6','phase6b','phase7','phase8','phase9','phase10','phase10r','phase11',
  'phase12','phase13a','phase13b','phase13c','phase14','phase15','phase16','phase17','phase18','phase19','phase20','phase21','phase22'
];
const routes = ['/', '/phases/', ...phaseSlugs.map((slug) => `/phases/${slug}/`)];
const viewports = [
  { name: 'desktop', width: 1440, height: 1000 },
  { name: 'phone', width: 390, height: 844, isMobile: true, hasTouch: true }
];
const capturesPerRoute = 5; // full page + four viewport positions

await fs.rm(ROOT, { recursive: true, force: true });
await fs.mkdir(SCREENSHOTS, { recursive: true });

const report = {
  base: BASE,
  startedAt: new Date().toISOString(),
  routes,
  viewports,
  capturesPerRoute,
  expectedByViewport: routes.length * capturesPerRoute,
  expectedTotal: routes.length * viewports.length * capturesPerRoute,
  screenshots: [],
  pages: [],
  blockers: [],
  warnings: []
};

const safe = (route) => route === '/' ? 'home' : route.replace(/^\/+|\/+$/g, '').replaceAll('/', '-');
const block = (pageKey, kind, details = {}) => report.blockers.push({ pageKey, kind, ...details });
const warn = (pageKey, kind, details = {}) => report.warnings.push({ pageKey, kind, ...details });

const browser = await chromium.launch({ headless: true });
try {
  for (const vp of viewports) {
    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
      isMobile: !!vp.isMobile,
      hasTouch: !!vp.hasTouch,
      reducedMotion: 'reduce',
      deviceScaleFactor: 1
    });

    for (const route of routes) {
      const pageKey = `${vp.name}:${route}`;
      const page = await context.newPage();
      const consoleErrors = [];
      const failedRequests = [];
      page.on('pageerror', (error) => consoleErrors.push(String(error?.message || error)));
      page.on('console', (message) => { if (message.type() === 'error') consoleErrors.push(message.text()); });
      page.on('requestfailed', (request) => failedRequests.push({ url: request.url(), error: request.failure()?.errorText || 'requestfailed' }));

      let response = null;
      try {
        response = await page.goto(`${BASE}${route}?final_sweep=1`, { waitUntil: 'domcontentloaded', timeout: 45000 });
        await page.waitForTimeout(700);
      } catch (error) {
        block(pageKey, 'load-failed', { error: String(error) });
      }

      // Force lazy editorial media to settle before any measurement or screenshot.
      const imgCount = await page.locator('img').count().catch(() => 0);
      for (let i = 0; i < imgCount; i += 1) {
        await page.locator('img').nth(i).scrollIntoViewIfNeeded().catch(() => {});
      }
      await page.waitForTimeout(220);
      await page.evaluate(async () => {
        await Promise.all([...document.images].map((img) => img.decode?.().catch(() => undefined)));
        window.scrollTo(0, 0);
      }).catch(() => {});
      await page.waitForTimeout(120);

      const metrics = await page.evaluate(({ route, isPhone }) => {
        const root = document.documentElement;
        const body = document.body;
        const visible = (el) => {
          if (!el) return false;
          const s = getComputedStyle(el);
          const r = el.getBoundingClientRect();
          return s.display !== 'none' && s.visibility !== 'hidden' && Number(s.opacity || 1) > 0 && r.width > 0 && r.height > 0;
        };
        const rect = (el) => el ? (() => { const r = el.getBoundingClientRect(); return { x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom }; })() : null;
        const rgb = (value) => {
          const m = String(value || '').match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/i);
          return m ? m.slice(1,4).map(Number) : null;
        };
        const luminance = (arr) => arr ? (arr[0] + arr[1] + arr[2]) / 3 : null;

        const ids = [...document.querySelectorAll('[id]')].map((el) => el.id).filter(Boolean);
        const dupIds = [...new Set(ids.filter((id, i) => ids.indexOf(id) !== i))];
        const brokenImages = [...document.images].filter((img) => !img.complete || img.naturalWidth === 0).map((img) => img.currentSrc || img.src);
        const missingAlt = [...document.images].filter((img) => !img.hasAttribute('alt')).map((img) => img.currentSrc || img.src);
        const brokenAnchors = [...document.querySelectorAll('a[href^="#"]')]
          .map((a) => a.getAttribute('href'))
          .filter((href) => href && href !== '#' && !document.getElementById(decodeURIComponent(href.slice(1))));
        const internalLinks = [...document.querySelectorAll('a[href]')]
          .map((a) => a.getAttribute('href'))
          .filter((href) => href && (href.startsWith('/') || href.startsWith('#')));

        const controls = [...document.querySelectorAll('a,button,input,select,textarea,[role="button"]')].filter(visible);
        const smallTargets = controls.map((el) => ({
          tag: el.tagName,
          text: (el.getAttribute('aria-label') || el.textContent || el.getAttribute('placeholder') || '').trim().slice(0,80),
          r: rect(el)
        })).filter((x) => x.r && (x.r.width < 40 || x.r.height < 40));
        const tinyText = [...document.querySelectorAll('p,li,a,button,span,small,figcaption,dd,dt')]
          .filter(visible)
          .map((el) => ({ text:(el.textContent || '').trim().slice(0,80), size:parseFloat(getComputedStyle(el).fontSize || '0') }))
          .filter((x) => x.text && x.size > 0 && x.size < 11 && !/^\d{1,2}$/.test(x.text));

        const themeMeta = document.querySelector('meta[name="theme-color"]')?.content || '';
        const bodyBg = getComputedStyle(body).backgroundColor;
        const bodyText = getComputedStyle(body).color;
        const themeRgb = /^#([0-9a-f]{6})$/i.test(themeMeta)
          ? [parseInt(themeMeta.slice(1,3),16), parseInt(themeMeta.slice(3,5),16), parseInt(themeMeta.slice(5,7),16)]
          : rgb(themeMeta);
        const bodyBgLum = luminance(rgb(bodyBg));
        const themeLum = luminance(themeRgb);

        const phasePage = /^\/phases\/phase/i.test(route);
        const phaseChip = document.querySelector('.phase-identity-chip');
        const roleCard = document.querySelector('.phase-role-card');
        const editorial = document.querySelector('.phase-editorial-photo, [data-editorial-photo]');
        const consistencyLink = document.querySelector('link[data-aegis-phase-ui-consistency]');
        const header = document.querySelector('header, .top, .site-header, .topbar');
        const main = document.querySelector('main');
        const footer = document.querySelector('footer');
        const h1 = document.querySelector('h1');
        const bodyStyles = getComputedStyle(body);

        const pageSections = [...document.querySelectorAll('main section[id], main article[id]')].filter(visible).map((el) => ({ id:el.id, rect:rect(el) }));
        const contentLabels = [...document.querySelectorAll('main h2, main h3')].filter(visible).map((el) => (el.textContent || '').trim()).filter(Boolean).slice(0,40);

        return {
          route,
          statusText: document.readyState,
          title: document.title,
          scrollWidth: root.scrollWidth,
          clientWidth: root.clientWidth,
          overflowX: root.scrollWidth - root.clientWidth,
          scrollHeight: root.scrollHeight,
          innerHeight: innerHeight,
          main: !!main,
          mainRect: rect(main),
          footerRect: rect(footer),
          headerRect: rect(header),
          h1Count: document.querySelectorAll('h1').length,
          h1Text: (h1?.textContent || '').trim(),
          h1Size: h1 ? parseFloat(getComputedStyle(h1).fontSize || '0') : 0,
          bodyBg,
          bodyText,
          bodyFont: bodyStyles.fontFamily,
          themeMeta,
          themeVsBodyMismatch: bodyBgLum !== null && themeLum !== null && bodyBgLum > 220 && themeLum < 100,
          brokenImages,
          missingAlt,
          dupIds,
          brokenAnchors: [...new Set(brokenAnchors)],
          internalLinks: [...new Set(internalLinks)],
          smallTargets: isPhone ? smallTargets : [],
          tinyText,
          phasePage,
          phaseChip: visible(phaseChip),
          roleCard: visible(roleCard),
          editorialVisual: visible(editorial),
          consistencyLayer: !!consistencyLink,
          bodyPhase: body?.dataset?.phase || '',
          bodyCategory: body?.dataset?.phaseCategory || '',
          pageSections,
          contentLabels,
          words: (body?.innerText || '').trim().split(/\s+/).filter(Boolean).length
        };
      }, { route, isPhone: vp.name === 'phone' }).catch(() => null);

      const status = response?.status() || 0;
      if (!status || status >= 400) block(pageKey, 'bad-http-status', { status });
      if (!metrics) block(pageKey, 'metrics-unavailable');
      else {
        if (!metrics.main || metrics.h1Count !== 1) block(pageKey, 'semantic-shell', { main: metrics.main, h1Count: metrics.h1Count });
        if (metrics.overflowX > 2) block(pageKey, 'horizontal-overflow', { overflowX: metrics.overflowX });
        if (metrics.brokenImages.length) block(pageKey, 'broken-images', { images: metrics.brokenImages });
        if (metrics.missingAlt.length) block(pageKey, 'missing-image-alt', { images: metrics.missingAlt });
        if (metrics.dupIds.length) block(pageKey, 'duplicate-ids', { ids: metrics.dupIds });
        if (metrics.brokenAnchors.length) block(pageKey, 'broken-in-page-anchors', { anchors: metrics.brokenAnchors });
        if (metrics.phasePage && (!metrics.phaseChip || !metrics.roleCard)) block(pageKey, 'phase-flow-components-missing', { chip:metrics.phaseChip, role:metrics.roleCard });
        if (metrics.phasePage && !metrics.editorialVisual) block(pageKey, 'phase-editorial-visual-missing');
        if ((metrics.phasePage || route === '/phases/') && !metrics.consistencyLayer) block(pageKey, 'phase-consistency-layer-missing');
        if (metrics.themeVsBodyMismatch) warn(pageKey, 'theme-color-does-not-match-light-page', { themeMeta:metrics.themeMeta, bodyBg:metrics.bodyBg });
        if (vp.name === 'phone' && metrics.smallTargets.length) warn(pageKey, 'small-phone-targets', { count:metrics.smallTargets.length, examples:metrics.smallTargets.slice(0,10) });
        if (metrics.tinyText.length) warn(pageKey, 'tiny-descriptive-text', { count:metrics.tinyText.length, examples:metrics.tinyText.slice(0,10) });
        if (metrics.words > 2200) warn(pageKey, 'very-long-page', { words:metrics.words });
      }

      const filteredConsole = consoleErrors.filter((x) => !/favicon|ERR_BLOCKED_BY_CLIENT/i.test(x));
      const filteredRequests = failedRequests.filter((x) => !/favicon|github\.com|linkedin\.com/i.test(x.url));
      if (filteredConsole.length) block(pageKey, 'browser-console-errors', { errors:filteredConsole });
      if (filteredRequests.length) block(pageKey, 'network-request-failures', { requests:filteredRequests });

      const prefix = `${safe(route)}-${vp.name}`;
      const fullFile = path.join(SCREENSHOTS, `${prefix}-00-full.png`);
      await page.evaluate(() => window.scrollTo(0, 0)).catch(() => {});
      await page.waitForTimeout(80);
      await page.screenshot({ path: fullFile, fullPage: true });
      report.screenshots.push({ viewport:vp.name, route, kind:'full', file:fullFile });

      const maxScroll = Math.max(0, (metrics?.scrollHeight || await page.evaluate(() => document.documentElement.scrollHeight)) - vp.height);
      const positions = [0, 0.33, 0.66, 1];
      for (let i = 0; i < positions.length; i += 1) {
        const y = Math.round(maxScroll * positions[i]);
        await page.evaluate((scrollY) => window.scrollTo(0, scrollY), y);
        await page.waitForTimeout(100);
        const file = path.join(SCREENSHOTS, `${prefix}-${String(i + 1).padStart(2,'0')}-${Math.round(positions[i] * 100)}pct.png`);
        await page.screenshot({ path: file, fullPage: false });
        report.screenshots.push({ viewport:vp.name, route, kind:`viewport-${positions[i]}`, y, file });
      }

      report.pages.push({ pageKey, viewport:vp, route, status, metrics, consoleErrors:filteredConsole, failedRequests:filteredRequests });
      await page.close();
    }
    await context.close();
  }
} finally {
  await browser.close();
}

report.finishedAt = new Date().toISOString();
report.counts = Object.fromEntries(viewports.map((vp) => [vp.name, report.screenshots.filter((s) => s.viewport === vp.name).length]));
for (const vp of viewports) {
  if ((report.counts[vp.name] || 0) < 100) block('global', 'insufficient-screenshot-count', { viewport:vp.name, count:report.counts[vp.name] || 0 });
}
if (report.screenshots.length !== report.expectedTotal) block('global', 'screenshot-total-mismatch', { expected:report.expectedTotal, actual:report.screenshots.length });

await fs.writeFile(path.join(ROOT, 'report.json'), JSON.stringify(report, null, 2));
const summary = [
  '# AegisLand Final 280-Screenshot Sweep',
  '',
  `- Base: ${BASE}`,
  `- Routes: ${routes.length}`,
  `- Desktop screenshots: ${report.counts.desktop || 0}`,
  `- Phone screenshots: ${report.counts.phone || 0}`,
  `- Total screenshots: ${report.screenshots.length}/${report.expectedTotal}`,
  `- Blockers: ${report.blockers.length}`,
  `- Warnings: ${report.warnings.length}`,
  '',
  '## Blockers',
  ...(report.blockers.length ? report.blockers.map((x) => `- ${x.pageKey} — ${x.kind}`) : ['- None']),
  '',
  '## Warnings',
  ...(report.warnings.length ? report.warnings.map((x) => `- ${x.pageKey} — ${x.kind}`) : ['- None'])
].join('\n');
await fs.writeFile(path.join(ROOT, 'summary.md'), summary);
console.log(summary);
if (report.blockers.length) process.exit(1);
