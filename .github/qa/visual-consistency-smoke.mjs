import { chromium } from 'playwright';
import fsSync from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const BASE = process.env.QA_BASE_URL || 'http://127.0.0.1:4173';
const results = [];
const temporaryUploads = [];
let failed = 0;
const add = (name, ok, details = {}) => { results.push({ name, ok, ...details }); if (!ok) failed++; };

const routes = [
  '/', '/model-vase/', '/phases/', '/failure-atlas/', '/reproduce/',
  '/phases/phase1/', '/phases/phase2/', '/phases/phase3/', '/phases/phase4/', '/phases/phase5/',
  '/phases/phase6/', '/phases/phase6b/', '/phases/phase7/', '/phases/phase8/', '/phases/phase9/',
  '/phases/phase10/', '/phases/phase10r/', '/phases/phase11/', '/phases/phase12/',
  '/phases/phase13a/', '/phases/phase13b/', '/phases/phase13c/', '/phases/phase14/', '/phases/phase15/',
  '/phases/phase16/', '/phases/phase17/', '/phases/phase18/', '/phases/phase19/', '/phases/phase20/',
  '/phases/phase21/', '/phases/phase22/', '/phases/phase23/', '/phases/phase24/', '/phases/phase25/'
];

const launchOptions = { headless: true };
if (process.platform === 'win32' && fsSync.existsSync('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe')) {
  launchOptions.executablePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
}
const browser = await chromium.launch(launchOptions);
try {
  for (const viewport of [
    { name: 'desktop', width: 1440, height: 1000 },
    { name: 'small-desktop', width: 1180, height: 1000 },
    { name: 'compact', width: 1040, height: 1000 },
    { name: 'tablet', width: 820, height: 1180 }
  ]) {
    const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height }, reducedMotion: 'reduce' });
    for (const route of routes) {
      const page = await context.newPage();
      const browserErrors = [];
      page.on('pageerror', error => browserErrors.push(String(error?.message || error)));
      page.on('console', message => { if (message.type() === 'error') browserErrors.push(message.text()); });

      const response = await page.goto(BASE + route, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await page.waitForTimeout(300);
      add(`${viewport.name}-${route}-status`, !!response && response.status() >= 200 && response.status() < 400, { status: response?.status() || 0 });

      const state = await page.evaluate(() => ({
        overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        main: !!document.querySelector('main'),
        h1: document.querySelectorAll('h1').length,
        polish: [...document.querySelectorAll('link[rel="stylesheet"]')].some(link => (link.getAttribute('href') || '').startsWith('/phase-polish.css')),
        personalization: [...document.querySelectorAll('link[rel="stylesheet"]')].some(link => (link.getAttribute('href') || '').startsWith('/phase-personalization.css')),
        responsivePhaseStyle: [...document.querySelectorAll('link[rel="stylesheet"]')].some(link => (link.getAttribute('href') || '').startsWith('/phase-reading-responsive.css')),
        phaseHeroColumns: (() => {
          const element = document.querySelector('body.archive-shell .hero, .phase-detail__hero, .hero-grid');
          if (!element || getComputedStyle(element).display !== 'grid') return null;
          return getComputedStyle(element).gridTemplateColumns.trim().split(/\s+/).filter(Boolean).length;
        })(),
        phaseStoryColumns: (() => {
          const element = document.querySelector('body.archive-shell .story-pair');
          if (!element || getComputedStyle(element).display !== 'grid') return null;
          return getComputedStyle(element).gridTemplateColumns.trim().split(/\s+/).filter(Boolean).length;
        })(),
        phaseBodyColumns: (() => {
          const element = document.querySelector('.phase-detail__body');
          if (!element || getComputedStyle(element).display !== 'grid') return null;
          return getComputedStyle(element).gridTemplateColumns.trim().split(/\s+/).filter(Boolean).length;
        })()
      }));
      add(`${viewport.name}-${route}-no-horizontal-overflow`, state.overflow <= 1, { overflow: state.overflow });
      add(`${viewport.name}-${route}-semantic-shell`, state.main && state.h1 >= 1, { main: state.main, h1: state.h1 });
      if (/^\/phases\/(phase(?:[1-9]|10|10r|11|1[2-9][abc]?|2[0-2]|6b))\/?$/.test(route)) {
        add(`${viewport.name}-${route}-shared-phase-polish`, state.polish, { polish: state.polish });
        add(`${viewport.name}-${route}-personalization-style`, state.personalization, { personalization: state.personalization });
        add(`${viewport.name}-${route}-responsive-phase-style`, state.responsivePhaseStyle, { responsivePhaseStyle: state.responsivePhaseStyle });
        if (viewport.name !== 'desktop') {
          const phaseLayoutHasRoom = viewport.name === 'small-desktop'
            ? state.phaseHeroColumns >= 1 && state.phaseHeroColumns <= 2 && (state.phaseStoryColumns === null || state.phaseStoryColumns === 1) && (state.phaseBodyColumns === null || state.phaseBodyColumns <= 2)
            : state.phaseHeroColumns === 1 && (state.phaseStoryColumns === null || state.phaseStoryColumns === 1) && (state.phaseBodyColumns === null || state.phaseBodyColumns === 1);
          add(`${viewport.name}-${route}-phase-layout-has-room`, phaseLayoutHasRoom, {
            heroColumns: state.phaseHeroColumns,
            storyColumns: state.phaseStoryColumns,
            bodyColumns: state.phaseBodyColumns
          });
        }
      }
      add(`${viewport.name}-${route}-browser-clean`, browserErrors.length === 0, { browserErrors });
      await page.close();
    }
    await context.close();
  }

  // The desktop navigation used to disappear from 901px through 980px.
  // Check the homepage inside that range, between the existing tablet/desktop sizes.
  {
    const context = await browser.newContext({ viewport: { width: 940, height: 1000 }, reducedMotion: 'reduce' });
    const page = await context.newPage();
    const response = await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForFunction(
      () => document.documentElement.dataset.finalConvergence === 'ready',
      null,
      { timeout: 15000 }
    ).catch(() => {});
    const navigation = await page.evaluate(() => {
      const visible = (element) => {
        if (!element) return false;
        const rect = element.getBoundingClientRect();
        const style = getComputedStyle(element);
        return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
      };
      const header = document.querySelector('.site-header');
      const brand = header?.querySelector('.brand');
      const nav = header?.querySelector('.site-nav');
      const actions = header?.querySelector('.header-actions');
      const overlap = (left, right) => {
        if (!visible(left) || !visible(right)) return false;
        const a = left.getBoundingClientRect();
        const b = right.getBoundingClientRect();
        return a.left < b.right - 2 && b.left < a.right - 2 && a.top < b.bottom - 2 && b.top < a.bottom - 2;
      };
      return {
        navVisible: visible(nav),
        navLinkCount: nav?.querySelectorAll('a').length || 0,
        actionsVisible: visible(actions),
        mobileToggleVisible: visible(document.querySelector('#mobileMenuToggle')),
        headerOverlap: overlap(brand, nav) || overlap(nav, actions),
        horizontalOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth
      };
    });
    add('home-940-navigation-continuity', !!response && response.status() < 400 && navigation.navVisible && navigation.navLinkCount >= 3 && navigation.actionsVisible && !navigation.mobileToggleVisible && !navigation.headerOverlap && navigation.horizontalOverflow <= 2, { ...navigation, status: response?.status() || 0 });
    await page.close();
    await context.close();
  }

  {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
    const page = await context.newPage();
    const response = await page.goto(BASE + '/model-vase/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    const modelVase = await page.evaluate(() => ({
      heading: document.querySelector('h1')?.innerText || '',
      text: document.querySelector('main')?.innerText || '',
      markLoaded: (() => { const image = document.querySelector('.vase-brand img'); return !!image && image.complete && image.naturalWidth > 0; })(),
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      imageLoaded: (() => { const image = document.querySelector('.vase-hero__image img'); return !!image && image.complete && image.naturalWidth > 0; })()
    }));
    add('model-vase-has-original-mark-and-real-frame', !!response && response.status() < 400 && modelVase.markLoaded && modelVase.imageLoaded, { status: response?.status() || 0, ...modelVase });
    add('model-vase-states-conditional-research-answer', /not yet from real camera input/i.test(modelVase.text) && /not a newly trained vision network/i.test(modelVase.text) && /97\.6%/.test(modelVase.text) && /−13\.3 pp/.test(modelVase.text) && /Integration status/i.test(modelVase.text), { excerpt: modelVase.text.slice(0, 900) });
    await page.setViewportSize({ width: 390, height: 844 });
    add('model-vase-mobile-no-horizontal-overflow', await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth <= 1), { overflow: await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth) });
    await page.close();
    await context.close();
  }

  {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
    const page = await context.newPage();
    await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(400);

    const shell = await page.evaluate(() => document.documentElement.dataset.siteShell || '');
    add('home-frozen-native-shell', shell === 'native frozen-archive', { shell });
    const teslaStyles = await page.locator('link[href^="/aegisland.css"]').count();
    add('home-uses-tesla-style-source', teslaStyles === 1, { teslaStyles });
    const evidenceRows = await page.locator('#evidenceSpine .evidence-row').count();
    const passRows = await page.locator('#evidenceSpine .evidence-row[data-verdict="PASS"]').count();
    const failRows = await page.locator('#evidenceSpine .evidence-row[data-verdict="FAIL"]').count();
    add('home-has-complete-frozen-spine', evidenceRows === 13, { evidenceRows });
    add('home-preserves-pass-fail-record', passRows === 6 && failRows === 7, { passRows, failRows });

    const homeText = await page.locator('main').textContent() || '';
    const heroOverlay = await page.locator('#top .research-photo__frame').evaluate(element => getComputedStyle(element, '::after').backgroundImage);
    add('home-hero-photo-shaded-for-readable-copy', /linear-gradient/i.test(heroOverlay), { heroOverlay });
    add('home-current-thesis-visible', /Can the system know when its landing estimate is unreliable/i.test(homeText) && /A simulation found a recovery signal/i.test(homeText), { excerpt: homeText.slice(0, 500) });
    add('home-current-project-framing-visible', /Phase 22/i.test(homeText) && /Phase 24/i.test(homeText) && /six-condition average/i.test(homeText));
    add('home-researcher-brief-visible', /No physical-flight safety/i.test(homeText) && /same 86 protected camera frames/i.test(homeText));
    add('home-phase22-final-visible', /0\.8319/.test(homeText) && /0\.7744/.test(homeText) && /10 \/ 10 gates passed/i.test(homeText) && /100%/.test(homeText), { excerpt: homeText.slice(0, 900) });
    add('home-science-is-explicitly-frozen', /Phase 12\s*→\s*Phase 22/i.test(homeText) && /6 PASS \/ 7 FAIL/i.test(homeText) && /Final synthetic 32-cell holdout/i.test(homeText), { excerpt: homeText.slice(0, 1200) });
    const boundary = await page.locator('meta[name="aegis-evidence-boundary"]').getAttribute('content');
    add('home-claim-boundary-visible', boundary === 'simulation_only=true; safety_acceptance=false; controller_tuning_allowed=false' && /No flight-safety claim/i.test(homeText));
    const phase23Links = await page.locator('a[href*="phase23"]').count();
    add('home-links-phase23-detector', phase23Links > 0, { phase23Links });
    add('home-features-measured-baseline-atlas',
      await page.locator('#top a[href="/failure-atlas/"]').count() === 1
        && await page.locator('#phase25 .phase25-feature__images img').count() === 2
        && await page.locator('#phase25 .phase25-feature__proof a[href*="phase25_reconstruction_audit.json"]').count() === 1
        && /Baseline measured · Phase 23 pending/i.test(await page.locator('#phase25').innerText()));
    await page.close();
    await context.close();
  }

  {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
    const page = await context.newPage();
    await page.goto(BASE + '/phases/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(500);
    const categories = await page.locator('.archive-category').count();
    const categoryNav = await page.locator('#categoryNav a').count();
    const allCards = await page.locator('.archive-card.phase-personalized').count();
    const frozenCards = await page.locator('.archive-card[data-frozen="true"]').count();
    const historicalCards = await page.locator('.archive-card[data-frozen="false"]').count();
    const frozenPass = await page.locator('.archive-card[data-frozen="true"] .verdict-chip--pass').count();
    const frozenFail = await page.locator('.archive-card[data-frozen="true"] .verdict-chip--fail').count();
    const identities = await page.locator('.archive-card__identity').count();
    const questions = await page.locator('.archive-card__question').count();
    const signals = await page.locator('.archive-card__signal').count();
    const archiveText = await page.locator('main').innerText();
    const archivePolish = await page.locator('link[href^="/phase-polish.css"]').count();
    const archivePersonalization = await page.locator('link[href^="/phase-personalization.css"]').count();
    const archiveSignature = await page.locator('link[href^="/signature.css"]').count();
    await page.setViewportSize({ width: 390, height: 844 });
    const firstCategoryFits = await page.locator('#categoryNav a').first().evaluate((el) => el.scrollWidth <= el.clientWidth + 1);
    await page.setViewportSize({ width: 1440, height: 1000 });
    add('archive-has-seven-research-categories', categories === 7 && categoryNav === 7, { categories, categoryNav });
    add('archive-first-category-label-fits-on-phone', firstCategoryFits);
    add('archive-has-all-28-phase-records', allCards === 28, { allCards });
    add('archive-preserves-13-frozen-and-15-other-records', frozenCards === 13 && historicalCards === 15, { frozenCards, historicalCards });
    add('archive-preserves-6-pass-7-fail', frozenPass === 6 && frozenFail === 7, { frozenPass, frozenFail });
    add('archive-personalizes-every-card', identities === 28 && questions === 28 && signals === 28, { identities, questions, signals });
    add('archive-uses-polished-tesla-shell', archivePolish === 1 && archivePersonalization === 1 && archiveSignature === 0, { archivePolish, archivePersonalization, archiveSignature });
    add('archive-has-category-led-thesis', /Keep every result in view/i.test(archiveText));
    const phase23Card = await page.locator('.archive-card[href="/phases/phase23/"]').count();
    add('archive-links-phase23', phase23Card === 1, { phase23Card });
    await page.goto(BASE + '/phases/phase23/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForFunction(() => {
      const images = [...document.querySelectorAll('.condition-gallery img')];
      return images.length === 6 && images.every(img => img.complete && img.naturalWidth === 640 && img.naturalHeight === 585);
    }, null, { timeout: 15000 }).catch(() => {});
    await page.locator('#checkpoint-recovery > summary').click();
    const phase23 = await page.evaluate(() => ({
      rows: document.querySelectorAll('main .table-wrap tbody tr').length,
      gallery: [...document.querySelectorAll('.condition-gallery img')].map(img => ({ loaded: img.complete && img.naturalWidth > 0, width: img.naturalWidth, height: img.naturalHeight })),
      source: document.querySelector('footer a')?.getAttribute('href') || '',
      hasBoundary: /separate from the frozen Phase 1–22 simulation record/i.test(document.querySelector('main')?.innerText || ''),
      recovery: document.querySelector('#checkpoint-recovery')?.innerText || '',
      noHorizontalOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth <= 1
    }));
    add('phase23-six-condition-images-load-at-source-ratio', phase23.gallery.length === 6 && phase23.gallery.every(image => image.loaded && image.width === 640 && image.height === 585), phase23.gallery);
    add('phase23-shows-committed-results-and-checkpoint-gate', phase23.rows === 6 && phase23.source.includes('phase23_robust_detector/summary.md') && phase23.hasBoundary && /exact Phase 23/.test(phase23.recovery) && phase23.noHorizontalOverflow, phase23);
    await page.goto(BASE + '/phases/phase24/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForFunction(() => {
      const charts = [...document.querySelectorAll('[data-phase24-chart]')];
      const rows = document.querySelectorAll('#conditionRows tr').length;
      return charts.length === 4 && charts.every(chart => chart.querySelector('svg')) && rows === 6
        && !document.querySelector('#macroMapDelta')?.textContent.includes('Loading');
    }, null, { timeout: 15000 }).catch(() => {});
    const phase24 = await page.evaluate(() => ({
      title: document.querySelector('h1')?.innerText || '',
      chartCount: document.querySelectorAll('[data-phase24-chart] svg').length,
      conditionRows: document.querySelectorAll('#conditionRows tr').length,
      provenance: document.querySelector('.provenance')?.innerText || '',
      noHorizontalOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth <= 1
    }));
    add('phase24-renders-four-data-driven-charts', phase24.chartCount === 4 && phase24.conditionRows === 6, phase24);
    add('phase24-labels-reanalysis-and-evidence-limits', /What the average hides/i.test(phase24.title) && /Reanalysis only/i.test(phase24.provenance) && phase24.noHorizontalOverflow, phase24);
    await page.goto(BASE + '/phases/phase25/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.locator('.atlas-visual .atlas-condition-button').first().waitFor({ timeout: 15000 });
    await page.locator('.atlas-visual [data-atlas-condition="mixed"]').click();
    const phase25 = await page.evaluate(() => ({
      title: document.querySelector('h1')?.textContent || '',
      status: document.querySelector('.atlas-status')?.textContent || '',
      images: document.querySelectorAll('.atlas-visual__pair img').length,
      inputAudit: document.querySelector('.atlas-inputs')?.textContent || '',
      controls: document.querySelectorAll('.atlas-visual .atlas-condition-button').length,
      chartRows: document.querySelectorAll('.atlas-visual .atlas-chart-row').length,
      mixedImage: document.querySelector('.atlas-visual [data-atlas-image]')?.getAttribute('src'),
      mixedDelta: document.querySelector('.atlas-visual [data-atlas-delta]')?.textContent,
      text: document.querySelector('main')?.innerText || '',
      noHorizontalOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth <= 1
    }));
    add('phase25-shows-method-and-honest-pending-status',
      /Find the misses/i.test(phase25.title) && /exact Phase 23 model and original inference versions/i.test(phase25.status)
      && phase25.images === 2 && /retrospective audit/i.test(phase25.text)
      && /86/.test(phase25.inputAudit) && /516/.test(phase25.inputAudit)
      && phase25.noHorizontalOverflow, phase25);
    add('phase25-stress-lens-uses-published-aggregates',
      phase25.controls === 6 && phase25.chartRows === 6
      && phase25.mixedImage === '/media/perception/kios_mixed.jpg'
      && /−5\.5 points/.test(phase25.mixedDelta), phase25);

    await page.goto(BASE + '/failure-atlas/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.locator('#frame-title').waitFor({ timeout: 15000 });
    await page.locator('#conditions button').first().waitFor({ timeout: 15000 });
    await page.waitForFunction(() => document.querySelector('#frame-image')?.naturalWidth > 0
      && document.querySelector('#phase23-frame-image')?.naturalWidth > 0, null, { timeout: 15000 });
    const atlas = await page.evaluate(() => ({
      title: document.querySelector('h1')?.textContent || '',
      conditions: document.querySelectorAll('#conditions button').length,
      matrix: document.querySelectorAll('#matrix button').length,
      score: document.querySelector('#baseline-metrics')?.textContent || '',
      pending: document.querySelector('.pending-panel')?.textContent || '',
      phase23Map50: document.querySelector('#phase23-map50')?.textContent || '',
      phase23Recall: document.querySelector('#phase23-recall')?.textContent || '',
      folderInput: document.querySelector('#local-folder')?.hasAttribute('webkitdirectory') || false,
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      heroImage: document.querySelector('.intro-image img')?.getAttribute('src') || '',
      sourceImageLoaded: document.querySelector('#frame-image')?.naturalWidth > 0,
      phase23ImageLoaded: document.querySelector('#phase23-frame-image')?.naturalWidth > 0,
      phase23ImageSameSource: document.querySelector('#phase23-frame-image')?.currentSrc === document.querySelector('#frame-image')?.currentSrc,
      phase23ImageBadge: document.querySelector('#phase23-image-badge')?.textContent || '',
      sceneFill: (() => {
        const scene = document.querySelector('#baseline-scene');
        const sceneBox = scene?.getBoundingClientRect();
        const panelBox = scene?.parentElement?.getBoundingClientRect();
        return Boolean(sceneBox && panelBox && Math.abs(sceneBox.width - panelBox.width) < 1
          && Math.abs(sceneBox.width / sceneBox.height - 1052 / 961) < .01);
      })(),
      visibleLabels: document.querySelectorAll('#box-layer .overlay-box em').length,
      caseSummary: document.querySelector('#case-features')?.textContent || ''
    }));
    add('atlas-live-baseline-and-published-phase23-aggregates', /See where the model fails/i.test(atlas.title)
      && atlas.conditions === 6 && atlas.matrix === 516 && /BEST IoU/.test(atlas.score)
      && /Frame outcomes pending/i.test(atlas.pending) && atlas.phase23Map50 === '55.5%' && atlas.phase23Recall === '59.3%'
      && atlas.folderInput && atlas.overflow <= 1
      && atlas.heroImage === '/media/perception/kios_clean.jpg' && atlas.sourceImageLoaded
      && atlas.phase23ImageLoaded && atlas.phase23ImageSameSource && /Same source frame/.test(atlas.phase23ImageBadge), atlas);
    add('atlas-source-proportional-panels-and-readable-boxes', atlas.sceneFill && atlas.visibleLabels <= 5
      && /all counted/.test(atlas.caseSummary), atlas);
    const startFrame = await page.locator('#frame-range').evaluate(el => Number(el.value));
    await page.locator('#next-frame').click();
    const nextFrame = await page.locator('#frame-range').evaluate(el => Number(el.value));
    await page.locator('#prev-frame').click();
    add('atlas-frame-navigation-wraps-and-reverses', nextFrame === (startFrame + 1) % 86
      && await page.locator('#frame-range').evaluate(el => Number(el.value)) === startFrame);
    await page.locator('#show-baseline').uncheck();
    const boxesHidden = await page.locator('#box-layer .overlay-box:not(.gt)').count() === 0
      && /0 shown/.test(await page.locator('#case-features').innerText());
    await page.locator('#show-baseline').check();
    await page.locator('#show-gt').uncheck();
    const groundTruthHidden = await page.locator('#box-layer .overlay-box.gt').count() === 0;
    await page.locator('#show-gt').check();
    add('atlas-overlay-toggles-match-visible-summary', boxesHidden && groundTruthHidden);
    await page.locator('#view-mode').click();
    const stacked = await page.locator('#comparison').evaluate(el => el.classList.contains('stacked'));
    await page.locator('#view-mode').click();
    add('atlas-side-by-side-toggle-reverses', stacked && !(await page.locator('#comparison').evaluate(el => el.classList.contains('stacked'))));
    await page.locator('#conditions button[data-condition="mixed"]').click();
    const mixedAggregate = await page.locator('#phase23-map50').innerText();
    await page.locator('#filter-outcome').selectOption('miss');
    add('atlas-filter-and-condition-work', /MIXED/.test(await page.locator('#frame-sequence').innerText())
      && /matching views/.test(await page.locator('#match-count').innerText())
      && Number((await page.locator('#match-count').innerText()).split('/')[0].trim()) < 516
      && mixedAggregate === '12.9%');
    await page.locator('[data-open-evidence]').first().click();
    add('atlas-evidence-opens', await page.locator('#evidence-dialog').evaluate(el => el.open));
    await page.locator('#close-evidence').click();
    await page.setViewportSize({ width: 390, height: 844 });
    await page.locator('.mobile-menu summary').click();
    const mobileMenuWorks = await page.locator('.mobile-menu').evaluate(el => el.open)
      && await page.locator('.mobile-menu nav a[href="/reproduce/"]').isVisible();
    await page.locator('.mobile-menu summary').click();
    await page.setViewportSize({ width: 1440, height: 1000 });
    add('atlas-mobile-navigation-opens', mobileMenuWorks);

    const uploadRoot = fsSync.mkdtempSync(path.join(os.tmpdir(), 'aegisland-atlas-images-'));
    temporaryUploads.push(uploadRoot);
    for (const condition of ['clean', 'mixed']) {
      const folder = path.join(uploadRoot, condition);
      fsSync.mkdirSync(folder, { recursive: true });
      fsSync.copyFileSync(path.resolve('deploy/vercel/media/perception/kios_clean.jpg'), path.join(folder, 'land_pad2__2100.jpg'));
    }
    await page.locator('#local-folder').setInputFiles(uploadRoot);
    await page.waitForFunction(() => document.querySelector('#frame-image')?.naturalWidth === 640
      && document.querySelector('#phase23-frame-image')?.naturalWidth === 640, null, { timeout: 10000 }).catch(() => {});
    const folderStatus = await page.locator('#image-note').innerText();
    await page.locator('#conditions button[data-condition="clean"]').click();
    await page.waitForFunction(() => document.querySelector('#frame-image')?.naturalWidth === 640
      && document.querySelector('#phase23-frame-image')?.naturalWidth === 640, null, { timeout: 10000 }).catch(() => {});
    const cleanFolderImageLoaded = await page.locator('#frame-image').evaluate(img => img.naturalWidth === 640 && !img.hidden);
    const cleanPhase23ImageLoaded = await page.locator('#phase23-frame-image').evaluate(img => img.naturalWidth === 640 && !img.hidden);
    await page.locator('#conditions button[data-condition="mixed"]').click();
    await page.waitForFunction(() => document.querySelector('#frame-image')?.naturalWidth === 640
      && document.querySelector('#phase23-frame-image')?.naturalWidth === 640, null, { timeout: 10000 }).catch(() => {});
    const mixedFolderImageLoaded = await page.locator('#frame-image').evaluate(img => img.naturalWidth === 640 && !img.hidden);
    const mixedPhase23ImageLoaded = await page.locator('#phase23-frame-image').evaluate(img => img.naturalWidth === 640 && !img.hidden);
    add('atlas-folder-loader-maps-matching-images-by-condition', /Loaded 2 image views/.test(folderStatus)
      && /Clean 1/.test(folderStatus) && /Mixed 1/.test(folderStatus)
      && cleanFolderImageLoaded && cleanPhase23ImageLoaded && mixedFolderImageLoaded && mixedPhase23ImageLoaded,
      { folderStatus, cleanFolderImageLoaded, cleanPhase23ImageLoaded, mixedFolderImageLoaded, mixedPhase23ImageLoaded });

    const phaseChecks = [
      ['/phases/phase1/', /First safety supervisor/i, /HOLD \/ ABORT/i],
      ['/phases/phase10r/', /Shifted holdout/i, /Tail \+ coverage/i],
      ['/phases/phase11/', /Protected reliability check/i, /Protected gates/i],
      ['/phases/phase12/', /Frozen uncertainty reference/i, /2\.23035/],
      ['/phases/phase13a/', /External-validity challenge/i, /External-Validity Gauntlet/i],
      ['/phases/phase18/', /Protected residual check/i, /missed two q90 checks/i],
      ['/phases/phase22/', /Frozen additive transfer/i, /0\.8319/]
    ];
    for (const [route, identity, evidence] of phaseChecks) {
      await page.goto(BASE + route, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await page.waitForTimeout(350);
      const text = await page.locator('main').innerText();
      const chip = await page.locator('.phase-identity-chip').count();
      const role = await page.locator('.phase-role-card').count();
      const category = await page.evaluate(() => document.body.dataset.phaseCategory || '');
      add(`${route}-identity-visible`, identity.test(text) && chip === 1 && role === 1, { chip, role, excerpt: text.slice(0, 500) });
      add(`${route}-evidence-visible`, evidence.test(text), { excerpt: text.slice(0, 700) });
      add(`${route}-category-bound`, category.length > 0, { category });
    }

    await page.goto(BASE + '/phases/phase12/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(250);
    const phase12Text = await page.locator('main').innerText();
    add('phase12-locked-verdict-visible', /PASS/.test(phase12Text));
    add('phase12-boundary-visible', /Frozen result\. No retuning/i.test(phase12Text));

    await page.goto(BASE + '/phases/phase22/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(250);
    const phase22Text = await page.locator('main').innerText();
    add('phase22-has-final-r2-pair', /0\.8319/.test(phase22Text) && /0\.7744/.test(phase22Text));
    add('phase22-has-sealed-identities', /0ddc968b8bd48c2de6d904194b417854913389a8927cff0b15b96c6501f8294c/.test(phase22Text) && /62e75d7b39088c2e66f1cc6be4d180501b79632f2f6847af1fbe0bd96be17551/.test(phase22Text));

    await page.goto(BASE + '/phases/phase11/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(250);
    const phase11Text = await page.locator('main').innerText();
    add('phase11-failed-predecessor-remains-visible', /2\.435/.test(phase11Text) && /2\.25/.test(phase11Text), { excerpt: phase11Text.slice(0, 500) });
    await page.close();
    await context.close();
  }

  {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, reducedMotion: 'reduce' });
    const page = await context.newPage();
    for (const route of ['/', '/phases/', '/failure-atlas/', '/phases/phase23/', '/phases/phase1/', '/phases/phase10r/', '/phases/phase13a/', '/phases/phase22/']) {
      await page.goto(BASE + route, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await page.waitForTimeout(300);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      add(`mobile-${route}-no-horizontal-overflow`, overflow <= 1, { overflow });
    }
    await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    const ctas = await page.locator('.hero .button').evaluateAll(els => els.map(el => Math.round(el.getBoundingClientRect().height)));
    add('mobile-home-ctas-touchable', ctas.length >= 2 && ctas.every(height => height >= 40), { ctas });
    await page.goto(BASE + '/phases/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(300);
    const mobileCategoryLinks = await page.locator('#categoryNav a').count();
    add('mobile-archive-keeps-all-category-links', mobileCategoryLinks === 7, { mobileCategoryLinks });
    await page.close();
    await context.close();
  }
} finally {
  await browser.close();
  for (const directory of temporaryUploads) fsSync.rmSync(directory, { recursive: true, force: true });
}

console.log(JSON.stringify({ base: BASE, passed: results.filter(result => result.ok).length, failed, results }, null, 2));
if (failed) process.exitCode = 1;
