import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';

const BASE = process.env.QA_BASE_URL;
if (!BASE) throw new Error('QA_BASE_URL is required');

const ROOT = path.join('qa-artifacts', 'craft-grade');
const phaseSlugs = ['phase1','phase2','phase3','phase4','phase5','phase6','phase6b','phase7','phase8','phase9','phase10','phase10r','phase11','phase12','phase13a','phase13b','phase13c','phase14','phase15','phase16','phase17','phase18','phase19','phase20','phase21','phase22'];
const legacySlugs = ['phase1','phase2','phase3','phase4','phase5','phase6','phase6b','phase7','phase8','phase9','phase10','phase10r'];
const frozenSlugs = ['phase12','phase13a','phase13b','phase13c','phase14','phase15','phase16','phase17','phase18','phase19','phase20','phase21','phase22'];
const routes = ['/', '/phases/', ...phaseSlugs.map((slug) => `/phases/${slug}/`)];
const phaseRoutes = phaseSlugs.map((slug) => `/phases/${slug}/`);
const legacyRoutes = legacySlugs.map((slug) => `/phases/${slug}/`);
const frozenRoutes = frozenSlugs.map((slug) => `/phases/${slug}/`);
const viewports = [
  { name:'desktop', width:1440, height:1000 },
  { name:'phone', width:390, height:844, isMobile:true, hasTouch:true }
];

await fs.rm(ROOT, { recursive:true, force:true });
await fs.mkdir(ROOT, { recursive:true });

