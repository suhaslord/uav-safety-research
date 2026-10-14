import { chromium } from 'playwright';
import { spawn } from 'node:child_process';

const base = process.env.QA_BASE_URL || 'http://127.0.0.1:4173';
const server = process.env.QA_BASE_URL ? null : spawn('node',['.github/qa/local-vercel-server.mjs'],{stdio:'ignore'});
let browser;
const checks=[];
const check=(name,pass,details={})=>{
  checks.push({name,pass,...details});
  if(!pass)throw new Error('Prototype smoke failed: '+name+' '+JSON.stringify(details));
};
try{
  for(let i=0;i<60;i++){
    try{if((await fetch(base+'/prototype/')).ok)break;}catch{}
    await new Promise(resolve=>setTimeout(resolve,100));
  }
  browser=await chromium.launch({headless:true});
  const cameraSvg='<svg xmlns="http://www.w3.org/2000/svg" width="640" height="585"><rect width="640" height="585" fill="#d4ecfd"/></svg>';
  for(const viewport of [{name:'desktop',width:1440,height:900},{name:'mobile',width:390,height:844}]){
    const context=await browser.newContext({viewport:{width:viewport.width,height:viewport.height},reducedMotion:'reduce'});
    const page=await context.newPage();
    const errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.route('**/media/phase25/**',route=>route.fulfill({status:200,contentType:'image/svg+xml',body:cameraSvg}));
    const response=await page.goto(base+'/prototype/',{waitUntil:'domcontentloaded'});
    check(viewport.name+'-route',response?.status()===200);
    await page.locator('#prototype-app').waitFor({state:'visible',timeout:15000});
    check(viewport.name+'-loaded',await page.locator('#prototype-status').isHidden());
    check(viewport.name+'-initial-group',await page.locator('#accepted-total').innerText()==='of 86 frames');
    check(viewport.name+'-decision',/^(ACCEPT|ABSTAIN)$/.test(await page.locator('#decision').innerText()));
    const first=await page.locator('#frame-label').innerText();
    await page.locator('#next-frame').click();
    check(viewport.name+'-next-frame',(await page.locator('#frame-label').innerText())!==first);
    await page.locator('#previous-frame').click();
    check(viewport.name+'-previous-frame',(await page.locator('#frame-label').innerText())===first);
    await page.locator('#model-select').selectOption('baseline');
    await page.locator('#condition-select').selectOption('mixed');
    check(viewport.name+'-change-condition',await page.locator('#accepted-total').innerText()==='of 86 frames');
    await page.locator('#cutoff').fill('0.95');
    check(viewport.name+'-threshold-updates',await page.locator('#cutoff-value').innerText()==='0.95');
    check(viewport.name+'-truth-after-decision',/^(Yes|No|No top box)$/.test(await page.locator('#localization-result').innerText()));
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);
    check(viewport.name+'-no-overflow',overflow<=2,{overflow});
    check(viewport.name+'-browser-errors',errors.length===0,{errors});
    await context.close();
  }
  const context=await browser.newContext();
  const page=await context.newPage();
  await page.route('**/prototype-cases.json*',route=>route.fulfill({status:200,contentType:'application/json',body:'{"status":"fake"}'}));
  await page.goto(base+'/prototype/');
  await page.waitForFunction(()=>document.getElementById('prototype-status')?.textContent?.includes('could not be verified'));
  check('tampered-data-fails-closed',await page.locator('#prototype-app').isHidden());
  await context.close();
  console.log(JSON.stringify({status:'PASS',checks},null,2));
}catch(error){
  console.error(JSON.stringify({status:'FAIL',checks,error:String(error)},null,2));
  process.exitCode=1;
}finally{
  if(browser)await browser.close();
  if (server) server.kill();
}
