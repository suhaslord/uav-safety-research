import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';

const BASE = process.env.QA_BASE_URL;
if (!BASE) throw new Error('QA_BASE_URL is required');

const legacySlugs = [
  'phase1','phase2','phase3','phase4','phase5','phase6','phase6b',
  'phase7','phase8','phase9','phase10','phase10r'
];
const routes = legacySlugs.map((slug) => `/phases/${slug}/`);
const OUT = path.join('qa-artifacts', 'mobile-density');
await fs.rm(OUT, { recursive:true, force:true });
await fs.mkdir(OUT, { recursive:true });

const browser = await chromium.launch({ headless:true });
const context = await browser.newContext({
  viewport:{ width:390, height:844 },
  isMobile:true,
  hasTouch:true,
  reducedMotion:'reduce'
});

const results = [];
try {
  for (const route of routes) {
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', (error) => errors.push(String(error?.message || error)));
    page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()); });

    const response = await page.goto(`${BASE}${route}?mobile_density=1`, {
      waitUntil:'domcontentloaded', timeout:12000
    });
    await page.waitForFunction(
      () => document.documentElement.dataset.finalConvergence === 'ready',
      null,
      { timeout:4000 }
    );
    await page.waitForTimeout(250);

    const metrics = await page.evaluate(() => {
      const number = (value) => Number.parseFloat(value || '0') || 0;
      const style = (selector) => {
        const el = document.querySelector(selector);
        return el ? getComputedStyle(el) : null;
      };
      const hero = style('.hero');
      const program = style('.program-goal');
      const finding = style('.finding blockquote');
      const evidence = style('.evidence-visual');
      const sections = [...document.querySelectorAll('.section')];
      const sectionStyles = sections.map((el) => getComputedStyle(el));
      return {
        scrollWidth:document.documentElement.scrollWidth,
        clientWidth:document.documentElement.clientWidth,
        heroMinHeight:number(hero?.minHeight),
        heroGap:number(hero?.gap),
        programPresent:!!program,
        programMinHeight:number(program?.minHeight),
        programGap:number(program?.gap),
        sectionMinHeights:sectionStyles.map((s) => number(s.minHeight)),
        sectionPaddingTop:sectionStyles.map((s) => number(s.paddingTop)),
        sectionPaddingBottom:sectionStyles.map((s) => number(s.paddingBottom)),
        findingPresent:!!finding,
        findingFontSize:number(finding?.fontSize),
        findingLineHeight:number(finding?.lineHeight),
        evidenceMinHeight:number(evidence?.minHeight),
        convergenceReady:document.documentElement.dataset.finalConvergence || ''
      };
    });

    const checks = {
      status:Boolean(response && response.status() >= 200 && response.status() < 400),
      convergence:metrics.convergenceReady === 'ready',
      noOverflow:metrics.scrollWidth - metrics.clientWidth <= 2,
      heroNotForcedFullscreen:metrics.heroMinHeight <= 1,
      programExists:metrics.programPresent,
      programNotForcedFullscreen:metrics.programMinHeight <= 1,
      programGapCompact:metrics.programGap <= 30,
      sectionsNotForcedFullscreen:metrics.sectionMinHeights.every((value) => value <= 1),
      sectionPaddingCompact:metrics.sectionPaddingTop.every((value) => value <= 52)
        && metrics.sectionPaddingBottom.every((value) => value <= 52),
      findingExists:metrics.findingPresent,
      findingReadableScale:metrics.findingFontSize >= 26 && metrics.findingFontSize <= 32.1,
      evidenceVisualCompact:metrics.evidenceMinHeight === 0 || metrics.evidenceMinHeight <= 262,
      consoleClean:errors.filter((x) => !/favicon|ERR_BLOCKED_BY_CLIENT/i.test(x)).length === 0
    };
    const pass = Object.values(checks).every(Boolean);
    results.push({ route, pass, checks, metrics, errors });
    console.log(`${pass ? 'PASS' : 'FAIL'} ${route}`);

    if (route === '/phases/phase1/') {
      await page.screenshot({
        path:path.join(OUT, 'phase1-mobile-density.png'),
        fullPage:true
      });
    }
    await page.close();
  }
} finally {
  await context.close();
  await browser.close();
}

const passed = results.filter((item) => item.pass).length;
const report = {
  base:BASE,
  viewport:'390x844',
  passed,
  total:results.length,
  results,
  finishedAt:new Date().toISOString()
};
await fs.writeFile(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2));
await fs.writeFile(
  path.join(OUT, 'summary.md'),
  `# Mobile density smoke\n\n- Passed: ${passed} / ${results.length}\n- Viewport: 390 × 844\n- Rule: no forced full-screen legacy sections; finding ≤32px; compact program/evidence rhythm.\n`
);

if (passed !== results.length) {
  const failed = results.filter((item) => !item.pass).map((item) => item.route).join(', ');
  throw new Error(`Mobile density regression: ${passed}/${results.length} passed. Failed: ${failed}`);
}

console.log(`✓ mobile density smoke ${passed}/${results.length}`);
