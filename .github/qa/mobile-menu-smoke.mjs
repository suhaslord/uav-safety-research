import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';

const BASE = process.env.QA_BASE_URL || 'https://aegisland-research-cockpit.vercel.app';
const OUT = 'qa-artifacts';
const results = [];
let failed = 0;
const add = (name, ok, details = {}) => { results.push({ name, ok, ...details }); if (!ok) failed++; };

await fs.mkdir(path.join(OUT, 'screenshots'), { recursive: true });
const browser = await chromium.launch({ headless: true });
try {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
    reducedMotion: 'reduce'
  });

  // Homepage deliberately uses the original Tesla-style drawer rather than the
  // later always-visible signature navigation.
  {
    const page = await context.newPage();
    const browserErrors = [];
    page.on('pageerror', (error) => browserErrors.push(String(error?.message || error)));
    page.on('console', (message) => { if (message.type() === 'error') browserErrors.push(message.text()); });
    const response = await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(500);
    add('home-status', !!response && response.status() >= 200 && response.status() < 400, { status: response?.status() || 0 });

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    add('home-no-horizontal-overflow', overflow <= 2, { overflow });
    add('home-browser-clean', browserErrors.length === 0, { browserErrors });
    add('home-tesla-brand-visible', await page.locator('.brand').count() === 1);

    const toggle = page.locator('.mobile-menu-toggle').first();
    const toggleCount = await toggle.count();
    add('home-menu-toggle-exists', toggleCount === 1, { toggleCount });
    if (toggleCount) {
      const box = await toggle.boundingBox();
      add('home-menu-toggle-touchable', !!box && box.height >= 40, { height: box?.height || 0 });
      await toggle.click();
      await page.waitForTimeout(200);
      add('home-menu-opens', await toggle.getAttribute('aria-expanded') === 'true');
      const sheet = page.locator('#mobileMenuSheet');
      add('home-menu-sheet-visible', await sheet.getAttribute('aria-hidden') === 'false');
      add('home-menu-has-phase22', await sheet.locator('a[href="/phases/phase22/"]').count() === 1);
      add('home-menu-has-archive', await sheet.locator('a[href="/phases/"]').count() === 1);
      await page.screenshot({ path: path.join(OUT, 'screenshots', 'mobile-home-menu-open.png'), fullPage: false });
      await page.keyboard.press('Escape');
      await page.waitForTimeout(200);
      add('home-menu-closes', await toggle.getAttribute('aria-expanded') === 'false');
    }

    const text = await page.locator('body').innerText();
    add('home-phase22-visible', /Frozen through Phase 22/i.test(text) && text.includes('0.8319') && text.includes('0.7744'));
    add('home-professor-framing-visible', /Research question/i.test(text) && /Main purpose/i.test(text) && /Main conclusion/i.test(text));
    add('home-claim-boundary-visible', text.includes('simulation_only=true') && text.includes('safety_acceptance=false') && text.includes('controller_tuning_allowed=false'));
    await page.close();
  }

  // Frozen archive/detail pages retain their shared archive navigation.
  for (const item of [
    { name: 'archive', route: '/', url: '/phases/' },
    { name: 'phase13a', route: '/phases/', url: '/phases/phase13a/' },
    { name: 'phase22', route: '/phases/', url: '/phases/phase22/' }
  ]) {
    const page = await context.newPage();
    const response = await page.goto(BASE + item.url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(400);
    add(`${item.name}-status`, !!response && response.status() >= 200 && response.status() < 400, { status: response?.status() || 0 });
    const state = await page.evaluate(() => ({
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      brand: !!document.querySelector('.signature-brand'),
      nav: !!document.querySelector('.signature-nav'),
      text: document.body?.innerText || ''
    }));
    add(`${item.name}-no-horizontal-overflow`, state.overflow <= 2, { overflow: state.overflow });
    add(`${item.name}-archive-brand-present`, state.brand);
    add(`${item.name}-archive-nav-present`, state.nav);
    if (item.name === 'phase13a') add('phase13a-fail-visible', /LOCKED VERDICT\s+FAIL/i.test(state.text));
    if (item.name === 'phase22') add('phase22-pass-visible', /LOCKED VERDICT\s+PASS/i.test(state.text) && state.text.includes('0.8319') && state.text.includes('0.7744'));
    await page.close();
  }

  await context.close();
} finally {
  await browser.close();
}

const summary = { base: BASE, passed: results.filter((result) => result.ok).length, failed, results };
await fs.writeFile(path.join(OUT, 'mobile-navigation-summary.json'), JSON.stringify(summary, null, 2));
await fs.appendFile(path.join(OUT, 'summary.md'), `\n\n## Mobile navigation\n\n- Passed: ${summary.passed}\n- Failed: ${summary.failed}\n${results.map((result) => `- ${result.ok ? 'PASS' : 'FAIL'} — ${result.name}`).join('\n')}\n`);
console.log(JSON.stringify(summary, null, 2));
if (failed) process.exitCode = 1;
