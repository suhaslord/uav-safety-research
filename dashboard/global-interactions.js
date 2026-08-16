(()=>{
  const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const coarse=window.matchMedia('(pointer: coarse)').matches;

  /* ---- Scroll reveal for home + phase progression rails. ---- */
  const rails=[...document.querySelectorAll('#homeModelRail,.phase-rail-section')];
  for(const rail of rails){
    rail.classList.add('rail-enter');
    const steps=[...rail.querySelectorAll('.home-rail-step,.rail-step')];
    steps.forEach((step,i)=>{
      step.classList.add('rail-child-enter');
      step.style.setProperty('--rail-delay',`${Math.min(i*34,300)}ms`);
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

  /* ---- Tiny square burst for progression links. ---- */
  if(!reduced&&!coarse){
    let lastBurst=0;
    function burst(target,strong=false){
      const now=performance.now();
      if(!strong&&now-lastBurst<150)return;
      lastBurst=now;
      const r=target.getBoundingClientRect();
      const cx=r.left+r.width/2,cy=r.top+Math.min(r.height*.42,34);
      const count=strong?9:6;
      for(let i=0;i<count;i++){
        const p=document.createElement('i');
        p.className='rail-burst-particle';
        const a=(Math.PI*2*i/count)+Math.random()*.3;
        const d=(strong?22:15)+Math.random()*(strong?18:11);
        p.style.left=`${cx+(Math.random()-.5)*8}px`;
        p.style.top=`${cy+(Math.random()-.5)*5}px`;
        p.style.setProperty('--bx',`${Math.cos(a)*d}px`);
        p.style.setProperty('--by',`${Math.sin(a)*d}px`);
        p.style.setProperty('--r',`${Math.round(Math.random()*90)}deg`);
        document.body.appendChild(p);
        p.addEventListener('animationend',()=>p.remove(),{once:true});
      }
    }
    document.addEventListener('pointerover',e=>{
      const step=e.target.closest?.('.home-rail-step,.rail-step');
      if(!step||step.contains(e.relatedTarget))return;
      burst(step,false);
    },{passive:true});
    document.addEventListener('pointerdown',e=>{
      const step=e.target.closest?.('.home-rail-step,.rail-step');
      if(step)burst(step,true);
    },{passive:true});
  }

  /* ---- Global cursor trail: ephemeral cube fragments, not an orbit. ---- */
  if(reduced||coarse)return;
  const layer=document.createElement('div');
  layer.className='cursor-trail-layer';
  layer.setAttribute('aria-hidden','true');
  document.body.appendChild(layer);

  let lastSpawn=0,lastX=-999,lastY=-999,variant=0;
  function spawn(x,y,click=false){
    const count=click?4:1;
    for(let j=0;j<count;j++){
      const el=document.createElement('i');
      variant=(variant+1)%3;
      el.className=`cursor-trail-cube v${variant+1}`;
      const size=click?5+Math.random()*4:4+Math.random()*3.5;
      const angle=Math.random()*Math.PI*2;
      const dist=(click?13:7)+Math.random()*(click?18:12);
      const ox=(Math.random()-.5)*(click?14:9);
      const oy=(Math.random()-.5)*(click?14:9);
      el.style.setProperty('--s',`${size.toFixed(1)}px`);
      el.style.setProperty('--x',`${(x+ox).toFixed(1)}px`);
      el.style.setProperty('--y',`${(y+oy).toFixed(1)}px`);
      el.style.setProperty('--dx',`${(Math.cos(angle)*dist).toFixed(1)}px`);
      el.style.setProperty('--dy',`${(Math.sin(angle)*dist-4).toFixed(1)}px`);
      el.style.setProperty('--rot',`${Math.round(Math.random()*70-35)}deg`);
      el.style.setProperty('--spin',`${Math.round((Math.random()>.5?1:-1)*(35+Math.random()*65))}deg`);
      el.style.setProperty('--life',`${Math.round(820+Math.random()*220)}ms`);
      layer.appendChild(el);
      el.addEventListener('animationend',()=>el.remove(),{once:true});
    }
  }

  window.addEventListener('pointermove',e=>{
    const now=performance.now();
    const dist=Math.hypot(e.clientX-lastX,e.clientY-lastY);
    if(now-lastSpawn<58||dist<7)return;
    lastSpawn=now;lastX=e.clientX;lastY=e.clientY;
    spawn(e.clientX,e.clientY,false);
  },{passive:true});
  window.addEventListener('pointerdown',e=>spawn(e.clientX,e.clientY,true),{passive:true});
})();
