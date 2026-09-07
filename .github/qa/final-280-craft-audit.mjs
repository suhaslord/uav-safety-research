import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';

const BASE = process.env.QA_BASE_URL || 'http://127.0.0.1:4173';
const ROOT = path.join('qa-artifacts', 'final-280');
const SHOTS = path.join(ROOT, 'screenshots');

const phaseSlugs = [
  'phase1','phase2','phase3','phase4','phase5','phase6','phase6b','phase7','phase8','phase9','phase10','phase10r','phase11',
  'phase12','phase13a','phase13b','phase13c','phase14','phase15','phase16','phase17','phase18','phase19','phase20','phase21','phase22'
];
const routes = ['/', '/phases/', ...phaseSlugs.map((slug) => `/phases/${slug}/`)];
const viewports = [
  { name: 'phone-320', width: 320, height: 568, mobile: true },
  { name: 'phone-360', width: 360, height: 800, mobile: true },
  { name: 'phone-390', width: 390, height: 844, mobile: true },
  { name: 'phone-430', width: 430, height: 932, mobile: true },
  { name: 'tablet-768', width: 768, height: 1024 },
  { name: 'tablet-820', width: 820, height: 1180 },
  { name: 'landscape-1024', width: 1024, height: 768 },
  { name: 'desktop-1280', width: 1280, height: 800 },
  { name: 'desktop-1440', width: 1440, height: 1000 },
  { name: 'desktop-1920', width: 1920, height: 1080 }
];

await fs.rm(ROOT, { recursive: true, force: true });
await fs.mkdir(SHOTS, { recursive: true });

const blockers = [];
const warnings = [];
const pages = [];
const gateFailures = new Map();
const gate = (name, ok, details) => {
  if (!ok) {
    const arr = gateFailures.get(name) || [];
    arr.push(details);
    gateFailures.set(name, arr);
  }
};
const addBlocker = (pageKey, kind, details = {}) => blockers.push({ pageKey, kind, ...details });
const addWarning = (pageKey, kind, details = {}) => warnings.push({ pageKey, kind, ...details });
const safeName = (route) => route === '/' ? 'home' : route.replace(/^\/+|\/+$/g, '').replaceAll('/', '-');

