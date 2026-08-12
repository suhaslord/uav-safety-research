document.documentElement.classList.add("motion-ready");

const evidence = {
  phase9: {
    headSha: "33c5c73768757b508f5c613b2fba73f94e3fd5a6",
    runId: "31523496671",
    artifactId: "9114281248",
    artifactDigest: "bd2387f9518c7feb0bb5b8d7d02ccc7cbf416a73cd13e150ebeab06551b041a6",
    px4Sha: "d6f12ad1c4f70ad3230afd7d86e971421e02fef4",
    traceSha: "8e3dc7e20f471af08f9810bd7de865c25f844066ff88862cf1893e4617defc18",
    resultSha: "071d90896053c11204d7764342bb462dbb2a0dbd33270a6417a4f45b734f2c08",
    rawUlogSha: "b0f064cd28d4d790ec2315ea359762e8080a2a82188dea764ac791a03ece1389",
    rawCaptureSha: "f405969652ad8d158f23d41fa90088713f85720d5cb338a1c235bce8748d1e31",
    rows: 67,
    ulogDuration: 24.684,
    traceDuration: 21.78,
    paired: 25,
    visibleRate: 0.373134328358209,
    missRate: 0,
    fpRate: 0,
    lateralMae: 0.99761451215501,
    altitudeMae: 1.5202676288532118,
    pixelMae: 40.989067717870654,
    pixelP95: 113.79846544893583,
    aruco: 18,
    quad: 7
  },
  visible: [22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,43,46,47,48,49,50],
  aruco: [23,24,25,26,28,29,30,31,32,33,34,35,36,37,39,47,48,49],
  quad: [22,27,38,40,43,46,50],
  pose: [
    {t:7.36,x:0,y:0,z:.087},{t:8.68,x:0,y:0,z:.087},{t:10,x:0,y:0,z:.087},{t:11.32,x:0,y:0,z:.087},
    {t:12.64,x:0,y:0,z:.087},{t:13.632,x:0,y:0,z:.087},{t:14.952,x:.011,y:.12,z:.615},{t:16.272,x:.196,y:1.09,z:2.547},
    {t:17.592,x:1.182,y:-.481,z:2.489},{t:18.912,x:.199,y:-.517,z:2.134},{t:20.232,x:-.944,y:.276,z:1.502},
    {t:21.552,x:.597,y:.905,z:1.267},{t:22.872,x:.728,y:.068,z:1.07},{t:23.86,x:.348,y:-.14,z:.459},
    {t:25.18,x:.327,y:-.121,z:.087},{t:26.5,x:.327,y:-.121,z:.087},{t:27.82,x:.327,y:-.121,z:.087},{t:29.14,x:.327,y:-.121,z:.087}
  ]
};

const pct = (v, digits = 1) => `${(v * 100).toFixed(digits)}%`;
const clamp = (v, min = 0, max = 1) => Math.min(max, Math.max(min, v));
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const chartState = new Map();
let scrollTicking = false;

function populate() {
  const p = evidence.phase9;
  const values = {
    pairedFrames: `${p.paired}`,
    visibleRate: pct(p.visibleRate),
    missRate: pct(p.missRate),
    fpRate: pct(p.fpRate),
    lateralMae: `${p.lateralMae.toFixed(3)} m`,
    altitudeMae: `${p.altitudeMae.toFixed(3)} m`,
    pixelMae: `${p.pixelMae.toFixed(1)} px`,
    detectorMix: `${p.aruco} ArUco · ${p.quad} fixed quad fallback`,
    runRef: `#${p.runId}`,
    artifactRef: `#${p.artifactId}`
  };
  Object.entries(values).forEach(([id, value]) => {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  });

  const hashes = {
    headSha: p.headSha,
    artifactDigest: p.artifactDigest,
    px4Sha: p.px4Sha,
    traceSha: p.traceSha,
    resultSha: p.resultSha,
    rawUlogSha: p.rawUlogSha,
    rawCaptureSha: p.rawCaptureSha
  };
  Object.entries(hashes).forEach(([id, value]) => {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  });
}

