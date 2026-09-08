import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';
import sharp from 'sharp';

const BASE = process.env.QA_BASE_URL;
if (!BASE) throw new Error('QA_BASE_URL is required');

const ROOT = path.join('qa-artifacts', 'mobile-ui-sweep-504');
const SCREENSHOTS = path.join(ROOT, 'screenshots');
const phaseSlugs = ['phase1','phase2','phase3','phase4','phase5','phase6','phase6b','phase7','phase8','phase9','phase10','phase10r','phase11','phase12','phase13a','phase13b','phase13c','phase14','phase15','phase16','phase17','phase18','phase19','phase20','phase21','phase22'];
const routes = ['/', '/phases/', ...phaseSlugs.map((slug) => `/phases/${slug}/`)];
const phones = [
  { name:'phone-320', width:320, height:568 },
  { name:'phone-360', width:360, height:800 },
  { name:'phone-375', width:375, height:667 },
  { name:'phone-390', width:390, height:844 },
  { name:'phone-412', width:412, height:915 },
  { name:'phone-430', width:430, height:932 }
];

await fs.rm(ROOT, { recursive:true, force:true });
await fs.mkdir(SCREENSHOTS, { recursive:true });

const report = {
  base:BASE,
  routes,
  viewports:phones,
  standardTarget: routes.length * phones.length * 3,
  screenshots:[], pages:[], blockers:[], warnings:[], imageAnalyses:[],
  startedAt:new Date().toISOString()
};
const block = (key, kind, details={}) => report.blockers.push({ key, kind, ...details });
const warn = (key, kind, details={}) => report.warnings.push({ key, kind, ...details });
const safe = (route) => route === '/' ? 'home' : route.replace(/^\/+|\/+$/g,'').replaceAll('/','-');

