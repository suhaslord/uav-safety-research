import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';
import sharp from 'sharp';

const BASE = process.env.QA_BASE_URL;
if (!BASE) throw new Error('QA_BASE_URL is required');

const ROOT = path.join('qa-artifacts', 'ui-bug-sweep-560');
const SCREENSHOTS = path.join(ROOT, 'screenshots');
const phaseSlugs = ['phase1','phase2','phase3','phase4','phase5','phase6','phase6b','phase7','phase8','phase9','phase10','phase10r','phase11','phase12','phase13a','phase13b','phase13c','phase14','phase15','phase16','phase17','phase18','phase19','phase20','phase21','phase22'];
const routes = ['/', '/phases/', ...phaseSlugs.map((slug) => `/phases/${slug}/`)];
const viewports = [
  { name:'desktop', width:1440, height:1000 },
  { name:'laptop', width:1280, height:800 },
  { name:'tablet', width:768, height:1024, hasTouch:true },
  { name:'phone', width:390, height:844, isMobile:true, hasTouch:true }
];
const menuAuditRoutes = new Set(['/', '/phases/', '/phases/phase22/']);

await fs.rm(ROOT, { recursive:true, force:true });
await fs.mkdir(SCREENSHOTS, { recursive:true });

const report = { base:BASE, routes, viewports, screenshots:[], pages:[], blockers:[], warnings:[], imageAnalyses:[], startedAt:new Date().toISOString() };
const block = (key, kind, details={}) => report.blockers.push({ key, kind, ...details });
const warn = (key, kind, details={}) => report.warnings.push({ key, kind, ...details });
const safe = (route) => route === '/' ? 'home' : route.replace(/^\/+|\/+$/g,'').replaceAll('/','-');