function renderDetectionTrack() {
  const root = document.getElementById("detectionTrack");
  if (!root) return;
  const visible = new Set(evidence.visible);
  const aruco = new Set(evidence.aruco);
  const quad = new Set(evidence.quad);
  root.replaceChildren();
  for (let i = 0; i < evidence.phase9.rows; i += 1) {
    const cell = document.createElement("div");
    cell.className = "det-cell";
    cell.style.setProperty("--cell-delay", `${Math.min(i * 8, 420)}ms`);
    let state = "target not projected visible";
    if (visible.has(i)) { cell.classList.add("visible"); state = "visible + observed"; }
    if (aruco.has(i)) { cell.classList.add("aruco"); state = "visible · ArUco detector"; }
    if (quad.has(i)) { cell.classList.add("quad"); state = "visible · fixed quad fallback"; }
    cell.dataset.tip = `Frame ${i}: ${state}`;
    root.appendChild(cell);
  }
}

function fitCanvas(canvas) {
  const dpr = Math.max(1, window.devicePixelRatio || 1);
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(260, rect.width);
  const height = Math.max(160, rect.height);
  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);
  return {ctx, width, height};
}

function drawGrid(ctx, width, height, pad, rows = 4, cols = 4) {
  ctx.strokeStyle = "#e8e9ec";
  ctx.lineWidth = 1;
  for (let i = 0; i <= rows; i += 1) {
    const y = pad.t + (height - pad.t - pad.b) * i / rows;
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(width - pad.r, y); ctx.stroke();
  }
  for (let i = 0; i <= cols; i += 1) {
    const x = pad.l + (width - pad.l - pad.r) * i / cols;
    ctx.beginPath(); ctx.moveTo(x, pad.t); ctx.lineTo(x, height - pad.b); ctx.stroke();
  }
}

function strokePartial(ctx, points, progress, xFn, yFn) {
  if (!points.length || progress <= 0) return;
  const scaled = clamp(progress) * Math.max(0, points.length - 1);
  const whole = Math.floor(scaled);
  const frac = scaled - whole;
  ctx.beginPath();
  ctx.moveTo(xFn(points[0]), yFn(points[0]));
  for (let i = 1; i <= whole; i += 1) ctx.lineTo(xFn(points[i]), yFn(points[i]));
  if (whole < points.length - 1 && frac > 0) {
    const a = points[whole];
    const b = points[whole + 1];
    const partial = {};
    Object.keys(a).forEach(key => {
      if (typeof a[key] === "number" && typeof b[key] === "number") partial[key] = a[key] + (b[key] - a[key]) * frac;
    });
    ctx.lineTo(xFn(partial), yFn(partial));
  }
  ctx.stroke();
}

function renderPoseChart(progress = 1) {
  const canvas = document.getElementById("poseChart");
  if (!canvas) return;
  const {ctx, width, height} = fitCanvas(canvas);
  const pad = {l: 38, r: 14, t: 12, b: 26};
  drawGrid(ctx, width, height, pad, 4, 0);
  const ts = evidence.pose.map(p => p.t);
  const minT = Math.min(...ts);
  const maxT = Math.max(...ts);
  const minV = -1.2;
  const maxV = 2.8;
  const px = p => pad.l + (p.t - minT) / (maxT - minT) * (width - pad.l - pad.r);
  const pyFor = key => p => pad.t + (maxV - p[key]) / (maxV - minV) * (height - pad.t - pad.b);

  [["x", "#171a20"], ["y", "#5c5e62"], ["z", "#3e6ae1"]].forEach(([key, color]) => {
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    strokePartial(ctx, evidence.pose, progress, px, pyFor(key));
  });

  ctx.font = "11px -apple-system, BlinkMacSystemFont, Segoe UI, Arial, sans-serif";
  ctx.fillStyle = "#5c5e62";
  [minT, (minT + maxT) / 2, maxT].forEach(t => {
    const x = pad.l + (t - minT) / (maxT - minT) * (width - pad.l - pad.r);
    ctx.fillText(`${t.toFixed(1)}s`, x - 12, height - 7);
  });
  document.querySelector(".chart-frame")?.style.setProperty("--chart-dot-x", `${clamp(progress) * 100}%`);
}

function coveragePoints() {
  const seen = new Set(evidence.visible);
  let total = 0;
  return Array.from({length: evidence.phase9.rows}, (_, frame) => {
    if (seen.has(frame)) total += 1;
    return {frame, total};
  });
}

