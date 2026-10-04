import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import fs from 'node:fs/promises';

const base=process.env.QA_BASE_URL || 'http://127.0.0.1:4173';
const local=!process.env.QA_BASE_URL;
const server=local ? spawn('node',['.github/qa/local-vercel-server.mjs'],{stdio:'ignore'}) : null;
const out=process.env.QA_OUT || 'qa-artifacts/phase22-release';
await fs.mkdir(out,{recursive:true});
for(let attempt=0;attempt<30;attempt++) {
  try { if((await fetch(base)).ok) break; } catch {}
  await new Promise(r=>setTimeout(r,100));
}
const browser=await chromium.launch({headless:true});
const report={base,checks:[],screenshots:[]};
const routes=['/','/phases/','/phases/phase22/','/phases/phase23/','/phases/phase25/','/model-vase/','/failure-atlas/','/reproduce/','/phase22-detector-study/'];
try {
  for(const viewport of [{name:'desktop',width:1440,height:1000},{name:'mobile',width:390,height:844}]) {
    const context=await browser.newContext({viewport:{width:viewport.width,height:viewport.height},isMobile:viewport.name==='mobile',hasTouch:viewport.name==='mobile',reducedMotion:'reduce'});
    for(const route of routes) {
      const page=await context.newPage();const errors=[];
      page.on('pageerror',e=>errors.push(e.message));
      const response=await page.goto(base+route,{waitUntil:'domcontentloaded',timeout:45000});
      await page.locator('main').waitFor({state:'visible',timeout:15000});
      // current-data.js replaces the archive/phase lab asynchronously. Wait for
      // its actual camera images before making the lazy-image audit snapshot.
      if(['/phases/','/phases/phase22/'].includes(route)) {
        await page.locator('#experiment-lab[data-current-dataset="kios-real-video"] img').first().waitFor({state:'attached',timeout:15000});
      }
      // A full-page audit must load offscreen lazy images before measuring them.
      await page.locator('img').evaluateAll(images=>images
        .filter(i=>i.getAttribute('src')&&i.getClientRects().length)
        .forEach(i=>{i.loading='eager';}));
      await page.evaluate(async()=>{
        const images=[...document.images].filter(i=>i.getAttribute('src')&&i.getClientRects().length);
        await Promise.race([
          Promise.all(images.map(i=>i.decode().catch(()=>{}))),
          new Promise(resolve=>setTimeout(resolve,15000))
        ]);
      });
      const text=await page.locator('body').innerText();
      const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);
      const images=await page.locator('img').evaluateAll(images=>images.filter(i=>i.getAttribute('src')&&i.getClientRects().length&&(!i.complete||i.naturalWidth===0)).map(i=>i.getAttribute('src')));
      // Checkout QA lacks deployment-only reconstructed/editorial assets. Production checks every visible image.
      const deploymentOnlyImages=local?images.filter(src=>/^\/media\/(editorial|phase25|perception)\//.test(src)):[];
      const brokenImages=images.filter(src=>!deploymentOnlyImages.includes(src));
      report.checks.push({viewport:viewport.name,route,status:response.status(),content:text.length>100,overflow,brokenImages,deploymentOnlyImages,errors,
        ok:response.ok()&&text.length>100&&overflow<=2&&brokenImages.length===0&&errors.length===0});
      if(route==='/phase22-detector-study/') {
        for(const expected of ['INCONCLUSIVE','Clean gate FAILED','STAGE A / REPRESENTATION','COMPLETE · CLEAN GATE PASS','516 cases','NOT APPLICABLE','53/86','48/86']) {
          report.checks.push({viewport:viewport.name,route,expected,ok:text.includes(expected)});
        }
      }
      if(viewport.name==='mobile'&&['/reproduce/','/phase22-detector-study/'].includes(route)) {
        const menu=page.locator('details.mobile-menu');
        await menu.locator('summary').focus();await page.keyboard.press('Enter');
        report.checks.push({viewport:viewport.name,route,name:'native-menu-keyboard-open',ok:await menu.getAttribute('open')!==null});
        await page.keyboard.press('Escape');
        report.checks.push({viewport:viewport.name,route,name:'native-menu-keyboard-close',ok:await menu.getAttribute('open')===null});
      }
      if(route==='/reproduce/') report.checks.push({viewport:viewport.name,route,name:'current-candidate-gate',ok:text.includes('validate_research_release.py')&&text.includes('1.0.0rc1')&&text.includes('NO_DATASET_ADMITTED')});
      if(route==='/phases/') report.checks.push({viewport:viewport.name,route,name:'paired-audit-in-archive',ok:await page.locator('.archive-card[href="/phases/phase25/"]').count()===1&&text.includes('29 phase records')});
      if(route==='/phases/phase25/') report.checks.push({viewport:viewport.name,route,name:'original-replay-and-separate-pairs',ok:text.includes('24 / 24')&&text.includes('860 within-model pairs')&&text.includes('516 cross-model views')});
      if(route==='/phases/phase22/') report.checks.push({viewport:viewport.name,route,name:'detector-followup-link',ok:await page.locator('a[href="/phase22-detector-study/"]').count()===1});
      if(viewport.name==='mobile'&&(route==='/'||route==='/phases/phase22/')) {
        const toggle=page.locator('#mobileMenuToggle');await toggle.click();
        report.checks.push({viewport:viewport.name,route,name:'mobile-menu-opens',ok:await toggle.getAttribute('aria-expanded')==='true'&&await page.locator('#mobileMenuSheet').getAttribute('aria-hidden')==='false'});
        await page.keyboard.press('Escape');
        report.checks.push({viewport:viewport.name,route,name:'mobile-menu-closes',ok:await toggle.getAttribute('aria-expanded')==='false'});
      }
      if(['/','/phases/','/reproduce/','/phases/phase25/','/phase22-detector-study/','/phases/phase22/'].includes(route)) {
        const filename=`${viewport.name}-${route.replaceAll('/','')}.png`;
        await page.screenshot({path:out+'/'+filename,fullPage:true});report.screenshots.push(filename);
      }
      const links=await page.locator('a[href^="https://github.com/suhaslord/uav-safety-research"]').evaluateAll(a=>a.map(x=>x.href));
      report.checks.push({viewport:viewport.name,route,name:'research-links-valid-repository',count:links.length,ok:links.every(url=>url.startsWith('https://github.com/suhaslord/uav-safety-research'))});
      await page.close();
    }
    await context.close();
  }
} finally {await browser.close();if(server)server.kill();}
report.failed=report.checks.filter(c=>!c.ok);
report.status=report.failed.length?'FAIL':'PASS';
await fs.writeFile(out+'/report.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({status:report.status,checks:report.checks.length,failed:report.failed},null,2));
if(report.failed.length)process.exitCode=1;
