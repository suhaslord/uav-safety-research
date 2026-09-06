import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';

const BASE = process.env.QA_BASE_URL || 'https://aegisland-research-cockpit.vercel.app';
const OUT = 'qa-artifacts';
const FROZEN_HEAD = '668d065714dde279857bc0e196f0ef7cc5e182ed';
const PHASE22_RESULT = '0ddc968b8bd48c2de6d904194b417854913389a8927cff0b15b96c6501f8294c';
const PHASE22_CANDIDATE = '62e75d7b39088c2e66f1cc6be4d180501b79632f2f6847af1fbe0bd96be17551';

const legacyRoutes = [
  '/phases/phase1/', '/phases/phase2/', '/phases/phase3/', '/phases/phase4/',
  '/phases/phase5/', '/phases/phase6/', '/phases/phase6b/', '/phases/phase7/',
  '/phases/phase8/', '/phases/phase9/', '/phases/phase10/', '/phases/phase10r/',
  '/phases/phase11/'
];
const frozenSlugs = [
  'phase12', 'phase13a', 'phase13b', 'phase13c', 'phase14', 'phase15',
  'phase16', 'phase17', 'phase18', 'phase19', 'phase20', 'phase21', 'phase22'
];
const frozenRoutes = frozenSlugs.map((slug) => `/phases/${slug}/`);
const routes = ['/', '/phases/', ...legacyRoutes, ...frozenRoutes];
const viewports = [
  { name: 'desktop', width: 1440, height: 1000 },
  { name: 'tablet', width: 820, height: 1180 },
  { name: 'mobile', width: 390, height: 844, isMobile: true, hasTouch: true }
];
const screenshotRoutes = new Set(['/', '/phases/', '/phases/phase13a/', '/phases/phase18/', '/phases/phase22/']);
const report = { base: BASE, startedAt: new Date().toISOString(), checks: [], errors: [], warnings: [], screenshots: [] };

await fs.rm(OUT, { recursive: true, force: true });
await fs.mkdir(path.join(OUT, 'screenshots'), { recursive: true });

const add = (name, ok, details = {}) => {
  report.checks.push({ name, ok, ...details });
  if (!ok) report.errors.push({ name, ...details });
};
const safeName = (route) => route === '/' ? 'home' : route.replace(/^\/+|\/+$/g, '').replaceAll('/', '-');

