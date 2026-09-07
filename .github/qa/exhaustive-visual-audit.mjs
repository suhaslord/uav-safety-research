import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';

const BASE = process.env.QA_BASE_URL || 'https://aegisland-research-cockpit.vercel.app';
const ROOT = path.join('qa-artifacts', 'exhaustive');
const SCREENSHOTS = path.join(ROOT, 'screenshots');

const phaseSlugs = [
  'phase1','phase2','phase3','phase4','phase5','phase6','phase6b','phase7','phase8','phase9','phase10','phase10r','phase11',
  'phase12','phase13a','phase13b','phase13c','phase14','phase15','phase16','phase17','phase18','phase19','phase20','phase21','phase22'
];
const routes = ['/', '/phases/', ...phaseSlugs.map((slug) => `/phases/${slug}/`)];
const viewports = [
  { name: 'desktop', width: 1440, height: 1000 },
  { name: 'tablet', width: 820, height: 1180 },
  { name: 'mobile', width: 390, height: 844, isMobile: true, hasTouch: true }
];

await fs.rm(ROOT, { recursive: true, force: true });
await fs.mkdir(SCREENSHOTS, { recursive: true });

const report = {
  base: BASE,
  startedAt: new Date().toISOString(),
  routes,
  viewports,
  expectedScreenshots: routes.length * viewports.length,
  screenshots: [],
  pages: [],
  blockers: [],
  warnings: []
};

