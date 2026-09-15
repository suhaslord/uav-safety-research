(() => {
  'use strict';

  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');

  // Keep every live experiment panel on the current protected KIOS benchmark while
  // leaving the frozen historical phase records untouched.
  if (!document.querySelector('script[data-aegis-current-data]')) {
    const current = document.createElement('script');
    current.src = '/lab/current-data.js?v=1';
    current.dataset.aegisCurrentData = '';
    document.head.appendChild(current);
  }

  // The homepage intentionally uses NASA editorial context. Those images are normally
  // materialized into /media by the editorial-media fetch step. Direct Vercel/Git
  // previews do not always run that step, so use the canonical NASA originals as a
  // deterministic browser fallback instead of leaving broken image boxes.
  const nasaImageIds = {
    'phase01-context.jpg': 'ACD24-0180-005',
    'phase02-context.jpg': 'ACD24-0180-034',
    'acero-ground-control.jpg': 'ACD24-0180-009',
    'phase04-context.jpg': 'ACD24-0180-012',
    'phase05-context.jpg': 'ACD24-0180-001',
    'acero-uav-flight.jpg': 'ACD24-0180-035',
    'phase06b-context.jpg': 'ACD24-0180-036',
    'phase07-context.jpg': 'NHQ202105050027',
    'phase08-context.jpg': 'NHQ202105050015',
    'acero-uav-landing.jpg': 'ACD24-0180-037',
    'phase10-context.jpg': 'NHQ202105050020',
    'phase10r-context.jpg': 'NHQ202105050025',
    'stereo-uav-preflight.jpg': 'NHQ202105050002',
    'phase12-context.jpg': 'ACD24-0180-016',
    'phase13a-context.jpg': 'NHQ202105050026',
    'phase13b-context.jpg': 'ACD24-0180-022',
    'phase13c-context.jpg': 'ACD24-0180-023',
    'phase14-context.jpg': 'ACD24-0180-021',
    'phase15-context.jpg': 'ACD24-0180-002',
    'phase16-context.jpg': 'ACD24-0180-003',
    'phase17-context.jpg': 'ACD24-0180-004',
    'phase18-context.jpg': 'ACD24-0180-038',
    'phase19-context.jpg': 'ACD24-0180-006',
    'phase20-context.jpg': 'ACD24-0180-029',
    'phase21-context.jpg': 'ACD24-0180-033',
    'phase22-context.jpg': 'NHQ202105050014'
  };
  document.querySelectorAll('img[src^="/media/"]').forEach((image) => {
    const file = image.getAttribute('src').split('/').pop();
    const id = nasaImageIds[file];
    if (!id) return;
    const fallback = `https://images-assets.nasa.gov/image/${id}/${id}~orig.jpg`;
    image.addEventListener('error', () => {
      if (image.dataset.nasaFallbackApplied) return;
      image.dataset.nasaFallbackApplied = 'true';
      image.src = fallback;
    }, { once: true });
  });

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

  // Add the research-understanding layer requested in the September review:
  // block-level inputs/outputs, system handoffs, a plain-English test, and the
  // actual previous test inputs plus the current protected real-data result.
  const main = document.querySelector('main');
  const purpose = document.getElementById('purpose');
  if (main && !document.getElementById('understanding')) {
    const section = document.createElement('section');
    section.className = 'section';
    section.id = 'understanding';
    section.setAttribute('aria-labelledby', 'understanding-title');
    section.innerHTML = `
      <div class="wrap">
        <div class="section-head">
          <p class="eyebrow">Understand the system before making it more complicated</p>
          <div>
            <h2 id="understanding-title">Input → block → output → next block.</h2>
            <p class="copy">AegisLand now has two clearly separated evidence tracks: the earlier synthetic-image experiments and the current KIOS real-video detector benchmark. The old phase records stay frozen; new live experiments use the real dataset.</p>
          </div>
        </div>
        <div class="evidence-list" aria-label="Block-level project explanation">
          <div class="evidence-item"><span>1 · Camera / image source</span><strong>Before: generated 96×96 landing-pad images. Now: KIOS real-video landing-pad frames.</strong></div>
          <div class="evidence-item"><span>2 · Controlled degradation</span><strong>Input: protected real test frame → Output: clean, blur, low-light, noise, occlusion, or mixed condition.</strong></div>
          <div class="evidence-item"><span>3 · Perception model</span><strong>Before: threshold + weighted centroid. Now: YOLO11n landing-pad detector trained only on the development split.</strong></div>
          <div class="evidence-item"><span>4 · Protected split</span><strong>252 train + 64 validation + 20 embargoed + 86 protected test frames.</strong></div>
          <div class="evidence-item"><span>5 · Evaluation</span><strong>Precision, recall, mAP50, and mAP50–95 on the protected real test frames.</strong></div>
          <div class="evidence-item"><span>6 · Evidence boundary</span><strong>Current results are perception benchmarks, not real-flight safety or certification evidence.</strong></div>
        </div>

        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:20px;margin-top:32px">
          <figure class="research-photo" style="margin:0">
            <div style="padding:16px;border:1px solid #e2e3e5;border-radius:8px;background:#fff">
              <div style="font:700 13px Arial,Helvetica,sans-serif;margin-bottom:12px">BEFORE · ACTUAL SYNTHETIC TEST INPUTS</div>
              <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:6px">
                <img src="https://raw.githubusercontent.com/suhaslord/uav-safety-research/main/docs/assets/readme/dataset/clean.png" alt="Old clean synthetic landing-pad test image" loading="lazy" decoding="async" style="width:100%;aspect-ratio:1;object-fit:cover;border-radius:4px">
                <img src="https://raw.githubusercontent.com/suhaslord/uav-safety-research/main/docs/assets/readme/dataset/blur.png" alt="Old blur synthetic landing-pad test image" loading="lazy" decoding="async" style="width:100%;aspect-ratio:1;object-fit:cover;border-radius:4px">
                <img src="https://raw.githubusercontent.com/suhaslord/uav-safety-research/main/docs/assets/readme/dataset/low_light.png" alt="Old low-light synthetic landing-pad test image" loading="lazy" decoding="async" style="width:100%;aspect-ratio:1;object-fit:cover;border-radius:4px">
                <img src="https://raw.githubusercontent.com/suhaslord/uav-safety-research/main/docs/assets/readme/dataset/occlusion.png" alt="Old occlusion synthetic landing-pad test image" loading="lazy" decoding="async" style="width:100%;aspect-ratio:1;object-fit:cover;border-radius:4px">
                <img src="https://raw.githubusercontent.com/suhaslord/uav-safety-research/main/docs/assets/readme/dataset/mixed.png" alt="Old mixed synthetic landing-pad test image" loading="lazy" decoding="async" style="width:100%;aspect-ratio:1;object-fit:cover;border-radius:4px">
              </div>
              <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:6px;margin-top:6px;font:600 10px Arial,Helvetica,sans-serif;color:#666;text-align:center"><span>Clean</span><span>Blur</span><span>Low light</span><span>Occlusion</span><span>Mixed</span></div>
            </div>
            <figcaption><span class="research-photo__context">The exact synthetic image conditions used in the earlier pixel benchmark</span><span class="research-photo__credit">Historical evidence only — these are no longer the active dataset.</span></figcaption>
          </figure>

          <figure class="research-photo" style="margin:0">
            <div style="padding:16px;border:1px solid #e2e3e5;border-radius:8px;background:#fff">
              <div style="font:700 13px Arial,Helvetica,sans-serif;margin-bottom:5px">NOW · ACTUAL KIOS PROTECTED TEST</div>
              <div style="font:12px Arial,Helvetica,sans-serif;color:#666;margin-bottom:12px">86 held-out real-video frames · same frames across every stress condition</div>
              <table style="width:100%;border-collapse:collapse;font:12px Arial,Helvetica,sans-serif">
                <thead><tr><th style="text-align:left;padding:7px 5px;border-bottom:1px solid #ddd">Condition</th><th style="text-align:right;padding:7px 5px;border-bottom:1px solid #ddd">Precision</th><th style="text-align:right;padding:7px 5px;border-bottom:1px solid #ddd">Recall</th><th style="text-align:right;padding:7px 5px;border-bottom:1px solid #ddd">mAP50</th></tr></thead>
                <tbody>
                  <tr><td style="padding:7px 5px">Clean</td><td style="text-align:right">0.796</td><td style="text-align:right">0.384</td><td style="text-align:right">0.427</td></tr>
                  <tr><td style="padding:7px 5px">Blur</td><td style="text-align:right">0.844</td><td style="text-align:right">0.378</td><td style="text-align:right">0.413</td></tr>
                  <tr><td style="padding:7px 5px">Low light</td><td style="text-align:right">0.787</td><td style="text-align:right">0.372</td><td style="text-align:right">0.417</td></tr>
                  <tr><td style="padding:7px 5px">Noise</td><td style="text-align:right">0.895</td><td style="text-align:right">0.398</td><td style="text-align:right">0.433</td></tr>
                  <tr><td style="padding:7px 5px">Occlusion</td><td style="text-align:right">0.622</td><td style="text-align:right">0.326</td><td style="text-align:right">0.348</td></tr>
                  <tr><td style="padding:7px 5px;font-weight:700">Mixed</td><td style="text-align:right;font-weight:700">0.597</td><td style="text-align:right;font-weight:700">0.186</td><td style="text-align:right;font-weight:700">0.185</td></tr>
                </tbody>
              </table>
            </div>
            <figcaption><span class="research-photo__context">Current real-image detector benchmark</span><span class="research-photo__credit">KIOS real-video subset · temporal split · 86 protected test frames · mixed degradation is the main failure.</span></figcaption>
          </figure>
        </div>

        <div class="research-alert" role="note" style="margin-top:32px">
          <div class="research-alert__label">Non-technical understanding test</div>
          <p>If someone who does not know image processing or computer vision asks what the project does, the explanation should still make sense. If a block cannot be explained simply without hiding behind “AI” or “the algorithm,” it needs better documentation first.</p>
          <a href="https://github.com/suhaslord/uav-safety-research#plain-english-explanation" target="_blank" rel="noreferrer">Read the block-by-block README →</a>
        </div>
      </div>`;
    if (purpose) purpose.before(section);
    else main.append(section);

    const desktopNav = document.querySelector('.site-nav');
    if (desktopNav && !desktopNav.querySelector('a[href="#understanding"]')) {
      const link = document.createElement('a');
      link.href = '#understanding';
      link.textContent = 'System';
      desktopNav.append(link);
    }
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