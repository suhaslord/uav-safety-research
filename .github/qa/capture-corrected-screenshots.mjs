import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';

const BASE = process.env.QA_BASE_URL || 'http://127.0.0.1:4173';
const OUT = 'corrected-visual-artifacts/screenshots';
const routes = [
  { name: 'home', path: '/' },
  { name: 'archive', path: '/phases/' },
  { name: 'phase10r', path: '/phases/phase10r/' },
  { name: 'phase11', path: '/phases/phase11/' }
];
const viewports = [
  { name: 'desktop', width: 1440, height: 1000 },
  { name: 'tablet', width: 820, height: 1180 },
  { name: 'mobile', width: 390, height: 844, isMobile: true, hasTouch: true }
];

await fs.mkdir(OUT, { recursive: true });
const browser = await chromium.launch({ headless: true });
try {
  for (const vp of viewports) {
    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
      isMobile: vp.isMobile || false,
      hasTouch: vp.hasTouch || false,
      reducedMotion: 'reduce'
    });
    for (const route of routes) {
      const page = await context.newPage();
      await page.goto(BASE + route.path, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await page.waitForTimeout(2200);
      await page.screenshot({ path: path.join(OUT, `${route.name}-${vp.name}.png`), fullPage: true });
      await page.close();
    }
    await context.close();
  }
} finally {
  await browser.close();
}
