import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const base = process.env.QA_BASE_URL || 'http://127.0.0.1:4173';
const options = { headless: true };
const chrome = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
if (process.platform === 'win32' && fs.existsSync(chrome)) options.executablePath = chrome;
const browser = await chromium.launch(options);
const image = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=', 'base64');
try {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, reducedMotion: 'reduce' });
  await page.goto(base, { waitUntil: 'load' });
  await page.locator('#mobileMenuToggle').click();
  await page.waitForFunction(() => document.activeElement?.classList.contains('mobile-menu-close'));
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.waitForTimeout(200);
  assert.equal(await page.locator('#mobileMenuToggle').getAttribute('aria-expanded'), 'false', 'desktop resize must close mobile navigation');
  assert.equal(await page.locator('#mobileMenuSheet').getAttribute('aria-hidden'), 'true');
  assert.equal(await page.evaluate(() => document.body.classList.contains('menu-open')), false);
  assert.equal(await page.evaluate(() => document.activeElement?.closest('#mobileMenuSheet') !== null), false, 'focus must not remain in the hidden sheet');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator('#mobileMenuToggle').click();
  await page.waitForFunction(() => document.activeElement?.classList.contains('mobile-menu-close'));
  await page.keyboard.press('Escape');
  await page.waitForFunction(() => document.activeElement?.id === 'mobileMenuToggle');
  console.log('PASS mobile resize, scroll unlock, and Escape focus restoration');
  await page.close();

  // Deterministic media promises reproduce a slow play() settling after exit
  // from the viewport or after reduced motion is enabled, without real codecs.
  const media = await browser.newPage();
  await media.setContent('<body class="home-workspace"><div class="home-field-media"><video data-autoplay="visible"></video></div></body>');
  await media.evaluate(() => {
    window.mediaPaused = true;
    window.pendingPlay = [];
    Object.defineProperty(HTMLMediaElement.prototype, 'paused', { get: () => window.mediaPaused });
    HTMLMediaElement.prototype.pause = function () { window.mediaPaused = true; this.dispatchEvent(new Event('pause')); };
    HTMLMediaElement.prototype.play = function () {
      const video = this;
      return new Promise(resolve => window.pendingPlay.push(() => { window.mediaPaused = false; video.dispatchEvent(new Event('play')); resolve(); }));
    };
    window.IntersectionObserver = class { constructor(callback) { window.mediaObserver = callback; } observe() {} };
  });
  await media.addScriptTag({ path: path.resolve('deploy/vercel/presentation.js') });
  await media.evaluate(() => window.mediaObserver([{ isIntersecting: true }]));
  await media.evaluate(() => window.mediaObserver([{ isIntersecting: false }]));
  await media.evaluate(async () => { window.pendingPlay.shift()(); await Promise.resolve(); });
  assert.equal(await media.evaluate(() => window.mediaPaused), true, 'late play must stop after leaving the viewport');
  await media.evaluate(() => window.mediaObserver([{ isIntersecting: true }]));
  await media.emulateMedia({ reducedMotion: 'reduce' });
  await media.waitForTimeout(100);
  await media.evaluate(async () => { window.pendingPlay.shift()(); await Promise.resolve(); });
  assert.equal(await media.evaluate(() => window.mediaPaused), true, 'late play must respect reduced motion');
  await media.emulateMedia({ reducedMotion: 'no-preference' });
  await media.waitForTimeout(100);
  await media.evaluate(async () => { window.pendingPlay.shift()(); await Promise.resolve(); });
  assert.equal(await media.evaluate(() => window.mediaPaused), false, 'eligible playback must resume');
  await media.evaluate(() => document.querySelector('video').pause());
  await media.evaluate(() => { window.mediaObserver([{ isIntersecting: false }]); window.mediaObserver([{ isIntersecting: true }]); });
  assert.equal(await media.evaluate(() => window.pendingPlay.length), 0, 'a user pause must survive viewport changes');
  console.log('PASS slow video playback, reduced motion, and manual pause');
  await media.close();

  const atlas = await browser.newPage();
  const frozen = await atlas.request.get(`${base}/failure-atlas-frozen.js?v=8`);
  assert.equal(frozen.status(), 200);
  assert.deepEqual(await frozen.body(), fs.readFileSync('deploy/vercel/failure-atlas.js'), 'the served research runtime must stay byte-identical');
  await atlas.route('**/media/phase25/**', route => route.fulfill({ contentType: 'image/png', body: image }));
  await atlas.goto(`${base}/failure-atlas/`, { waitUntil: 'load' });
  await atlas.waitForFunction(() => document.querySelector('#conditions').children.length === 6);
  const filename = await atlas.locator('#frame-image').evaluate(img => new URL(img.src).pathname.split('/').pop());
  await atlas.locator('#local-files').setInputFiles({ name: filename, mimeType: 'image/jpeg', buffer: image });
  assert.match(await atlas.locator('#frame-image').getAttribute('alt'), /local.*unverified/i);
  assert.match(await atlas.locator('#phase23-frame-image').getAttribute('alt'), /local.*unverified/i);
  assert.match(await atlas.locator('#phase23-image-badge').textContent(), /local.*unverified/i);
  assert.match(await atlas.locator('#image-note').textContent(), /hashes are not checked/i);
  await atlas.locator('#next-frame').click();
  assert.match(await atlas.locator('#phase23-image-badge').textContent(), /reconstructed/i);
  console.log('PASS local images are distinguished from verified reconstructed evidence');
  await atlas.close();
} finally {
  await browser.close();
}