const browser = await chromium.launch({ headless: true });
try {
  // Production UI QA can race the deploy workflow on a main push. Wait until the
  // public alias exposes the frozen archive identity before evaluating the page set.
  const readinessContext = await browser.newContext({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' });
  const readiness = await readinessContext.newPage();
  let ready = false;
  let readinessExcerpt = '';
  for (let attempt = 1; attempt <= 20; attempt++) {
    try {
      const response = await readiness.goto(`${BASE}/?qa_release=${Date.now()}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await readiness.waitForTimeout(500);
      const state = await readiness.evaluate(() => ({
        shell: document.documentElement.dataset.siteShell || '',
        text: document.body?.innerText || '',
        head: document.querySelector('.signature-section__intro code')?.textContent || ''
      }));
      readinessExcerpt = state.text.slice(0, 300);
      if (response && response.status() < 400 && state.shell === 'native frozen-archive' && state.head === FROZEN_HEAD && /Frozen through Phase 22/i.test(state.text)) {
        ready = true;
        break;
      }
    } catch {}
    await readiness.waitForTimeout(1500);
  }
  add('production-frozen-release-ready', ready, { frozenHead: FROZEN_HEAD, excerpt: readinessExcerpt });
  await readiness.close();
  await readinessContext.close();

  for (const vp of viewports) {
    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
      isMobile: !!vp.isMobile,
      hasTouch: !!vp.hasTouch,
      reducedMotion: 'reduce'
    });

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
      add(`${vp.name}-${route}-status`, status >= 200 && status < 400, { status });

      const state = await page.evaluate(() => {
        const root = document.documentElement;
        const bodyText = document.body?.innerText || '';
        return {
          overflowX: root.scrollWidth - root.clientWidth,
          main: !!document.querySelector('main'),
          h1: document.querySelectorAll('h1').length,
          text: bodyText,
          title: document.title,
          shell: root.dataset.siteShell || '',
          brokenImages: [...document.images].filter((img) => !img.complete || img.naturalWidth === 0).map((img) => img.currentSrc || img.src),
          missingHashTargets: [...document.querySelectorAll('a[href^="#"]')]
            .map((a) => a.getAttribute('href'))
            .filter((href) => href && href.length > 1 && !document.querySelector(href))
        };
      });

      add(`${vp.name}-${route}-semantic-shell`, state.main && state.h1 >= 1, { main: state.main, h1: state.h1, title: state.title });
      add(`${vp.name}-${route}-no-horizontal-overflow`, state.overflowX <= 2, { overflowX: state.overflowX });
      add(`${vp.name}-${route}-images-load`, state.brokenImages.length === 0, { brokenImages: state.brokenImages });
      add(`${vp.name}-${route}-hash-targets`, state.missingHashTargets.length === 0, { missing: state.missingHashTargets });
      add(`${vp.name}-${route}-no-placeholder-text`, !/(^|\s)(undefined|null|\[object Object\])(\s|$)/i.test(state.text));

      const filteredErrors = browserErrors.filter((entry) => !/favicon|ERR_BLOCKED_BY_CLIENT/i.test(entry));
      const filteredRequests = failedRequests.filter((entry) => !/favicon|github\.com|linkedin\.com/i.test(entry.url));
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
  await page.waitForTimeout(700);
  const home = await page.evaluate(({ resultSha, candidateSha, frozenHead }) => {
    const data = window.AEGIS_FROZEN_LINEAGE;
    const text = document.body?.innerText || '';
    return {
      shell: document.documentElement.dataset.siteShell || '',
      halo: document.querySelectorAll('.aegis-halo').length,
      evidenceRows: document.querySelectorAll('#evidenceSpine .evidence-row').length,
      passRows: document.querySelectorAll('#evidenceSpine .evidence-row[data-verdict="PASS"]').length,
      failRows: document.querySelectorAll('#evidenceSpine .evidence-row[data-verdict="FAIL"]').length,
      noPhase23Link: document.querySelectorAll('a[href*="phase23"]').length === 0,
      hasBoundary: text.includes('simulation_only=true') && text.includes('safety_acceptance=false') && text.includes('controller_tuning_allowed=false'),
      hasFinalMetrics: text.includes('0.8319') && text.includes('0.7744') && text.includes('100%'),
      saysFrozen: /Frozen through Phase 22/i.test(text) && /No Phase 23 is implied or authorized/i.test(text),
      dataOk: !!data && data.frozenThrough === 'Phase 22' && data.phases.length === 13 && data.counts.PASS === 6 && data.counts.FAIL === 7 && data.frozenScientificHead === frozenHead && data.bySlug.phase22.resultSha === resultSha && data.bySlug.phase22.candidateSha === candidateSha
    };
  }, { resultSha: PHASE22_RESULT, candidateSha: PHASE22_CANDIDATE, frozenHead: FROZEN_HEAD });
  add('home-native-frozen-shell', home.shell === 'native frozen-archive', home);
  add('home-aegis-halo', home.halo === 1, home);
  add('home-13-record-spine', home.evidenceRows === 13, home);
  add('home-preserves-6-pass-7-fail', home.passRows === 6 && home.failRows === 7, home);
  add('home-frozen-lineage-identity', home.dataOk, home);
  add('home-final-metrics-visible', home.hasFinalMetrics, home);
  add('home-claim-boundary-visible', home.hasBoundary, home);
  add('home-no-phase23', home.noPhase23Link && home.saysFrozen, home);

  const inspectArchive = page.getByRole('link', { name: /inspect every phase/i }).first();
  add('home-archive-cta-exists', await inspectArchive.count() === 1);
  if (await inspectArchive.count()) {
    await inspectArchive.click();
    await page.waitForTimeout(500);
    add('home-archive-cta-routes', /\/phases\/?$/.test(new URL(page.url()).pathname), { url: page.url() });
  }

  await page.goto(BASE + '/phases/', { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(650);
  const archive = await page.evaluate(() => ({
    frozenCards: document.querySelectorAll('#frozenCards .archive-card').length,
    legacyCards: document.querySelectorAll('#legacyCards .archive-card').length,
    text: document.body?.innerText || ''
  }));
  add('archive-13-frozen-records', archive.frozenCards === 13, archive);
  add('archive-13-foundational-records', archive.legacyCards === 13, archive);
  add('archive-nothing-rewritten', /Every frozen phase/i.test(archive.text) && /Nothing rewritten/i.test(archive.text), archive);

  const expectedVerdicts = { phase12: 'PASS', phase13a: 'FAIL', phase18: 'FAIL', phase22: 'PASS' };
  for (const [slug, verdict] of Object.entries(expectedVerdicts)) {
    await page.goto(`${BASE}/phases/${slug}/`, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(500);
    const snapshot = await page.evaluate(() => ({
      text: document.body?.innerText || '',
      phaseContent: !!document.querySelector('#phaseContent'),
      hashText: [...document.querySelectorAll('.phase-hash')].map((el) => el.textContent || '').join('\n')
    }));
    add(`${slug}-shared-frozen-detail`, snapshot.phaseContent, snapshot);
    add(`${slug}-locked-${verdict.toLowerCase()}`, new RegExp(`LOCKED VERDICT\\s+${verdict}`, 'i').test(snapshot.text), { excerpt: snapshot.text.slice(0, 400) });
    add(`${slug}-boundary-visible`, /Synthetic, frozen simulation evidence only/i.test(snapshot.text), { excerpt: snapshot.text.slice(0, 500) });
    if (slug === 'phase22') {
      add('phase22-sealed-result-sha-visible', snapshot.hashText.includes(PHASE22_RESULT), { hashText: snapshot.hashText });
      add('phase22-sealed-candidate-sha-visible', snapshot.hashText.includes(PHASE22_CANDIDATE), { hashText: snapshot.hashText });
      add('phase22-final-r2-visible', snapshot.text.includes('0.8319') && snapshot.text.includes('0.7744'), { excerpt: snapshot.text.slice(0, 650) });
    }
  }

  await page.goto(BASE + '/phases/phase11/', { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(500);
  const phase11Text = await page.locator('body').innerText();
  add('phase11-predecessor-reachable', /Phase 11 P14R/i.test(phase11Text));
  add('phase11-failure-remains-visible', /2\.435/.test(phase11Text) && /2\.25/.test(phase11Text) && /not exposed/i.test(phase11Text), { excerpt: phase11Text.slice(0, 700) });

  await page.close();
  await context.close();
} finally {
  await browser.close();
}

report.finishedAt = new Date().toISOString();
report.failedChecks = report.checks.filter((check) => !check.ok).length;
report.passedChecks = report.checks.filter((check) => check.ok).length;
await fs.writeFile(path.join(OUT, 'production-ui-report.json'), JSON.stringify(report, null, 2));
const summary = [
  '# AegisLand Production UI QA',
  '',
  `- Base: ${BASE}`,
  `- Passed: ${report.passedChecks}`,
  `- Failed: ${report.failedChecks}`,
  `- Screenshots: ${report.screenshots.length}`,
  '',
  ...report.errors.map((error) => `- FAIL — ${error.name}: ${JSON.stringify(error)}`)
].join('\n');
await fs.writeFile(path.join(OUT, 'summary.md'), summary);
console.log(summary);
if (report.failedChecks > 0) process.exitCode = 1;
