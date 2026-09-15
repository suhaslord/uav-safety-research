import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';

const BASE = process.env.QA_BASE_URL || 'https://aegisland-research-cockpit.vercel.app';
const OUT = 'qa-artifacts';
const PHASE22_RESULT = '0ddc968b8bd48c2de6d904194b417854913389a8927cff0b15b96c6501f8294c';
const PHASE22_CANDIDATE = '62e75d7b39088c2e66f1cc6be4d180501b79632f2f6847af1fbe0bd96be17551';

const phaseSlugs = [
  'phase1','phase2','phase3','phase4','phase5','phase6','phase6b','phase7','phase8','phase9','phase10','phase10r','phase11',
  'phase12','phase13a','phase13b','phase13c','phase14','phase15','phase16','phase17','phase18','phase19','phase20','phase21','phase22'
];
const frozenSlugs = new Set(['phase12','phase13a','phase13b','phase13c','phase14','phase15','phase16','phase17','phase18','phase19','phase20','phase21','phase22']);
const routes = ['/', '/phases/', ...phaseSlugs.map((slug) => `/phases/${slug}/`)];
const viewports = [
  { name: 'desktop', width: 1440, height: 1000 },
  { name: 'tablet', width: 820, height: 1180 },
  { name: 'mobile', width: 390, height: 844, isMobile: true, hasTouch: true }
];
const screenshotRoutes = new Set(['/', '/phases/', '/phases/phase1/', '/phases/phase10r/', '/phases/phase22/']);
const report = { base: BASE, startedAt: new Date().toISOString(), checks: [], errors: [], screenshots: [] };

await fs.rm(OUT, { recursive: true, force: true });
await fs.mkdir(path.join(OUT, 'screenshots'), { recursive: true });

const add = (name, ok, details = {}) => {
  report.checks.push({ name, ok, ...details });
  if (!ok) report.errors.push({ name, ...details });
};
const safeName = (route) => route === '/' ? 'home' : route.replace(/^\/+|\/+$/g, '').replaceAll('/', '-');

