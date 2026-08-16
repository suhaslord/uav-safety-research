(()=>{
  const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const coarse=window.matchMedia('(pointer: coarse)').matches;

  /* Phase 10R has older frontier decoration code for archive metadata. Keep that
     data work, but make the shared research scene authoritative after every
     phase script has mounted. */
  if(/\/phases\/phase10r\/?$/i.test(location.pathname)){
    const normalize10r=()=>{
      const hero=document.getElementById('phaseHero');
      if(!hero)return;
      hero.classList.remove('frontier-hero');
      hero.classList.add('scene-hero');
      hero.querySelector('.frontier-badge')?.remove();
      const object=hero.querySelector('.object');
      if(object?.classList.contains('hero-scene-phase10r')){
        object.style.removeProperty('position');
        object.style.removeProperty('inset');
        object.style.removeProperty('transform');
      }
    };
    requestAnimationFrame(()=>requestAnimationFrame(normalize10r));
    setTimeout(normalize10r,160);
  }

  /* Scroll reveal only: keep the progression calm and readable. */
  const rails=[...document.querySelectorAll('#homeModelRail,.phase-rail-section')];
  for(const rail of rails){
    rail.classList.add('rail-enter');
    const steps=[...rail.querySelectorAll('.home-rail-step,.rail-step')];
    steps.forEach((step,i)=>{
      step.classList.add('rail-child-enter');
      step.style.setProperty('--rail-delay',`${Math.min(i*32,280)}ms`);
    });
    if(reduced){
      rail.classList.add('is-visible');
      steps.forEach(s=>s.classList.add('is-visible'));
      continue;
    }
    const io=new IntersectionObserver(entries=>{
      for(const entry of entries){
        if(!entry.isIntersecting)continue;
        rail.classList.add('is-visible');
        steps.forEach(s=>s.classList.add('is-visible'));
        io.disconnect();
      }
    },{threshold:.16,rootMargin:'0px 0px -7% 0px'});
    io.observe(rail);
  }

  /* Minimal global cursor trail: one tiny cube, short drift, ~1 second fade. */
  if(reduced||coarse)return;
  const layer=document.createElement('div');
  layer.className='cursor-trail-layer';
  layer.setAttribute('aria-hidden','true');
  document.body.appendChild(layer);

  let lastSpawn=0,lastX=-999,lastY=-999,variant=0;
  function spawn(x,y){
    const el=document.createElement('i');
    variant=(variant+1)%3;
    el.className=`cursor-trail-cube v${variant+1}`;
    const size=3.5+Math.random()*2.5;
    const side=Math.random()>.5?1:-1;
    const ox=side*(5+Math.random()*8);
    const oy=(Math.random()-.5)*10;
    const dx=side*(3+Math.random()*7);
    const dy=-2-Math.random()*8;
    el.style.setProperty('--s',`${size.toFixed(1)}px`);
    el.style.setProperty('--x',`${(x+ox).toFixed(1)}px`);
    el.style.setProperty('--y',`${(y+oy).toFixed(1)}px`);
    el.style.setProperty('--dx',`${dx.toFixed(1)}px`);
    el.style.setProperty('--dy',`${dy.toFixed(1)}px`);
    el.style.setProperty('--rot',`${Math.round(Math.random()*24-12)}deg`);
    el.style.setProperty('--spin',`${Math.round((Math.random()>.5?1:-1)*(12+Math.random()*24))}deg`);
    el.style.setProperty('--life',`${Math.round(880+Math.random()*120)}ms`);
    layer.appendChild(el);
    el.addEventListener('animationend',()=>el.remove(),{once:true});
  }

  window.addEventListener('pointermove',e=>{
    const now=performance.now();
    const dist=Math.hypot(e.clientX-lastX,e.clientY-lastY);
    if(now-lastSpawn<88||dist<10)return;
    lastSpawn=now;lastX=e.clientX;lastY=e.clientY;
    spawn(e.clientX,e.clientY);
  },{passive:true});
})();
