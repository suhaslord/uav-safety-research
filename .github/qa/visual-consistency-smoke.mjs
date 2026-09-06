import { chromium } from 'playwright';

const BASE = process.env.QA_BASE_URL || 'http://127.0.0.1:4173';
const results = [];
let failed = 0;
const add = (name, ok, details = {}) => { results.push({ name, ok, ...details }); if (!ok) failed++; };

const routes = [
  '/', '/phases/',
  '/phases/phase1/', '/phases/phase2/', '/phases/phase3/', '/phases/phase4/', '/phases/phase5/',
  '/phases/phase6/', '/phases/phase6b/', '/phases/phase7/', '/phases/phase8/', '/phases/phase9/',
  '/phases/phase10/', '/phases/phase10r/', '/phases/phase11/', '/phases/phase12/',
  '/phases/phase13a/', '/phases/phase13b/', '/phases/phase13c/', '/phases/phase14/', '/phases/phase15/',
  '/phases/phase16/', '/phases/phase17/', '/phases/phase18/', '/phases/phase19/', '/phases/phase20/',
  '/phases/phase21/', '/phases/phase22/'
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
      await page.waitForTimeout(250);
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
    await page.waitForTimeout(400);

    const shell = await page.evaluate(() => document.documentElement.dataset.siteShell || '');
    add('home-frozen-native-shell', shell === 'native frozen-archive', { shell });
    const teslaStyles = await page.locator('link[href^="/aegisland.css"]').count();
    add('home-uses-tesla-style-source', teslaStyles === 1, { teslaStyles });
    const evidenceRows = await page.locator('#evidenceSpine .evidence-row').count();
    const passRows = await page.locator('#evidenceSpine .evidence-row[data-verdict="PASS"]').count();
    const failRows = await page.locator('#evidenceSpine .evidence-row[data-verdict="FAIL"]').count();
    add('home-has-complete-frozen-spine', evidenceRows === 13, { evidenceRows });
    add('home-preserves-pass-fail-record', passRows === 6 && failRows === 7, { passRows, failRows });

    const homeText = await page.locator('main').innerText();
    add('home-old-thesis-restored', /Evidence before confidence/i.test(homeText), { excerpt: homeText.slice(0, 280) });
    add('home-professor-framing-visible', /Research question/i.test(homeText) && /Main purpose/i.test(homeText) && /Problem being studied/i.test(homeText) && /Main conclusion/i.test(homeText));
    add('home-phase22-final-visible', /0\.8319/.test(homeText) && /0\.7744/.test(homeText) && /10\s+locked gates/i.test(homeText) && /100%/.test(homeText), { excerpt: homeText.slice(0, 900) });
    add('home-science-is-explicitly-frozen', /No Phase 23 is implied or authorized/i.test(homeText), { excerpt: homeText.slice(-500) });
    add('home-claim-boundary-visible', /simulation_only=true/.test(homeText) && /safety_acceptance=false/.test(homeText) && /controller_tuning_allowed=false/.test(homeText));
    const phase23Links = await page.locator('a[href*="phase23"]').count();
    add('home-does-not-link-new-phase', phase23Links === 0, { phase23Links });
    await page.close();
    await context.close();
  }

  {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
    const page = await context.newPage();
    await page.goto(BASE + '/phases/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(400);
    const frozenCards = await page.locator('#frozenCards .archive-card').count();
    const legacyCards = await page.locator('#legacyCards .archive-card').count();
    const frozenPass = await page.locator('#frozenCards .verdict-chip--pass').count();
    const frozenFail = await page.locator('#frozenCards .verdict-chip--fail').count();
    const archiveText = await page.locator('main').innerText();
    add('archive-has-13-frozen-records', frozenCards === 13, { frozenCards });
    add('archive-has-13-foundational-records', legacyCards === 13, { legacyCards });
    add('archive-preserves-6-pass-7-fail', frozenPass === 6 && frozenFail === 7, { frozenPass, frozenFail });
    add('archive-says-nothing-rewritten', /Every frozen phase/i.test(archiveText) && /Nothing rewritten/i.test(archiveText));

    const phaseChecks = [
      ['/phases/phase12/', /PASS/, /2\.23035/],
      ['/phases/phase13a/', /FAIL/, /External-Validity Gauntlet/i],
      ['/phases/phase18/', /FAIL/, /protected validation missed two q90 gates/i],
      ['/phases/phase22/', /PASS/, /0\.8319/]
    ];
    for (const [route, verdict, evidence] of phaseChecks) {
      await page.goto(BASE + route, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await page.waitForTimeout(250);
      const text = await page.locator('main').innerText();
      add(`${route}-locked-verdict-visible`, verdict.test(text), { excerpt: text.slice(0, 280) });
      add(`${route}-evidence-visible`, evidence.test(text), { excerpt: text.slice(0, 500) });
      add(`${route}-boundary-visible`, /Synthetic, frozen simulation evidence only/i.test(text), { excerpt: text.slice(-300) });
    }

    await page.goto(BASE + '/phases/phase22/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(250);
    const phase22Text = await page.locator('main').innerText();
    add('phase22-has-final-r2-pair', /0\.8319/.test(phase22Text) && /0\.7744/.test(phase22Text));
    add('phase22-has-sealed-identities', /0ddc968b8bd48c2de6d904194b417854913389a8927cff0b15b96c6501f8294c/.test(phase22Text) && /62e75d7b39088c2e66f1cc6be4d180501b79632f2f6847af1fbe0bd96be17551/.test(phase22Text));

    await page.goto(BASE + '/phases/phase11/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(250);
    const phase11Text = await page.locator('main').innerText();
    add('phase11-failed-predecessor-remains-visible', /2\.435/.test(phase11Text) && /2\.25/.test(phase11Text), { excerpt: phase11Text.slice(0, 500) });
    await page.close();
    await context.close();
  }

  {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, reducedMotion: 'reduce' });
    const page = await context.newPage();
    for (const route of ['/', '/phases/', '/phases/phase13a/', '/phases/phase22/']) {
      await page.goto(BASE + route, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await page.waitForTimeout(250);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      add(`mobile-${route}-no-horizontal-overflow`, overflow <= 1, { overflow });
    }
    await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    const ctas = await page.locator('.hero .button').evaluateAll(els => els.map(el => Math.round(el.getBoundingClientRect().height)));
    add('mobile-home-ctas-touchable', ctas.length >= 2 && ctas.every(height => height >= 40), { ctas });
    await page.close();
    await context.close();
  }
} finally {
  await browser.close();
}

console.log(JSON.stringify({ base: BASE, passed: results.filter(result => result.ok).length, failed, results }, null, 2));
if (failed) process.exitCode = 1;