const browser = await chromium.launch({ headless: true });
try {
  const readinessContext = await browser.newContext({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' });
  const readiness = await readinessContext.newPage();
  let ready = false;
  let readinessExcerpt = '';
  for (let attempt = 1; attempt <= 40; attempt += 1) {
    try {
      const response = await readiness.goto(`${BASE}/?qa_release=${Date.now()}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
      const state = await readiness.evaluate(() => ({ shell: document.documentElement.dataset.siteShell || '', text: document.body?.innerText || '' }));
      readinessExcerpt = state.text.slice(0, 350);
      if (response && response.status() < 400 && state.shell === 'native real-data' && /KIOS Aerial Landing Pad/i.test(state.text) && /422 REAL VIDEO FRAMES/i.test(state.text) && /30\.6%/.test(state.text)) {
        ready = true;
        break;
      }
    } catch {}
    await readiness.waitForTimeout(1500);
  }
  add('production-real-data-release-ready', ready, { excerpt: readinessExcerpt });
  await readinessContext.close();

  for (const vp of viewports) {
    const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, isMobile: !!vp.isMobile, hasTouch: !!vp.hasTouch, reducedMotion: 'reduce' });
    for (const route of routes) {
      const page = await context.newPage();
      const browserErrors = [];
      const failedRequests = [];
      page.on('pageerror', (error) => browserErrors.push(String(error?.message || error)));
      page.on('console', (message) => { if (message.type() === 'error') browserErrors.push(message.text()); });
      page.on('requestfailed', (request) => failedRequests.push({ url: request.url(), error: request.failure()?.errorText || 'requestfailed' }));

      let response;
      try {
        response = await page.goto(BASE + route, { waitUntil: 'domcontentloaded', timeout: 45000 });
        await page.waitForTimeout(650);
      } catch (error) {
        add(`${vp.name}-${route}-load`, false, { error: String(error) });
        await page.close();
        continue;
      }

      const status = response?.status() || 0;
      const state = await page.evaluate(() => ({
        overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        main: !!document.querySelector('main'),
        h1: document.querySelectorAll('h1').length,
        title: document.title,
        text: document.body?.innerText || '',
        brokenImages: [...document.images].filter((img) => img.complete && img.naturalWidth === 0).map((img) => img.currentSrc || img.src),
        missingHashTargets: [...document.querySelectorAll('a[href^="#"]')].map((a) => a.getAttribute('href')).filter((href) => href && href.length > 1 && !document.querySelector(href))
      }));

      add(`${vp.name}-${route}-status`, status >= 200 && status < 400, { status });
      add(`${vp.name}-${route}-semantic-shell`, state.main && state.h1 === 1, { main: state.main, h1: state.h1, title: state.title });
      add(`${vp.name}-${route}-no-horizontal-overflow`, state.overflowX <= 2, { overflowX: state.overflowX });
      add(`${vp.name}-${route}-images-load`, state.brokenImages.length === 0, { brokenImages: state.brokenImages });
      add(`${vp.name}-${route}-hash-targets`, state.missingHashTargets.length === 0, { missing: state.missingHashTargets });
      add(`${vp.name}-${route}-no-placeholder-text`, !/(^|\s)(undefined|null|\[object Object\])(\s|$)/i.test(state.text));

      const filteredErrors = browserErrors.filter((entry) => !/favicon|ERR_BLOCKED_BY_CLIENT/i.test(entry));
      const filteredRequests = failedRequests.filter((entry) => !/favicon|github\.com|linkedin\.com|zenodo\.org/i.test(entry.url));
      add(`${vp.name}-${route}-browser-clean`, filteredErrors.length === 0, { browserErrors: filteredErrors });
      add(`${vp.name}-${route}-network-clean`, filteredRequests.length === 0, { failedRequests: filteredRequests });

      if (screenshotRoutes.has(route)) {
        const file = path.join(OUT, 'screenshots', `${safeName(route)}-${vp.name}.png`);
        await page.screenshot({ path: file, fullPage: true });
        report.screenshots.push(file);
      }
      await page.close();
    }
    await context.close();
  }

  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
  const page = await context.newPage();
  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 45000 });
  const home = await page.evaluate(() => {
    const text = document.body?.innerText || '';
    return {
      shell: document.documentElement.dataset.siteShell || '',
      hasKios: /KIOS Aerial Landing Pad/i.test(text),
      has422: /422 REAL VIDEO FRAMES/i.test(text) && /422 \/ 422/.test(text),
      hasMetrics: /76\.8%/.test(text) && /30\.6%/.test(text) && /0\.2176/.test(text) && /0\.5146/.test(text),
      hasNoTuning: /No tuning/i.test(text) && /No retraining or tuning/i.test(text),
      hasRightsNote: /Why no raw frame gallery here\?/i.test(text),
      hasArchive: document.querySelectorAll('a[href="/phases/"]').length > 0,
      nasaHomePhotos: document.querySelectorAll('img[src^="/media/"]').length
    };
  });
  add('home-real-data-shell', home.shell === 'native real-data', home);
  add('home-kios-dataset-visible', home.hasKios && home.has422, home);
  add('home-real-metrics-visible', home.hasMetrics, home);
  add('home-frozen-transfer-protocol-visible', home.hasNoTuning, home);
  add('home-rights-boundary-visible', home.hasRightsNote, home);
  add('home-keeps-archive-linked', home.hasArchive, home);
  add('home-removes-editorial-nasa-hero', home.nasaHomePhotos === 0, home);

  await page.goto(BASE + '/phases/', { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(600);
  const archive = await page.evaluate(() => ({
    categories: document.querySelectorAll('.archive-category').length,
    allCards: document.querySelectorAll('.archive-card.phase-personalized').length,
    frozenCards: document.querySelectorAll('.archive-card[data-frozen="true"]').length,
    historicalCards: document.querySelectorAll('.archive-card[data-frozen="false"]').length,
    frozenPass: document.querySelectorAll('.archive-card[data-frozen="true"] .verdict-chip--pass').length,
    frozenFail: document.querySelectorAll('.archive-card[data-frozen="true"] .verdict-chip--fail').length,
    identities: document.querySelectorAll('.archive-card__identity').length,
    text: document.body?.innerText || ''
  }));
  add('archive-six-research-categories', archive.categories === 6, archive);
  add('archive-all-26-records', archive.allCards === 26, archive);
  add('archive-13-frozen-13-historical', archive.frozenCards === 13 && archive.historicalCards === 13, archive);
  add('archive-preserves-6-pass-7-fail', archive.frozenPass === 6 && archive.frozenFail === 7, archive);
  add('archive-personalizes-all-records', archive.identities === 26, archive);
  add('archive-preserves-detours-language', /keeps the detours, not just the wins/i.test(archive.text), archive);

  for (const slug of phaseSlugs) {
    await page.goto(`${BASE}/phases/${slug}/`, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(450);
    const snapshot = await page.evaluate(() => ({
      text: document.body?.innerText || '',
      h1: document.querySelector('h1')?.textContent || '',
      identity: document.querySelectorAll('.phase-identity-chip').length,
      role: document.querySelectorAll('.phase-role-card').length,
      category: document.body.dataset.phaseCategory || '',
      hashes: [...document.querySelectorAll('.phase-hash')].map((el) => el.textContent || '').join('\n')
    }));
    add(`${slug}-identity-present`, snapshot.h1.length > 0 && snapshot.identity === 1 && snapshot.role === 1, { h1: snapshot.h1 });
    add(`${slug}-category-bound`, snapshot.category.length > 0, { category: snapshot.category });
    if (frozenSlugs.has(slug)) add(`${slug}-frozen-boundary-visible`, /simulation-only research archive/i.test(snapshot.text) && /safety_acceptance=false/i.test(snapshot.text), { excerpt: snapshot.text.slice(-500) });
    if (slug === 'phase22') {
      add('phase22-result-sha-visible', snapshot.hashes.includes(PHASE22_RESULT), { hashes: snapshot.hashes });
      add('phase22-candidate-sha-visible', snapshot.hashes.includes(PHASE22_CANDIDATE), { hashes: snapshot.hashes });
      add('phase22-locked-result-visible', /10 \/ 10/i.test(snapshot.text) && /PASS/i.test(snapshot.text), { excerpt: snapshot.text.slice(0, 1200) });
    }
  }
  await context.close();
} finally {
  await browser.close();
}

report.finishedAt = new Date().toISOString();
report.passed = report.checks.filter((check) => check.ok).length;
report.failed = report.errors.length;
await fs.writeFile(path.join(OUT, 'production-ui-qa.json'), JSON.stringify(report, null, 2));
const summary = ['# AegisLand Production UI QA','',`- Base: ${BASE}`,`- Passed: ${report.passed}`,`- Failed: ${report.failed}`,`- Screenshots: ${report.screenshots.length}`,'',...report.errors.map((error) => `- FAIL — ${error.name}: ${JSON.stringify(error)}`)].join('\n');
await fs.writeFile(path.join(OUT, 'production-ui-qa.md'), summary);
console.log(summary);
if (report.failed > 0) process.exit(1);
