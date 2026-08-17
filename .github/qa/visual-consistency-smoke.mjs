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
      const visibleToggle = await page.locator('.mobile-menu-toggle:visible,.archive-menu-toggle:visible').count();
      add(`${viewport.name}-${route}-mobile-menu-hidden`, visibleToggle === 0, { visibleToggle });
      await page.close();
    }
    await context.close();
  }

  {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, reducedMotion: 'reduce' });
    const page = await context.newPage();
    await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(1800);
    const opacity = await page.locator('.hero-image').evaluate(el => Number(getComputedStyle(el).opacity));
    add('mobile-home-hero-image-deemphasized-for-contrast', opacity <= 0.3, { opacity });
    const eraHeading = await page.locator('.lineage-era').filter({ hasText: 'Phase 9' }).locator('.lineage-era-heading h3').first().textContent().catch(() => '');
    add('home-phase9-is-historical-not-current', /historical camera evidence/i.test(eraHeading || ''), { eraHeading });
    await page.close();
    await context.close();
  }

  {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
    const page = await context.newPage();
    await page.goto(BASE + '/phases/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(1800);
    const p10r = page.locator('#archiveMap .phase-link[href="/phases/phase10r/"]').first();
    const oldHeading = await p10r.locator('xpath=ancestor::section[contains(@class,"era")]//h2').first().textContent().catch(() => '');
    add('archive-phase10r-era-is-frozen-predecessor', /frozen predecessor/i.test(oldHeading || ''), { oldHeading });
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
    await page.close();
    await context.close();
  }
} finally {
  await browser.close();
}

console.log(JSON.stringify({ base: BASE, passed: results.filter(r=>r.ok).length, failed, results }, null, 2));
if (failed) process.exitCode = 1;
