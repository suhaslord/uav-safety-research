import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';

const BASE = process.env.QA_BASE_URL || 'https://aegisland-research-cockpit.vercel.app';
const OUT = 'qa-artifacts';
const cases = [
  { name: 'home', route: '/', expectedLink: '/phases/' },
  { name: 'archive', route: '/phases/', expectedLink: '/' },
  { name: 'phase13a', route: '/phases/phase13a/', expectedLink: '/phases/' },
  { name: 'phase22', route: '/phases/phase22/', expectedLink: '/phases/' }
];
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

  for (const item of cases) {
    const page = await context.newPage();
    const browserErrors = [];
    page.on('pageerror', (error) => browserErrors.push(String(error?.message || error)));
    page.on('console', (message) => { if (message.type() === 'error') browserErrors.push(message.text()); });

    const response = await page.goto(BASE + item.route, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(700);
    add(`${item.name}-status`, !!response && response.status() >= 200 && response.status() < 400, { status: response?.status() || 0 });

    const state = await page.evaluate(() => {
      const brand = document.querySelector('.signature-brand');
      const nav = document.querySelector('.signature-nav');
      const navLinks = [...document.querySelectorAll('.signature-nav__links a')].map((link) => {
        const rect = link.getBoundingClientRect();
        const style = getComputedStyle(link);
        return {
          href: link.getAttribute('href'),
          text: (link.textContent || '').trim(),
          visible: rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden',
          width: Math.round(rect.width),
          height: Math.round(rect.height)
        };
      });
      const ctas = [...document.querySelectorAll('.signature-button')].map((button) => {
        const rect = button.getBoundingClientRect();
        return { text: (button.textContent || '').trim(), width: Math.round(rect.width), height: Math.round(rect.height) };
      });
      return {
        overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        brandVisible: !!brand && brand.getBoundingClientRect().width > 0,
        navVisible: !!nav && nav.getBoundingClientRect().height > 0,
        navLinks,
        ctas,
        shell: document.documentElement.dataset.siteShell || '',
        text: document.body?.innerText || ''
      };
    });

    add(`${item.name}-no-horizontal-overflow`, state.overflow <= 2, { overflow: state.overflow });
    add(`${item.name}-brand-visible`, state.brandVisible);
    add(`${item.name}-signature-nav-visible`, state.navVisible);
    add(`${item.name}-has-visible-nav-link`, state.navLinks.some((link) => link.visible), { navLinks: state.navLinks });
    add(`${item.name}-expected-nav-link-present`, state.navLinks.some((link) => link.href === item.expectedLink), { expectedLink: item.expectedLink, navLinks: state.navLinks });
    add(`${item.name}-touchable-primary-ctas`, state.ctas.filter((cta) => cta.width > 0).every((cta) => cta.height >= 42), { ctas: state.ctas });
    add(`${item.name}-browser-clean`, browserErrors.length === 0, { browserErrors });

    if (item.name === 'home') {
      add('home-mobile-frozen-shell', state.shell === 'native frozen-archive', { shell: state.shell });
      add('home-mobile-phase22-visible', /Frozen through Phase 22/i.test(state.text) && state.text.includes('0.8319') && state.text.includes('0.7744'));
      add('home-mobile-claim-boundary-visible', state.text.includes('simulation_only=true') && state.text.includes('safety_acceptance=false') && state.text.includes('controller_tuning_allowed=false'));
    }
    if (item.name === 'phase13a') add('phase13a-mobile-fail-visible', /LOCKED VERDICT\s+FAIL/i.test(state.text));
    if (item.name === 'phase22') add('phase22-mobile-pass-visible', /LOCKED VERDICT\s+PASS/i.test(state.text) && state.text.includes('0.8319') && state.text.includes('0.7744'));

    await page.screenshot({ path: path.join(OUT, 'screenshots', `mobile-${item.name}.png`), fullPage: true });
    await page.close();
  }
  await context.close();
} finally {
  await browser.close();
}

const summary = { base: BASE, passed: results.filter((result) => result.ok).length, failed, results };
await fs.writeFile(path.join(OUT, 'mobile-navigation-summary.json'), JSON.stringify(summary, null, 2));
await fs.appendFile(path.join(OUT, 'summary.md'), `\n\n## Mobile frozen-archive navigation\n\n- Passed: ${summary.passed}\n- Failed: ${summary.failed}\n${results.map((result) => `- ${result.ok ? 'PASS' : 'FAIL'} — ${result.name}`).join('\n')}\n`);
console.log(JSON.stringify(summary, null, 2));
if (failed) process.exitCode = 1;