const browser = await chromium.launch({ headless: true });
try {
  for (const vp of viewports) {
    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
      isMobile: !!vp.mobile,
      hasTouch: !!vp.mobile,
      reducedMotion: 'reduce',
      deviceScaleFactor: 1
    });

    for (const route of routes) {
      const page = await context.newPage();
      const pageKey = `${vp.name}:${route}`;
      const browserErrors = [];
      const failedRequests = [];
      page.on('pageerror', (error) => browserErrors.push(String(error?.message || error)));
      page.on('console', (message) => { if (message.type() === 'error') browserErrors.push(message.text()); });
      page.on('requestfailed', (request) => failedRequests.push({ url: request.url(), error: request.failure()?.errorText || 'requestfailed' }));

      let response = null;
      try {
        response = await page.goto(`${BASE}${route}?final_280_craft=1`, { waitUntil: 'domcontentloaded', timeout: 45000 });
        await page.waitForTimeout(450);
      } catch (error) {
        addBlocker(pageKey, 'load-failed', { error: String(error) });
      }

      // Settle lazy editorial media while returning to the top for consistent geometry.
      const imageCount = await page.locator('img').count().catch(() => 0);
      for (let i = 0; i < imageCount; i += 1) await page.locator('img').nth(i).scrollIntoViewIfNeeded().catch(() => {});
      await page.waitForTimeout(120);
      await page.evaluate(async () => {
        await Promise.all([...document.images].map((img) => img.decode?.().catch(() => undefined)));
        scrollTo(0, 0);
      }).catch(() => {});
      await page.waitForTimeout(80);

      const metrics = await page.evaluate(({ route, width, mobile }) => {
        const root = document.documentElement;
        const visible = (el) => {
          if (!el) return false;
          const s = getComputedStyle(el);
          const r = el.getBoundingClientRect();
          return s.display !== 'none' && s.visibility !== 'hidden' && Number(s.opacity || 1) > 0 && r.width > 0 && r.height > 0;
        };
        const rect = (el) => {
          if (!el) return null;
          const r = el.getBoundingClientRect();
          return { x:r.x, y:r.y, width:r.width, height:r.height, right:r.right, bottom:r.bottom };
        };
        const overlapArea = (a, b) => {
          if (!a || !b) return 0;
          const x = Math.max(0, Math.min(a.right, b.right) - Math.max(a.x, b.x));
          const y = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.y, b.y));
          return x * y;
        };
        const main = document.querySelector('main');
        const h1 = document.querySelector('main h1');
        const header = document.querySelector('body > header, .signature-nav, .site-header, .top');
        const phasePage = /^\/phases\/phase/i.test(route);
        const archivePage = route === '/phases/';
        const theme = document.querySelector('meta[name="theme-color"]')?.getAttribute('content') || '';
        const bodyBg = getComputedStyle(document.body).backgroundColor;
        const h1Style = h1 ? getComputedStyle(h1) : null;
        const bodyTextCandidates = [...document.querySelectorAll('main p, main li, main dd, main dt, main figcaption')].filter(visible);
        const minBodyFont = bodyTextCandidates.length ? Math.min(...bodyTextCandidates.map((el) => parseFloat(getComputedStyle(el).fontSize || '0')).filter((n) => n > 0)) : 999;
        const tinyText = [...document.querySelectorAll('main p,main li,main a,main button,main span,main small,main figcaption,main dd,main dt')]
          .filter(visible)
          .map((el) => ({ text:(el.textContent || '').trim().slice(0,72), size:parseFloat(getComputedStyle(el).fontSize || '0') }))
          .filter((item) => item.text && item.size > 0 && item.size < 11);
        const clickables = [...document.querySelectorAll('a,button,input,select,textarea,[role="button"]')].filter(visible);
        const tinyTargets = clickables.map((el) => ({ text:(el.getAttribute('aria-label') || el.textContent || '').trim().slice(0,72), r:rect(el) }))
          .filter((item) => item.r && (item.r.width < 40 || item.r.height < 40));
        const brokenImages = [...document.images].filter((img) => !img.complete || img.naturalWidth === 0).map((img) => img.currentSrc || img.src);
        const missingAlt = [...document.images].filter((img) => !img.hasAttribute('alt')).map((img) => img.currentSrc || img.src);
        const phaseChip = document.querySelector('.phase-identity-chip');
        const roleCard = document.querySelector('.phase-role-card');
        const editorial = document.querySelector('.phase-editorial-photo, [data-editorial-photo]');
        const consistency = document.querySelector('link[data-aegis-phase-ui-consistency]');
        const legacyCopy = document.querySelector('.scene-hero .hero-copy');
        const legacyScene = document.querySelector('.scene-hero .hero-scene');
        const frozenHero = document.querySelector('.phase-detail__hero');
        const frozenVerdict = document.querySelector('.phase-detail__hero .phase-verdict-panel');
        const frozenCopy = frozenHero?.firstElementChild || null;
        const navR = rect(header);
        // Fixed/sticky headers legitimately sit over a hero section's background and padding.
        // The real regression is overlap with the first meaningful hero content, not the
        // section box itself. Prefer the phase identity chip when present, otherwise the h1.
        const heroR = rect(phaseChip || h1);
        const sceneR = rect(legacyScene);
        const copyR = rect(legacyCopy);
        const frozenVerdictR = rect(frozenVerdict);
        const frozenCopyR = rect(frozenCopy);
        const clippedText = [...document.querySelectorAll('main h1,main h2,main h3,main p,main strong,main span,main a,main button')]
          .filter(visible)
          .filter((el) => {
            const s = getComputedStyle(el);
            if (!['hidden','clip'].includes(s.overflow) && !['hidden','clip'].includes(s.overflowX) && !['hidden','clip'].includes(s.overflowY)) return false;
            return el.scrollWidth > el.clientWidth + 2 || el.scrollHeight > el.clientHeight + 2;
          })
          .map((el) => ({ tag:el.tagName, text:(el.textContent || '').trim().slice(0,72), client:[el.clientWidth,el.clientHeight], scroll:[el.scrollWidth,el.scrollHeight] }));
        const archiveToolbar = document.querySelector('.archive-toolbar');
        const archiveCards = [...document.querySelectorAll('.archive-card.phase-personalized')];
        const archiveCardOverflow = archiveCards.filter((el) => el.scrollWidth > el.clientWidth + 2).length;
        const roleR = rect(roleCard);
        return {
          width,
          mobile,
          title:document.title,
          main:!!main,
          h1Count:document.querySelectorAll('h1').length,
          h1Font:h1Style ? parseFloat(h1Style.fontSize || '0') : 0,
          minBodyFont,
          scrollWidth:root.scrollWidth,
          clientWidth:root.clientWidth,
          overflowX:root.scrollWidth-root.clientWidth,
          theme,
          bodyBg,
          phasePage,
          archivePage,
          bodyPhase:document.body.dataset.phase || '',
          bodyCategory:document.body.dataset.phaseCategory || '',
          phaseChip:visible(phaseChip),
          roleCard:visible(roleCard),
          roleR,
          editorial:visible(editorial),
          consistency:!!consistency,
          brokenImages,
          missingAlt,
          tinyText,
          tinyTargets,
          clippedText,
          navR,
          heroR,
          navHeroOverlap:overlapArea(navR, heroR),
          legacyOverlap:width > 980 ? overlapArea(copyR, sceneR) : 0,
          frozenOverlap:width > 1040 ? overlapArea(frozenCopyR, frozenVerdictR) : 0,
          archiveToolbar:visible(archiveToolbar),
          archiveCardCount:archiveCards.length,
          archiveCardOverflow
        };
      }, { route, width: vp.width, mobile: !!vp.mobile }).catch(() => null);

      const status = response?.status() || 0;
      const cleanErrors = browserErrors.filter((entry) => !/favicon|ERR_BLOCKED_BY_CLIENT/i.test(entry));
      const cleanRequests = failedRequests.filter((entry) => !/favicon|github\.com|linkedin\.com/i.test(entry.url));

      if (!status || status >= 400) addBlocker(pageKey, 'http', { status });
      if (!metrics) addBlocker(pageKey, 'metrics-unavailable');
      else {
        if (!metrics.main || metrics.h1Count !== 1) addBlocker(pageKey, 'semantic-shell', { main:metrics.main, h1Count:metrics.h1Count });
        if (metrics.overflowX > 2) addBlocker(pageKey, 'horizontal-overflow', { overflowX:metrics.overflowX });
        if (metrics.brokenImages.length) addBlocker(pageKey, 'broken-images', { images:metrics.brokenImages });
        if (metrics.missingAlt.length) addBlocker(pageKey, 'missing-alt', { images:metrics.missingAlt });
        if (metrics.tinyText.length) addWarning(pageKey, 'tiny-text', { examples:metrics.tinyText.slice(0,6) });
        if (vp.mobile && metrics.tinyTargets.length) addWarning(pageKey, 'small-touch-targets', { examples:metrics.tinyTargets.slice(0,6) });
        if (metrics.clippedText.length) addWarning(pageKey, 'clipped-text', { examples:metrics.clippedText.slice(0,6) });
        if (metrics.navHeroOverlap > 2) addBlocker(pageKey, 'header-content-overlap', { area:metrics.navHeroOverlap });
        if (metrics.legacyOverlap > 4) addBlocker(pageKey, 'legacy-hero-column-overlap', { area:metrics.legacyOverlap });
        if (metrics.frozenOverlap > 4) addBlocker(pageKey, 'frozen-hero-column-overlap', { area:metrics.frozenOverlap });
        if (metrics.phasePage && (!metrics.phaseChip || !metrics.roleCard || !metrics.bodyCategory || !metrics.editorial || !metrics.consistency)) {
          addBlocker(pageKey, 'phase-system-missing', { chip:metrics.phaseChip, role:metrics.roleCard, category:metrics.bodyCategory, editorial:metrics.editorial, consistency:metrics.consistency });
        }
        if (metrics.archivePage && (!metrics.archiveToolbar || metrics.archiveCardCount !== 26 || metrics.archiveCardOverflow)) {
          addBlocker(pageKey, 'archive-integrity', { toolbar:metrics.archiveToolbar, cards:metrics.archiveCardCount, overflow:metrics.archiveCardOverflow });
        }
        if (metrics.h1Font < (vp.width <= 430 ? 30 : 34)) addWarning(pageKey, 'weak-h1-scale', { h1Font:metrics.h1Font });
      }
      if (cleanErrors.length) addBlocker(pageKey, 'browser-errors', { errors:cleanErrors.slice(0,6) });
      if (cleanRequests.length) addBlocker(pageKey, 'network-failures', { requests:cleanRequests.slice(0,6) });

      const file = path.join(SHOTS, `${safeName(route)}-${vp.name}.png`);
      await page.screenshot({ path:file, fullPage:true });
      pages.push({ pageKey, route, viewport:vp, status, metrics, browserErrors:cleanErrors, failedRequests:cleanRequests, screenshot:file });
      await page.close();
    }
    await context.close();
  }
} finally {
  await browser.close();
}