const observations = [];
const browser = await chromium.launch({ headless:true });
try {
  for (const vp of viewports) {
    const context = await browser.newContext({
      viewport:{ width:vp.width, height:vp.height },
      isMobile:!!vp.isMobile,
      hasTouch:!!vp.hasTouch,
      reducedMotion:'reduce'
    });

    for (const route of routes) {
      const page = await context.newPage();
      const consoleErrors = [];
      const failedRequests = [];
      page.on('pageerror', (error) => consoleErrors.push(String(error?.message || error)));
      page.on('console', (message) => { if (message.type() === 'error') consoleErrors.push(message.text()); });
      page.on('requestfailed', (request) => failedRequests.push({ url:request.url(), error:request.failure()?.errorText || 'failed' }));

      const response = await page.goto(`${BASE}${route}?craft_grade=1`, { waitUntil:'domcontentloaded', timeout:45000 });
      if (phaseRoutes.includes(route)) {
        await page.waitForFunction(() => document.documentElement.dataset.phaseCraft === 'ready', null, { timeout:10000 }).catch(() => {});
      }
      await page.waitForFunction(() => document.documentElement.dataset.finalConvergence === 'ready', null, { timeout:10000 }).catch(() => {});
      await page.waitForTimeout(450);
      await page.evaluate(async () => {
        await Promise.all([...document.images].map((img) => img.decode?.().catch(() => undefined)));
        window.scrollTo(0,0);
      }).catch(() => {});

      const metrics = await page.evaluate(({ route, phone }) => {
        const visible = (el) => {
          if (!el) return false;
          const s = getComputedStyle(el); const r = el.getBoundingClientRect();
          return s.display !== 'none' && s.visibility !== 'hidden' && Number(s.opacity || 1) > 0 && r.width > 0 && r.height > 0;
        };
        const css = (el) => el ? getComputedStyle(el) : null;
        const text = document.body.innerText || '';
        const h1 = document.querySelector('h1');
        const phase = /^\/phases\/phase/i.test(route);
        const legacy = document.body.classList.contains('archive-shell');
        const phase11 = document.body.classList.contains('phase11-polish');
        const frozen = phase && !legacy && !phase11;
        const role = document.querySelector('.phase-role-card');
        const roleStyle = css(role);
        const roleLabel = document.querySelector('.phase-role-card__label span')?.textContent.trim() || '';
        const roleQuestion = document.querySelector('.phase-role-card__question-label')?.textContent.trim() || '';
        const roleSignal = document.querySelector('.phase-role-card__signal span')?.textContent.trim() || '';
        const unified = document.querySelector('.phase-unified-nav');
        const mobileToggle = document.querySelector('.mobile-menu-toggle, .archive-menu-toggle');
        const editorial = document.querySelector('.phase-editorial-photo');
        const editorialFrame = editorial?.querySelector('.phase-editorial-photo__frame');
        const editorialCaption = editorial?.querySelector('figcaption')?.textContent || '';
        const controls = [...document.querySelectorAll('a,button,input,select,textarea,[role="button"]')].filter(visible);
        const smallTargets = phone ? controls.map((el) => {
          const r = el.getBoundingClientRect();
          return { text:(el.getAttribute('aria-label') || el.textContent || '').trim().slice(0,50), w:r.width, h:r.height };
        }).filter((x) => x.w < 40 || x.h < 40) : [];
        const links = [...(unified?.querySelectorAll('a') || [])].map((a) => ({ text:a.textContent.trim(), href:a.getAttribute('href') || '' }));
        const brokenImages = [...document.images].filter((img) => !img.complete || img.naturalWidth === 0).map((img) => img.currentSrc || img.src);
        const localStyles = [...document.styleSheets].map((sheet) => sheet.href || '').filter(Boolean);
        return {
          phase, legacy, phase11, frozen,
          main:!!document.querySelector('main'),
          h1Count:document.querySelectorAll('h1').length,
          h1Size:h1 ? parseFloat(css(h1).fontSize) : 0,
          scrollWidth:document.documentElement.scrollWidth,
          clientWidth:document.documentElement.clientWidth,
          scrollHeight:document.documentElement.scrollHeight,
          mobileToggleVisible:visible(mobileToggle),
          smallTargets,
          rolePresent:!!role,
          roleLabel, roleQuestion, roleSignal,
          roleBackground:roleStyle?.backgroundColor || '',
          roleRadius:roleStyle ? parseFloat(roleStyle.borderTopLeftRadius) : -1,
          roleBorderTop:roleStyle?.borderTopStyle || '',
          roleBorderBottom:roleStyle?.borderBottomStyle || '',
          unifiedVisible:visible(unified),
          unifiedLinks:links,
          craftReady:document.documentElement.dataset.phaseCraft || '',
          convergenceReady:document.documentElement.dataset.finalConvergence || '',
          genericSnapshot:text.includes('What was this phase trying to fix?'),
          genericSystem:text.includes('How this version works.'),
          genericEvidence:text.includes('What the recorded result actually showed.'),
          genericSupports:text.includes('What this phase supports.'),
          genericExplore:text.includes('Explore the case study'),
          lockedSource:text.includes('Locked source record'),
          fixedRecordLabel:text.includes('Why the record stays fixed'),
          editorialPresent:!!editorial,
          editorialHeight:editorialFrame?.getBoundingClientRect().height || 0,
          editorialCaption,
          brokenImages,
          archiveCategories:document.querySelectorAll('.archive-category').length,
          archiveCards:document.querySelectorAll('.archive-card.phase-personalized').length,
          archiveIdentities:document.querySelectorAll('.archive-card__identity').length,
          frozenCards:document.querySelectorAll('.archive-card[data-frozen="true"]').length,
          historicalCards:document.querySelectorAll('.archive-card[data-frozen="false"]').length,
          bodyText:text,
          styles:localStyles
        };
      }, { route, phone:vp.name === 'phone' });

      observations.push({
        key:`${vp.name}:${route}`,
        viewport:vp.name,
        route,
        status:response?.status() || 0,
        metrics,
        consoleErrors:consoleErrors.filter((x) => !/favicon|ERR_BLOCKED_BY_CLIENT/i.test(x)),
        failedRequests:failedRequests.filter((x) => !/favicon|github\.com|linkedin\.com|wikimedia\.org|nasa\.gov/i.test(x.url))
      });
      await page.close();
    }
    await context.close();
  }
} finally {
  await browser.close();
}