const browser = await chromium.launch({ headless:true });
try {
  for (const vp of viewports) {
    const context = await browser.newContext({ viewport:{width:vp.width,height:vp.height}, isMobile:!!vp.isMobile, hasTouch:!!vp.hasTouch, reducedMotion:'reduce' });
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
        response = await page.goto(`${BASE}${route}?ui_bug_sweep=1`, { waitUntil:'domcontentloaded', timeout:45000 });
        await page.waitForFunction(() => document.documentElement.dataset.finalConvergence === 'ready', null, { timeout:10000 }).catch(() => {});
        await page.waitForTimeout(350);
      } catch (error) {
        block(key, 'load-failed', { error:String(error) });
      }

      const imageCount = await page.locator('img').count().catch(() => 0);
      for (let i=0;i<imageCount;i+=1) await page.locator('img').nth(i).scrollIntoViewIfNeeded().catch(() => {});
      await page.evaluate(async () => {
        await Promise.all([...document.images].map((img) => img.decode?.().catch(() => undefined)));
        window.scrollTo(0,0);
      }).catch(() => {});
      await page.waitForTimeout(150);

      const m = await page.evaluate(({ route, width, hasTouch }) => {
        const visible = (el) => {
          if (!el) return false;
          const s = getComputedStyle(el);
          const r = el.getBoundingClientRect();
          return s.display !== 'none' && s.visibility !== 'hidden' && Number(s.opacity || 1) > 0 && r.width > 0 && r.height > 0;
        };
        const rect = (el) => {
          if (!el) return null;
          const r = el.getBoundingClientRect();
          return { left:r.left, right:r.right, top:r.top, bottom:r.bottom, width:r.width, height:r.height };
        };
        const intersects = (a,b) => a && b && Math.max(0,Math.min(a.right,b.right)-Math.max(a.left,b.left)) > 3 && Math.max(0,Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)) > 3;
        const header = document.querySelector('.site-header, .signature-nav, body.archive-shell .top');
        const brand = header?.querySelector('.brand, .signature-brand, .word');
        const mobileToggle = header?.querySelector('.mobile-menu-toggle, .archive-menu-toggle');
        const headerLinks = header ? [...header.querySelectorAll('a')].filter(visible).filter((a) => a !== brand && !a.closest('.brand,.signature-brand')) : [];
        const navigationMode = headerLinks.length ? 'links' : (visible(mobileToggle) ? 'menu' : 'none');
        const nav = header?.querySelector('.site-nav, .signature-nav__links, .nav');
        const navLinks = nav ? [...nav.querySelectorAll('a')].filter(visible) : [];
        const navRows = [...new Set(navLinks.map((a) => Math.round(a.getBoundingClientRect().top/3)*3))];
        const directHeaderChildren = header ? [...header.children].filter(visible) : [];
        const headerOverlaps = [];
        for (let i=0;i<directHeaderChildren.length;i+=1) {
          for (let j=i+1;j<directHeaderChildren.length;j+=1) {
            const a = directHeaderChildren[i]; const b = directHeaderChildren[j];
            if (intersects(rect(a),rect(b))) headerOverlaps.push(`${a.className || a.tagName} <> ${b.className || b.tagName}`);
          }
        }
        const brokenImages = [...document.images].filter((img)=>!img.complete || img.naturalWidth===0).map((img)=>img.currentSrc || img.src);
        const ids = [...document.querySelectorAll('[id]')].map((el)=>el.id).filter(Boolean);
        const duplicateIds = [...new Set(ids.filter((id,i)=>ids.indexOf(id)!==i))];
        const brokenAnchors = [...document.querySelectorAll('a[href^="#"]')].map((a)=>a.getAttribute('href')).filter((href)=>href && href!=='#' && !document.getElementById(decodeURIComponent(href.slice(1))));
        const controls = [...document.querySelectorAll('a,button,input,select,textarea,[role="button"]')].filter(visible);
        const smallTargets = hasTouch ? controls.map((el)=>{const r=el.getBoundingClientRect();return {text:(el.getAttribute('aria-label')||el.textContent||'').trim().slice(0,60),w:r.width,h:r.height};}).filter((x)=>x.w<40||x.h<40) : [];
        const offscreenControls = controls.map((el)=>{const r=el.getBoundingClientRect();return {text:(el.getAttribute('aria-label')||el.textContent||'').trim().slice(0,60),left:r.left,right:r.right,top:r.top,bottom:r.bottom};}).filter((x)=>x.left < -4 || x.right > innerWidth + 4);
        const clippedText = [...document.querySelectorAll('h1,h2,h3,p,a,button,strong,span,code')].filter(visible).map((el)=>{
          const s=getComputedStyle(el); return {el,s,text:(el.textContent||'').trim().slice(0,80)};
        }).filter(({el,s}) => !el.closest('.sr-only,[aria-hidden="true"]') && ['hidden','clip'].includes(s.overflowX) && el.scrollWidth > el.clientWidth + 6).map(({el,text})=>({tag:el.tagName,text,scrollWidth:el.scrollWidth,clientWidth:el.clientWidth}));
        const phasePage = /^\/phases\/phase/i.test(route);
        const frozen = phasePage && !document.body.classList.contains('archive-shell') && !document.body.classList.contains('phase11-polish');
        const duplicateFrozenContext = frozen && visible(document.querySelector('.phase-detail__hero .phase-identity-chip')) && visible(document.querySelector('.phase-detail__hero .workspace-context'));
        const workspaceContext = document.querySelector('.workspace-context');
        const contextSpans = workspaceContext ? [...workspaceContext.querySelectorAll(':scope > span')].filter(visible) : [];
        const contextRows = [...new Set(contextSpans.map((el)=>Math.round(el.getBoundingClientRect().top/3)*3))];
        const wrappedContextWithSeparators = width <= 900 && contextRows.length > 1 && contextSpans.slice(1).some((el)=>getComputedStyle(el,'::before').content && getComputedStyle(el,'::before').content !== 'none');
        const editorial = document.querySelector('.phase-detail .phase-editorial-photo');
        const shell = document.querySelector('.phase-detail.signature-shell, .phase-detail');
        let asymmetricContextPhoto = false;
        if (frozen && visible(editorial) && visible(shell) && width > 1040) {
          const er = editorial.getBoundingClientRect(); const sr = shell.getBoundingClientRect();
          const leftGap = Math.abs(er.left - sr.left); const rightGap = Math.abs(sr.right - er.right);
          asymmetricContextPhoto = er.width < sr.width * .88 && leftGap < 8 && rightGap > leftGap + 80;
        }
        const firstMainVisible = [...document.querySelectorAll('main > *, #phaseRoot > *, .archive-main > *')].find(visible);
        const headerGap = header && firstMainVisible ? firstMainVisible.getBoundingClientRect().top - header.getBoundingClientRect().bottom : 0;
        return {
          ready:document.documentElement.dataset.finalConvergence || '',
          main:!!document.querySelector('main'),
          h1Count:document.querySelectorAll('h1').length,
          scrollWidth:document.documentElement.scrollWidth,
          clientWidth:document.documentElement.clientWidth,
          scrollHeight:document.documentElement.scrollHeight,
          navigationMode,
          visibleHeaderLinks:headerLinks.length,
          mobileToggleVisible:visible(mobileToggle),
          navRows:navRows.length,
          headerOverlaps,
          brokenImages,duplicateIds,brokenAnchors:[...new Set(brokenAnchors)],smallTargets,offscreenControls,clippedText,
          duplicateFrozenContext,wrappedContextWithSeparators,asymmetricContextPhoto,headerGap
        };
      }, { route, width:vp.width, hasTouch:!!vp.hasTouch });

      const status = response?.status() || 0;
      if (!status || status >= 400) block(key,'bad-status',{status});
      if (!m.main || m.h1Count !== 1) block(key,'semantic-shell',{main:m.main,h1Count:m.h1Count});
      if (m.ready !== 'ready') block(key,'final-convergence-css-not-ready');
      if (m.scrollWidth - m.clientWidth > 2) block(key,'horizontal-overflow',{overflow:m.scrollWidth-m.clientWidth});
      if (m.navigationMode === 'none') block(key,'no-reachable-header-navigation');
      if (vp.width >= 901 && m.navigationMode !== 'links') block(key,'desktop-navigation-replaced-or-missing',{mode:m.navigationMode});
      if (vp.width <= 900 && m.navigationMode === 'links' && m.navRows > 1) block(key,'wrapped-tablet-mobile-nav',{rows:m.navRows});
      if (m.headerOverlaps.length) block(key,'header-control-overlap',{examples:m.headerOverlaps.slice(0,6)});
      if (m.brokenImages.length) block(key,'broken-images',{images:m.brokenImages});
      if (m.duplicateIds.length) block(key,'duplicate-ids',{ids:m.duplicateIds});
      if (m.brokenAnchors.length) block(key,'broken-anchors',{anchors:m.brokenAnchors});
      if (m.offscreenControls.length) block(key,'offscreen-controls',{examples:m.offscreenControls.slice(0,8)});
      if (m.clippedText.length) warn(key,'clipped-text',{count:m.clippedText.length,examples:m.clippedText.slice(0,8)});
      if (m.smallTargets.length) warn(key,'small-touch-targets',{count:m.smallTargets.length,examples:m.smallTargets.slice(0,8)});
      if (m.duplicateFrozenContext) warn(key,'duplicate-frozen-hero-context');
      if (m.wrappedContextWithSeparators) warn(key,'wrapped-context-separators');
      if (m.asymmetricContextPhoto) warn(key,'asymmetric-frozen-context-photo');
      if (m.headerGap > (vp.width <= 900 ? 150 : 190)) warn(key,'large-header-to-content-gap',{gap:m.headerGap});

      const filteredConsole = consoleErrors.filter((x)=>!/favicon|ERR_BLOCKED_BY_CLIENT/i.test(x));
      const filteredRequests = failedRequests.filter((x)=>!/favicon|github\.com|linkedin\.com/i.test(x.url));
      if (filteredConsole.length) block(key,'console-errors',{errors:filteredConsole});
      if (filteredRequests.length) block(key,'network-errors',{requests:filteredRequests});

      const prefix = `${safe(route)}-${vp.name}`;
      await page.screenshot({path:path.join(SCREENSHOTS,`${prefix}-00-full.png`),fullPage:true});
      report.screenshots.push({viewport:vp.name,route,kind:'full'});
      const maxScroll = Math.max(0,m.scrollHeight-vp.height);
      for (const [i,fraction] of [0,.33,.66,1].entries()) {
        await page.evaluate((y)=>window.scrollTo(0,y),Math.round(maxScroll*fraction));
        await page.waitForTimeout(80);
        await page.screenshot({path:path.join(SCREENSHOTS,`${prefix}-${String(i+1).padStart(2,'0')}-${Math.round(fraction*100)}pct.png`)});
        report.screenshots.push({viewport:vp.name,route,kind:`${fraction}`});
      }

      if (vp.hasTouch && menuAuditRoutes.has(route) && m.mobileToggleVisible) {
        await page.evaluate(()=>window.scrollTo(0,0));
        const toggle = page.locator('.mobile-menu-toggle, .archive-menu-toggle').first();
        await toggle.click().catch(()=>{});
        await page.waitForTimeout(100);
        const menuState = await page.evaluate(() => {
          const sheet = document.querySelector('.mobile-menu-sheet, .archive-menu-sheet');
          const toggle = document.querySelector('.mobile-menu-toggle, .archive-menu-toggle');
          const s = sheet ? getComputedStyle(sheet) : null; const r = sheet?.getBoundingClientRect();
          const visible = !!sheet && s.display !== 'none' && s.visibility !== 'hidden' && Number(s.opacity||1)>0 && r.width>0 && r.height>0;
          const links = sheet ? [...sheet.querySelectorAll('a')].filter((a)=>{const q=getComputedStyle(a);const z=a.getBoundingClientRect();return q.display!=='none'&&q.visibility!=='hidden'&&z.width>0&&z.height>0;}) : [];
          return { expanded:toggle?.getAttribute('aria-expanded'), hidden:sheet?.getAttribute('aria-hidden'), visible, links:links.length, right:r?.right||0, left:r?.left||0 };
        });
        if (menuState.expanded !== 'true' || menuState.hidden !== 'false' || !menuState.visible || menuState.links < 2) block(`${key}:menu`,'mobile-menu-open-state-broken',menuState);
        if (menuState.left < -3 || menuState.right > vp.width + 3) block(`${key}:menu`,'mobile-menu-offscreen',menuState);
        await page.screenshot({path:path.join(SCREENSHOTS,`${prefix}-05-menu-open.png`)});
        report.screenshots.push({viewport:vp.name,route,kind:'menu-open'});
        await page.keyboard.press('Escape').catch(()=>{});
        await page.waitForTimeout(80);
        const closed = await page.evaluate(() => ({ expanded:document.querySelector('.mobile-menu-toggle, .archive-menu-toggle')?.getAttribute('aria-expanded'), hidden:document.querySelector('.mobile-menu-sheet, .archive-menu-sheet')?.getAttribute('aria-hidden') }));
        if (closed.expanded !== 'false' || closed.hidden !== 'true') block(`${key}:menu`,'mobile-menu-escape-close-broken',closed);
      }

      report.pages.push({key,route,viewport:vp.name,status,metrics:m});
      await page.close();
    }
    await context.close();
  }
} finally { await browser.close(); }