function renderCoverageChart(progress = 1) {
  const canvas = document.getElementById("coverageChart");
  if (!canvas) return;
  const {ctx, width, height} = fitCanvas(canvas);
  const pad = {l: 32, r: 12, t: 12, b: 24};
  drawGrid(ctx, width, height, pad, 4, 4);
  const points = coveragePoints();
  const px = p => pad.l + p.frame / (evidence.phase9.rows - 1) * (width - pad.l - pad.r);
  const py = p => pad.t + (evidence.phase9.paired - p.total) / evidence.phase9.paired * (height - pad.t - pad.b);
  ctx.strokeStyle = "#3e6ae1";
  ctx.lineWidth = 2.2;
  strokePartial(ctx, points, progress, px, py);
  ctx.font = "10px -apple-system, BlinkMacSystemFont, Segoe UI, Arial, sans-serif";
  ctx.fillStyle = "#5c5e62";
  ctx.fillText("0", pad.l - 3, height - 6);
  ctx.fillText("66", width - pad.r - 12, height - 6);
  ctx.fillText("25", 4, pad.t + 4);
}

function renderXYChart(progress = 1) {
  const canvas = document.getElementById("xyChart");
  if (!canvas) return;
  const {ctx, width, height} = fitCanvas(canvas);
  const pad = {l: 28, r: 16, t: 14, b: 24};
  drawGrid(ctx, width, height, pad, 4, 4);
  const xs = evidence.pose.map(p => p.x);
  const ys = evidence.pose.map(p => p.y);
  const minX = Math.min(...xs) - .15;
  const maxX = Math.max(...xs) + .15;
  const minY = Math.min(...ys) - .15;
  const maxY = Math.max(...ys) + .15;
  const px = p => pad.l + (p.x - minX) / (maxX - minX) * (width - pad.l - pad.r);
  const py = p => pad.t + (maxY - p.y) / (maxY - minY) * (height - pad.t - pad.b);
  ctx.strokeStyle = "#171a20";
  ctx.lineWidth = 2;
  strokePartial(ctx, evidence.pose, progress, px, py);
  const lastIndex = Math.max(0, Math.min(evidence.pose.length - 1, Math.floor(clamp(progress) * (evidence.pose.length - 1))));
  if (progress > 0) {
    const p = evidence.pose[lastIndex];
    ctx.fillStyle = "#3e6ae1";
    ctx.beginPath(); ctx.arc(px(p), py(p), 4, 0, Math.PI * 2); ctx.fill();
  }
  ctx.font = "10px -apple-system, BlinkMacSystemFont, Segoe UI, Arial, sans-serif";
  ctx.fillStyle = "#5c5e62";
  ctx.fillText("x", width - 14, height - 7);
  ctx.fillText("y", 7, 12);
}

function cadenceBins() {
  const seen = new Set(evidence.visible);
  return Array.from({length: 7}, (_, bin) => {
    const start = bin * 10;
    const end = Math.min(evidence.phase9.rows, start + 10);
    let count = 0;
    for (let i = start; i < end; i += 1) if (seen.has(i)) count += 1;
    return {start, end: end - 1, count};
  });
}

function renderCadenceChart(progress = 1) {
  const canvas = document.getElementById("cadenceChart");
  if (!canvas) return;
  const {ctx, width, height} = fitCanvas(canvas);
  const pad = {l: 22, r: 10, t: 12, b: 26};
  drawGrid(ctx, width, height, pad, 4, 0);
  const bins = cadenceBins();
  const innerW = width - pad.l - pad.r;
  const gap = 7;
  const barW = (innerW - gap * (bins.length - 1)) / bins.length;
  const maxCount = Math.max(1, ...bins.map(b => b.count));
  bins.forEach((bin, i) => {
    const h = (height - pad.t - pad.b) * (bin.count / maxCount) * clamp(progress);
    const x = pad.l + i * (barW + gap);
    const y = height - pad.b - h;
    ctx.fillStyle = bin.count ? "#3e6ae1" : "#d8dadd";
    ctx.fillRect(x, y, barW, h || 1);
    ctx.fillStyle = "#5c5e62";
    ctx.font = "9px -apple-system, BlinkMacSystemFont, Segoe UI, Arial, sans-serif";
    ctx.fillText(`${bin.start}`, x, height - 7);
  });
}

const chartRenderers = {
  poseChart: renderPoseChart,
  coverageChart: renderCoverageChart,
  xyChart: renderXYChart,
  cadenceChart: renderCadenceChart
};