const safeName = (route) => route === '/' ? 'home' : route.replace(/^\/+|\/+$/g, '').replaceAll('/', '-');
const pushBlocker = (pageKey, kind, details = {}) => report.blockers.push({ pageKey, kind, ...details });
const pushWarning = (pageKey, kind, details = {}) => report.warnings.push({ pageKey, kind, ...details });

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
        response = await page.goto(`${BASE}${route}?exhaustive_visual_audit=2`, { waitUntil: 'domcontentloaded', timeout: 45000 });
        await page.waitForTimeout(900);
      } catch (error) {
        pushBlocker(pageKey, 'load-failed', { error: String(error) });
      }

      // Settle all lazy/editorial images. Always return to the top before measurement and
      // full-page capture so sticky headers are not painted halfway down the screenshot.
      const images = page.locator('img');
      const imageCount = await images.count().catch(() => 0);
      for (let i = 0; i < imageCount; i += 1) {
        await images.nth(i).scrollIntoViewIfNeeded().catch(() => {});
      }
      await page.waitForTimeout(250);
      await page.evaluate(async () => {
        const imgs = [...document.images];
        await Promise.all(imgs.map((img) => img.decode?.().catch(() => undefined)));
        window.scrollTo(0, 0);
      }).catch(() => {});
      await page.waitForTimeout(180);

      const metrics = await page.evaluate(({ route, viewportName }) => {
        const root = document.documentElement;
        const body = document.body;
        const rect = (el) => el ? (() => { const r = el.getBoundingClientRect(); return { x:r.x, y:r.y, width:r.width, height:r.height, bottom:r.bottom, right:r.right }; })() : null;
        const visible = (el) => {
          if (!el) return false;
          const s = getComputedStyle(el);
          const r = el.getBoundingClientRect();
          return s.display !== 'none' && s.visibility !== 'hidden' && Number(s.opacity || 1) > 0 && r.width > 0 && r.height > 0;
        };
        const onDocument = (el) => {
          const r = el.getBoundingClientRect();
          return r.bottom > 0 && r.right > 0;
        };
        const clickable = [...document.querySelectorAll('a,button,input,select,textarea,[role="button"]')].filter((el) => visible(el) && onDocument(el));
        const tinyTargets = clickable
          .map((el) => ({ tag: el.tagName, text: (el.getAttribute('aria-label') || el.textContent || el.getAttribute('placeholder') || '').trim().slice(0,80), r: rect(el) }))
          .filter((item) => item.r && (item.r.width < 40 || item.r.height < 40));
        const tinyText = [...document.querySelectorAll('p,li,a,button,span,small,figcaption,dd,dt')]
          .filter((el) => visible(el) && onDocument(el))
          .map((el) => ({ text: (el.textContent || '').trim().slice(0,80), size: parseFloat(getComputedStyle(el).fontSize || '0') }))
          .filter((item) => item.text && item.size > 0 && item.size < 11);
        const ids = [...document.querySelectorAll('[id]')].map((el) => el.id).filter(Boolean);
        const dupIds = ids.filter((id, index) => ids.indexOf(id) !== index);
        const brokenImages = [...document.images].filter((img) => !img.complete || img.naturalWidth === 0).map((img) => img.currentSrc || img.src);
        const missingAlt = [...document.images].filter((img) => !img.hasAttribute('alt')).map((img) => img.currentSrc || img.src);
        const controlName = (el) => {
          const direct = (el.getAttribute('aria-label') || el.getAttribute('title') || el.textContent || '').trim();
          if (direct) return direct;
          const labelledBy = (el.getAttribute('aria-labelledby') || '').trim();
          if (labelledBy && labelledBy.split(/\s+/).some((id) => document.getElementById(id)?.textContent?.trim())) return labelledBy;
          if ('labels' in el && el.labels?.length && [...el.labels].some((label) => label.textContent?.trim())) return 'associated-label';
          if ((el.getAttribute('placeholder') || '').trim()) return 'placeholder';
          if (el.querySelector?.('img[alt]')) return 'image-alt';
          return '';
        };
        const unlabeledControls = clickable.filter((el) => !controlName(el)).length;
        const phasePage = /^\/phases\/phase/i.test(route);
        const hero = document.querySelector('main h1')?.closest('section,header,article,div') || document.querySelector('main h1');
        const phaseChip = document.querySelector('.phase-identity-chip');
        const roleCard = document.querySelector('.phase-role-card');
        const editorial = document.querySelector('.phase-editorial-photo, [data-editorial-photo]');
        const nav = document.querySelector('header, .site-header, .topbar, nav');
        const main = document.querySelector('main');
        const footer = document.querySelector('footer');
        const consistencyLink = document.querySelector('link[data-aegis-phase-ui-consistency]');
        const structuralBlocks = [...document.querySelectorAll('main > section, main > article, main > div, main > figure[data-editorial-photo], .phase-detail > figure[data-editorial-photo]')]
          .filter(visible)
          .map((el) => ({ className: el.className || el.tagName, r: rect(el) }))
          .filter((item) => item.r)
          .sort((a, b) => a.r.y - b.r.y);
        const sectionGaps = [];
        for (let i=1;i<structuralBlocks.length;i+=1) {
          sectionGaps.push({
            gap: Math.round(structuralBlocks[i].r.y - structuralBlocks[i-1].r.bottom),
            from: String(structuralBlocks[i-1].className).slice(0,80),
            to: String(structuralBlocks[i].className).slice(0,80)
          });
        }
        return {
          viewportName,
          route,
          title: document.title,
          bodyHeight: Math.round(root.scrollHeight),
          clientWidth: root.clientWidth,
          scrollWidth: root.scrollWidth,
          overflowX: root.scrollWidth - root.clientWidth,
          main: !!main,
          mainRect: rect(main),
          h1Count: document.querySelectorAll('h1').length,
          navRect: rect(nav),
          footerRect: rect(footer),
          heroRect: rect(hero),
          phasePage,
          phaseChip: visible(phaseChip),
          roleCard: visible(roleCard),
          editorialVisual: visible(editorial),
          editorialRect: rect(editorial),
          consistencyLayer: !!consistencyLink,
          bodyPhase: body?.dataset?.phase || '',
          bodyCategory: body?.dataset?.phaseCategory || '',
          brokenImages,
          missingAlt,
          dupIds: [...new Set(dupIds)],
          unlabeledControls,
          tinyTargets,
          tinyText,
          sectionGaps,
          textLength: (body?.innerText || '').trim().length,
          words: (body?.innerText || '').trim().split(/\s+/).filter(Boolean).length
        };
      }, { route, viewportName: vp.name }).catch(() => null);

      const status = response?.status() || 0;
      if (!status || status >= 400) pushBlocker(pageKey, 'bad-http-status', { status });
      if (!metrics) pushBlocker(pageKey, 'metrics-unavailable');
      else {
        if (!metrics.main || metrics.h1Count !== 1) pushBlocker(pageKey, 'semantic-shell', { main: metrics.main, h1Count: metrics.h1Count });
        if (metrics.overflowX > 2) pushBlocker(pageKey, 'horizontal-overflow', { overflowX: metrics.overflowX });
        if (metrics.brokenImages.length) pushBlocker(pageKey, 'broken-images', { images: metrics.brokenImages });
        if (metrics.dupIds.length) pushBlocker(pageKey, 'duplicate-ids', { ids: metrics.dupIds });
        if (metrics.missingAlt.length) pushBlocker(pageKey, 'missing-image-alt', { images: metrics.missingAlt });
        if (metrics.unlabeledControls) pushBlocker(pageKey, 'unlabeled-controls', { count: metrics.unlabeledControls });
        if (metrics.phasePage && (!metrics.phaseChip || !metrics.roleCard)) pushBlocker(pageKey, 'phase-personalization-missing', { chip: metrics.phaseChip, role: metrics.roleCard });
        if (metrics.phasePage && !metrics.bodyCategory) pushBlocker(pageKey, 'phase-category-missing');
        if (metrics.phasePage && !metrics.editorialVisual) pushBlocker(pageKey, 'phase-editorial-visual-missing');
        if ((metrics.phasePage || route === '/phases/') && !metrics.consistencyLayer) pushBlocker(pageKey, 'phase-consistency-layer-missing');
        if (vp.name === 'mobile' && metrics.tinyTargets.length) pushWarning(pageKey, 'small-touch-targets', { count: metrics.tinyTargets.length, examples: metrics.tinyTargets.slice(0,8) });
        if (metrics.tinyText.length) pushWarning(pageKey, 'tiny-text', { count: metrics.tinyText.length, examples: metrics.tinyText.slice(0,8) });
        const overlaps = metrics.sectionGaps.filter((item) => item.gap < -2);
        const oversized = metrics.sectionGaps.filter((item) => item.gap > 220);
        if (overlaps.length) pushWarning(pageKey, 'section-overlap-suspected', { gaps: overlaps.slice(0,8) });
        if (oversized.length) pushWarning(pageKey, 'excessive-section-gap', { gaps: oversized.slice(0,8) });
      }

      const filteredConsole = consoleErrors.filter((entry) => !/favicon|ERR_BLOCKED_BY_CLIENT/i.test(entry));
      const filteredRequests = failedRequests.filter((entry) => !/favicon|github\.com|linkedin\.com/i.test(entry.url));
      if (filteredConsole.length) pushBlocker(pageKey, 'browser-console-errors', { errors: filteredConsole });
      if (filteredRequests.length) pushBlocker(pageKey, 'network-request-failures', { requests: filteredRequests });

      const file = path.join(SCREENSHOTS, `${safeName(route)}-${vp.name}.png`);
      await page.screenshot({ path: file, fullPage: true });
      report.screenshots.push(file);
      report.pages.push({ pageKey, viewport: vp, route, status, metrics, consoleErrors: filteredConsole, failedRequests: filteredRequests, screenshot: file });
      await page.close();
    }
    await context.close();
  }
} finally {
  await browser.close();
}