const obs = (viewport, route) => observations.find((x) => x.viewport === viewport && x.route === route);
const all = (fn) => observations.every(fn);
const onRoutes = (targetRoutes, fn) => observations.filter((x) => targetRoutes.includes(x.route)).every(fn);
const phaseObs = observations.filter((x) => phaseRoutes.includes(x.route));
const legacyObs = observations.filter((x) => legacyRoutes.includes(x.route));
const frozenObs = observations.filter((x) => frozenRoutes.includes(x.route));
const desktopObs = observations.filter((x) => x.viewport === 'desktop');
const phoneObs = observations.filter((x) => x.viewport === 'phone');

const gates = [];
const gate = (name, pass, detail) => gates.push({ name, pass:Boolean(pass), detail });

// 01-05: basic product integrity.
gate('01 · Every public route loads', all((x) => x.status >= 200 && x.status < 400), '28 routes × desktop/phone');
gate('02 · Semantic shell stays intact', all((x) => x.metrics.main && x.metrics.h1Count === 1), 'one <main> and one <h1> on every route');
gate('03 · No horizontal overflow', all((x) => x.metrics.scrollWidth - x.metrics.clientWidth <= 2), 'desktop and 390px phone');
gate('04 · Browser console stays clean', all((x) => x.consoleErrors.length === 0), 'no uncaught/page console errors');
gate('05 · Local assets and images stay healthy', all((x) => x.failedRequests.length === 0 && x.metrics.brokenImages.length === 0), 'no failed local requests or broken images');

// 06-10: interaction and hierarchy.
gate('06 · Navigation responds by viewport', desktopObs.every((x) => !x.metrics.mobileToggleVisible) && phoneObs.filter((x) => x.route !== '/phases/').every((x) => x.metrics.mobileToggleVisible), 'mobile controls stay on phone only');
gate('07 · Phone controls remain tappable', phoneObs.every((x) => x.metrics.smallTargets.length === 0), 'all visible controls at least 40×40px');
gate('08 · Phase titles stay editorial, not billboard-sized', phaseObs.every((x) => x.viewport === 'desktop' ? x.metrics.h1Size <= 49 : x.metrics.h1Size <= 35), '≤49px desktop / ≤35px phone');
gate('09 · Every phase names its actual question', phaseObs.every((x) => x.metrics.roleQuestion === 'Central question'), '26 phase routes, both viewports');
gate('10 · Every phase has one predictable ending', phaseObs.every((x) => x.metrics.unifiedVisible && x.metrics.unifiedLinks.length === 3 && x.metrics.unifiedLinks.some((l) => l.text === 'All phases')), 'Previous / All phases / Next');

// 11-16: human-made craft and phase-specific language.
gate('11 · Craft layer reaches every phase', phaseObs.every((x) => x.metrics.craftReady === 'ready' && x.metrics.styles.some((href) => href.includes('/craft-polish.css'))), 'craft-polish.css loaded on all 26 phase routes');
gate('12 · Phase metadata reads like an editorial note', phaseObs.every((x) => x.metrics.rolePresent && x.metrics.roleLabel === 'Place in the program' && x.metrics.roleSignal === 'Signal' && x.metrics.roleRadius === 0 && x.metrics.roleBorderTop !== 'none' && x.metrics.roleBorderBottom !== 'none'), 'rule-based metadata; no rounded chatbot card');
gate('13 · Legacy phases no longer repeat generic template headings', legacyObs.every((x) => !x.metrics.genericSnapshot && !x.metrics.genericSystem && !x.metrics.genericEvidence), 'phase-specific context/system language');
gate('14 · Legacy CTA copy is research-first', legacyObs.every((x) => !x.metrics.genericExplore), 'no “Explore the case study” marketing copy');
gate('15 · Frozen findings use phase identity', frozenObs.every((x) => !x.metrics.genericSupports), 'no repeated “What this phase supports.”');
gate('16 · Frozen source/freeze language is explicit', frozenObs.every((x) => x.metrics.lockedSource && x.metrics.fixedRecordLabel), 'Locked source record + Why the record stays fixed');

