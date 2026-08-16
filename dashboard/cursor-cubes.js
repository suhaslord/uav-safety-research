(() => {
  const hero = document.querySelector('main .hero');
  const media = hero?.querySelector('.hero-media');
  if (!hero || !media) return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  if (window.matchMedia('(pointer: coarse)').matches) return;

  const field = document.createElement('div');
  field.className = 'cursor-cube-field';
  field.setAttribute('aria-hidden', 'true');
  media.appendChild(field);

  const COUNT = 34;
  const cubes = [];
  const pointer = { x: 0, y: 0, active: false };
  const rectState = { left: 0, top: 0, width: 1, height: 1 };

  function refreshRect() {
    const r = media.getBoundingClientRect();
    rectState.left = r.left;
    rectState.top = r.top;
    rectState.width = Math.max(1, r.width);
    rectState.height = Math.max(1, r.height);
  }

  for (let i = 0; i < COUNT; i += 1) {
    const el = document.createElement('span');
    el.className = 'cursor-cube';
    const size = 7 + Math.random() * 17;
    const x = Math.random();
    const y = Math.random();
    const drift = 7 + Math.random() * 16;
    const phase = Math.random() * Math.PI * 2;
    const speed = 0.00018 + Math.random() * 0.00034;
    el.style.setProperty('--cube-size', `${size.toFixed(1)}px`);
    el.style.setProperty('--cube-opacity', (0.12 + Math.random() * 0.20).toFixed(2));
    field.appendChild(el);
    cubes.push({ el, x, y, drift, phase, speed, size, vx: 0, vy: 0, rx: Math.random() * 360 });
  }

  refreshRect();
  window.addEventListener('resize', refreshRect, { passive: true });
  window.addEventListener('scroll', refreshRect, { passive: true });

  hero.addEventListener('pointerenter', (event) => {
    pointer.active = true;
    pointer.x = event.clientX - rectState.left;
    pointer.y = event.clientY - rectState.top;
  });
  hero.addEventListener('pointermove', (event) => {
    pointer.active = true;
    pointer.x = event.clientX - rectState.left;
    pointer.y = event.clientY - rectState.top;
  }, { passive: true });
  hero.addEventListener('pointerleave', () => { pointer.active = false; });

  function frame(now) {
    const w = rectState.width;
    const h = rectState.height;
    const radius = Math.min(250, Math.max(150, w * 0.19));

    for (let i = 0; i < cubes.length; i += 1) {
      const c = cubes[i];
      const baseX = c.x * w + Math.cos(now * c.speed + c.phase) * c.drift;
      const baseY = c.y * h + Math.sin(now * c.speed * 1.17 + c.phase) * c.drift;
      let targetX = baseX;
      let targetY = baseY;

      if (pointer.active) {
        const dx = baseX - pointer.x;
        const dy = baseY - pointer.y;
        const d = Math.max(1, Math.hypot(dx, dy));
        if (d < radius) {
          const strength = 1 - d / radius;
          const nx = dx / d;
          const ny = dy / d;
          const tangentX = -ny;
          const tangentY = nx;
          const swirl = 72 * strength * strength;
          const repel = 34 * strength;
          targetX += tangentX * swirl + nx * repel;
          targetY += tangentY * swirl + ny * repel;
          c.rx += 1.8 + strength * 5.2;
        } else {
          c.rx += 0.22;
        }
      } else {
        c.rx += 0.16;
      }

      c.vx += (targetX - (c._x ?? baseX)) * 0.045;
      c.vy += (targetY - (c._y ?? baseY)) * 0.045;
      c.vx *= 0.84;
      c.vy *= 0.84;
      c._x = (c._x ?? baseX) + c.vx;
      c._y = (c._y ?? baseY) + c.vy;

      c.el.style.transform = `translate3d(${(c._x - c.size / 2).toFixed(2)}px, ${(c._y - c.size / 2).toFixed(2)}px, 0) rotate(${c.rx.toFixed(2)}deg)`;
    }
    requestAnimationFrame(frame);
  }

  requestAnimationFrame(frame);
})();
