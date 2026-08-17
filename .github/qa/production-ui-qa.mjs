import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';

const BASE = process.env.QA_BASE_URL || 'https://aegisland-research-cockpit.vercel.app';
const OUT = 'qa-artifacts';
const routes = [
  '/', '/phases/', '/phases/phase1/', '/phases/phase2/', '/phases/phase3/',
  '/phases/phase4/', '/phases/phase5/', '/phases/phase6/', '/phases/phase6b/',
  '/phases/phase7/', '/phases/phase8/', '/phases/phase9/', '/phases/phase10/',
  '/phases/phase10r/', '/phases/phase11/'
];
const viewports = [
  { name: 'desktop', width: 1440, height: 1000 },
  { name: 'tablet', width: 820, height: 1180 },
  { name: 'mobile', width: 390, height: 844, isMobile: true, hasTouch: true }
];
const screenshotRoutes = new Set(['/', '/phases/', '/phases/phase10r/', '/phases/phase11/']);
const report = { base: BASE, startedAt: new Date().toISOString(), checks: [], errors: [], warnings: [], screenshots: [], video: null };

await fs.rm(OUT, { recursive: true, force: true });
await fs.mkdir(path.join(OUT, 'screenshots'), { recursive: true });
await fs.mkdir(path.join(OUT, 'videos'), { recursive: true });

function safeName(route) {
  if (route === '/') return 'home';
  return route.replace(/^\/+|\/+$/g, '').replaceAll('/', '-');
}
function push(level, data) { report[level].push({ at: new Date().toISOString(), ...data }); }
function ok(name, details = {}) { report.checks.push({ name, ok: true, ...details }); }
function fail(name, details = {}) { report.checks.push({ name, ok: false, ...details }); push('errors', { name, ...details }); }