// 17-19: photography, archive architecture, and restrained surface language.
gate('17 · Photography stays contextual, not evidentiary', phaseObs.every((x) => x.metrics.editorialPresent && /not AegisLand experimental evidence/i.test(x.metrics.editorialCaption) && (x.viewport === 'desktop' ? x.metrics.editorialHeight <= 430 : x.metrics.editorialHeight <= 260)), 'captioned context photography under strict size caps');
const archiveDesktop = obs('desktop','/phases/');
const archivePhone = obs('phone','/phases/');
gate('18 · Archive remains a complete six-chapter map', [archiveDesktop,archivePhone].every((x) => x && x.metrics.archiveCategories === 6 && x.metrics.archiveCards === 26 && x.metrics.archiveIdentities === 26 && x.metrics.frozenCards === 13 && x.metrics.historicalCards === 13), '6 categories / 26 phases / 13 frozen + 13 historical');
gate('19 · Phase metadata avoids rounded-card soup', phaseObs.every((x) => x.metrics.roleBackground === 'rgba(0, 0, 0, 0)' || x.metrics.roleBackground === 'transparent'), 'metadata surface is transparent on every phase');

// 20: frozen scientific integrity. These exact public facts must survive every craft pass.
const home = obs('desktop','/');
const archive = obs('desktop','/phases/');
const phase22 = obs('desktop','/phases/phase22/');
const sciencePass = Boolean(home && archive && phase22)
  && home.metrics.bodyText.includes('0.8319')
  && home.metrics.bodyText.includes('0.7744')
  && home.metrics.bodyText.includes('100%')
  && home.metrics.bodyText.includes('10 / 10 locked gates passed')
  && home.metrics.bodyText.includes('6 PASS / 7 FAIL')
  && archive.metrics.frozenCards === 13
  && phase22.metrics.bodyText.includes('0.8319')
  && phase22.metrics.bodyText.includes('0.7744')
  && phase22.metrics.bodyText.includes('100%')
  && phase22.metrics.bodyText.includes('0ddc968b8bd48c2de6d904194b417854913389a8927cff0b15b96c6501f8294c')
  && phase22.metrics.bodyText.includes('62e75d7b39088c2e66f1cc6be4d180501b79632f2f6847af1fbe0bd96be17551')
  && phase22.metrics.bodyText.includes('simulation_only=true')
  && phase22.metrics.bodyText.includes('safety_acceptance=false')
  && phase22.metrics.bodyText.includes('controller_tuning_allowed=false');
gate('20 · Craft changes never rewrite the science', sciencePass, 'Phase 22 metrics/hashes/boundary + 6 PASS / 7 FAIL frozen lineage');

const passed = gates.filter((g) => g.pass).length;
const report = { base:BASE, score:passed, total:gates.length, gates, observations, finishedAt:new Date().toISOString() };
await fs.writeFile(path.join(ROOT,'report.json'), JSON.stringify(report,null,2));
const summary = [
  '# AegisLand human craft grade',
  '',
  `- Score: ${passed} / ${gates.length}`,
  `- Routes checked: ${routes.length}`,
  `- Viewports: desktop + phone`,
  '',
  ...gates.map((g) => `- ${g.pass ? 'PASS' : 'FAIL'} — ${g.name} — ${g.detail}`)
].join('\n');
await fs.writeFile(path.join(ROOT,'summary.md'), summary);
console.log(summary);
if (passed !== gates.length) process.exit(1);
