import { chromium } from 'playwright';

const BASE = process.env.QA_BASE_URL || 'http://127.0.0.1:4173';
const results = [];
let failed = 0;
const add = (name, ok, details = {}) => { results.push({ name, ok, ...details }); if (!ok) failed++; };

const browser = await chromium.launch({ headless: true });
try {
  for (const viewport of [{name:'desktop',width:1440,height:1000},{name:'tablet',width:820,height:1180}]) {
    const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height }, reducedMotion: 'reduce' });
    for (const route of ['/', '/phases/', '/phases/phase10r/']) {
      const page = await context.newPage();
      await page.goto(BASE + route, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await page.waitForTimeout(1800);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      add(`${viewport.name}-${route}-no-horizontal-overflow`, overflow <= 1, { overflow });
      const visibleToggle = await page.locator('.mobile-menu-toggle:visible,.archive-menu-toggle:visible').count();
      add(`${viewport.name}-${route}-mobile-menu-hidden`, visibleToggle === 0, { visibleToggle });
      await page.close();
    }
    await context.close();
  }

  {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
    const page = await context.newPage();
    await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(1800);
    const duplicateSummaryVisible = await page.locator('#phase11Summary:visible').count();
    add('home-no-duplicate-phase11-slab', duplicateSummaryVisible === 0, { duplicateSummaryVisible });
    const hero = await page.locator('.hero').evaluate(el => { const r=el.getBoundingClientRect(); return {height:r.height,width:r.width}; });
    add('home-hero-is-contained', hero.height >= 620 && hero.height <= 820, { hero });
    const image = await page.locator('.hero-image').evaluate(el => { const r=el.getBoundingClientRect(); const p=el.parentElement.getBoundingClientRect(); return {width:r.width,parentWidth:p.width,ratio:r.width/p.width}; });
    add('home-historical-visual-not-dominant', image.ratio <= 0.82, { image });
    const currentLegacyEraCount = await page.locator('.lineage-era-current').count();
    add('home-no-legacy-current-era-marker', currentLegacyEraCount === 0, { currentLegacyEraCount });
    const historicalHeading = await page.locator('.lineage-era-heading h3').filter({ hasText: 'Historical camera evidence' }).count();
    add('home-phase9-is-historical-not-current', historicalHeading === 1, { historicalHeading });
    await page.close();
    await context.close();
  }

  {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, reducedMotion: 'reduce' });
    const page = await context.newPage();
    await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(1800);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    add('mobile-home-no-horizontal-overflow', overflow <= 1, { overflow });
    const image = await page.locator('.hero-image').evaluate(el => { const r=el.getBoundingClientRect(); const p=el.parentElement.getBoundingClientRect(); return {width:r.width,parentWidth:p.width,ratio:r.width/p.width}; });
    add('mobile-home-historical-visual-contained', image.ratio <= 0.75, { image });
    const duplicateSummaryVisible = await page.locator('#phase11Summary:visible').count();
    add('mobile-home-no-duplicate-phase11-slab', duplicateSummaryVisible === 0, { duplicateSummaryVisible });
    await page.close();
    await context.close();
  }

  {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
    const page = await context.newPage();
    await page.goto(BASE + '/phases/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(1800);
    const frozenPredecessorHeadings = await page.locator('#archiveMap .era h2').filter({ hasText: 'Frozen predecessor' }).count();
    add('archive-legacy-frontier-is-frozen-predecessor', frozenPredecessorHeadings === 1, { frozenPredecessorHeadings });
    const legacyCurrentHeadings = await page.locator('#archiveMap .era h2').filter({ hasText: /^Current frontier$/ }).count();
    add('archive-no-legacy-current-frontier-heading', legacyCurrentHeadings === 0, { legacyCurrentHeadings });
    const phase11Heading = await page.locator('#phase11ArchiveEra h2').textContent().catch(() => '');
    add('archive-phase11-era-present', /phase 11 p14r/i.test(phase11Heading || ''), { phase11Heading });
    await page.goto(BASE + '/phases/phase10r/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(1800);
    const heroText = await page.locator('#phaseHero').innerText().catch(() => '');
    add('phase10r-no-latest-frontier-label', !/latest published frontier/i.test(heroText), { heroExcerpt: heroText.slice(0, 240) });
    add('phase10r-frozen-predecessor-label', /frozen predecessor/i.test(heroText), { heroExcerpt: heroText.slice(0, 240) });
    await page.goto(BASE + '/phases/phase10/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(1800);
    const nextLabel = await page.locator('#nextPhase span').first().textContent().catch(() => '');
    add('phase10-next-link-not-stale-frontier', /next phase/i.test(nextLabel || ''), { nextLabel });

    await page.goto(BASE + '/phases/phase11/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(500);
    const header = await page.locator('.top').evaluate(el => { const s=getComputedStyle(el); const r=el.getBoundingClientRect(); return {display:s.display,position:s.position,height:r.height}; });
    add('phase11-header-has-explicit-layout', header.display === 'grid' && header.position === 'fixed' && Math.round(header.height) === 64, { header });
    const brandStyle = await page.locator('.word').evaluate(el => { const s=getComputedStyle(el); return {color:s.color,decoration:s.textDecorationLine}; });
    add('phase11-brand-not-browser-default-link', brandStyle.decoration === 'none' && brandStyle.color === 'rgb(23, 26, 32)', { brandStyle });
    const navStyles = await page.locator('.nav a').evaluateAll(els => els.map(el => { const s=getComputedStyle(el); const r=el.getBoundingClientRect(); return {color:s.color,decoration:s.textDecorationLine,top:r.top,height:r.height}; }));
    add('phase11-nav-not-browser-default-links', navStyles.length === 2 && navStyles.every(x => x.decoration === 'none' && x.color !== 'rgb(0, 0, 238)'), { navStyles });
    add('phase11-desktop-nav-one-row', navStyles.length === 2 && Math.abs(navStyles[0].top-navStyles[1].top) < 1, { navStyles });
    const sectionHeights = await page.locator('main > section').evaluateAll(els => els.map(el => Math.round(el.getBoundingClientRect().height)));
    add('phase11-no-empty-viewport-panels', sectionHeights.every(h => h < 900), { sectionHeights });
    const phase11Overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    add('phase11-desktop-no-overflow', phase11Overflow <= 1, { phase11Overflow });
    await page.close();
    await context.close();
  }

  {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, reducedMotion: 'reduce' });
    const page = await context.newPage();
    await page.goto(BASE + '/phases/phase11/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(500);
    const mobileHeader = await page.locator('.top').evaluate(el => { const s=getComputedStyle(el); const r=el.getBoundingClientRect(); return {display:s.display,height:r.height,overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth}; });
    add('phase11-mobile-header-clean', mobileHeader.display === 'grid' && Math.round(mobileHeader.height) === 60 && mobileHeader.overflow <= 1, { mobileHeader });
    const mobileBrand = await page.locator('.word').evaluate(el => { const s=getComputedStyle(el); return {color:s.color,decoration:s.textDecorationLine}; });
    add('phase11-mobile-brand-not-default-link', mobileBrand.decoration === 'none' && mobileBrand.color === 'rgb(23, 26, 32)', { mobileBrand });
    const buttons = await page.locator('.hero .button').evaluateAll(els => els.map(el => Math.round(el.getBoundingClientRect().height)));
    add('phase11-mobile-hero-ctas-touchable', buttons.length === 2 && buttons.every(h => h >= 40), { buttons });
    await page.close();
    await context.close();
  }
} finally {
  await browser.close();
}

console.log(JSON.stringify({ base: BASE, passed: results.filter(r=>r.ok).length, failed, results }, null, 2));
if (failed) process.exitCode = 1;