const browser = await chromium.launch({ headless:true });
try {
  for (const vp of phones) {
    const context = await browser.newContext({
      viewport:{width:vp.width,height:vp.height},
      isMobile:true,
      hasTouch:true,
      deviceScaleFactor:1,
      reducedMotion:'reduce'
    });

    for (const route of routes) {
      const key = `${vp.name}:${route}`;
      const page = await context.newPage();
      const consoleErrors = [];
      const failedRequests = [];
      page.on('pageerror', (error) => consoleErrors.push(String(error?.message || error)));
      page.on('console', (message) => { if (message.type() === 'error') consoleErrors.push(message.text()); });
      page.on('requestfailed', (request) => failedRequests.push({ url:request.url(), error:request.failure()?.errorText || 'failed' }));

      let response;
      try {
        response = await page.goto(`${BASE}${route}?mobile_ui_sweep=1`, { waitUntil:'domcontentloaded', timeout:45000 });
        await page.waitForFunction(() => document.documentElement.dataset.finalConvergence === 'ready', null, { timeout:12000 }).catch(() => {});
        await page.waitForTimeout(250);
      } catch (error) {
        block(key, 'load-failed', { error:String(error) });
      }

      const imageCount = await page.locator('img').count().catch(() => 0);
      for (let i=0;i<imageCount;i+=1) await page.locator('img').nth(i).scrollIntoViewIfNeeded().catch(() => {});
      await page.evaluate(async () => {
        await Promise.all([...document.images].map((img) => img.decode?.().catch(() => undefined)));
        window.scrollTo(0,0);
      }).catch(() => {});
      await page.waitForTimeout(120);

      const metrics = await page.evaluate(({ route }) => {
        const visible = (el) => {
          if (!el) return false;
          const s = getComputedStyle(el);
          const r = el.getBoundingClientRect();
          return s.display !== 'none' && s.visibility !== 'hidden' && Number(s.opacity || 1) > 0 && r.width > 0 && r.height > 0;
        };
        const rect = (el) => {
          const r = el.getBoundingClientRect();
          return { left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height };
        };
        const intersects = (a,b) => Math.max(0,Math.min(a.right,b.right)-Math.max(a.left,b.left)) > 4 && Math.max(0,Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)) > 4;
        const text = document.body.innerText;
        const header = document.querySelector('.site-header, .signature-nav, body.archive-shell .top');
        const toggle = document.querySelector('.mobile-menu-toggle, .archive-menu-toggle');
        const controls = [...document.querySelectorAll('a,button,input,select,textarea,[role="button"]')].filter(visible);
        const smallTargets = controls.map((el) => {
          const r = rect(el);
          return { text:(el.getAttribute('aria-label') || el.textContent || '').trim().slice(0,70), width:r.width, height:r.height };
        }).filter((x) => x.width < 40 || x.height < 40);
        const marginalTargets = controls.map((el) => {
          const r = rect(el);
          return { text:(el.getAttribute('aria-label') || el.textContent || '').trim().slice(0,70), width:r.width, height:r.height };
        }).filter((x) => (x.width < 44 || x.height < 44) && !(x.width < 40 || x.height < 40));
        const offscreenControls = controls.map((el) => ({ text:(el.textContent||el.getAttribute('aria-label')||'').trim().slice(0,70), ...rect(el) }))
          .filter((x) => x.left < -3 || x.right > innerWidth + 3);
        const brokenImages = [...document.images].filter((img) => !img.complete || img.naturalWidth === 0).map((img) => img.currentSrc || img.src);
        const ids = [...document.querySelectorAll('[id]')].map((el) => el.id).filter(Boolean);
        const duplicateIds = [...new Set(ids.filter((id,i) => ids.indexOf(id) !== i))];
        const brokenAnchors = [...document.querySelectorAll('a[href^="#"]')].map((a) => a.getAttribute('href')).filter((href) => href && href !== '#' && !document.getElementById(decodeURIComponent(href.slice(1))));
        const clippedText = [...document.querySelectorAll('h1,h2,h3,p,a,button,strong,span,code,pre,li')].filter(visible).map((el) => {
          const s = getComputedStyle(el);
          return { tag:el.tagName, text:(el.textContent||'').trim().slice(0,90), scrollWidth:el.scrollWidth, clientWidth:el.clientWidth, overflowX:s.overflowX };
        }).filter((x) => ['hidden','clip'].includes(x.overflowX) && x.scrollWidth > x.clientWidth + 5);
        const fixed = [...document.querySelectorAll('body *')].filter(visible).filter((el) => ['fixed','sticky'].includes(getComputedStyle(el).position)).map((el) => ({
          tag:el.tagName,
          cls:String(el.className || '').slice(0,90),
          ...rect(el)
        }));
        const fixedOffscreen = fixed.filter((x) => x.left < -3 || x.right > innerWidth + 3 || x.width > innerWidth + 6);

        const visibleHeaderChildren = header ? [...header.children].filter(visible) : [];
        const headerOverlaps = [];
        for (let i=0;i<visibleHeaderChildren.length;i+=1) for (let j=i+1;j<visibleHeaderChildren.length;j+=1) {
          const a = rect(visibleHeaderChildren[i]); const b = rect(visibleHeaderChildren[j]);
          if (intersects(a,b)) headerOverlaps.push(`${visibleHeaderChildren[i].className || visibleHeaderChildren[i].tagName} <> ${visibleHeaderChildren[j].className || visibleHeaderChildren[j].tagName}`);
        }

        const lineage = [...document.querySelectorAll('.home-lineage__node')].filter(visible).map(rect);
        const archiveCats = [...document.querySelectorAll('.category-nav a')].filter(visible).map(rect);
        const earlyRail = document.querySelector('.phase-rail');
        const compactRail = document.querySelector('.phase-progress-compact');
        const boundaryCode = document.querySelector('.boundary-flags');

        const homePurpose = route === '/' ? {
          purposeClarity:document.body.dataset.purposeClarity === 'true',
          questionRemoved:!document.getElementById('question'),
          purposeVisible:visible(document.getElementById('purpose')),
          evidenceVisible:visible(document.getElementById('evidence')),
          intendedCopy:/What the project does/i.test(text) && /Find when landing perception becomes confidently wrong/i.test(text) && /Main conclusion/i.test(text),
          metrics:/0\.8319/.test(text) && /0\.7744/.test(text) && /100%/.test(text),
          claimFlags:/simulation_only=true/.test(text) && /safety_acceptance=false/.test(text) && /controller_tuning_allowed=false/.test(text)
        } : null;

        return {
          ready:document.documentElement.dataset.finalConvergence || '',
          mainCount:document.querySelectorAll('main').length,
          h1Count:document.querySelectorAll('h1').length,
          scrollWidth:document.documentElement.scrollWidth,
          clientWidth:document.documentElement.clientWidth,
          scrollHeight:document.documentElement.scrollHeight,
          toggleVisible:visible(toggle),
          toggleRect:toggle && visible(toggle) ? rect(toggle) : null,
          smallTargets,marginalTargets,offscreenControls,brokenImages,duplicateIds,brokenAnchors:[...new Set(brokenAnchors)],clippedText,
          fixed,fixedOffscreen,headerOverlaps,
          lineageCount:lineage.length,
          lineageOffscreen:lineage.filter((r) => r.left < -3 || r.right > innerWidth + 3).length,
          archiveCategoryOffscreen:archiveCats.filter((r) => r.left < -3 || r.right > innerWidth + 3).length,
          earlyRailVisible:visible(earlyRail),
          compactRailVisible:visible(compactRail),
          boundaryCodeOffscreen:boundaryCode && visible(boundaryCode) ? (rect(boundaryCode).left < -3 || rect(boundaryCode).right > innerWidth + 3) : false,
          homePurpose
        };
      }, { route });

      const status = response?.status() || 0;
      if (!status || status >= 400) block(key, 'bad-status', { status });
      if (metrics.mainCount !== 1 || metrics.h1Count !== 1) block(key, 'semantic-shell', { mainCount:metrics.mainCount,h1Count:metrics.h1Count });
      if (metrics.ready !== 'ready') block(key, 'final-convergence-css-not-ready');
      if (metrics.scrollWidth - metrics.clientWidth > 2) block(key, 'horizontal-overflow', { overflow:metrics.scrollWidth-metrics.clientWidth });
      if (!metrics.toggleVisible) block(key, 'mobile-menu-toggle-missing');
      if (metrics.toggleRect && (metrics.toggleRect.width < 44 || metrics.toggleRect.height < 44)) block(key, 'mobile-menu-toggle-too-small', metrics.toggleRect);
      if (metrics.headerOverlaps.length) block(key, 'header-overlap', { examples:metrics.headerOverlaps.slice(0,5) });
      if (metrics.brokenImages.length) block(key, 'broken-images', { images:metrics.brokenImages });
      if (metrics.duplicateIds.length) block(key, 'duplicate-ids', { ids:metrics.duplicateIds });
      if (metrics.brokenAnchors.length) block(key, 'broken-anchors', { anchors:metrics.brokenAnchors });
      if (metrics.offscreenControls.length) block(key, 'offscreen-controls', { examples:metrics.offscreenControls.slice(0,8) });
      if (metrics.smallTargets.length) block(key, 'touch-target-under-40', { count:metrics.smallTargets.length, examples:metrics.smallTargets.slice(0,8) });
      if (metrics.marginalTargets.length) warn(key, 'touch-target-under-44', { count:metrics.marginalTargets.length, examples:metrics.marginalTargets.slice(0,8) });
      if (metrics.clippedText.length) block(key, 'clipped-text', { count:metrics.clippedText.length, examples:metrics.clippedText.slice(0,8) });
      if (metrics.fixedOffscreen.length) block(key, 'fixed-or-sticky-offscreen', { examples:metrics.fixedOffscreen.slice(0,8) });
      if (metrics.boundaryCodeOffscreen) block(key, 'boundary-code-offscreen');
      if (route === '/' && (metrics.lineageCount !== 13 || metrics.lineageOffscreen)) block(key, 'home-lineage-clipped', { count:metrics.lineageCount, offscreen:metrics.lineageOffscreen });
      if (route === '/phases/' && metrics.archiveCategoryOffscreen) block(key, 'archive-categories-clipped', { offscreen:metrics.archiveCategoryOffscreen });
      if (/^\/phases\/phase(?:[1-9]|10r?|11)\/$/.test(route) && !metrics.compactRailVisible) warn(key, 'early-phase-compact-timeline-missing');
      if (metrics.homePurpose) {
        if (!metrics.homePurpose.purposeClarity || !metrics.homePurpose.questionRemoved || !metrics.homePurpose.purposeVisible || !metrics.homePurpose.evidenceVisible || !metrics.homePurpose.intendedCopy) block(key, 'home-purpose-framing-not-visible', metrics.homePurpose);
        if (!metrics.homePurpose.metrics) block(key, 'home-final-metrics-not-visible');
        if (!metrics.homePurpose.claimFlags) block(key, 'home-claim-boundary-not-visible');
      }

      const filteredConsole = consoleErrors.filter((x) => !/favicon|ERR_BLOCKED_BY_CLIENT/i.test(x));
      const filteredRequests = failedRequests.filter((x) => !/favicon|github\.com|linkedin\.com|wikimedia\.org/i.test(x.url));
      if (filteredConsole.length) block(key, 'console-errors', { errors:filteredConsole.slice(0,8) });
      if (filteredRequests.length) block(key, 'network-errors', { requests:filteredRequests.slice(0,8) });

      const prefix = `${safe(route)}-${vp.name}`;
      const maxScroll = Math.max(0, metrics.scrollHeight - vp.height);
      for (const [label,fraction] of [['top',0],['mid',0.5],['bottom',1]]) {
        await page.evaluate((y) => window.scrollTo(0,y), Math.round(maxScroll*fraction));
        await page.waitForTimeout(70);
        const name = `${prefix}-${label}.png`;
        await page.screenshot({ path:path.join(SCREENSHOTS,name) });
        report.screenshots.push({ viewport:vp.name,route,kind:label,file:name,standard:true });
      }

      await page.evaluate(() => window.scrollTo(0,0));
      const toggle = page.locator('.mobile-menu-toggle, .archive-menu-toggle').first();
      if (await toggle.count()) {
        await toggle.click().catch(() => {});
        await page.waitForTimeout(100);
        const menu = await page.evaluate(() => {
          const visible = (el) => {
            if (!el) return false;
            const s=getComputedStyle(el); const r=el.getBoundingClientRect();
            return s.display!=='none' && s.visibility!=='hidden' && Number(s.opacity||1)>0 && r.width>0 && r.height>0;
          };
          const sheet=document.querySelector('.mobile-menu-sheet, .archive-menu-sheet');
          const toggle=document.querySelector('.mobile-menu-toggle, .archive-menu-toggle');
          const close=sheet?.querySelector('.mobile-menu-close, .archive-menu-close');
          const r=sheet?.getBoundingClientRect();
          const links=sheet ? [...sheet.querySelectorAll('a')].filter(visible).map((a) => { const q=a.getBoundingClientRect(); return {text:(a.textContent||'').trim(),width:q.width,height:q.height,left:q.left,right:q.right}; }) : [];
          return {
            expanded:toggle?.getAttribute('aria-expanded'), hidden:sheet?.getAttribute('aria-hidden'), visible:visible(sheet),
            left:r?.left??0,right:r?.right??0,top:r?.top??0,bottom:r?.bottom??0,width:r?.width??0,height:r?.height??0,
            links, closeSize:close&&visible(close)?{width:close.getBoundingClientRect().width,height:close.getBoundingClientRect().height}:null,
            bodyOverflow:getComputedStyle(document.body).overflow,
            activeInside:!!sheet?.contains(document.activeElement),
            activeText:(document.activeElement?.getAttribute?.('aria-label') || document.activeElement?.textContent || '').trim().slice(0,50)
          };
        });
        if (menu.expanded !== 'true' || menu.hidden !== 'false' || !menu.visible) block(`${key}:menu`, 'menu-open-state-broken', menu);
        if (menu.left < -3 || menu.right > vp.width + 3 || menu.top < -3 || menu.width > vp.width + 6) block(`${key}:menu`, 'menu-offscreen', menu);
        if (!menu.links.length || menu.links.some((x) => x.height < 44 || x.left < -3 || x.right > vp.width + 3)) block(`${key}:menu`, 'menu-link-touch-or-position-failure', { links:menu.links });
        if (!menu.closeSize || menu.closeSize.width < 44 || menu.closeSize.height < 44) block(`${key}:menu`, 'menu-close-target-too-small', { closeSize:menu.closeSize });
        if (!menu.activeInside) block(`${key}:menu`, 'menu-focus-not-moved-inside', { activeText:menu.activeText });
        if (!/hidden|clip/i.test(menu.bodyOverflow) && !document.body.classList.contains('menu-open')) warn(`${key}:menu`, 'background-scroll-not-locked', { overflow:menu.bodyOverflow });
        const menuName = `${prefix}-menu-open.png`;
        await page.screenshot({ path:path.join(SCREENSHOTS,menuName) });
        report.screenshots.push({ viewport:vp.name,route,kind:'menu-open',file:menuName,standard:false });
        await page.keyboard.press('Escape').catch(() => {});
        await page.waitForTimeout(80);
        const closed = await page.evaluate(() => ({
          expanded:document.querySelector('.mobile-menu-toggle, .archive-menu-toggle')?.getAttribute('aria-expanded'),
          hidden:document.querySelector('.mobile-menu-sheet, .archive-menu-sheet')?.getAttribute('aria-hidden'),
          activeIsToggle:document.activeElement === document.querySelector('.mobile-menu-toggle, .archive-menu-toggle')
        }));
        if (closed.expanded !== 'false' || closed.hidden !== 'true') block(`${key}:menu`, 'menu-escape-close-broken', closed);
        if (!closed.activeIsToggle) warn(`${key}:menu`, 'menu-focus-not-returned-to-toggle', closed);
      }

      report.pages.push({ key,route,viewport:vp.name,status,metrics });
      await page.close();
    }
    await context.close();
  }
} finally {
  await browser.close();
}

