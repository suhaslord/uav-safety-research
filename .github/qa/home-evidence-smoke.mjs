import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import fs from 'node:fs/promises';
const base = process.env.QA_BASE_URL || 'http://127.0.0.1:4173';
const server = process.env.QA_BASE_URL ? null : spawn('node',['.github/qa/local-vercel-server.mjs'],{stdio:'ignore'});
const out = process.env.QA_OUT || 'qa-artifacts/home-evidence';
await fs.mkdir(out,{recursive:true});
for(let i=0;i<30;i++){try{if((await fetch(base)).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
const payload = await fetch(base+'/failure-atlas-data.json?v=3').then(r=>r.json());
const models = {baseline:payload.cases,phase23:payload.phase23.cases};
const frame = 'land_pad2__2475.jpg';
const report={base,checks:[],screenshots:[]};
const add=(name,ok,detail={})=>report.checks.push({name,ok,...detail});
const browser=await chromium.launch({headless:true});
try {
  for(const width of [1440,940,768,375,320]) {
    const context=await browser.newContext({viewport:{width,height:1000},reducedMotion:'reduce'});
    const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto(base+'/',{waitUntil:'networkidle'});
    await page.waitForFunction(()=>document.querySelector('#home-comparison')?.dataset.loaded==='true');
    for(const condition of payload.conditions) {
      await page.locator(`[data-home-condition="${condition}"]`).click();
      await page.waitForFunction(()=>[...document.querySelectorAll('.home-camera img')].every(i=>!i.hidden&&i.complete&&i.naturalWidth>0));
      for(const model of ['baseline','phase23']) {
        const expected=models[model].find(r=>r.id===frame&&r.condition===condition);
        const panel=page.locator(`[data-home-model="${model}"]`);
        const values=await panel.locator('[data-home-metric]').allTextContents();
        add(`${width}-${condition}-${model}-saved-metrics`,JSON.stringify(values)===JSON.stringify([expected.tp,expected.fp,expected.fn].map(String)));
        add(`${width}-${condition}-${model}-saved-verdict`,(await panel.locator('[data-home-verdict]').innerText())===(expected.pass?'TARGET MATCHED':'TARGET MISSED'));
        add(`${width}-${condition}-${model}-all-matched-boxes`,await panel.locator('.home-overlay-box.tp').count()===expected.boxes.filter(b=>b[6]).length);
      }
      const same=await page.locator('.home-camera img').evaluateAll(imgs=>imgs[0].currentSrc===imgs[1].currentSrc);
      add(`${width}-${condition}-same-source`,same);
    }
    await page.locator('[data-home-condition="occlusion"]').click();
    await page.waitForFunction(()=>[...document.querySelectorAll('.home-camera img')].every(i=>!i.hidden&&i.complete&&i.naturalWidth>0));
    await page.locator('#home-show-boxes').uncheck();
    add(`${width}-box-toggle`,await page.locator('.home-boxes').evaluateAll(l=>l.every(x=>x.hidden)));
    await page.locator('#home-show-boxes').check();
    const geometry=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,previewTop:document.querySelector('#home-comparison').getBoundingClientRect().top,previewWidth:document.querySelector('#home-comparison').getBoundingClientRect().width,contextOpen:document.querySelector('.field-context').open,chartRows:document.querySelectorAll('[data-atlas-chart] .atlas-chart-row').length,height:document.documentElement.scrollHeight}));
    add(`${width}-no-horizontal-overflow`,geometry.overflow<=1,geometry);
    add(`${width}-evidence-before-context`,!geometry.contextOpen&&geometry.chartRows===6);
    if(width===1440)add('desktop-comparison-in-first-viewport',geometry.previewTop<300&&geometry.previewWidth>500,geometry);
    if(width<=768) {
      await page.locator('#mobileMenuToggle').click();
      add(`${width}-menu-opens`,await page.locator('#mobileMenuToggle').getAttribute('aria-expanded')==='true');
      await page.keyboard.press('Escape');
      add(`${width}-menu-focus-restored`,await page.locator('#mobileMenuToggle').evaluate(el=>el===document.activeElement));
    }
    await page.locator('[data-home-condition="clean"]').focus();await page.keyboard.press('Enter');
    add(`${width}-keyboard-condition`,await page.locator('[data-home-condition="clean"]').getAttribute('aria-pressed')==='true');
    await page.locator('[data-home-condition="occlusion"]').click();
    await page.waitForFunction(()=>[...document.querySelectorAll('.home-camera img')].every(i=>!i.hidden&&i.complete&&i.naturalWidth>0));
    add(`${width}-no-js-exceptions`,errors.length===0,{errors});
    const filename=`home-${width}.png`;await page.screenshot({path:out+'/'+filename,fullPage:true});report.screenshots.push(filename);
    await context.close();
  }
  const context=await browser.newContext({viewport:{width:1440,height:1000}});
  const broken=await context.newPage();
  await broken.route('**/failure-atlas-data.json*',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify({...payload,cases:[]})}));
  await broken.goto(base+'/',{waitUntil:'networkidle'});
  add('invalid-data-not-shown-as-zero',await broken.locator('[data-home-metric]').evaluateAll(items=>items.every(i=>i.textContent==='—')));
  add('invalid-data-actionable-error',/Open Failure Atlas/.test(await broken.locator('#home-case-note').innerText()));
  await context.close();
  const imageContext=await browser.newContext({viewport:{width:1440,height:1000}});
  const badImage=await imageContext.newPage();await badImage.route('**/media/phase25/**',r=>r.abort());
  await badImage.goto(base+'/',{waitUntil:'networkidle'});
  await badImage.waitForFunction(()=>document.querySelector('#home-comparison')?.dataset.loaded==='true');
  add('failed-image-hides-overlays',await badImage.locator('.home-boxes').evaluateAll(layers=>layers.every(l=>l.hidden)));
  add('failed-image-retains-measurements',await badImage.locator('[data-home-model="baseline"] [data-home-metric="tp"]').innerText()==='1');
  await imageContext.close();
} finally {await browser.close();server?.kill();}
report.failed=report.checks.filter(c=>!c.ok);report.status=report.failed.length?'FAIL':'PASS';
await fs.writeFile(out+'/report.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({status:report.status,checks:report.checks.length,failed:report.failed},null,2));
if(report.failed.length)process.exitCode=1;
