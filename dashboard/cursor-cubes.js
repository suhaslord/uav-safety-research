(()=>{
  const hero=document.querySelector('main .hero');
  const media=hero?.querySelector('.hero-media');
  if(!hero||!media)return;
  if(window.matchMedia('(prefers-reduced-motion: reduce)').matches)return;
  if(window.matchMedia('(pointer: coarse)').matches)return;

  const field=document.createElement('div');
  field.className='cursor-cube-field';
  field.setAttribute('aria-hidden','true');
  media.appendChild(field);

  const VARIANTS=['wire','diamond','double','core','corner'];
  const COUNT=Math.max(30,Math.min(38,Math.round(window.innerWidth/50)));
  const rectState={width:1,height:1};
  const cubes=[];

  function seeded(i,k){
    const value=Math.sin((i+1)*12.9898+k*78.233)*43758.5453;
    return value-Math.floor(value);
  }
  function refreshRect(){
    const r=media.getBoundingClientRect();
    rectState.width=Math.max(1,r.width);
    rectState.height=Math.max(1,r.height);
  }
  refreshRect();

  for(let i=0;i<COUNT;i++){
    const el=document.createElement('span');
    const variant=VARIANTS[i%VARIANTS.length];
    el.className=`cursor-cube cursor-cube-${variant}`;
    const size=9+seeded(i,1)*14;
    const depth=.52+seeded(i,2)*.42;
    el.style.setProperty('--cube-size',`${size.toFixed(1)}px`);
    el.style.setProperty('--cube-depth',depth.toFixed(2));
    field.appendChild(el);
    cubes.push({
      el,size,depth,
      bx:.08+seeded(i,3)*.84,
      by:.10+seeded(i,4)*.78,
      phase:seeded(i,5)*Math.PI*2,
      speed:.18+seeded(i,6)*.34,
      driftX:7+seeded(i,7)*20,
      driftY:5+seeded(i,8)*15,
      rot:seeded(i,9)*360,
      rotSpeed:(seeded(i,10)>.5?1:-1)*(.08+seeded(i,11)*.28)
    });
  }

  window.addEventListener('resize',refreshRect,{passive:true});

  let last=performance.now();
  function frame(now){
    const dt=Math.min(34,Math.max(1,now-last))/16.667;
    last=now;
    const t=now/1000;
    for(const c of cubes){
      const x=c.bx*rectState.width+Math.cos(t*c.speed+c.phase)*c.driftX;
      const y=c.by*rectState.height+Math.sin(t*(c.speed*.86)+c.phase*1.21)*c.driftY;
      c.rot+=c.rotSpeed*dt;
      c.el.classList.remove('is-active');
      c.el.style.transform=`translate3d(${(x-c.size/2).toFixed(2)}px,${(y-c.size/2).toFixed(2)}px,0) rotate(${c.rot.toFixed(1)}deg) scale(${(.80+c.depth*.32).toFixed(2)})`;
    }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
})();
