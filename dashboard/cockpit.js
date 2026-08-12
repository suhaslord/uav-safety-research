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
    let state = "target not projected visible";
    if (visible.has(i)) { cell.classList.add("visible"); state = "visible + observed"; }
    if (aruco.has(i)) { cell.classList.add("aruco"); state = "visible · ArUco detector"; }
    if (quad.has(i)) { cell.classList.add("quad"); state = "visible · fixed quad fallback"; }
    cell.dataset.tip = `Frame ${i}: ${state}`;
    root.appendChild(cell);
  }
}

function renderPoseChart() {
  const canvas = document.getElementById("poseChart");
  if (!canvas) return;
  const dpr = Math.max(1, window.devicePixelRatio || 1);
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(320, rect.width);
  const height = Math.max(180, rect.height);
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);

  const pad = {l: 38, r: 14, t: 12, b: 26};
  const iw = width - pad.l - pad.r;
  const ih = height - pad.t - pad.b;
  const ts = evidence.pose.map(p => p.t);
  const minT = Math.min(...ts);
  const maxT = Math.max(...ts);
  const minV = -1.2;
  const maxV = 2.8;
  const px = t => pad.l + (t - minT) / (maxT - minT) * iw;
  const py = v => pad.t + (maxV - v) / (maxV - minV) * ih;

  ctx.strokeStyle = "#eeeeee";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i += 1) {
    const y = pad.t + ih * i / 4;
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(width - pad.r, y); ctx.stroke();
  }

  const series = [["x", "#171a20"], ["y", "#5c5e62"], ["z", "#3e6ae1"]];
  for (const [key, color] of series) {
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    evidence.pose.forEach((p, i) => {
      const x = px(p.t), y = py(p[key]);
      if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y);
    });
    ctx.stroke();
  }

  ctx.font = "11px -apple-system, BlinkMacSystemFont, Segoe UI, Arial, sans-serif";
  ctx.fillStyle = "#8e8e8e";
  [minT, (minT + maxT) / 2, maxT].forEach(t => ctx.fillText(`${t.toFixed(1)}s`, px(t) - 12, height - 7));
}

async function refreshGithubStatus() {
  const label = document.getElementById("liveLabel");
  const meta = document.getElementById("liveMeta");
  if (label) label.textContent = "Checking GitHub…";
  try {
    const res = await fetch("https://api.github.com/repos/suhaslord/uav-safety-research/actions/runs?branch=phase9-external-perception-validation&per_page=30", {headers: {Accept: "application/vnd.github+json"}});
    if (!res.ok) throw new Error(`GitHub ${res.status}`);
    const data = await res.json();
    const wanted = ["CI", "Phase 9 Perception Validation", "Phase 9 Gazebo Camera Evidence"];
    const latest = {};
    for (const run of data.workflow_runs || []) if (wanted.includes(run.name) && !latest[run.name]) latest[run.name] = run;
    const vals = Object.values(latest);
    const allGreen = vals.length === 3 && vals.every(r => r.conclusion === "success");
    if (label) label.textContent = allGreen ? "Latest workflows green" : "Mixed workflow status";
    if (meta) meta.textContent = vals.length ? vals.map(r => `${r.name.replace("Phase 9 ", "P9 ")}: ${r.conclusion || r.status}`).join(" · ") : "Audited snapshot";
  } catch {
    if (label) label.textContent = "Audited snapshot";
    if (meta) meta.textContent = "Live GitHub refresh unavailable · frozen evidence shown";
  }
}

function updateHeader() {
  document.getElementById("siteHeader")?.classList.toggle("scrolled", window.scrollY > 24);
}

window.addEventListener("scroll", updateHeader, {passive: true});
window.addEventListener("resize", () => { clearTimeout(window.__poseTimer); window.__poseTimer = setTimeout(renderPoseChart, 90); });
window.addEventListener("DOMContentLoaded", () => {
  populate();
  renderDetectionTrack();
  renderPoseChart();
  refreshGithubStatus();
  updateHeader();
  document.getElementById("refreshStatus")?.addEventListener("click", refreshGithubStatus);
});
