/**
 * Regenerate docs/assets/readme/shots/*.png from the local dashboard.
 * Usage: python3 scripts/serve_dashboard.py &
 *        node scripts/capture_readme_shots.mjs
 * Then reframe/compress into frame_*.png if the README hero assets need refresh.
 */
import puppeteer from "puppeteer-core";
import { mkdirSync } from "fs";
import { resolve } from "path";

const chrome =
  process.env.CHROME_PATH || "/usr/bin/google-chrome-stable";
const outDir = resolve("docs/assets/readme/shots");
mkdirSync(outDir, { recursive: true });

const shots = [
  { name: "home", url: "http://127.0.0.1:8765/", w: 1440, h: 920, wait: 2500 },
  {
    name: "home_full",
    url: "http://127.0.0.1:8765/",
    w: 1440,
    h: 2200,
    wait: 3000,
    full: true,
  },
  {
    name: "phase10",
    url: "http://127.0.0.1:8765/phases/phase.html?phase=phase10",
    w: 1440,
    h: 1100,
    wait: 4000,
  },
  {
    name: "phase10_full",
    url: "http://127.0.0.1:8765/phases/phase.html?phase=phase10",
    w: 1440,
    h: 3600,
    wait: 4000,
    full: true,
  },
  {
    name: "phase9",
    url: "http://127.0.0.1:8765/phases/phase.html?phase=phase9",
    w: 1440,
    h: 1100,
    wait: 4000,
  },
  {
    name: "phase6b",
    url: "http://127.0.0.1:8765/phases/phase.html?phase=phase6b",
    w: 1440,
    h: 1100,
    wait: 4000,
  },
  {
    name: "phase3",
    url: "http://127.0.0.1:8765/phases/phase.html?phase=phase3",
    w: 1440,
    h: 1100,
    wait: 4000,
  },
  {
    name: "phases",
    url: "http://127.0.0.1:8765/phases/index.html",
    w: 1440,
    h: 1800,
    wait: 4000,
    full: true,
  },
  {
    name: "mobile",
    url: "http://127.0.0.1:8765/",
    w: 430,
    h: 920,
    wait: 3000,
  },
];

const browser = await puppeteer.launch({
  executablePath: chrome,
  headless: "new",
  args: ["--no-sandbox", "--disable-gpu", "--hide-scrollbars"],
});

for (const shot of shots) {
  const page = await browser.newPage();
  await page.setViewport({
    width: shot.w,
    height: shot.h,
    deviceScaleFactor: 1.5,
  });
  await page.goto(shot.url, { waitUntil: "networkidle0", timeout: 60000 });
  await new Promise((r) => setTimeout(r, shot.wait));
  // dismiss boot overlay if still present
  await page.evaluate(() => {
    const boot = document.getElementById("archiveBoot") || document.querySelector(".boot");
    if (boot) boot.style.display = "none";
    document.body.classList.add("is-ready");
  });
  await new Promise((r) => setTimeout(r, 500));
  const path = resolve(outDir, `${shot.name}.png`);
  await page.screenshot({ path, fullPage: !!shot.full });
  console.log("wrote", path);
  await page.close();
}

await browser.close();
