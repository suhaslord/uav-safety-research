import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';
import sharp from 'sharp';

const BASE = process.env.QA_BASE_URL;
if (!BASE) throw new Error('QA_BASE_URL is required');
const ROOT = path.join('qa-artifacts','mobile-ui-sweep-504');
const SHOTS = path.join(ROOT,'screenshots');
const slugs = ['phase1','phase2','phase3','phase4','phase5','phase6','phase6b','phase7','phase8','phase9','phase10','phase10r','phase11','phase12','phase13a','phase13b','phase13c','phase14','phase15','phase16','phase17','phase18','phase19','phase20','phase21','phase22'];
const routes = ['/', '/phases/', ...slugs.map((s)=>`/phases/${s}/`)];
const phones = [
  ['phone-320',320,568],['phone-360',360,800],['phone-375',375,667],
  ['phone-390',390,844],['phone-412',412,915],['phone-430',430,932]
].map(([name,width,height])=>({name,width,height}));

await fs.rm(ROOT,{recursive:true,force:true});
await fs.mkdir(SHOTS,{recursive:true});
const report={base:BASE,routes,viewports:phones,standardTarget:routes.length*phones.length*3,screenshots:[],pages:[],blockers:[],warnings:[],imageAnalyses:[],startedAt:new Date().toISOString()};
const block=(key,kind,details={})=>report.blockers.push({key,kind,...details});
const warn=(key,kind,details={})=>report.warnings.push({key,kind,...details});
const safe=(route)=>route==='/'?'home':route.replace(/^\/+|\/+$/g,'').replaceAll('/','-');

