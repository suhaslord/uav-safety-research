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

  const VARIANTS = ['wire', 'diamond', 'double', 'core', 'corner'];
  const COUNT = Math.max(36, Math.min(48, Math.round(window.innerWidth / 42)));
  const cubes = [];
  const pointer = { x: 0, y: 0, active: false };
  const anchor = { x: 0, y: 0, vx: 0, vy: 0 };
  const rectState = { left: 0, top: 0, width: 1, height: 1 };

  function seeded(i, k) {
    const value = Math.sin((i + 1) * 12.9898 + k * 78.233) * 43758.5453;
    return value - Math.floor(value);
  }

  function refreshRect() {
    const r = media.getBoundingClientRect();
    rectState.left = r.left;
    rectState.top = r.top;
    rectState.width = Math.max(1, r.width);
    rectState.height = Math.max(1, r.height);
    if (!pointer.active && anchor.x === 0 && anchor.y === 0) {
      anchor.x = rectState.width * 0.66;
      anchor.y = rectState.height * 0.50;
    }
  }

  refreshRect();

  for (let i = 0; i < COUNT; i += 1) {
    const el = document.createElement('span');
    const variant = VARIANTS[i % VARIANTS.length];
    el.className = `cursor-cube cursor-cube-${variant}`;

    const size = 9 + seeded(i, 1) * 17;
    const orbitRadius = 42 + seeded(i, 2) * Math.min(250, rectState.width * 0.22);
    const orbitAngle = seeded(i, 3) * Math.PI * 2;
    const direction = seeded(i, 4) > 0.5 ? 1 : -1;
    const orbitSpeed = direction * (0.00135 + seeded(i, 5) * 0.00225);
    const ellipse = 0.48 + seeded(i, 6) * 0.40;
    const wobble = 4 + seeded(i, 7) * 18;
    const phase = seeded(i, 8) * Math.PI * 2;
    const tilt = (seeded(i, 9) - 0.5) * 0.75;
    const rotSpeed = (0.12 + seeded(i, 10) * 0.75) * direction;
    const depth = 0.52 + seeded(i, 11) * 0.48;

    el.style.setProperty('--cube-size', `${size.toFixed(1)}px`);
    el.style.setProperty('--cube-depth', depth.toFixed(2));
    field.appendChild(el);

    cubes.push({
      el,
      size,
      orbitRadius,
      orbitAngle,
      orbitSpeed,
      ellipse,
      wobble,
      phase,
      tilt,
      rot: seeded(i, 12) * 360,
      rotSpeed,
      x: rectState.width * 0.66,
      y: rectState.height * 0.50,
      vx: 0,
      vy: 0,
      depth
    });
  }

  function setPointer(event) {
    refreshRect();
    pointer.active = true;
    pointer.x = event.clientX - rectState.left;
    pointer.y = event.clientY - rectState.top;
    field.style.setProperty('--cursor-x', `${pointer.x}px`);
    field.style.setProperty('--cursor-y', `${pointer.y}px`);
    field.style.setProperty('--cursor-active', '1');
  }

  hero.addEventListener('pointerenter', setPointer, { passive: true });
  hero.addEventListener('pointermove', setPointer, { passive: true });
  hero.addEventListener('pointerleave', () => {
    pointer.active = false;
    field.style.setProperty('--cursor-active', '0');
  }, { passive: true });
  window.addEventListener('resize', refreshRect, { passive: true });
  window.addEventListener('scroll', refreshRect, { passive: true });

  let last = performance.now();
  function frame(now) {
    const dt = Math.min(34, now - last);
    last = now;
    const step = dt / 16.667;
    const t = now * 0.001;

    const desiredX = pointer.active ? pointer.x : rectState.width * 0.66;
    const desiredY = pointer.active ? pointer.y : rectState.height * 0.50;

    anchor.vx += (desiredX - anchor.x) * 0.035 * step;
    anchor.vy += (desiredY - anchor.y) * 0.035 * step;
    anchor.vx *= Math.pow(pointer.active ? 0.70 : 0.78, step);
    anchor.vy *= Math.pow(pointer.active ? 0.70 : 0.78, step);
    anchor.x += anchor.vx * step;
    anchor.y += anchor.vy * step;

    for (let i = 0; i < cubes.length; i += 1) {
      const c = cubes[i];
      c.orbitAngle += c.orbitSpeed * dt;

      const pulse = Math.sin(t * (0.72 + c.depth * 0.54) + c.phase);
      const radius = c.orbitRadius + pulse * c.wobble;
      const a = c.orbitAngle;
      const cosA = Math.cos(a);
      const sinA = Math.sin(a);

      const rawX = cosA * radius;
      const rawY = sinA * radius * c.ellipse;
      const tiltCos = Math.cos(c.tilt);
      const tiltSin = Math.sin(c.tilt);
      const orbitX = rawX * tiltCos - rawY * tiltSin;
      const orbitY = rawX * tiltSin + rawY * tiltCos;

      const microX = Math.cos(t * 1.15 + c.phase * 1.7) * (3 + c.depth * 7);
      const microY = Math.sin(t * 1.03 + c.phase * 1.3) * (2 + c.depth * 6);
      const targetX = anchor.x + orbitX + microX;
      const targetY = anchor.y + orbitY + microY;

      const spring = pointer.active ? 0.085 : 0.050;
      c.vx += (targetX - c.x) * spring * step;
      c.vy += (targetY - c.y) * spring * step;
      c.vx *= Math.pow(pointer.active ? 0.72 : 0.80, step);
      c.vy *= Math.pow(pointer.active ? 0.72 : 0.80, step);
      c.x += c.vx * step;
      c.y += c.vy * step;
      c.rot += c.rotSpeed * (pointer.active ? 2.2 : 0.9) * step;

      const distance = Math.hypot(c.x - anchor.x, c.y - anchor.y);
      const activeRadius = Math.min(265, rectState.width * 0.25);
      c.el.classList.toggle('is-active', pointer.active && distance < activeRadius);
      c.el.style.transform = `translate3d(${(c.x - c.size / 2).toFixed(2)}px, ${(c.y - c.size / 2).toFixed(2)}px, 0) rotate(${c.rot.toFixed(1)}deg) scale(${(0.78 + c.depth * 0.38).toFixed(2)})`;
    }

    requestAnimationFrame(frame);
  }

  requestAnimationFrame(frame);
})();
