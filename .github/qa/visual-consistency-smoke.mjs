import { chromium } from 'playwright';

const BASE = process.env.QA_BASE_URL || 'http://127.0.0.1:4173';
const results = [];
let failed = 0;
const add = (name, ok, details = {}) => { results.push({ name, ok, ...details }); if (!ok) failed++; };

const routes = [
  '/', '/phases/', '/phases/phase1/', '/phases/phase2/', '/phases/phase3/',
  '/phases/phase4/', '/phases/phase5/', '/phases/phase6/', '/phases/phase6b/',
  '/phases/phase7/', '/phases/phase8/', '/phases/phase9/', '/phases/phase10/',
  '/phases/phase10r/', '/phases/phase11/'
];

const browser = await chromium.launch({ headless: true });
try {
  for (const viewport of [
    { name: 'desktop', width: 1440, height: 1000 },
    { name: 'tablet', width: 820, height: 1180 }
  ]) {
    const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height }, reducedMotion: 'reduce' });
    for (const route of routes) {
      const page = await context.newPage();
      const browserErrors = [];
      page.on('pageerror', error => browserErrors.push(String(error?.message || error)));
      page.on('console', message => { if (message.type() === 'error') browserErrors.push(message.text()); });

      const response = await page.goto(BASE + route, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await page.waitForTimeout(800);
      add(`${viewport.name}-${route}-status`, !!response && response.status() >= 200 && response.status() < 400, { status: response?.status() || 0 });

      const state = await page.evaluate(() => ({
        overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        main: !!document.querySelector('main'),
        h1: document.querySelectorAll('h1').length
      }));
      add(`${viewport.name}-${route}-no-horizontal-overflow`, state.overflow <= 1, { overflow: state.overflow });
      add(`${viewport.name}-${route}-semantic-shell`, state.main && state.h1 >= 1, { main: state.main, h1: state.h1 });
      add(`${viewport.name}-${route}-browser-clean`, browserErrors.length === 0, { browserErrors });
      await page.close();
    }
    await context.close();
  }

  {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
    const page = await context.newPage();
    await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(300);

    const shell = await page.evaluate(() => document.documentElement.dataset.siteShell || '');
    add('home-native-static-shell', shell === 'native', { shell });
    const railCount = await page.locator('#homeModelRail .home-rail-step').count();
    add('home-has-complete-phase-rail', railCount === 13, { railCount });
    const current = await page.locator('#homeModelRail .home-rail-step.active[href="/phases/phase11/"]').count();
    add('home-phase11-is-current-frontier', current === 1, { current });
    const hero = await page.locator('.hero').evaluate(el => { const r = el.getBoundingClientRect(); return { height: Math.round(r.height), width: Math.round(r.width) }; });
    add('home-hero-is-contained', hero.height >= 600 && hero.height <= 940, { hero });
    const statusText = await page.locator('.result-card').innerText();
    add(
      'home-keeps-failed-gate-visible',
      /1 locked component failed/i.test(statusText) && /2\.435/.test(statusText) && /2\.25/.test(statusText) && /mixed \/ failed overall/i.test(statusText),
      { statusText: statusText.slice(0, 300) }
    );
    const desktopMenu = await page.locator('.mobile-menu-toggle').evaluate(el => ({ display: getComputedStyle(el).display, width: el.getBoundingClientRect().width }));
    add('home-desktop-mobile-menu-hidden', desktopMenu.display === 'none' && desktopMenu.width === 0, { desktopMenu });
    await page.close();
    await context.close();
  }

  {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, reducedMotion: 'reduce' });
    const page = await context.newPage();
    await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(300);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    add('mobile-home-no-horizontal-overflow', overflow <= 1, { overflow });
    const menu = await page.locator('.mobile-menu-toggle').evaluate(el => { const r = el.getBoundingClientRect(); return { display: getComputedStyle(el).display, width: Math.round(r.width), height: Math.round(r.height) }; });
    add('mobile-home-menu-is-visible-and-touchable', menu.display !== 'none' && menu.width >= 44 && menu.height >= 40, { menu });
    const railCount = await page.locator('#homeModelRail .home-rail-step').count();
    add('mobile-home-keeps-complete-phase-rail', railCount === 13, { railCount });
    const ctas = await page.locator('.hero .button').evaluateAll(els => els.map(el => Math.round(el.getBoundingClientRect().height)));
    add('mobile-home-ctas-touchable', ctas.length === 2 && ctas.every(height => height >= 42), { ctas });
    await page.close();
    await context.close();
  }

  {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
    const page = await context.newPage();
    await page.goto(BASE + '/phases/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(500);
    const phase11Heading = await page.locator('#phase11ArchiveEra h2').textContent().catch(() => '');
    add('archive-phase11-era-present', /phase 11 p14r/i.test(phase11Heading || ''), { phase11Heading });
    const oldCurrent = await page.locator('#archiveMap .era').filter({ has: page.locator('h2', { hasText: /^Current frontier$/ }) }).count();
    add('archive-no-stale-current-frontier', oldCurrent === 0, { oldCurrent });
    const frozen = await page.locator('#archiveMap .era h2').filter({ hasText: 'Frozen predecessor' }).count();
    add('archive-phase10r-is-frozen-predecessor', frozen >= 1, { frozen });

    await page.goto(BASE + '/phases/phase10r/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(500);
    const heroText = await page.locator('#phaseHero').innerText().catch(() => '');
    add('phase10r-no-latest-frontier-label', !/latest published frontier/i.test(heroText), { heroExcerpt: heroText.slice(0, 240) });
    add('phase10r-frozen-predecessor-label', /frozen predecessor/i.test(heroText), { heroExcerpt: heroText.slice(0, 240) });
    const phase11Rail = await page.locator('#phaseRail a[href="/phases/phase11/"]').count();
    add('phase10r-rail-links-to-phase11', phase11Rail === 1, { phase11Rail });

    await page.goto(BASE + '/phases/phase10/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(500);
    const nextLabel = await page.locator('#nextPhase span').first().textContent().catch(() => '');
    add('phase10-next-link-not-stale-frontier', /next phase/i.test(nextLabel || ''), { nextLabel });

    await page.goto(BASE + '/phases/phase11/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(300);
    const header = await page.locator('.site-header').evaluate(el => { const s = getComputedStyle(el); const r = el.getBoundingClientRect(); return { display: s.display, position: s.position, height: Math.round(r.height) }; });
    add('phase11-uses-cockpit-header-scale', header.display === 'grid' && header.position === 'fixed' && header.height === 56, { header });
    const navLabels = await page.locator('.site-nav a').allTextContents();
    add('phase11-nav-is-stable', JSON.stringify(navLabels) === JSON.stringify(['Result','Evidence','Boundary','Provenance']), { navLabels });
    const sectionHeights = await page.locator('main > section').evaluateAll(els => els.map(el => Math.round(el.getBoundingClientRect().height)));
    add('phase11-no-empty-viewport-panels', sectionHeights.every(height => height < 1000), { sectionHeights });
    const boundaryText = await page.locator('#boundary').innerText();
    add('phase11-protected-boundary-is-explicit', /2\.435/.test(boundaryText) && /2\.25/.test(boundaryText) && /not exposed/i.test(boundaryText), { boundaryExcerpt: boundaryText.slice(0, 320) });
    await page.close();
    await context.close();
  }

  {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, reducedMotion: 'reduce' });
    const page = await context.newPage();
    await page.goto(BASE + '/phases/phase11/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(300);
    const mobileHeader = await page.locator('.site-header').evaluate(el => { const r = el.getBoundingClientRect(); return { display: getComputedStyle(el).display, height: Math.round(r.height), overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth }; });
    add('phase11-mobile-header-clean', mobileHeader.display === 'grid' && mobileHeader.height === 52 && mobileHeader.overflow <= 1, { mobileHeader });
    const menu = await page.locator('#mobileMenuToggle').evaluate(el => ({ display: getComputedStyle(el).display, width: Math.round(el.getBoundingClientRect().width), height: Math.round(el.getBoundingClientRect().height) }));
    add('phase11-mobile-menu-is-touchable', ['flex','inline-flex'].includes(menu.display) && menu.width >= 58 && menu.width < 110 && menu.height >= 40, { menu });
    await page.close();
    await context.close();
  }
} finally {
  await browser.close();
}

console.log(JSON.stringify({ base: BASE, passed: results.filter(result => result.ok).length, failed, results }, null, 2));
if (failed) process.exitCode = 1;