const browser=await chromium.launch({headless:true});
try{
  for(const vp of phones){
    const context=await browser.newContext({viewport:{width:vp.width,height:vp.height},isMobile:true,hasTouch:true,deviceScaleFactor:1,reducedMotion:'reduce'});
    for(const route of routes){
      const key=`${vp.name}:${route}`;
      const page=await context.newPage();
      const consoleErrors=[]; const failedRequests=[];
      page.on('pageerror',(e)=>consoleErrors.push(String(e?.message||e)));
      page.on('console',(m)=>{if(m.type()==='error')consoleErrors.push(m.text());});
      page.on('requestfailed',(r)=>failedRequests.push({url:r.url(),error:r.failure()?.errorText||'failed'}));
      let response;
      try{
        response=await page.goto(`${BASE}${route}?mobile_ui_sweep=1`,{waitUntil:'domcontentloaded',timeout:45000});
        await page.waitForFunction(()=>document.documentElement.dataset.finalConvergence==='ready',null,{timeout:12000}).catch(()=>{});
        await page.waitForTimeout(220);
      }catch(error){block(key,'load-failed',{error:String(error)});}

      const imgCount=await page.locator('img').count().catch(()=>0);
      for(let i=0;i<imgCount;i++)await page.locator('img').nth(i).scrollIntoViewIfNeeded().catch(()=>{});
      await page.evaluate(async()=>{await Promise.all([...document.images].map((img)=>img.decode?.().catch(()=>undefined)));window.scrollTo(0,0);}).catch(()=>{});
      await page.waitForTimeout(100);

      const m=await page.evaluate(({route})=>{
        const visible=(el)=>{if(!el)return false;const s=getComputedStyle(el),r=el.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&Number(s.opacity||1)>0&&r.width>0&&r.height>0;};
        const rect=(el)=>{const r=el.getBoundingClientRect();return{left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height};};
        const cw=document.documentElement.clientWidth;
        const text=document.body.innerText;
        const header=document.querySelector('.site-header,.signature-nav,body.archive-shell .top');
        const toggle=document.querySelector('.mobile-menu-toggle,.archive-menu-toggle');
        const controls=[...document.querySelectorAll('a,button,input,select,textarea,[role="button"]')].filter(visible);
        const sizes=controls.map((el)=>({text:(el.getAttribute('aria-label')||el.textContent||'').trim().slice(0,70),cls:String(el.className||'').slice(0,80),...rect(el)}));
        const under40=sizes.filter((x)=>x.width<40||x.height<40);
        const under44=sizes.filter((x)=>(x.width<44||x.height<44)&&!(x.width<40||x.height<40));
        const offscreen=sizes.filter((x)=>x.left<-3||x.right>cw+3);
        const brokenImages=[...document.images].filter((img)=>!img.complete||img.naturalWidth===0).map((img)=>img.currentSrc||img.src);
        const ids=[...document.querySelectorAll('[id]')].map((el)=>el.id).filter(Boolean);
        const duplicateIds=[...new Set(ids.filter((id,i)=>ids.indexOf(id)!==i))];
        const brokenAnchors=[...new Set([...document.querySelectorAll('a[href^="#"]')].map((a)=>a.getAttribute('href')).filter((href)=>href&&href!=='#'&&!document.getElementById(decodeURIComponent(href.slice(1)))) )];
        const clipped=[...document.querySelectorAll('h1,h2,h3,p,a,button,strong,span,code,pre,li')].filter(visible).map((el)=>{const s=getComputedStyle(el);return{tag:el.tagName,text:(el.textContent||'').trim().slice(0,90),scrollWidth:el.scrollWidth,clientWidth:el.clientWidth,overflowX:s.overflowX};}).filter((x)=>['hidden','clip'].includes(x.overflowX)&&x.scrollWidth>x.clientWidth+5);
        const fixedOffscreen=[...document.querySelectorAll('body *')].filter(visible).filter((el)=>['fixed','sticky'].includes(getComputedStyle(el).position)).map((el)=>({tag:el.tagName,cls:String(el.className||'').slice(0,80),...rect(el)})).filter((x)=>x.left<-3||x.right>cw+3||x.width>cw+6);
        const lineage=[...document.querySelectorAll('.home-lineage__node')].filter(visible).map(rect);
        const categories=[...document.querySelectorAll('.category-nav a')].filter(visible).map(rect);
        const boundary=document.querySelector('.boundary-flags');
        const home=route==='/'?{
          purposeClarity:document.body.dataset.purposeClarity==='true',
          questionRemoved:!document.getElementById('question'),
          purposeVisible:visible(document.getElementById('purpose')),
          evidenceVisible:visible(document.getElementById('evidence')),
          intendedCopy:/What the project does/i.test(text)&&/Find when landing perception becomes confidently wrong/i.test(text)&&/Main conclusion/i.test(text),
          metrics:/0\.8319/.test(text)&&/0\.7744/.test(text)&&/100%/.test(text),
          claims:/simulation_only=true/.test(text)&&/safety_acceptance=false/.test(text)&&/controller_tuning_allowed=false/.test(text)
        }:null;
        return{
          ready:document.documentElement.dataset.finalConvergence||'',mainCount:document.querySelectorAll('main').length,h1Count:document.querySelectorAll('h1').length,
          scrollWidth:document.documentElement.scrollWidth,clientWidth:cw,scrollHeight:document.documentElement.scrollHeight,
          headerRect:header&&visible(header)?rect(header):null,toggleVisible:visible(toggle),toggleRect:toggle&&visible(toggle)?rect(toggle):null,
          under40,under44,offscreen,brokenImages,duplicateIds,brokenAnchors,clipped,fixedOffscreen,
          lineageCount:lineage.length,lineageOffscreen:lineage.filter((x)=>x.left<-3||x.right>cw+3).length,
          categoryOffscreen:categories.filter((x)=>x.left<-3||x.right>cw+3).length,
          boundaryOffscreen:boundary&&visible(boundary)?(rect(boundary).left<-3||rect(boundary).right>cw+3):false,home
        };
      },{route});

      const status=response?.status()||0;
      if(!status||status>=400)block(key,'bad-status',{status});
      if(m.mainCount!==1||m.h1Count!==1)block(key,'semantic-shell',{mainCount:m.mainCount,h1Count:m.h1Count});
      if(m.ready!=='ready')block(key,'final-convergence-css-not-ready');
      if(m.scrollWidth-m.clientWidth>2)block(key,'horizontal-overflow',{overflow:m.scrollWidth-m.clientWidth,header:m.headerRect});
      if(!m.toggleVisible)block(key,'mobile-menu-toggle-missing');
      if(m.toggleRect&&(m.toggleRect.width<44||m.toggleRect.height<44))block(key,'mobile-menu-toggle-too-small',m.toggleRect);
      if(m.brokenImages.length)block(key,'broken-images',{images:m.brokenImages});
      if(m.duplicateIds.length)block(key,'duplicate-ids',{ids:m.duplicateIds});
      if(m.brokenAnchors.length)block(key,'broken-anchors',{anchors:m.brokenAnchors});
      if(m.offscreen.length)block(key,'offscreen-controls',{examples:m.offscreen.slice(0,8)});
      if(m.under40.length)block(key,'touch-target-under-40',{count:m.under40.length,examples:m.under40.slice(0,8)});
      if(m.under44.length)warn(key,'touch-target-under-44',{count:m.under44.length,examples:m.under44.slice(0,8)});
      if(m.clipped.length)block(key,'clipped-text',{count:m.clipped.length,examples:m.clipped.slice(0,8)});
      if(m.fixedOffscreen.length)block(key,'fixed-or-sticky-offscreen',{examples:m.fixedOffscreen.slice(0,8)});
      if(m.boundaryOffscreen)block(key,'boundary-code-offscreen');
      if(route==='/'&&(m.lineageCount!==13||m.lineageOffscreen))block(key,'home-lineage-clipped',{count:m.lineageCount,offscreen:m.lineageOffscreen});
      if(route==='/phases/'&&m.categoryOffscreen)block(key,'archive-categories-clipped',{offscreen:m.categoryOffscreen});
      if(m.home){
        if(!m.home.purposeClarity||!m.home.questionRemoved||!m.home.purposeVisible||!m.home.evidenceVisible||!m.home.intendedCopy)block(key,'home-purpose-framing-not-visible',m.home);
        if(!m.home.metrics)block(key,'home-final-metrics-not-visible');
        if(!m.home.claims)block(key,'home-claim-boundary-not-visible');
      }
      const ce=consoleErrors.filter((x)=>!/favicon|ERR_BLOCKED_BY_CLIENT/i.test(x));
      const fr=failedRequests.filter((x)=>!/favicon|github\.com|linkedin\.com|wikimedia\.org/i.test(x.url));
      if(ce.length)block(key,'console-errors',{errors:ce.slice(0,8)});
      if(fr.length)block(key,'network-errors',{requests:fr.slice(0,8)});

      const prefix=`${safe(route)}-${vp.name}`,maxScroll=Math.max(0,m.scrollHeight-vp.height);
      for(const [label,f] of [['top',0],['mid',.5],['bottom',1]]){
        await page.evaluate((y)=>window.scrollTo(0,y),Math.round(maxScroll*f));await page.waitForTimeout(60);
        const file=`${prefix}-${label}.png`;await page.screenshot({path:path.join(SHOTS,file)});report.screenshots.push({viewport:vp.name,route,kind:label,file,standard:true});
      }

      await page.evaluate(()=>window.scrollTo(0,0));
      const toggle=page.locator('.mobile-menu-toggle,.archive-menu-toggle').first();
      if(await toggle.count()){
        await toggle.click().catch(()=>{});await page.waitForTimeout(100);
        const menu=await page.evaluate(()=>{
          const visible=(el)=>{if(!el)return false;const s=getComputedStyle(el),r=el.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&Number(s.opacity||1)>0&&r.width>0&&r.height>0;};
          const sheet=document.querySelector('.mobile-menu-sheet,.archive-menu-sheet'),toggle=document.querySelector('.mobile-menu-toggle,.archive-menu-toggle'),close=sheet?.querySelector('.mobile-menu-close,.archive-menu-close');
          const r=sheet?.getBoundingClientRect(),cw=document.documentElement.clientWidth;
          const links=sheet?[...sheet.querySelectorAll('a')].filter(visible).map((a)=>{const q=a.getBoundingClientRect();return{text:(a.textContent||'').trim(),width:q.width,height:q.height,left:q.left,right:q.right};}):[];
          return{expanded:toggle?.getAttribute('aria-expanded'),hidden:sheet?.getAttribute('aria-hidden'),visible:visible(sheet),left:r?.left??0,right:r?.right??0,top:r?.top??0,width:r?.width??0,cw,links,
            closeSize:close&&visible(close)?{width:close.getBoundingClientRect().width,height:close.getBoundingClientRect().height}:null,
            bodyOverflow:getComputedStyle(document.body).overflow,bodyMenuOpen:document.body.classList.contains('menu-open'),activeInside:!!sheet?.contains(document.activeElement)};
        });
        if(menu.expanded!=='true'||menu.hidden!=='false'||!menu.visible)block(`${key}:menu`,'menu-open-state-broken',menu);
        if(menu.left<-3||menu.right>menu.cw+3||menu.top<-3||menu.width>menu.cw+6)block(`${key}:menu`,'menu-offscreen',menu);
        if(!menu.links.length||menu.links.some((x)=>x.height<44||x.left<-3||x.right>menu.cw+3))block(`${key}:menu`,'menu-link-touch-or-position-failure',{links:menu.links});
        if(!menu.closeSize||menu.closeSize.width<44||menu.closeSize.height<44)block(`${key}:menu`,'menu-close-target-too-small',{closeSize:menu.closeSize});
        if(!menu.activeInside)block(`${key}:menu`,'menu-focus-not-moved-inside');
        if(!/hidden|clip/i.test(menu.bodyOverflow)&&!menu.bodyMenuOpen)warn(`${key}:menu`,'background-scroll-not-locked',{overflow:menu.bodyOverflow});
        const file=`${prefix}-menu-open.png`;await page.screenshot({path:path.join(SHOTS,file)});report.screenshots.push({viewport:vp.name,route,kind:'menu-open',file,standard:false});
        await page.keyboard.press('Escape').catch(()=>{});await page.waitForTimeout(70);
        const closed=await page.evaluate(()=>({expanded:document.querySelector('.mobile-menu-toggle,.archive-menu-toggle')?.getAttribute('aria-expanded'),hidden:document.querySelector('.mobile-menu-sheet,.archive-menu-sheet')?.getAttribute('aria-hidden'),activeIsToggle:document.activeElement===document.querySelector('.mobile-menu-toggle,.archive-menu-toggle')}));
        if(closed.expanded!=='false'||closed.hidden!=='true')block(`${key}:menu`,'menu-escape-close-broken',closed);
        if(!closed.activeIsToggle)warn(`${key}:menu`,'menu-focus-not-returned-to-toggle',closed);
      }
      report.pages.push({key,route,viewport:vp.name,status,metrics:m});await page.close();
    }
    await context.close();
  }
}finally{await browser.close();}