const browser = await chromium.launch({ headless: true });
try {
  for (const vp of viewports) {
    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
      isMobile: !!vp.isMobile,
      hasTouch: !!vp.hasTouch,
      reducedMotion: 'reduce'
    });

    for (const route of routes) {
      const page = await context.newPage();
      const consoleErrors = [];
      const pageErrors = [];
      const failedRequests = [];
      page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
      page.on('pageerror', e => pageErrors.push(String(e?.message || e)));
      page.on('requestfailed', req => failedRequests.push({ url: req.url(), error: req.failure()?.errorText || 'requestfailed' }));

      let response;
      try {
        response = await page.goto(BASE + route, { waitUntil: 'domcontentloaded', timeout: 45000 });
        await page.waitForTimeout(2400);
      } catch (error) {
        fail('route-load', { viewport: vp.name, route, error: String(error) });
        await page.close();
        continue;
      }

      const status = response?.status() ?? 0;
      const contentType = (await response?.allHeaders().catch(() => ({})))?.['content-type'] || '';
      if (status >= 200 && status < 400) ok('route-load', { viewport: vp.name, route, status, contentType });
      else fail('route-load', { viewport: vp.name, route, status, contentType });
      if (route === '/phases/phase11/') {
        if (/text\/html/i.test(contentType)) ok('phase11-document-content-type', { viewport: vp.name, contentType });
        else fail('phase11-document-content-type', { viewport: vp.name, contentType });
      }

      const state = await page.evaluate(() => {
        const de = document.documentElement;
        const bodyText = document.body?.innerText || '';
        const images = [...document.images].map(img => ({ src: img.currentSrc || img.src, complete: img.complete, naturalWidth: img.naturalWidth, naturalHeight: img.naturalHeight }));
        const anchors = [...document.querySelectorAll('a[href]')].map(a => ({ href: a.getAttribute('href'), text: (a.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 120) }));
        const hashLinks = anchors.filter(a => a.href?.startsWith('#') && a.href.length > 1);
        const missingHashTargets = hashLinks.filter(a => !document.querySelector(a.href)).map(a => a.href);
        const visibleButtons = [...document.querySelectorAll('a,button')].filter(el => {
          const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
          return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
        }).map(el => { const r=el.getBoundingClientRect(); return { tag:el.tagName, cls:el.className || '', text:(el.textContent||'').trim().replace(/\s+/g,' ').slice(0,80), w:Math.round(r.width), h:Math.round(r.height), href:el.getAttribute('href') }; });

        const rail = document.querySelector('#phaseRail,.phase-rail');
        const railSteps = rail ? [...rail.querySelectorAll(':scope > a')] : [];
        const railStyle = rail ? getComputedStyle(rail) : null;
        const railGridRows = railStyle?.gridTemplateRows || '';
        const railGridCols = railStyle?.gridTemplateColumns || '';
        const railRect = rail?.getBoundingClientRect();
        const railSingleTrack = !!rail && railSteps.length > 0 && railSteps.every(a => {
          const r = a.getBoundingClientRect();
          return r.top >= railRect.top - 1 && r.bottom <= railRect.bottom + 1;
        });

        const homeRail = document.querySelector('#homeModelRail');
        const homeSteps = homeRail ? [...homeRail.querySelectorAll('.home-rail-step')] : [];
        const overflowOffenders = [...document.querySelectorAll('body *')].map(el => {
          const r = el.getBoundingClientRect();
          return { tag: el.tagName, id: el.id || '', cls: typeof el.className === 'string' ? el.className.slice(0,120) : '', left: Math.round(r.left), right: Math.round(r.right), width: Math.round(r.width) };
        }).filter(x => x.right > innerWidth + 2 || x.left < -2).sort((a,b) => (b.right-innerWidth) - (a.right-innerWidth)).slice(0,12);

        const sourcePrefix = bodyText.trimStart().slice(0, 250).toLowerCase();
        const looksLikeSourceText = sourcePrefix.startsWith('<!doctype') || sourcePrefix.startsWith('<html') || sourcePrefix.includes('<head>');

        return {
          title: document.title,
          bodyWidth: de.scrollWidth,
          viewportWidth: innerWidth,
          bodyHeight: de.scrollHeight,
          viewportHeight: innerHeight,
          overflowX: de.scrollWidth - innerWidth,
          overflowOffenders,
          images,
          anchors,
          missingHashTargets,
          visibleButtons,
          railCount: railSteps.length,
          railGridRows,
          railGridCols,
          railSingleTrack,
          homeRailCount: homeSteps.length,
          hasUndefined: /(^|\s)(undefined|null|\[object Object\])(\s|$)/i.test(bodyText),
          looksLikeSourceText,
          mainExists: !!document.querySelector('main'),
          h1Count: document.querySelectorAll('h1').length
        };
      });

      if (!state.looksLikeSourceText) ok('html-rendered-not-source', { viewport: vp.name, route });
      else fail('html-rendered-not-source', { viewport: vp.name, route, title: state.title });

      if (state.mainExists && state.h1Count >= 1) ok('semantic-shell', { viewport: vp.name, route, h1Count: state.h1Count });
      else fail('semantic-shell', { viewport: vp.name, route, mainExists: state.mainExists, h1Count: state.h1Count });

      const allowance = 2;
      if (state.overflowX <= allowance) ok('body-horizontal-overflow', { viewport: vp.name, route, overflowPx: state.overflowX });
      else fail('body-horizontal-overflow', { viewport: vp.name, route, overflowPx: state.overflowX, offenders: state.overflowOffenders });

      const brokenImages = state.images.filter(i => !i.complete || i.naturalWidth === 0 || i.naturalHeight === 0);
      if (!brokenImages.length) ok('images-load', { viewport: vp.name, route, count: state.images.length });
      else fail('images-load', { viewport: vp.name, route, brokenImages });

      if (!state.missingHashTargets.length) ok('hash-targets', { viewport: vp.name, route });
      else fail('hash-targets', { viewport: vp.name, route, missing: state.missingHashTargets });

      if (!state.hasUndefined) ok('no-placeholder-text', { viewport: vp.name, route });
      else fail('no-placeholder-text', { viewport: vp.name, route });

      const importantTinyTargets = state.visibleButtons.filter(x => x.h < 36 && /(button|top-btn|site-nav|header-actions|menu|phase-link)/i.test(`${x.tag} ${x.cls} ${x.text}`));
      if (importantTinyTargets.length) push('warnings', { name: 'small-important-click-targets', viewport: vp.name, route, examples: importantTinyTargets.slice(0, 8) });

      const filteredConsole = consoleErrors.filter(x => !/favicon|ERR_BLOCKED_BY_CLIENT/i.test(x));
      const filteredReq = failedRequests.filter(x => !/favicon|linkedin\.com|github\.com/i.test(x.url));
      if (!pageErrors.length && !filteredConsole.length) ok('browser-errors', { viewport: vp.name, route });
      else fail('browser-errors', { viewport: vp.name, route, pageErrors, consoleErrors: filteredConsole });
      if (!filteredReq.length) ok('network-failures', { viewport: vp.name, route });
      else fail('network-failures', { viewport: vp.name, route, failedRequests: filteredReq });

      if (route.startsWith('/phases/phase') && route !== '/phases/phase11/') {
        if (state.railCount === 13) ok('historical-phase-rail-count', { viewport: vp.name, route, count: state.railCount });
        else fail('historical-phase-rail-count', { viewport: vp.name, route, count: state.railCount });
        if (vp.name === 'desktop') {
          if (state.railSingleTrack) ok('historical-phase-rail-single-track', { viewport: vp.name, route, rows: state.railGridRows, cols: state.railGridCols });
          else fail('historical-phase-rail-single-track', { viewport: vp.name, route, rows: state.railGridRows, cols: state.railGridCols });
        }
      }
      if (route === '/' && state.homeRailCount !== 13) fail('home-phase-rail-count', { viewport: vp.name, count: state.homeRailCount });
      else if (route === '/') ok('home-phase-rail-count', { viewport: vp.name, count: state.homeRailCount });

      if (screenshotRoutes.has(route)) {
        const file = path.join(OUT, 'screenshots', `${safeName(route)}-${vp.name}.png`);
        await page.screenshot({ path: file, fullPage: true });
        report.screenshots.push(file);
      }
      await page.close();
    }
    await context.close();
  }

  // Deep interaction flow + video.
  const flowContext = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    recordVideo: { dir: path.join(OUT, 'videos'), size: { width: 1280, height: 720 } },
    reducedMotion: 'reduce'
  });
  const flow = await flowContext.newPage();
  const flowErrors = [];
  flow.on('pageerror', e => flowErrors.push(String(e?.message || e)));
  flow.on('console', m => { if (m.type() === 'error') flowErrors.push(`console: ${m.text()}`); });

  await flow.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 45000 });
  await flow.waitForTimeout(2500);
  const openPhase11 = flow.getByRole('link', { name: /open phase 11/i }).first();
  if (await openPhase11.count()) {
    await openPhase11.click();
    await flow.waitForTimeout(1800);
    if (/\/phases\/phase11\/?$/.test(new URL(flow.url()).pathname)) ok('click-home-to-phase11');
    else fail('click-home-to-phase11', { url: flow.url() });
  } else fail('click-home-to-phase11', { error: 'CTA not found' });

  const evidence = flow.getByRole('link', { name: /view the evidence/i }).first();
  if (await evidence.count()) {
    await evidence.click();
    await flow.waitForTimeout(600);
    if (flow.url().endsWith('#evidence')) ok('click-phase11-evidence-anchor');
    else fail('click-phase11-evidence-anchor', { url: flow.url() });
  } else fail('click-phase11-evidence-anchor', { error: 'link not found' });

  const finalHref = await flow.getByRole('link', { name: /read final report/i }).first().getAttribute('href').catch(() => null);
  if (finalHref?.includes('phase11_final_report.md')) ok('phase11-final-report-link', { href: finalHref });
  else fail('phase11-final-report-link', { href: finalHref });

  await flow.goto(BASE + '/phases/', { waitUntil: 'domcontentloaded', timeout: 45000 });
  await flow.waitForTimeout(2200);
  const archiveP11 = flow.locator('a[href="/phases/phase11/"]');
  if (await archiveP11.count()) ok('archive-phase11-link', { count: await archiveP11.count() });
  else fail('archive-phase11-link');

  await flow.goto(BASE + '/phases/phase10r/', { waitUntil: 'domcontentloaded', timeout: 45000 });
  await flow.waitForTimeout(2200);
  const railP11 = flow.locator('#phaseRail a[href="/phases/phase11/"],.phase-rail a[href="/phases/phase11/"]');
  if (await railP11.count()) ok('phase10r-to-phase11-rail-link');
  else fail('phase10r-to-phase11-rail-link');

  for (let i = 0; i < 7; i++) { await flow.mouse.wheel(0, 620); await flow.waitForTimeout(260); }
  await flow.goto(BASE + '/phases/phase11/', { waitUntil: 'domcontentloaded', timeout: 45000 });
  await flow.waitForTimeout(1800);
  for (let i = 0; i < 8; i++) { await flow.mouse.wheel(0, 560); await flow.waitForTimeout(260); }

  if (!flowErrors.length) ok('interaction-flow-browser-errors');
  else fail('interaction-flow-browser-errors', { flowErrors });
  const video = flow.video();
  await flow.close();
  await flowContext.close();
  if (video) { try { report.video = await video.path(); } catch {} }

  // Probe every unique internal route found in key pages with the request API.
  const req = await browser.newContext();
  const probePage = await req.newPage();
  const discovered = new Set(routes);
  for (const route of ['/', '/phases/', '/phases/phase10r/', '/phases/phase11/']) {
    await probePage.goto(BASE + route, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await probePage.waitForTimeout(1800);
    const hrefs = await probePage.locator('a[href]').evaluateAll(as => as.map(a => a.getAttribute('href')).filter(Boolean));
    for (const href of hrefs) {
      if (href.startsWith('/') && !href.startsWith('//')) discovered.add(href.split('#')[0].split('?')[0] || '/');
    }
  }
  for (const route of [...discovered].sort()) {
    try {
      const r = await req.request.get(BASE + route, { failOnStatusCode: false, maxRedirects: 5, timeout: 30000 });
      const ct = r.headers()['content-type'] || '';
      if (r.status() < 400) ok('internal-link-http', { route, status: r.status(), contentType: ct });
      else fail('internal-link-http', { route, status: r.status(), contentType: ct });
    } catch (error) { fail('internal-link-http', { route, error: String(error) }); }
  }
  await req.close();
} finally {
  await browser.close();
}

report.finishedAt = new Date().toISOString();
report.totalChecks = report.checks.length;
report.failedChecks = report.checks.filter(c => !c.ok).length;
report.passedChecks = report.totalChecks - report.failedChecks;
await fs.writeFile(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2));

const lines = [
  '# AegisLand production UI QA', '',
  `- Base: ${BASE}`,
  `- Passed: ${report.passedChecks}`,
  `- Failed: ${report.failedChecks}`,
  `- Warnings: ${report.warnings.length}`,
  `- Screenshots: ${report.screenshots.length}`,
  `- Video: ${report.video || 'not available'}`, '',
  '## Failed checks',
  ...(report.errors.length ? report.errors.map(e => `- **${e.name}** — ${JSON.stringify(e)}`) : ['- None']), '',
  '## Warnings',
  ...(report.warnings.length ? report.warnings.map(w => `- **${w.name}** — ${JSON.stringify(w)}`) : ['- None'])
];
await fs.writeFile(path.join(OUT, 'summary.md'), lines.join('\n'));
console.log(lines.join('\n'));
if (report.failedChecks > 0) process.exitCode = 1;