const files = (await fs.readdir(SCREENSHOTS)).filter((name)=>name.endsWith('.png')).sort();
for (const name of files) {
  const file = path.join(SCREENSHOTS,name);
  const stat = await fs.stat(file);
  const image = sharp(file,{failOn:'error'});
  const [metadata,stats] = await Promise.all([image.metadata(),image.stats()]);
  const stdev = stats.channels.map((c)=>Number(c.stdev.toFixed(3)));
  const entropy = Number((stats.entropy ?? 0).toFixed(4));
  const suspiciouslyFlat = entropy < .02 && Math.max(...stdev) < .5;
  const suspiciouslyTiny = stat.size < 3500;
  const item = {file:name,bytes:stat.size,width:metadata.width||0,height:metadata.height||0,entropy,stdev,suspiciouslyFlat,suspiciouslyTiny};
  report.imageAnalyses.push(item);
  if (suspiciouslyFlat || suspiciouslyTiny || !item.width || !item.height) block(name,'image-level-render-anomaly',item);
}

const standardExpected = routes.length * viewports.length * 5;
if (files.length < standardExpected) block('global','screenshot-count-below-560',{count:files.length,expected:standardExpected});
if (report.imageAnalyses.length !== files.length) block('global','missing-image-analysis',{screenshots:files.length,analyses:report.imageAnalyses.length});
report.finishedAt = new Date().toISOString();
report.screenshotCount = files.length;
report.expectedMinimum = standardExpected;
await fs.writeFile(path.join(ROOT,'report.json'),JSON.stringify(report,null,2));
const summary = [
  '# AegisLand strict 560+ screenshot UI bug sweep',
  '',
  `- Base: ${BASE}`,
  `- Standard minimum: ${standardExpected}`,
  `- Screenshots captured: ${files.length}`,
  `- Screenshots image-analyzed: ${report.imageAnalyses.length}`,
  `- Blockers: ${report.blockers.length}`,
  `- Warnings: ${report.warnings.length}`,
  '',
  '## Blockers',
  ...(report.blockers.length ? report.blockers.map((x)=>`- ${x.key} — ${x.kind}`) : ['- None']),
  '',
  '## Warnings',
  ...(report.warnings.length ? report.warnings.map((x)=>`- ${x.key} — ${x.kind}`) : ['- None'])
].join('\n');
await fs.writeFile(path.join(ROOT,'summary.md'),summary);
console.log(summary);
if (report.blockers.length || report.warnings.length) process.exit(1);
