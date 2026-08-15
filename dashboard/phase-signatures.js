(() => {
  const ORDER = ["phase1","phase2","phase3","phase4","phase5","phase6","phase6b","phase7","phase8","phase9","phase10"];
  const GOAL = "AegisLand studies how autonomous aerial systems can make safer decisions under uncertainty. Rather than chasing success alone, the research focuses on trustworthy perception, calibrated confidence, controlled abstention, and evidence you can inspect phase by phase.";

  const keyFromLocation = () => {
    const match = location.pathname.match(/\/(phase(?:1|2|3|4|5|6|6b|7|8|9|10))\/?$/i);
    return (document.body.dataset.phase || (match && match[1]) || "").toLowerCase();
  };

  const phaseLabels = {
    phase1: "Safety versus availability tradeoff",
    phase2: "Temporal filtering and hysteresis signal",
    phase3: "Dual-estimator disagreement and fusion",
    phase4: "Intentional research numbering gap",
    phase5: "Robustness sweep across degradation strength",
    phase6: "Image-to-control perception pipeline",
    phase6b: "Split lateral and altitude confidence",
    phase7: "External-validity factorial experiment matrix",
    phase8: "PX4/Gazebo trace-validation outcome board",
    phase9: "Camera detection versus metric geometry result",
    phase10: "Current frontier: frozen temporal metric perception and calibrated uncertainty"
  };

  const barRow = (label, value, text, accent = false) => `
    <div class="sig-bar-row${accent ? " accent" : ""}">
      <span>${label}</span>
      <i><b style="--v:${Math.max(0, Math.min(100, value))}%"></b></i>
      <strong>${text}</strong>
    </div>`;

  const matrixCells = () => Array.from({length: 20}, (_, i) => `<i class="sig-matrix-cell" style="--d:${i * 22}ms"></i>`).join("");

  const signatures = {
    phase1: () => `
      <div class="sig-head"><span>SAFETY / AVAILABILITY</span><strong>Mixed degradation</strong></div>
      <div class="sig-bars">
        ${barRow("Baseline unsafe",82.8,"82.8%")}
        ${barRow("V1 unsafe",0,"0%",true)}
        ${barRow("V1 abort",100,"100%")}
      </div>
      <div class="sig-caption">V1 prevented unsafe touchdowns by becoming unusably conservative.</div>`,

    phase2: () => `
      <div class="sig-head"><span>TEMPORAL STABILITY</span><strong>Risk over time</strong></div>
      <svg class="sig-signal" viewBox="0 0 420 250" aria-hidden="true">
        <line x1="18" y1="70" x2="402" y2="70" class="threshold severe"/>
        <line x1="18" y1="142" x2="402" y2="142" class="threshold hold"/>
        <polyline class="raw" points="18,184 42,128 66,176 90,76 114,156 138,60 162,134 186,118 210,160 234,94 258,116 282,82 306,130 330,106 354,122 378,98 402,114"/>
        <path class="filtered" pathLength="1" d="M18 176 C65 161 86 137 122 132 S184 118 216 122 S275 106 307 110 S364 108 402 112"/>
        <text x="24" y="62">ABORT</text><text x="24" y="134">HOLD</text>
      </svg>
      <div class="sig-legend"><span><i class="raw-dot"></i>instantaneous risk</span><span><i class="smooth-dot"></i>filtered risk</span></div>`,

    phase3: () => `
      <div class="sig-head"><span>DUAL-ESTIMATOR BREAKTHROUGH</span><strong>Independent error structure</strong></div>
      <div class="sig-fusion">
        <div class="sig-source visual"><small>01</small><strong>Vision</strong><span>biased stream</span></div>
        <div class="sig-source reference"><small>02</small><strong>Reference</strong><span>independent stream</span></div>
        <div class="sig-fusion-lines" aria-hidden="true"><i></i><i></i></div>
        <div class="sig-disagreement"><span>persistent</span><strong>Δ</strong><span>disagreement</span></div>
        <div class="sig-fused"><small>BIAS-AWARE</small><strong>Fused estimate</strong><span>97.6% mixed success</span></div>
      </div>`,

    phase4: () => `
      <div class="sig-head"><span>PROVENANCE MARKER</span><strong>No invented experiment</strong></div>
      <div class="sig-gap-rail">
        <div><i></i><span>V1</span></div><div><i></i><span>V2</span></div><div><i></i><span>V3</span></div>
        <div class="gap"><i></i><strong>—</strong><span>no Phase 4</span></div>
        <div><i></i><span>Phase 5</span></div>
      </div>
      <div class="sig-caption">The discontinuity is shown because it is part of the real archive.</div>`,

    phase5: () => `
      <div class="sig-head"><span>ROBUSTNESS EXPANSION</span><strong>Mixed degradation sweep</strong></div>
      <svg class="sig-stress" viewBox="0 0 430 250" aria-hidden="true">
        <g class="grid"><line x1="40" y1="34" x2="40" y2="205"/><line x1="40" y1="205" x2="410" y2="205"/><line x1="40" y1="120" x2="410" y2="120"/></g>
        <polyline pathLength="1" class="stress-line" points="40,48 114,54 188,52 262,50 336,58 410,64"/>
        <g class="stress-points"><circle cx="40" cy="48" r="4"/><circle cx="114" cy="54" r="4"/><circle cx="188" cy="52" r="4"/><circle cx="262" cy="50" r="4"/><circle cx="336" cy="58" r="4"/><circle cx="410" cy="64" r="4"/></g>
        <g class="stress-labels"><text x="34" y="226">0.6×</text><text x="105" y="226">0.8×</text><text x="180" y="226">1.0×</text><text x="253" y="226">1.2×</text><text x="327" y="226">1.4×</text><text x="400" y="226">1.6×</text></g>
      </svg>
      <div class="sig-statline"><span>V3 success</span><strong>99 → 92%</strong><span>as stress increased</span></div>`,

    phase6: () => `
      <div class="sig-head"><span>IMAGE PERCEPTION ENTERS THE LOOP</span><strong>Pixel → control</strong></div>
      <div class="sig-camera-pipeline">
        <div class="sig-camera-frame"><span class="pad"></span><span class="target-box"></span><small>96×96 image</small></div>
        <i class="sig-arrow">→</i>
        <div class="sig-pipeline-stack"><span>confidence</span><span>temporal track</span><span>velocity</span></div>
        <i class="sig-arrow">→</i>
        <div class="sig-controller"><small>AEGIS</small><strong>Controller</strong><span>landing</span></div>
      </div>
      <div class="sig-statline"><span>Mixed success</span><strong>63 → 92%</strong><span>image-only → image+Aegis</span></div>`,

    phase6b: () => `
      <div class="sig-head"><span>COMPONENT CONFIDENCE</span><strong>Mixed held-out selective audit</strong></div>
      <div class="sig-split">
        <div class="sig-confidence-lane"><span>Lateral coverage</span><i><b style="--v:96.6%"></b><em style="--gate:80%"></em></i><strong>96.6%</strong></div>
        <div class="sig-confidence-lane"><span>Altitude coverage</span><i><b style="--v:.85%"></b><em style="--gate:80%"></em></i><strong>0.85%</strong></div>
      </div>
      <div class="sig-gate"><span>Frozen component-confidence gate</span><strong>0.80 / 0.80</strong></div>
      <div class="sig-statline"><span>Mixed success</span><strong>57 → 94 → 99%</strong><span>image-only · P6 · P6B</span></div>`,

    phase7: () => `
      <div class="sig-head"><span>EXTERNAL-VALIDITY STRESS</span><strong>Factorial development design</strong></div>
      <div class="sig-matrix-wrap">
        <div class="sig-matrix-labels rows"><span>clean</span><span>low light</span><span>occlusion</span><span>mixed</span></div>
        <div class="sig-matrix">${matrixCells()}</div>
        <div class="sig-matrix-labels cols"><span>ind.</span><span>drift</span><span>bias</span><span>drop</span><span>latency</span></div>
        <strong class="sig-plants">× 2 plant models</strong>
      </div>
      <div class="sig-statline"><span>Design</span><strong>4 × 5 × 2</strong><span>40 condition/fault/plant cells</span></div>`,

    phase8: () => `
      <div class="sig-head"><span>PX4 / GAZEBO TRACE VALIDATION</span><strong>External resemblance result</strong></div>
      <div class="sig-outcome-board">
        <div><span>close</span><strong>1</strong><i style="--v:7%"></i></div>
        <div><span>watch</span><strong>2</strong><i style="--v:14%"></i></div>
        <div class="major"><span>mismatch</span><strong>9</strong><i style="--v:64%"></i></div>
        <div><span>insufficient</span><strong>14</strong><i style="--v:100%"></i></div>
      </div>
      <div class="sig-caption">Overall diagnostic: mismatch. The negative result stayed frozen.</div>`,

    phase9: () => `
      <div class="sig-head"><span>GENUINE CAMERA EVIDENCE</span><strong>Detection ≠ metric geometry</strong></div>
      <div class="sig-camera-geometry">
        <div class="sig-camera-result"><div class="mini-target"><i></i><b></b></div><span>visible → observed</span><strong>25 / 25</strong><small>0 false positives</small></div>
        <div class="sig-divider"></div>
        <div class="sig-geometry-result"><span>lateral MAE</span><strong>0.998 m</strong><span>altitude MAE</span><strong>1.520 m</strong></div>
      </div>
      <div class="sig-caption">The target was seen reliably on this trace; geometry remained the bottleneck.</div>`,

    phase10: () => `
      <div class="frontier-topline"><span>CURRENT FRONTIER</span><strong>FROZEN HOLDOUT</strong></div>
      <div class="frontier-core" aria-hidden="true">
        <span class="frontier-ring r1"></span><span class="frontier-ring r2"></span><span class="frontier-ring r3"></span>
        <svg class="frontier-trace" viewBox="0 0 260 260"><path pathLength="1" d="M28 180 C54 84 97 206 132 116 S201 61 234 108"/></svg>
        <span class="frontier-center"><small>AEGIS</small><strong>T10</strong></span>
      </div>
      <div class="frontier-metrics">
        <div><span>lateral normalized residual</span><strong>0.646</strong></div>
        <div><span>altitude normalized residual</span><strong>0.521</strong></div>
        <div><span>truth-visible observed</span><strong>15 / 20</strong></div>
        <div><span>point-error win gate</span><strong>not passed</strong></div>
      </div>
      <div class="frontier-foot"><span>Phase 9 uncertainty was overconfident</span><strong>Phase 10 made uncertainty substantially more honest.</strong></div>`
  };

  function goalBlock() {
    const section = document.createElement("section");
    section.className = "program-goal";
    section.setAttribute("aria-labelledby", "programGoalTitle");
    section.innerHTML = `
      <div class="program-goal-copy">
        <p class="kicker">Our goal</p>
        <h2 id="programGoalTitle">Make autonomous perception worthy of trust.</h2>
        <p>${GOAL}</p>
      </div>
      <div class="program-pillars" aria-label="AegisLand research priorities">
        <div><span>01</span><strong>Trust only when justified</strong></div>
        <div><span>02</span><strong>Detect uncertainty before unsafe action</strong></div>
        <div><span>03</span><strong>Preserve safety without hiding failures</strong></div>
        <div><span>04</span><strong>Show evidence phase by phase</strong></div>
      </div>`;
    return section;
  }

  function insertGoalAfter(anchor) {
    if (!anchor || document.querySelector(".program-goal")) return;
    anchor.insertAdjacentElement("afterend", goalBlock());
  }

  function enhancePhase() {
    const hero = document.getElementById("phaseHero");
    if (!hero) return false;
    const key = keyFromLocation();
    if (!signatures[key]) return true;

    document.body.dataset.signaturePhase = key;
    const object = hero.querySelector(".object");
    if (object) {
      object.className = `object signature-visual signature-${key}`;
      object.removeAttribute("aria-hidden");
      object.setAttribute("role", "img");
      object.setAttribute("aria-label", phaseLabels[key]);
      object.innerHTML = signatures[key]();
    }

    if (key === "phase10") {
      hero.classList.add("frontier-hero");
      const copy = hero.querySelector(".hero-copy");
      if (copy && !copy.querySelector(".frontier-badge")) {
        const badge = document.createElement("div");
        badge.className = "frontier-badge";
        badge.innerHTML = `<span>Current frontier</span><strong>Phase 10 · AegisT10</strong>`;
        copy.prepend(badge);
      }
    }

    insertGoalAfter(hero);
    return true;
  }

  function enhanceArchiveIndex() {
    const hero = document.querySelector(".index-hero");
    if (!hero) return false;
    insertGoalAfter(hero);
    document.querySelectorAll('.phase-link[href="/phases/phase10/"]').forEach(link => link.classList.add("frontier-link"));
    return true;
  }

  function enhanceMainCockpit() {
    if (document.getElementById("phaseHero") || document.querySelector(".index-hero")) return false;
    const hero = document.querySelector("main .hero.viewport-section");
    if (!hero) return false;
    insertGoalAfter(hero);
    return true;
  }

  function activate() {
    enhancePhase();
    enhanceArchiveIndex();
    enhanceMainCockpit();
    requestAnimationFrame(() => document.querySelector(".program-goal")?.classList.add("is-visible"));
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", activate, {once:true});
  else activate();
})();