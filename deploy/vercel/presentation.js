(() => {
  'use strict';

  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const film = document.getElementById('researchFilm');
  const toggle = document.getElementById('filmToggle');
  const error = document.getElementById('filmError');
  if (film && toggle) {
    let loaded = false;
    let visible = false;
    let manualPause = false;
    let failed = false;
    let playbackRequest = 0;
    const automatic = () => !motion.matches && !navigator.connection?.saveData && window.matchMedia('(min-width: 901px)').matches;
    const sync = () => { toggle.textContent = film.paused ? 'Play video' : 'Pause video'; };
    const play = async () => {
      if (failed) return;
      const request = ++playbackRequest;
      if (!loaded) {
        const source = film.querySelector('source');
        source.src = source.dataset.src;
        loaded = true;
        film.load();
      }
      try {
        await film.play();
        if (request !== playbackRequest || document.hidden || !visible) film.pause();
      } catch { sync(); }
    };
    const pause = () => { playbackRequest += 1; film.pause(); sync(); };
    toggle.hidden = false;
    toggle.addEventListener('click', () => {
      if (film.paused) { manualPause = false; play(); }
      else { manualPause = true; pause(); }
    });
    film.addEventListener('play', sync);
    film.addEventListener('pause', sync);
    const unavailable = () => {
      failed = true;
      pause();
      error.hidden = false;
      toggle.hidden = true;
    };
    film.addEventListener('error', unavailable);
    film.querySelector('source').addEventListener('error', unavailable);
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(([entry]) => {
        visible = entry.isIntersecting;
        if (!visible) pause();
        else if (automatic() && !manualPause && !document.hidden) play();
      }, { threshold: .25 }).observe(film);
    } else { visible = true; }
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) pause();
      else if (visible && automatic() && !manualPause) play();
    });
    motion.addEventListener('change', () => { if (motion.matches) pause(); });
  }

  document.querySelectorAll('.explainer-film video').forEach((video,index)=>{
    const frame=document.createElement('div');frame.className='nasa-film-frame';video.before(frame);frame.append(video);
    video.id ||= `nasa-film-${index}`;video.controls=false;video.loop=true;
    const button=document.createElement('button');button.type='button';button.className='film-toggle';button.setAttribute('aria-controls',video.id);frame.append(button);
    const options=document.createElement('details');options.className='nasa-player-options';options.innerHTML='<summary>Playback options</summary><label><input type="checkbox"> Show timeline and fullscreen controls</label>';frame.after(options);
    options.querySelector('input').onchange=e=>{video.controls=e.target.checked;frame.classList.toggle('native-controls',video.controls);};
    let visible=false,manualPause=false,request=0;
    const label=()=>button.textContent=video.paused?'Play video':'Pause video';
    const pause=()=>{request++;video.pause();label();};
    const play=async()=>{const id=++request;button.textContent='Loading…';try{await video.play();if(id!==request||!visible||document.hidden)video.pause();}catch{}label();};
    const sync=()=>{if(!visible||document.hidden){pause();return;}if(!manualPause&&!motion.matches&&!navigator.connection?.saveData)play();};
    button.onclick=()=>{if(video.paused){manualPause=false;play();}else{manualPause=true;pause();}};
    video.addEventListener('play',label);video.addEventListener('pause',label);label();
    if('IntersectionObserver' in window)new IntersectionObserver(([entry])=>{visible=entry.isIntersecting;sync();},{threshold:.25}).observe(video);else visible=true;
    document.addEventListener('visibilitychange',sync);motion.addEventListener('change',()=>{if(motion.matches)pause();else sync();});
    const message=document.createElement('p');message.hidden=true;message.setAttribute('role','status');message.textContent='Video unavailable. Use the NASA source link below to view the original.';frame.after(message);video.addEventListener('error',()=>{message.hidden=false;button.hidden=true;});
  });

  const track = document.getElementById('chapterTrack');
  if (track) {
    const cards = [...track.querySelectorAll('.chapter-card')];
    const previous = document.getElementById('chapterPrev');
    const next = document.getElementById('chapterNext');
    const position = document.getElementById('chapterPosition');
    document.getElementById('chapterControls').hidden = false;
    let current = 0;
    let scheduled = false;
    const update = () => {
      const left = track.getBoundingClientRect().left + parseFloat(getComputedStyle(track).paddingLeft);
      current = cards.reduce((best, card, index) => Math.abs(card.getBoundingClientRect().left - left) < Math.abs(cards[best].getBoundingClientRect().left - left) ? index : best, 0);
      previous.disabled = current === 0;
      next.disabled = current === cards.length - 1;
      position.textContent = `${current + 1} / ${cards.length}`;
      scheduled = false;
    };
    const go = (index) => {
      const target = cards[Math.max(0, Math.min(cards.length - 1, index))];
      const left = target.getBoundingClientRect().left - track.getBoundingClientRect().left - parseFloat(getComputedStyle(track).paddingLeft);
      track.scrollBy({ left, behavior: motion.matches ? 'auto' : 'smooth' });
    };
    previous.addEventListener('click', () => go(current - 1));
    next.addEventListener('click', () => go(current + 1));
    track.addEventListener('scroll', () => {
      if (!scheduled) { scheduled = true; requestAnimationFrame(update); }
    }, { passive: true });
    track.addEventListener('keydown', (event) => {
      if (event.target !== track) return;
      if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
        event.preventDefault();
        go(current + (event.key === 'ArrowRight' ? 1 : -1));
      }
    });
    window.addEventListener('resize', update, { passive: true });
    update();
  }

  // The photo recedes as the visitor leaves the opening scene. Native scrolling stays intact.
  const hero=document.querySelector('#top'), photo=hero?.querySelector('.research-photo img');
  let pending=false;
  const frame=()=>{
    pending=false;if(!hero||!photo)return;
    const progress=Math.max(0,Math.min(1,-hero.getBoundingClientRect().top/hero.offsetHeight));
    photo.style.transform=motion.matches?'none':`scale(${1.025-progress*.025}) translateY(${progress*24}px)`;
  };
  if(hero&&photo){
    addEventListener('scroll',()=>{if(!pending){pending=true;requestAnimationFrame(frame);}},{passive:true});
    motion.addEventListener('change',frame);frame();
  }
})();