function animateChart(id, renderer, duration = 900) {
  if (chartState.get(id) === 1) return;
  if (reducedMotion.matches) {
    chartState.set(id, 1);
    renderer(1);
    return;
  }
  const started = performance.now();
  const tick = now => {
    const raw = clamp((now - started) / duration);
    const eased = 1 - Math.pow(1 - raw, 3);
    chartState.set(id, eased);
    renderer(eased);
    if (raw < 1) requestAnimationFrame(tick);
    else chartState.set(id, 1);
  };
  requestAnimationFrame(tick);
}

function setupChartAnimations() {
  Object.entries(chartRenderers).forEach(([id, renderer]) => {
    chartState.set(id, 0);
    renderer(0);
  });
  if (reducedMotion.matches || !("IntersectionObserver" in window)) {
    Object.entries(chartRenderers).forEach(([id, renderer]) => animateChart(id, renderer, 1));
    return;
  }
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const canvas = entry.target.querySelector("canvas") || entry.target;
      const renderer = chartRenderers[canvas.id];
      if (renderer) animateChart(canvas.id, renderer, canvas.id === "poseChart" ? 1150 : 900);
      observer.unobserve(entry.target);
    });
  }, {threshold: .28, rootMargin: "0px 0px -8% 0px"});
  document.querySelectorAll(".telemetry-panel, .chart-frame").forEach(el => observer.observe(el));
}

async function refreshGithubStatus() {
  const label = document.getElementById("liveLabel");
  const meta = document.getElementById("liveMeta");
  const button = document.getElementById("refreshStatus");
  button?.classList.add("is-loading");
  if (label) label.textContent = "Audited evidence · checking current CI…";
  try {
    const res = await fetch("https://api.github.com/repos/suhaslord/uav-safety-research/actions/runs?branch=phase9-external-perception-validation&per_page=20", {headers: {Accept: "application/vnd.github+json"}});
    if (!res.ok) throw new Error(`GitHub ${res.status}`);
    const data = await res.json();
    const ci = (data.workflow_runs || []).find(run => run.name === "CI");
    const ciState = ci ? (ci.conclusion || ci.status) : "unavailable";
    if (label) label.textContent = ciState === "success" ? "Current CI green · evidence frozen" : `Current CI ${ciState} · evidence frozen`;
    if (meta) meta.textContent = `Current UI/analysis CI: ${ciState} · audited Phase 9 evidence: run #${evidence.phase9.runId}`;
  } catch {
    if (label) label.textContent = "Audited evidence snapshot";
    if (meta) meta.textContent = `Live CI unavailable · audited Phase 9 evidence: run #${evidence.phase9.runId}`;
  } finally {
    button?.classList.remove("is-loading");
  }
}

function updateScrollEffects() {
  scrollTicking = false;
  const header = document.getElementById("siteHeader");
  if (header) {
    header.classList.toggle("scrolled", window.scrollY > 24);
    const sampleY = Math.min(window.innerHeight - 1, header.offsetHeight + 8);
    const sample = document.elementFromPoint(Math.max(1, Math.min(window.innerWidth / 2, window.innerWidth - 2)), sampleY);
    const section = sample?.closest?.(".viewport-section");
    header.classList.toggle("on-dark", Boolean(section?.classList.contains("dark")));
  }

  const maxScroll = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
  document.documentElement.style.setProperty("--scroll-progress", `${clamp(window.scrollY / maxScroll) * 100}%`);

  const result = document.getElementById("result");
  if (result) {
    const rect = result.getBoundingClientRect();
    const local = clamp((window.innerHeight - rect.top) / (window.innerHeight + rect.height));
    document.getElementById("resultOrbit")?.style.setProperty("--orbit-angle", `${-28 + local * 118}deg`);
  }

  const timeline = document.getElementById("timeline");
  if (timeline) {
    const rect = timeline.getBoundingClientRect();
    const local = clamp((window.innerHeight * .55 - rect.top) / Math.max(1, rect.height));
    document.getElementById("timelineSignal")?.style.setProperty("--timeline-dot", `${local * 100}%`);
  }

  const geometry = document.getElementById("geometry");
  if (geometry) {
    const rect = geometry.getBoundingClientRect();
    const local = clamp((window.innerHeight - rect.top) / (window.innerHeight + rect.height));
    const beacon = document.getElementById("geometryBeacon");
    if (beacon) beacon.style.transform = `rotate(${local * 120}deg) translateY(${(local - .5) * 8}px)`;
  }
}