const files = (await fs.readdir(SCREENSHOTS)).filter((name) => name.endsWith('.png')).sort();
for (const name of files) {
  const file = path.join(SCREENSHOTS,name);
  try {
    const stat = await fs.stat(file);
    const image = sharp(file, { failOn:'error' });
    const [metadata,stats] = await Promise.all([image.metadata(), image.stats()]);
    const channels = stats.channels || [];
    const stdev = channels.length ? channels.reduce((sum,c) => sum + Number(c.stdev || 0),0) / channels.length : 0;
    const entropy = Number(stats.entropy || 0);
    const analysis = { name,width:metadata.width,height:metadata.height,bytes:stat.size,entropy,stdev };
    report.imageAnalyses.push(analysis);
    if (!metadata.width || !metadata.height || stat.size < 1200) block(`image:${name}`, 'screenshot-empty-or-tiny', analysis);
    if (entropy < 0.08 || stdev < 2) block(`image:${name}`, 'screenshot-suspiciously-flat', analysis);
  } catch (error) {
    block(`image:${name}`, 'screenshot-analysis-failed', { error:String(error) });
  }
}

report.finishedAt = new Date().toISOString();
report.standardCaptured = report.screenshots.filter((x) => x.standard).length;
report.interactionCaptured = report.screenshots.filter((x) => !x.standard).length;
report.totalCaptured = report.screenshots.length;
report.imageAnalyzed = report.imageAnalyses.length;

await fs.writeFile(path.join(ROOT,'report.json'), JSON.stringify(report,null,2));
const summary = [
  '# AegisLand mobile UI sweep',
  '',
  `- Base: ${BASE}`,
  `- Routes: ${routes.length}`,
  `- Phone sizes: ${phones.length}`,
  `- Standard screenshots: ${report.standardCaptured}/${report.standardTarget}`,
  `- Interaction screenshots: ${report.interactionCaptured}`,
  `- Total screenshots: ${report.totalCaptured}`,
  `- Image-analyzed: ${report.imageAnalyzed}`,
  `- Blockers: ${report.blockers.length}`,
  `- Warnings: ${report.warnings.length}`,
  '',
  '## Blockers',
  ...(report.blockers.length ? report.blockers.map((x) => `- ${x.key}: ${x.kind}`) : ['- None']),
  '',
  '## Warnings',
  ...(report.warnings.length ? report.warnings.map((x) => `- ${x.key}: ${x.kind}`) : ['- None'])
].join('\n');
await fs.writeFile(path.join(ROOT,'summary.md'), summary);
console.log(summary);

if (report.standardCaptured !== report.standardTarget || report.blockers.length || report.warnings.length) process.exitCode = 1;
