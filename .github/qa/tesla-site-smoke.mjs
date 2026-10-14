import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import fsSync from 'node:fs';

const base = process.env.QA_BASE_URL || 'http://127.0.0.1:4173';
const out = process.env.QA_OUT || 'qa-artifacts/tesla-site';
const phases = ['1','2','3','4','5','6','6b','7','8','9','10','10r','11','12','13a','13b','13c','14','15','16','17','18','19','20','21','22','23','24','25'];
const routes = ['/prototype/','/failure-atlas/','/confidence-audit/','/model-vase/','/reproduce/','/fdi-results/','/ornik-fdi/','/phase22-detector-study/','/phases/',...phases.map(id=>`/phases/phase${id}/`),'/dashboard/index.html','/dashboard/phase7.html','/dashboard/phase10r.html'];
const options = { headless: true };
const chrome = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
if (process.platform === 'win32' && fsSync.existsSync(chrome)) options.executablePath = chrome;
await fs.mkdir(out,{recursive:true});
const browser = await chromium.launch(options);
const checks = [];
const add = (name,ok,detail={})=>checks.push({name,ok,...detail});
try {
  for (const width of [1440,390]) {
    const context = await browser.newContext({viewport:{width,height:900},reducedMotion:'reduce'});
    for (const route of routes) {
      const page = await context.newPage(), errors=[];
      page.on('pageerror',error=>errors.push(error.message));
      const response = await page.goto(base+route,{waitUntil:'networkidle'});
      await page.waitForFunction(()=>document.querySelector('[data-tesla-hero]')?.querySelector('h1'));
      const state = await page.evaluate(()=>{
        const hero=document.querySelector('[data-tesla-hero]'), heading=hero.querySelector('h1');
        const r=hero.getBoundingClientRect(), h=heading.getBoundingClientRect();
        const style=getComputedStyle(heading);
        const phasePhoto=document.querySelector('.phase-editorial-photo');
        return {
          overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
          heading:heading.textContent.trim(), headingVisible:style.display!=='none'&&h.height>0,
          heroWidth:r.width, heroHeight:r.height,
          photoLoaded:!phasePhoto||[...phasePhoto.querySelectorAll('img')].every(i=>i.complete&&i.naturalWidth>0),
          caption:phasePhoto?.querySelector('figcaption')?.textContent||hero.querySelector('.tesla-hero-credit')?.textContent||'',
          viewportWidth:document.documentElement.clientWidth
        };
      });
      add(`${width}-${route}-route`,response.status()===200);
      add(`${width}-${route}-visible-heading`,state.headingVisible&&state.heading.length>0,state);
      add(`${width}-${route}-no-overflow`,state.overflow<=1,{overflow:state.overflow});
      add(`${width}-${route}-photo-ready`,state.photoLoaded);
      add(`${width}-${route}-clean-runtime`,errors.length===0,{errors});
      if (width===390) {
        const native=page.locator('.tesla-page-menu');
        if (await native.count()) {
          await native.locator('summary').click();
          add(`${width}-${route}-mobile-links`,await native.locator('nav a').count()>0&&await native.locator('nav a').first().isVisible());
          await native.locator('summary').press('Escape');
          add(`${width}-${route}-menu-escape`,!(await native.evaluate(e=>e.open)));
        }
      }
      if (['/prototype/','/confidence-audit/','/model-vase/','/phases/','/phases/phase1/','/phases/phase22/','/failure-atlas/','/fdi-results/'].includes(route)) {
        await page.screenshot({path:`${out}/${route.replaceAll('/','_')}-${width}.png`,fullPage:true});
      }
      if (route==='/phases/') {
        await page.locator('#archiveSearch').fill('no matching phase zz999');
        add(`${width}-archive-empty-state`,await page.locator('#archiveEmptyState').isVisible());
        await page.locator('#archiveReset').click();
        add(`${width}-archive-reset`,await page.locator('#archiveSearch').inputValue()==='');
      }
      if (route==='/phases/phase22/') {
        const text=await page.locator('#phaseContent').innerText();
        add(`${width}-phase22-frozen-numbers`,['0.8319','0.7744','100%'].every(value=>text.includes(value)));
      }
      await page.close();
    }
    await context.close();
  }
} finally { await browser.close(); }
const failed=checks.filter(c=>!c.ok);
await fs.writeFile(`${out}/report.json`,JSON.stringify({status:failed.length?'FAIL':'PASS',checks,failed},null,2));
console.log(JSON.stringify({status:failed.length?'FAIL':'PASS',checks:checks.length,failed},null,2));
if(failed.length)process.exitCode=1;