// Ten explicit craft gates. A 10/10 requires every gate and zero warnings/blockers.
const all = (fn) => pages.every((page) => page.metrics && fn(page));
gate('1 Routing + semantics', blockers.every((b) => !['http','load-failed','semantic-shell','metrics-unavailable'].includes(b.kind)), blockers.filter((b) => ['http','load-failed','semantic-shell','metrics-unavailable'].includes(b.kind)));
gate('2 Responsive geometry', all((p) => p.metrics.overflowX <= 2) && !blockers.some((b) => /overlap/.test(b.kind)), blockers.filter((b) => b.kind.includes('overflow') || b.kind.includes('overlap')));
gate('3 Type hierarchy', !warnings.some((w) => ['tiny-text','weak-h1-scale'].includes(w.kind)), warnings.filter((w) => ['tiny-text','weak-h1-scale'].includes(w.kind)));
gate('4 Touch + focus scale', !warnings.some((w) => w.kind === 'small-touch-targets'), warnings.filter((w) => w.kind === 'small-touch-targets'));
gate('5 No clipped copy', !warnings.some((w) => w.kind === 'clipped-text'), warnings.filter((w) => w.kind === 'clipped-text'));
gate('6 Phase personalization', !blockers.some((b) => b.kind === 'phase-system-missing'), blockers.filter((b) => b.kind === 'phase-system-missing'));
gate('7 Archive taxonomy', !blockers.some((b) => b.kind === 'archive-integrity'), blockers.filter((b) => b.kind === 'archive-integrity'));
gate('8 Editorial media', !blockers.some((b) => ['broken-images','missing-alt'].includes(b.kind)), blockers.filter((b) => ['broken-images','missing-alt'].includes(b.kind)));
gate('9 Browser + network cleanliness', !blockers.some((b) => ['browser-errors','network-failures'].includes(b.kind)), blockers.filter((b) => ['browser-errors','network-failures'].includes(b.kind)));
gate('10 Light research-system consistency', all((p) => (!p.metrics.phasePage && !p.metrics.archivePage) || p.metrics.consistency), pages.filter((p) => (p.metrics?.phasePage || p.metrics?.archivePage) && !p.metrics?.consistency).map((p) => p.pageKey));