report.finishedAt = new Date().toISOString();
report.actualScreenshots = report.screenshots.length;
if (report.actualScreenshots !== report.expectedScreenshots) {
  pushBlocker('global', 'screenshot-count-mismatch', { expected: report.expectedScreenshots, actual: report.actualScreenshots });
}

const phasePages = report.pages.filter((p) => p.metrics?.phasePage);
const templateGroups = {};
for (const page of phasePages) {
  const key = `${page.viewport.name}:${page.route.includes('phase11') ? 'phase11' : /phase(1|2|3|4|5|6|6b|7|8|9|10|10r)\//.test(page.route) ? 'legacy' : 'frozen'}`;
  templateGroups[key] ||= [];
  templateGroups[key].push(page);
}
for (const [key, pages] of Object.entries(templateGroups)) {
  const widths = pages.map((p) => p.metrics?.mainRect?.width).filter(Number.isFinite);
  if (widths.length > 1) {
    const spread = Math.max(...widths) - Math.min(...widths);
    if (spread > 12) pushWarning(key, 'template-main-width-drift', { spread, widths });
  }
}

await fs.writeFile(path.join(ROOT, 'report.json'), JSON.stringify(report, null, 2));
const summary = [
  '# AegisLand Exhaustive Visual Audit',
  '',
  `- Base: ${BASE}`,
  `- Routes: ${routes.length}`,
  `- Viewports: ${viewports.length}`,
  `- Screenshots: ${report.actualScreenshots}/${report.expectedScreenshots}`,
  `- Blockers: ${report.blockers.length}`,
  `- Warnings: ${report.warnings.length}`,
  '',
  '## Blockers',
  ...(report.blockers.length ? report.blockers.map((b) => `- ${b.pageKey} — ${b.kind}`) : ['- None']),
  '',
  '## Warnings',
  ...(report.warnings.length ? report.warnings.map((w) => `- ${w.pageKey} — ${w.kind}`) : ['- None'])
].join('\n');
await fs.writeFile(path.join(ROOT, 'summary.md'), summary);
console.log(summary);
if (report.blockers.length) process.exit(1);
