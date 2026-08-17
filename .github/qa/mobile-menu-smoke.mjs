import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';

const BASE = process.env.QA_BASE_URL || 'https://aegisland-research-cockpit.vercel.app';
const OUT = 'qa-artifacts';
const cases = [
  { name: 'home', route: '/' },
  { name: 'archive', route: '/phases/' },
  { name: 'phase10r', route: '/phases/phase10r/' }
];
const results = [];
let failed = 0;
const add = (name, ok, details = {}) => { results.push({ name, ok, ...details }); if (!ok) failed++; };

await fs.mkdir(path.join(OUT, 'screenshots'), { recursive: true });
const browser = await chromium.launch({ headless: true });
try {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, reducedMotion: 'reduce' });
  for (const item of cases) {
    const page = await context.newPage();
    await page.goto(BASE + item.route, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(2200);
    const toggle = page.locator('.mobile-menu-toggle,.archive-menu-toggle').first();
    const count = await toggle.count();
    add(`${item.name}-menu-toggle-exists`, count === 1, { route: item.route, count });
    if (!count) { await page.close(); continue; }

    const box = await toggle.boundingBox();
    add(`${item.name}-menu-toggle-height`, !!box && box.height >= 40, { route: item.route, height: box?.height || 0 });

    await toggle.click();
    await page.waitForTimeout(250);
    const expanded = await toggle.getAttribute('aria-expanded');
    add(`${item.name}-menu-opens`, expanded === 'true', { route: item.route, ariaExpanded: expanded });

    const archiveSheet = page.locator('#archiveMobileMenu');
    if (await archiveSheet.count()) {
      const hidden = await archiveSheet.getAttribute('aria-hidden');
      const openClass = await archiveSheet.evaluate(el => el.classList.contains('open'));
      add(`${item.name}-menu-sheet-open-state`, hidden === 'false' && openClass, { route: item.route, ariaHidden: hidden, openClass });
    }

    if (item.name === 'home') {
      const frontier = page.locator('#mobileMenuSheet a[href="/phases/phase11/"]');
      const frontierText = (await frontier.first().textContent().catch(() => ''))?.trim() || '';
      add('home-mobile-frontier-is-phase11', await frontier.count() === 1 && /phase\s*11/i.test(frontierText), { count: await frontier.count(), text: frontierText });
      const stale = page.locator('#mobileMenuSheet a').filter({ hasText: /Phase\s*7/i });
      add('home-mobile-no-stale-phase7', await stale.count() === 0, { staleCount: await stale.count() });
    }
    if (item.name === 'archive') {
      const frontier = page.locator('#archiveMobileMenu .archive-menu-links a.primary');
      const href = await frontier.getAttribute('href').catch(() => null);
      const text = (await frontier.textContent().catch(() => ''))?.trim() || '';
      add('archive-mobile-frontier-is-phase11', href === '/phases/phase11/' && /phase\s*11/i.test(text), { href, text });
      const stale = page.locator('#archiveMobileMenu .archive-menu-links a').filter({ hasText: /^Phase\s*10$/i });
      add('archive-mobile-no-stale-phase10', await stale.count() === 0, { staleCount: await stale.count() });
    }

    await page.screenshot({ path: path.join(OUT, 'screenshots', `menu-${item.name}-mobile-open.png`), fullPage: false });

    await page.keyboard.press('Escape');
    await page.waitForTimeout(250);
    let closed = await toggle.getAttribute('aria-expanded');
    if (closed !== 'false') {
      const close = page.locator('.archive-menu-close,.mobile-menu-close,[aria-label="Close navigation"]').first();
      if (await close.count()) { await close.click(); await page.waitForTimeout(250); closed = await toggle.getAttribute('aria-expanded'); }
    }
    add(`${item.name}-menu-closes`, closed === 'false', { route: item.route, ariaExpanded: closed });
    await page.close();
  }
  await context.close();
} finally {
  await browser.close();
}

const summary = { base: BASE, passed: results.filter(r => r.ok).length, failed, results };
await fs.writeFile(path.join(OUT, 'mobile-menu-summary.json'), JSON.stringify(summary, null, 2));
await fs.appendFile(path.join(OUT, 'summary.md'), `\n\n## Mobile navigation interaction\n\n- Passed: ${summary.passed}\n- Failed: ${summary.failed}\n${results.map(r => `- ${r.ok ? 'PASS' : 'FAIL'} — ${r.name}${r.height ? ` (${r.height}px)` : ''}`).join('\n')}\n`);
console.log(JSON.stringify(summary, null, 2));
if (failed) process.exitCode = 1;
