(()=>{
  function check(){
    const scene=document.querySelector('#phaseHero .hero-scene');
    if(!scene)return;
    const root=scene.getBoundingClientRect();
    const watched=[...scene.querySelectorAll('.scene-label,.scene-canvas,.scene-foot')];
    let overflow=0;
    for(const el of watched){
      const r=el.getBoundingClientRect();
      if(r.left<root.left-1||r.right>root.right+1||r.top<root.top-1||r.bottom>root.bottom+1)overflow++;
    }
    scene.dataset.qaFit=overflow===0?'pass':'fail';
    scene.dataset.qaOverflow=String(overflow);
    scene.dataset.qaSvgText=String(scene.querySelectorAll('svg text').length);
    scene.dataset.qaWidth=Math.round(root.width).toString();
    scene.dataset.qaHeight=Math.round(root.height).toString();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>requestAnimationFrame(()=>requestAnimationFrame(check)),{once:true});
  else requestAnimationFrame(()=>requestAnimationFrame(check));
  window.addEventListener('resize',()=>requestAnimationFrame(check),{passive:true});
})();