for(const name of (await fs.readdir(SHOTS)).filter((n)=>n.endsWith('.png')).sort()){
  const file=path.join(SHOTS,name);
  try{
    const stat=await fs.stat(file),image=sharp(file,{failOn:'error'}),[meta,stats]=await Promise.all([image.metadata(),image.stats()]);
    const channels=stats.channels||[],stdev=channels.length?channels.reduce((s,c)=>s+Number(c.stdev||0),0)/channels.length:0,entropy=Number(stats.entropy||0);
    const a={name,width:meta.width,height:meta.height,bytes:stat.size,entropy,stdev};report.imageAnalyses.push(a);
    if(!meta.width||!meta.height||stat.size<1200)block(`image:${name}`,'screenshot-empty-or-tiny',a);
    if(entropy<.08||stdev<2)block(`image:${name}`,'screenshot-suspiciously-flat',a);
  }catch(error){block(`image:${name}`,'screenshot-analysis-failed',{error:String(error)});}
}
report.finishedAt=new Date().toISOString();report.standardCaptured=report.screenshots.filter((x)=>x.standard).length;report.interactionCaptured=report.screenshots.filter((x)=>!x.standard).length;report.totalCaptured=report.screenshots.length;report.imageAnalyzed=report.imageAnalyses.length;
await fs.writeFile(path.join(ROOT,'report.json'),JSON.stringify(report,null,2));
const summary=['# AegisLand mobile UI sweep','',`- Base: ${BASE}`,`- Routes: ${routes.length}`,`- Phone sizes: ${phones.length}`,`- Standard screenshots: ${report.standardCaptured}/${report.standardTarget}`,`- Interaction screenshots: ${report.interactionCaptured}`,`- Total screenshots: ${report.totalCaptured}`,`- Image-analyzed: ${report.imageAnalyzed}`,`- Blockers: ${report.blockers.length}`,`- Warnings: ${report.warnings.length}`,'','## Blockers',...(report.blockers.length?report.blockers.map((x)=>`- ${x.key}: ${x.kind}`):['- None']),'','## Warnings',...(report.warnings.length?report.warnings.map((x)=>`- ${x.key}: ${x.kind}`):['- None'])].join('\n');
await fs.writeFile(path.join(ROOT,'summary.md'),summary);console.log(summary);
if(report.standardCaptured!==report.standardTarget||report.blockers.length||report.warnings.length)process.exitCode=1;
