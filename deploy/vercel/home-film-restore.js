/* Muted, in-view playback with native controls or an accessible pause switch.
   NASA footage is context only; it never presents itself as AegisLand data. */
(() => {
  'use strict';

  const films = [...document.querySelectorAll('[data-home-film]')];
  if (!films.length) return;
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const saveData = () => Boolean(navigator.connection && navigator.connection.saveData);
  const state = new WeakMap();

  for (const video of films) {
    const toggle = video.closest('.home-film-hero')?.querySelector('[data-film-toggle]');
    const filmState = { visible: false, manuallyPaused: false, request: 0 };
    state.set(video, filmState);
    video.muted = true;
    video.defaultMuted = true;
    video.playsInline = true;
    video.loop = true;
    video.preload = 'metadata';
    video.controls = !toggle;  // Native pause/seek always available on the secondary clip.

    const updateButton = () => {
      if (!toggle) return;
      const paused = video.paused;
      toggle.textContent = paused ? 'Play' : 'Pause';
      toggle.setAttribute('aria-label', paused ? 'Play aircraft footage' : 'Pause aircraft footage');
      toggle.setAttribute('aria-pressed', String(!paused));
    };

    const pause = () => {
      ++filmState.request;
      if (!video.paused) video.pause();
      updateButton();
    };

    const play = async (manual = false) => {
      if (!manual && (document.hidden || !filmState.visible || motion.matches || saveData() || filmState.manuallyPaused)) return;
      const request = ++filmState.request;
      try {
        await video.play();
        if (request !== filmState.request || document.hidden || !filmState.visible) video.pause();
      } catch {
        // Browser policies may restrict playback; keep an explicit play control.
        if (toggle) video.controls = true;
      }
      updateButton();
    };

    if (toggle) {
      if (video.id === '') video.id = 'aegis-feature-film';
      toggle.setAttribute('aria-controls', video.id);
      toggle.hidden = false;
      toggle.addEventListener('click', () => {
        if (video.paused) {
          filmState.manuallyPaused = false;
          void play(true);
        } else {
          filmState.manuallyPaused = true;
          pause();
        }
      });
    }

    video.addEventListener('play', updateButton);
    video.addEventListener('pause', updateButton);
    video.addEventListener('error', () => {
      video.controls = true;
      if (toggle) toggle.hidden = true;
    });
    updateButton();

    if ('IntersectionObserver' in window) {
      new IntersectionObserver(([entry]) => {
        filmState.visible = entry.isIntersecting && entry.intersectionRatio >= 0.2;
        if (!filmState.visible) pause();
        else void play();
      }, { threshold: [0, 0.2, 0.5] }).observe(video);
    } else {
      filmState.visible = true;
      void play();
    }
  }

  const sync = () => {
    for (const video of films) {
      const filmState = state.get(video);
      if (!filmState) continue;
      if (document.hidden || motion.matches || saveData()) {
        ++filmState.request;
        video.pause();
      } else if (filmState.visible && !filmState.manuallyPaused) {
        void video.play().catch(() => {
          video.controls = true;
        });
      }
    }
  };
  document.addEventListener('visibilitychange', sync);
  if (typeof motion.addEventListener === 'function') motion.addEventListener('change', sync);
  if (navigator.connection?.addEventListener) navigator.connection.addEventListener('change', sync);
})();