const gates = [
  '1 Routing + semantics','2 Responsive geometry','3 Type hierarchy','4 Touch + focus scale','5 No clipped copy',
  '6 Phase personalization','7 Archive taxonomy','8 Editorial media','9 Browser + network cleanliness','10 Light research-system consistency'
].map((name) => ({ name, pass:!gateFailures.has(name), failures:gateFailures.get(name) || [] }));
const score = gates.filter((g) => g.pass).length;
const report = {
  base:BASE,
  startedAt:pages[0]?.startedAt,
  finishedAt:new Date().toISOString(),
  routes:routes.length,
  viewports:viewports.length,
  expectedScreenshots:routes.length*viewports.length,
  screenshots:pages.length,
  score,
  scoreOutOf:10,
  gates,
  blockers,
  warnings,
  pages
};
await fs.writeFile(path.join(ROOT, 'report.json'), JSON.stringify(report, null, 2));
const summary = [
  '# AegisLand Final 280-Screenshot Craft Audit',
  '',
  `- Base: ${BASE}`,
  `- Routes: ${routes.length}`,
  `- Viewports: ${viewports.length}`,
  `- Screenshots: ${pages.length}/${routes.length*viewports.length}`,
  `- Craft gates: ${score}/10`,
  `- Blockers: ${blockers.length}`,
  `- Warnings: ${warnings.length}`,
  '',
  '## Gates',
  ...gates.map((g) => `- ${g.pass ? 'PASS' : 'FAIL'} — ${g.name}`),
  '',
  '## Blockers',
  ...(blockers.length ? blockers.map((b) => `- ${b.pageKey} — ${b.kind}`) : ['- None']),
  '',
  '## Warnings',
  ...(warnings.length ? warnings.map((w) => `- ${w.pageKey} — ${w.kind}`) : ['- None'])
].join('\n');
await fs.writeFile(path.join(ROOT, 'summary.md'), summary);
console.log(summary);
if (pages.length !== routes.length*viewports.length || blockers.length || warnings.length || score !== 10) process.exit(1);
