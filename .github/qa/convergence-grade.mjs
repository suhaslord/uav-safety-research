import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';

const BASE = process.env.QA_BASE_URL;
if (!BASE) throw new Error('QA_BASE_URL is required');

const ROOT = path.join('qa-artifacts', 'convergence-grade');
const SCREENSHOTS = path.join(ROOT, 'screenshots');
const phaseSlugs = ['phase1','phase2','phase3','phase4','phase5','phase6','phase6b','phase7','phase8','phase9','phase10','phase10r','phase11','phase12','phase13a','phase13b','phase13c','phase14','phase15','phase16','phase17','phase18','phase19','phase20','phase21','phase22'];
const routes = ['/', '/phases/', ...phaseSlugs.map((slug) => `/phases/${slug}/`)];
const viewports = [
  { name:'desktop', width:1440, height:1000 },
  { name:'phone', width:390, height:844, isMobile:true, hasTouch:true }
];

await fs.rm(ROOT, { recursive:true, force:true });
await fs.mkdir(SCREENSHOTS, { recursive:true });

const report = { base:BASE, routes, viewports, screenshots:[], pages:[], blockers:[], warnings:[], startedAt:new Date().toISOString() };
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
        response = await page.goto(`${BASE}${route}?convergence_grade=1`, { waitUntil:'domcontentloaded', timeout:45000 });
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

      const m = await page.evaluate(({route, phone}) => {
        const visible = (el) => {
          if (!el) return false;
          const s = getComputedStyle(el); const r = el.getBoundingClientRect();
          return s.display !== 'none' && s.visibility !== 'hidden' && Number(s.opacity || 1) > 0 && r.width > 0 && r.height > 0;
        };
        const style = (el) => el ? getComputedStyle(el) : null;
        const phasePage = /^\/phases\/phase/i.test(route);
        const legacy = document.body.classList.contains('archive-shell');
        const phase11 = document.body.classList.contains('phase11-polish');
        const frozen = phasePage && !legacy && !phase11;
        const h1 = document.querySelector('h1');
        const editorial = document.querySelector('.phase-editorial-photo');
        const railSection = document.querySelector('.phase-rail-section');
        const rail = document.querySelector('.phase-rail');
        const compactRail = document.querySelector('.phase-progress-compact');
        const oldSwitcher = document.querySelector('.switcher');
        const oldFrozenNav = document.querySelector('.phase-detail__nav');
        const oldPhase11Jump = document.querySelector('.phase11-jump');
        const unified = document.querySelector('.phase-unified-nav');
        const roleQuestionLabel = document.querySelector('.phase-role-card__question-label');
        const mobileToggle = document.querySelector('.mobile-menu-toggle');
        const back = document.querySelector('.phase-detail__back');
        const contextHeading = document.querySelector('.phase-detail__context-grid h2');
        const hash = document.querySelector('.phase-hash, .provenance code, .signature-footer code');
        const nav = document.querySelector('.top .nav, .site-nav, .signature-nav__links');
        const navText = nav ? [...nav.querySelectorAll('a')].map((a)=>a.textContent.trim()) : [];
        const brokenImages = [...document.images].filter((img)=>!img.complete || img.naturalWidth===0).map((img)=>img.currentSrc || img.src);
        const ids = [...document.querySelectorAll('[id]')].map((el)=>el.id).filter(Boolean);
        const duplicateIds = [...new Set(ids.filter((id,i)=>ids.indexOf(id)!==i))];
        const brokenAnchors = [...document.querySelectorAll('a[href^="#"]')].map((a)=>a.getAttribute('href')).filter((href)=>href && href!=='#' && !document.getElementById(decodeURIComponent(href.slice(1))));
        const controls = [...document.querySelectorAll('a,button,input,select,textarea,[role="button"]')].filter(visible);
        const smallTargets = phone ? controls.map((el)=>{const r=el.getBoundingClientRect();return {text:(el.getAttribute('aria-label')||el.textContent||'').trim().slice(0,60),w:r.width,h:r.height};}).filter((x)=>x.w<40||x.h<40) : [];
        return {
          ready:document.documentElement.dataset.finalConvergence || '',
          scrollWidth:document.documentElement.scrollWidth,
          clientWidth:document.documentElement.clientWidth,
          scrollHeight:document.documentElement.scrollHeight,
          h1Count:document.querySelectorAll('h1').length,
          h1Size:h1?parseFloat(style(h1).fontSize):0,
          phasePage,legacy,phase11,frozen,
          mobileToggleVisible:visible(mobileToggle),
          roleQuestionLabel:roleQuestionLabel?.textContent.trim() || '',
          unifiedVisible:visible(unified),
          oldSwitcherVisible:visible(oldSwitcher),
          oldFrozenNavVisible:visible(oldFrozenNav),
          oldPhase11JumpVisible:visible(oldPhase11Jump),
          railPosition:railSection?style(railSection).position:'',
          railVisible:visible(rail),
          compactRailVisible:visible(compactRail),
          editorialHeight:editorial?.querySelector('.phase-editorial-photo__frame')?.getBoundingClientRect().height || 0,
          backVisible:visible(back),
          contextHeadingSize:contextHeading?parseFloat(style(contextHeading).fontSize):0,
          hashSize:hash?parseFloat(style(hash).fontSize):0,
          navText,
          brokenImages,duplicateIds,brokenAnchors:[...new Set(brokenAnchors)],smallTargets,
          main:!!document.querySelector('main')
        };
      }, { route, phone:vp.name==='phone' });

      const status = response?.status() || 0;
      if (!status || status >= 400) block(key,'bad-status',{status});
      if (!m.main || m.h1Count !== 1) block(key,'semantic-shell',{main:m.main,h1Count:m.h1Count});
      if (m.ready !== 'ready') block(key,'final-convergence-css-not-ready');
      if (m.scrollWidth - m.clientWidth > 2) block(key,'horizontal-overflow',{overflow:m.scrollWidth-m.clientWidth});
      if (m.brokenImages.length) block(key,'broken-images',{images:m.brokenImages});
      if (m.duplicateIds.length) block(key,'duplicate-ids',{ids:m.duplicateIds});
      if (m.brokenAnchors.length) block(key,'broken-anchors',{anchors:m.brokenAnchors});
      if (vp.name==='desktop' && m.mobileToggleVisible) block(key,'desktop-mobile-menu-visible');
      if (vp.name==='phone' && route !== '/phases/' && !m.mobileToggleVisible) warn(key,'phone-menu-not-visible');
      if (vp.name==='phone' && m.smallTargets.length) warn(key,'small-phone-targets',{count:m.smallTargets.length,examples:m.smallTargets.slice(0,8)});

      if (m.phasePage) {
        if (m.roleQuestionLabel !== 'Central question') block(key,'central-question-label-missing');
        if (!m.unifiedVisible) block(key,'unified-bottom-nav-missing');
        if (vp.name==='desktop' && m.h1Size > 49) block(key,'phase-title-too-large',{size:m.h1Size});
        if (vp.name==='phone' && m.h1Size > 35) block(key,'phone-phase-title-too-large',{size:m.h1Size});
        if (m.editorialHeight && vp.name==='desktop' && m.editorialHeight > 430) block(key,'context-photo-too-dominant',{height:m.editorialHeight});
        if (m.editorialHeight && vp.name==='phone' && m.editorialHeight > 260) block(key,'phone-context-photo-too-dominant',{height:m.editorialHeight});
        if (m.legacy) {
          if (m.railPosition === 'sticky' || m.railPosition === 'fixed') block(key,'legacy-rail-overlays-content',{position:m.railPosition});
          if (vp.name==='phone' && m.railVisible) block(key,'full-legacy-rail-visible-on-phone');
          if (vp.name==='phone' && !m.compactRailVisible) block(key,'compact-legacy-rail-missing');
          if (m.oldSwitcherVisible) block(key,'old-legacy-footer-visible');
          if (vp.name==='desktop' && m.scrollHeight > 7600) warn(key,'legacy-page-still-too-long',{height:m.scrollHeight});
          if (vp.name==='phone' && m.scrollHeight > 9000) warn(key,'legacy-phone-page-still-too-long',{height:m.scrollHeight});
        }
        if (m.phase11 && m.oldPhase11JumpVisible) block(key,'old-phase11-jump-visible');
        if (m.frozen) {
          if (m.oldFrozenNavVisible) block(key,'old-frozen-nav-visible');
          if (m.backVisible) warn(key,'duplicate-frozen-back-control');
          if (m.contextHeadingSize > 31) warn(key,'frozen-policy-heading-too-large',{size:m.contextHeadingSize});
          if (m.hashSize && m.hashSize < 12) warn(key,'provenance-too-small',{size:m.hashSize});
        }
      }

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
      report.pages.push({key,route,viewport:vp.name,status,metrics:m});
      await page.close();
    }
    await context.close();
  }
} finally { await browser.close(); }

const counts = Object.fromEntries(viewports.map((vp)=>[vp.name,report.screenshots.filter((s)=>s.viewport===vp.name).length]));
if ((counts.desktop||0) !== 140) block('global','desktop-screenshot-count',{count:counts.desktop||0});
if ((counts.phone||0) !== 140) block('global','phone-screenshot-count',{count:counts.phone||0});
report.finishedAt = new Date().toISOString();
report.counts = counts;
report.grade = Math.max(0, 10 - report.blockers.length - report.warnings.length * 0.2);
await fs.writeFile(path.join(ROOT,'report.json'),JSON.stringify(report,null,2));
const summary = [
  '# AegisLand convergence grade',
  '',
  `- Preview: ${BASE}`,
  `- Desktop screenshots: ${counts.desktop||0}`,
  `- Phone screenshots: ${counts.phone||0}`,
  `- Blockers: ${report.blockers.length}`,
  `- Warnings: ${report.warnings.length}`,
  `- Grade: ${report.grade.toFixed(1)} / 10`,
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
