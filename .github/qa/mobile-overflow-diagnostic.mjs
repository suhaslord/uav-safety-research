import { chromium } from 'playwright';

const base = process.env.QA_BASE_URL || 'http://127.0.0.1:4173';
const browser = await chromium.launch({ headless: true });
try {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, reducedMotion: 'reduce' });
  const page = await context.newPage();
  await page.goto(base + '/', { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(700);
  const report = await page.evaluate(() => {
    const vw = document.documentElement.clientWidth;
    const selector = el => {
      if (el.id) return `#${el.id}`;
      const cls = [...el.classList].slice(0,4).join('.');
      return `${el.tagName.toLowerCase()}${cls ? '.' + cls : ''}`;
    };
    const offenders = [...document.querySelectorAll('body *')].map(el => {
      const r = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      return {
        selector: selector(el),
        left: Math.round(r.left * 10) / 10,
        right: Math.round(r.right * 10) / 10,
        width: Math.round(r.width * 10) / 10,
        overLeft: Math.max(0, Math.round(-r.left * 10) / 10),
        overRight: Math.max(0, Math.round((r.right - vw) * 10) / 10),
        position: s.position,
        display: s.display,
        overflowX: s.overflowX,
        marginLeft: s.marginLeft,
        marginRight: s.marginRight,
        paddingLeft: s.paddingLeft,
        paddingRight: s.paddingRight,
        boxSizing: s.boxSizing,
        text: (el.textContent || '').trim().replace(/\s+/g,' ').slice(0,100)
      };
    }).filter(x => x.overLeft > 1 || x.overRight > 1)
      .sort((a,b) => Math.max(b.overLeft,b.overRight) - Math.max(a.overLeft,a.overRight));
    return {
      viewport: vw,
      scrollWidth: document.documentElement.scrollWidth,
      overflow: document.documentElement.scrollWidth - vw,
      bodyWidth: document.body.getBoundingClientRect().width,
      offenders: offenders.slice(0,40)
    };
  });
  console.log(JSON.stringify(report, null, 2));
  if (report.overflow > 1) process.exitCode = 1;
  await context.close();
} finally {
  await browser.close();
}
