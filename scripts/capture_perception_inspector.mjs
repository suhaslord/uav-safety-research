import { chromium } from 'playwright';
import fsSync from 'node:fs';
import path from 'node:path';

const BASE = process.env.QA_BASE_URL || 'http://127.0.0.1:4173';
const outDir = 'C:\\Users\\suhas\\.gemini\\antigravity\\brain\\da02154c-5644-4bb6-80fb-b07dade5d626';

const launchOptions = { headless: true };
if (process.platform === 'win32' && fsSync.existsSync('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe')) {
  launchOptions.executablePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
}

const browser = await chromium.launch(launchOptions);
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
  await page.goto(`${BASE}/`, { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(1000);

  // Scroll to experiment-lab
  const lab = page.locator('#experiment-lab');
  await lab.scrollIntoViewIfNeeded();
  await page.waitForTimeout(500);

  // Take screenshot of the Perception Inspector section
  await lab.screenshot({ path: path.join(outDir, 'perception-inspector-desktop.png') });
  console.log('Saved perception-inspector-desktop.png');

  // Switch condition to blur
  await page.selectOption('#current-data-condition', 'blur');
  await page.waitForTimeout(500);
  await lab.screenshot({ path: path.join(outDir, 'perception-inspector-blur-desktop.png') });
  console.log('Saved perception-inspector-blur-desktop.png');

  // Switch to baseline model
  await page.click('button[data-model="baseline"]');
  await page.waitForTimeout(500);
  await lab.screenshot({ path: path.join(outDir, 'perception-inspector-baseline-desktop.png') });
  console.log('Saved perception-inspector-baseline-desktop.png');

  // Mobile viewport
  await page.setViewportSize({ width: 390, height: 844 });
  await page.click('button[data-model="phase23"]');
  await page.selectOption('#current-data-condition', 'clean');
  await page.waitForTimeout(500);
  await lab.screenshot({ path: path.join(outDir, 'perception-inspector-mobile.png') });
  console.log('Saved perception-inspector-mobile.png');

} finally {
  await browser.close();
}
