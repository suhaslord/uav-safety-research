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

  const replaceExplainerWithNasa = ({ captionId, videoId, title, lead, copy, source }) => {
    const caption = document.getElementById(captionId);
    const figure = caption?.closest('.explainer-film');
    const original = figure?.querySelector('video');
    if (!caption || !figure || !original) return;

    const iframe = document.createElement('iframe');
    iframe.src = `https://www.youtube-nocookie.com/embed/${videoId}?rel=0`;
    iframe.title = title;
    iframe.loading = 'lazy';
    iframe.referrerPolicy = 'strict-origin-when-cross-origin';
    iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
    iframe.allowFullscreen = true;
    iframe.style.display = 'block';
    iframe.style.width = '100%';
    iframe.style.aspectRatio = '16 / 9';
    iframe.style.border = '0';
    iframe.style.borderRadius = '4px';
    iframe.style.background = '#f4f4f4';
    original.replaceWith(iframe);

    caption.innerHTML = `<strong>${lead}</strong> ${copy} <a href="${source}" target="_blank" rel="noreferrer">NASA source</a><span>NASA context only — not AegisLand experimental evidence.</span>`;
  };

  replaceExplainerWithNasa({
    captionId: 'uncertainty-caption',
    videoId: '0Kc01cV7vCU',
    title: 'NASA Safeguard System: An Assured Safety Net Technology for UAS',
    lead: 'NASA context: an independent safety net.',
    copy: 'NASA’s Safeguard work shows how separate safety logic can monitor a UAS for unsafe boundary behavior instead of relying only on the primary autonomy.',
    source: 'https://www.nasa.gov/wp-content/uploads/2022/08/sensor_solutions_508.pdf'
  });

  replaceExplainerWithNasa({
    captionId: 'evaluation-caption',
    videoId: 'cF2S81xmGr0',
    title: 'NASA Flight Test Series Provides a UAS Road Map',
    lead: 'NASA context: test before you trust.',
    copy: 'This NASA UAS flight-test video fits the evaluation section: define the test, collect evidence, and keep the result separate from the claim you want to make.',
    source: 'https://www.nasa.gov/wp-content/uploads/2022/08/sensor_solutions_508.pdf'
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

  if ('IntersectionObserver' in window) {
    const reveal = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        if (!motion.matches && entry.target.animate) {
          entry.target.animate([{ opacity: .6, transform: 'translateY(16px)' }, { opacity: 1, transform: 'translateY(0)' }], { duration: 550, easing: 'cubic-bezier(.2,.65,.3,1)' });
        }
        reveal.unobserve(entry.target);
      });
    }, { threshold: .12 });
    document.querySelectorAll('.chapter-heading, .section-head, .research-photo--inline, .method-visual-grid').forEach((element) => reveal.observe(element));
  }
})();