function requestScrollEffects() {
  if (scrollTicking) return;
  scrollTicking = true;
  requestAnimationFrame(updateScrollEffects);
}

function setupHeroParallax() {
  const media = document.getElementById("heroMedia");
  if (!media || reducedMotion.matches) return;
  media.addEventListener("pointermove", event => {
    if (event.pointerType === "touch") return;
    const rect = media.getBoundingClientRect();
    const nx = (event.clientX - rect.left) / rect.width - .5;
    const ny = (event.clientY - rect.top) / rect.height - .5;
    media.style.setProperty("--hero-x", `${nx * 18}px`);
    media.style.setProperty("--hero-y", `${ny * 18}px`);
  });
  media.addEventListener("pointerleave", () => {
    media.style.setProperty("--hero-x", "0px");
    media.style.setProperty("--hero-y", "0px");
  });
}

function addReveal(selector, baseDelay = 0, step = 0, extraClass = "") {
  document.querySelectorAll(selector).forEach((el, index) => {
    el.classList.add("reveal");
    if (extraClass) el.classList.add(extraClass);
    el.style.setProperty("--reveal-delay", `${baseDelay + index * step}ms`);
  });
}

function setupMotion() {
  addReveal(".hero-intro > div:first-child", 60, 0);
  addReveal(".hero-meta", 170, 0);
  addReveal(".hero-media", 90, 0, "reveal-media");
  addReveal(".hero-foot", 230, 0);
  addReveal("#result .section-copy", 0, 0);
  addReveal("#result .metric-item", 80, 70);
  addReveal("#availability .section-copy", 0, 0);
  addReveal("#availability .frame-visual", 100, 0);
  addReveal("#telemetry .section-copy", 0, 0);
  addReveal("#telemetry .telemetry-panel", 70, 75);
  addReveal("#telemetry .telemetry-note", 190, 0);
  addReveal("#geometry .section-copy", 0, 0);
  addReveal("#geometry .geometry-numbers > div", 70, 70);
  addReveal("#geometry .chart-frame", 170, 0);
  addReveal("#geometry > .caption", 210, 0);
  addReveal("#timeline .section-copy", 0, 0);
  addReveal("#timeline .timeline-list li", 60, 55);
  addReveal("#provenance .section-copy", 0, 0);
  addReveal("#provenance .provenance-table > div", 40, 35);
  addReveal("#provenance .provenance-actions", 130, 0);
  addReveal(".boundaries-section .boundary-copy", 0, 0);
  addReveal(".boundaries-section .boundary-list p", 70, 45);
  addReveal(".boundaries-section .boundary-actions", 160, 0);

  const items = [...document.querySelectorAll(".reveal")];
  if (reducedMotion.matches || !("IntersectionObserver" in window)) {
    items.forEach(el => el.classList.add("is-visible"));
    return;
  }

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add("is-visible");
      observer.unobserve(entry.target);
    });
  }, {threshold: 0.14, rootMargin: "0px 0px -7% 0px"});

  items.forEach(el => observer.observe(el));
}

function setupSectionNav() {
  const links = [...document.querySelectorAll(".site-nav a[href^='#']")];
  if (!links.length || !("IntersectionObserver" in window)) return;
  const targets = links
    .map(link => ({link, section: document.querySelector(link.getAttribute("href"))}))
    .filter(item => item.section);

  const observer = new IntersectionObserver(entries => {
    const visible = entries.filter(entry => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (!visible) return;
    targets.forEach(({link, section}) => {
      const active = section === visible.target;
      link.classList.toggle("is-active", active);
      if (active) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    });
  }, {threshold: [0.24, 0.45, 0.7], rootMargin: "-18% 0px -55% 0px"});

  targets.forEach(({section}) => observer.observe(section));
}

window.addEventListener("scroll", requestScrollEffects, {passive: true});
window.addEventListener("resize", () => {
  clearTimeout(window.__chartTimer);
  window.__chartTimer = setTimeout(() => {
    Object.entries(chartRenderers).forEach(([id, renderer]) => renderer(chartState.get(id) || 0));
    requestScrollEffects();
  }, 100);
});

window.addEventListener("DOMContentLoaded", () => {
  populate();
  renderDetectionTrack();
  refreshGithubStatus();
  setupMotion();
  setupChartAnimations();
  setupSectionNav();
  setupHeroParallax();
  updateScrollEffects();
  document.getElementById("refreshStatus")?.addEventListener("click", refreshGithubStatus);
});
